# Development

The project is maintained by tensilQ.app (GitHub organization: tensilQ-app, info@tensilq.app).

For manual and AI-assisted commits made on behalf of the organization, use the approved author and committer identity:

```sh
git config user.name 'tensilQ-app'
git config user.email 'info@tensilq.app'
```

Do not identify manual or ChatGPT-assisted commits as bot commits. Do not add OpenAI or ChatGPT to contributors, authors, maintainers or copyright holders. Preserve upstream license and copyright notices. Independent external contributors keep their own identities.

For commits actually created by GitHub Actions, use:

```sh
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
```

Dependabot retains its own bot identity. Never merge branches descended from the pre-migration history into main. Recreate dependency changes on the current main instead.

## Release operations

Manual dispatch accepts an optional stable `version`. An older explicitly selected version does not update `3` or `latest`. An older patch also does not update its minor-series alias when a newer stable patch is listed upstream. Scheduled GitHub Actions may be disabled after prolonged repository inactivity; check the Actions tab and failure notifications. Dependabot tracks workflow actions and Docker base references.

### First publication

GHCR creates new packages as private by default. After the first staging upload, an organization package administrator must open the package settings and change visibility to **Public**. The release job deliberately fails its anonymous-download gate until this is done; it does not silently publish release aliases for an inaccessible image. Re-run the failed publish job after setting visibility. Subsequent releases reuse the same public package.


## Source authentication and supply chain

1. Discover stable versions on `https://bird.nic.cz/get-bird/` over verified HTTPS; restrict redirects to explicit CZ.NIC hosts.
2. Fetch the exact release tag from `https://gitlab.nic.cz/labs/bird.git`, with Git HTTP redirects disabled. If this transport remains unavailable after bounded retries (including HTTP 403), use the upstream-owned `https://github.com/CZ-NIC/bird.git` repository as a second official transport.
3. Verify its OpenPGP signature against the committed key in `keys/bird-release.asc`. The pinned primary fingerprint is **6EFA4F8288F022C523505F30BA756F665CB418E2**, published on the [official BIRD contact page](https://bird.nic.cz/contact/). Verify that the signed `VERSION` file matches the release.
4. Archive that signed commit, record commit, signer and SHA-256 in `source.json`, and independently verify the archive digest inside each Docker build.

Transient HTTPS/Git transport failures, including HTTP 403, are retried a limited number of times against the two explicit official endpoints; the selected origin is recorded in `source.json`. Signature and checksum failures have no fallback.

These are official Git sources, archived locally after signature verification, rather than the unsigned website release tarball. Autoconf generates the build system inside the build stage. Both official transports must pass the same pinned-key tag signature and signed-version checks. A signature failure does not trigger a mirror retry. An unsigned release, unexpected signer, expired/revoked key, invalid signature or checksum mismatch blocks the build. Key rotation requires maintainer review against upstream's published fingerprint; there is no insecure fallback or automatic trust of new keys.

Each native build exports an OCI archive with BuildKit **SBOM and maximum provenance**. It is loaded for functional tests and scanned by **Trivy**. Any **HIGH/CRITICAL vulnerability with an available fix** blocks publication; failures to download the vulnerability database or run the scanner also fail the job. Unfixed CVEs and lower severities do not block this policy, and a successful scan is not a guarantee of absence of vulnerabilities. Trivy does not replace upstream security review and may not identify every issue in custom-built binaries.

Only after **both** architectures pass does the publish job copy those same OCI archives, preserving digests and attestations, to GHCR. It assembles and validates the index, downloads both platforms without credentials, and then promotes the existing index to version aliases. No build occurs during promotion. Build/test/scan failure leaves the previously published `latest` untouched. Registry tag updates are separate operations and cannot be a transaction across all aliases; transient promotion failures may require a rerun. BuildKit provenance describes the build; this project does not currently provide an independent Cosign signature.

Functional jobs use Bash with `errexit` and `pipefail`, and require an explicit final PASS marker; log capture cannot mask a failed test. Functional checks cover version output, missing/invalid configuration rejection, parsing all required protocol definitions, real daemon startup, active IPv4/IPv6 static routes, a Unix control socket, `birdc show status`, `show protocols`, `show route`, `configure check`, and graceful SIGTERM shutdown. Network-facing protocol definitions are disabled in the fixture: these checks prove availability and basic operation, not interoperability or live adjacency formation for every routing protocol.

Actions artifacts include runtime logs, Trivy JSON, verified sources, source metadata, and tested OCI archives. Release logs and summaries contain the published index digest. SBOM/provenance are registry attestations (additional `unknown/unknown` index entries are expected). These can be inspected with `docker buildx imagetools inspect` and tools supporting OCI attestations.

### Alpine build compatibility

Optional link-time optimization (LTO) is disabled with upstream's `--disable-lto` configure option. The BIRD 3.4.0 route exporter uses extended structures; in the Alpine/GCC LTO build, Fortify's source-size check traps while announcing even a basic static route. The non-LTO build passes the same native IPv4/IPv6 regression checks on both platforms. Optimization remains enabled, Fortify remains enabled and is asserted during the build, and no BIRD source patches or security-check bypasses are applied. This is a build compatibility choice, not a reduction of supported protocols.

### Local development

Requires Python 3, Git, GnuPG, Docker with Buildx, and network access to upstream services:

```sh
python3 scripts/test-release.py
python3 scripts/check-release.py
VERSION=$(python3 -c 'import json; print(json.load(open("source.json"))["version"])')
SHA256=$(python3 -c 'import json; print(json.load(open("source.json"))["sha256"])')
docker build --pull --no-cache --build-arg BIRD_VERSION="$VERSION" --build-arg BIRD_SHA256="$SHA256" -t bird3-local .
bash scripts/test-image.sh bird3-local linux/amd64 "$VERSION"
```

Use `linux/arm64` on ARM64 hosts. Cross-platform local builds require emulation or a remote builder; release checks always run natively. Package repositories change over time, so dependency-refresh builds are not byte-for-byte reproducible. The signed source commit and archive checksum remain recorded for auditing.
