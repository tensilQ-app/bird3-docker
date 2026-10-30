#!/usr/bin/env python3
"""Select a stable CZ.NIC release and archive its signature-verified Git sources."""
import argparse
import gzip
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request
from urllib.parse import urlsplit

PAGE = 'https://bird.nic.cz/get-bird/'
GIT = 'https://gitlab.nic.cz/labs/bird.git'
FINGERPRINT = '6EFA4F8288F022C523505F30BA756F665CB418E2'
VERSION = re.compile(r'3\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)')

class OfficialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def check_url(url):
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname not in {'bird.nic.cz', 'gitlab.nic.cz', 'pkg.labs.nic.cz'} or p.username or p.password:
        raise ValueError(f'Unexpected source URL: {url}')

def stable_versions(page):
    text = html.unescape(re.sub(r'<[^>]*>', ' ', page))
    return {v for v in re.findall(r'BIRD\s+(3\.[0-9]+\.[0-9]+)\s*\(', text) if VERSION.fullmatch(v)}

def run(*args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--version', default='')
    p.add_argument('--download', default='bird.tar.gz')
    p.add_argument('--output', default='')
    args = p.parse_args()
    with urllib.request.build_opener(OfficialRedirect()).open(PAGE, timeout=60) as response:
        check_url(response.url)
        versions = stable_versions(response.read().decode())
    if not versions:
        raise RuntimeError('No stable BIRD 3 releases on the official release page')
    latest = max(versions, key=lambda v: tuple(map(int, v.split('.'))))
    version = args.version or latest
    if version not in versions:
        raise ValueError(f'{version!r} is not an officially listed stable release')
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / 'source'
        home = Path(tmp) / 'gnupg'
        home.mkdir(mode=0o700)
        env = dict(os.environ, GNUPGHOME=str(home))
        key = Path(__file__).resolve().parents[1] / 'keys/bird-release.asc'
        listing = run('gpg', '--batch', '--with-colons', '--show-keys', str(key), env=env)
        fingerprints = [s.split(':')[9] for s in listing.splitlines() if s.startswith('fpr:')]
        if not fingerprints or fingerprints[0] != FINGERPRINT:
            raise RuntimeError('Unexpected release key fingerprint')
        run('gpg', '--batch', '--dearmor', '--output', str(home / 'release.gpg'), str(key), env=env)
        (home / 'gpg.conf').write_text(f'no-default-keyring\nkeyring {home / "release.gpg"}\nno-autostart\n')
        run('git', 'init', '-q', str(repo))
        tag = f'v{version}'
        run('git', '-C', str(repo), '-c', 'http.followRedirects=false', 'fetch', '--depth=1', GIT, f'refs/tags/{tag}:refs/tags/{tag}')
        verified = subprocess.run(['git', '-C', str(repo), 'verify-tag', '--raw', tag], env=env, capture_output=True, text=True, check=True)
        if not any(line.startswith('[GNUPG:] VALIDSIG ') and (line.split()[2] == FINGERPRINT or line.split()[-1] == FINGERPRINT) for line in verified.stderr.splitlines()):
            raise RuntimeError('Tag is not signed by the pinned BIRD release key')
        commit = run('git', '-C', str(repo), 'rev-parse', f'{tag}^{{commit}}')
        if run('git', '-C', str(repo), 'show', f'{tag}:VERSION') != version:
            raise RuntimeError('Signed VERSION does not match the release')
        raw = subprocess.check_output(['git', '-C', str(repo), 'archive', '--format=tar', f'--prefix=bird-{version}/', f'{tag}^{{commit}}'])
        archive = gzip.compress(raw, mtime=0)
    Path(args.download).write_bytes(archive)
    values = {'version': version, 'latest': latest, 'sha256': hashlib.sha256(archive).hexdigest(), 'commit': commit, 'signer': FINGERPRINT}
    Path('source.json').write_text(json.dumps(values, indent=2) + '\n')
    if args.output:
        with open(args.output, 'a') as f:
            for k, v in values.items():
                print(f'{k}={v}', file=f)
    print(json.dumps(values))

if __name__ == '__main__':
    main()
