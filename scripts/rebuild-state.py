#!/usr/bin/env python3
"""Compare resolved native build inputs with labels on the published image."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shlex
import subprocess
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LABEL = 'app.tensilq.bird.build-inputs'
ACCEPT = ', '.join(['application/vnd.oci.image.index.v1+json', 'application/vnd.docker.distribution.manifest.list.v2+json', 'application/vnd.oci.image.manifest.v1+json', 'application/vnd.docker.distribution.manifest.v2+json'])


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def request_json(url, headers=None):
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=60) as response:
        raw = response.read()
        return json.loads(raw), hashlib.sha256(raw).hexdigest()


class Registry:
    """Read public GHCR metadata without stored credentials; only 404 means absent."""
    def __init__(self, image):
        if not re.fullmatch(r'ghcr.io/[a-z0-9_.-]+/[a-z0-9_.-]+', image):
            raise ValueError('Expected a public GHCR image')
        self.repo = image.removeprefix('ghcr.io/')
        query = urllib.parse.urlencode({'service': 'ghcr.io', 'scope': f'repository:{self.repo}:pull'})
        data, _ = request_json(f'https://ghcr.io/token?{query}')
        self.headers = {'Authorization': f'Bearer {data["token"]}', 'Accept': ACCEPT}

    def get(self, kind, ref):
        return request_json(f'https://ghcr.io/v2/{self.repo}/{kind}/{ref}', self.headers)

    def index(self, ref):
        return self.get('manifests', ref)

    def labels(self, version, arch):
        try:
            index, _ = self.index(version)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return {}
            raise
        manifests = [m for m in index['manifests'] if m.get('platform', {}).get('os') == 'linux' and m['platform'].get('architecture') == arch]
        if len(manifests) != 1:
            raise ValueError(f'Expected exactly one linux/{arch} manifest')
        manifest, _ = self.get('manifests', manifests[0]['digest'])
        config, _ = self.get('blobs', manifest['config']['digest'])
        return config.get('config', {}).get('Labels', {}) or {}


def recipe(path=ROOT / 'Dockerfile'):
    text = path.read_text()
    bases = re.findall(r'^FROM (\S+) AS (build|runtime)$', text, re.M)
    if bases != [('alpine:3.24', 'build'), ('alpine:3.24', 'runtime')]:
        raise ValueError('Update the dependency probe for the new base/stages')
    groups = re.findall(r'RUN apk upgrade --no-cache && apk add --no-cache \\\n((?:.*\\\n)*.*)', text)
    if len(groups) != 2:
        raise ValueError('Expected two APK install recipes')
    packages = []
    for group in groups:
        names = shlex.split(group.replace('\\\n', ' ').split('&&', 1)[0])
        if not names or any(not re.fullmatch(r'[a-zA-Z0-9+_.-]+', name) for name in names):
            raise ValueError('Unsupported package recipe')
        packages.append(names)
    return 'alpine:3.24', dict(zip(('build', 'runtime'), packages))


def packaging_hash():
    paths = run('git', '-C', str(ROOT), 'ls-files').splitlines()
    selected = [p for p in paths if p in {'Dockerfile', '.dockerignore'} or p.startswith(('licenses/', 'keys/', 'scripts/', '.github/workflows/'))]
    digest = hashlib.sha256()
    for name in sorted(selected):
        digest.update(name.encode() + b'\0' + (ROOT / name).read_bytes() + b'\0')
    return digest.hexdigest()


def fingerprint(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def decision(current, previous, force=False):
    return force or current != previous


def emit(values, output):
    print(json.dumps(values, indent=2))
    if output:
        with open(output, 'a') as stream:
            for key, value in values.items():
                print(f'{key}={str(value).lower() if isinstance(value, bool) else value}', file=stream)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['version', 'probe', 'resolve'])
    parser.add_argument('--version', default='')
    parser.add_argument('--image', default='ghcr.io/tensilq-app/bird3')
    parser.add_argument('--arch', choices=['amd64', 'arm64'])
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--output', default='')
    args = parser.parse_args()
    if args.command == 'version':
        spec = importlib.util.spec_from_file_location('release', ROOT / 'scripts/check-release.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        versions = module.stable_versions(module.fetch_page())
        if not versions:
            raise ValueError('No official stable BIRD 3 releases')
        version = args.version or max(versions, key=lambda v: tuple(map(int, v.split('.'))))
        if version not in versions:
            raise ValueError('Requested version is not an official stable release')
        emit({'version': version}, args.output)
    elif args.command == 'resolve':
        index, digest = Registry(args.image).index('3')
        platforms = [m.get('platform', {}) for m in index['manifests']]
        for arch in ('amd64', 'arm64'):
            if sum(p.get('os') == 'linux' and p.get('architecture') == arch for p in platforms) != 1:
                raise ValueError('Incomplete published index')
        emit({'image': args.image + '@sha256:' + digest}, args.output)
    else:
        if not args.arch or not re.fullmatch(r'3\.[0-9]+\.[0-9]+', args.version):
            raise ValueError('Probe requires a stable version and native architecture')
        base, groups = recipe()
        run('docker', 'pull', '--platform', f'linux/{args.arch}', base)
        base_id = run('docker', 'image', 'inspect', '--format', '{{.Id}}', base)
        base_digests = json.loads(run('docker', 'image', 'inspect', '--format', '{{json .RepoDigests}}', base))
        if not base_digests:
            raise ValueError('Pulled Alpine image has no registry digest')
        packages = {}
        for stage, names in groups.items():
            command = 'apk upgrade --no-cache >&2 && apk add --no-cache ' + ' '.join(names) + ' >&2 && apk info -v | LC_ALL=C sort'
            packages[stage] = run('docker', 'run', '--rm', '--platform', f'linux/{args.arch}', base_id, 'sh', '-ec', command).splitlines()
        state = {'schema': 1, 'version': args.version, 'architecture': args.arch, 'base': base_id, 'base_digests': sorted(base_digests), 'packages': packages, 'packaging': packaging_hash()}
        current = fingerprint(state)
        previous = Registry(args.image).labels(args.version, args.arch).get(LABEL, '')
        changed = decision(current, previous, args.force)
        Path(f'inputs-{args.arch}.json').write_text(json.dumps(dict(state, fingerprint=current, previous=previous, changed=changed), indent=2) + '\n')
        emit({'fingerprint': current, 'changed': changed}, args.output)


if __name__ == '__main__':
    main()
