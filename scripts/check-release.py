#!/usr/bin/env python3
"""Find stable BIRD 3 on official CZ.NIC page and download a checksum-pinned tarball."""
import argparse
import hashlib
import os
import re
import sys
import urllib.request
from urllib.parse import urlsplit
from pathlib import Path

PAGE = "https://bird.nic.cz/get-bird/"
DOWNLOAD = "https://bird.nic.cz/download/bird-{version}.tar.gz"
VERSION = re.compile(r"(?<![0-9A-Za-z.-])3\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?![0-9A-Za-z.-])")


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": "bird3-docker-release-check/1"})
    with urllib.request.urlopen(request, timeout=35) as response:
        if urlsplit(response.url).scheme != "https" or urlsplit(response.url).hostname not in {"bird.nic.cz", "gitlab.nic.cz"}:
            raise RuntimeError("Unexpected redirect host")
        return response.read()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--version", default="")
    p.add_argument("--download", default="bird.tar.gz")
    p.add_argument("--output", default="")
    args = p.parse_args()
    html = get(PAGE).decode("utf-8")
    # Only accept named releases in CZ.NIC's public release listing.
    versions = set(re.findall(r"BIRD\s+(3\.[0-9]+\.[0-9]+)\s*\(", re.sub(r"<[^>]*>", " ", html)))
    versions = {v for v in versions if VERSION.fullmatch(v)}
    if not versions:
        raise RuntimeError("No stable numeric BIRD 3 releases found on official page")
    ver = args.version or max(versions, key=lambda x: tuple(map(int, x.split("."))))
    if ver not in versions:
        raise RuntimeError(f"Version {ver!r} not listed as stable on CZ.NIC")
    archive = get(DOWNLOAD.format(version=ver))
    if not archive.startswith(b"\x1f\x8b"):
        raise RuntimeError("Downloaded payload is not a gzip archive")
    digest = hashlib.sha256(archive).hexdigest()
    Path(args.download).write_bytes(archive)
    values = {"version": ver, "sha256": digest}
    if args.output:
        with open(args.output, "a", encoding="utf-8") as out:
            for k, v in values.items():
                print(f"{k}={v}", file=out)
    print(f"Official CZ.NIC BIRD {ver}, SHA-256 {digest}", file=sys.stderr)


if __name__ == "__main__":
    main()
