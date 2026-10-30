# BIRD 3 OCI images

Unofficial, independently maintained multi-architecture images of the [BIRD Internet Routing Daemon](https://bird.nic.cz/), built from **signature-verified official CZ.NIC sources** on Alpine Linux **3.24**. This project is not affiliated with or endorsed by CZ.NIC.

**Image:** `ghcr.io/tensilq-app/bird3` · [Packages](https://github.com/orgs/tensilQ-app/packages/container/package/bird3) · [CI](https://github.com/tensilQ-app/bird3-docker/actions/workflows/ci.yml) · [Releases](https://github.com/tensilQ-app/bird3-docker/actions/workflows/release.yml)

## Platforms and features

Native builds and runtime tests run on **linux/amd64** and **linux/arm64**. No emulation is used in release validation. All standard upstream protocols remain enabled, including BGP, OSPFv2/v3, Babel, BFD, RIP/RIPng, RPKI, IPv4/IPv6, kernel, direct and static; libssh support is explicitly required. The image contains `bird`, `birdc`, `birdcl`, their runtime libraries, license notices and corresponding BIRD source. Build tools remain in a separate build stage. The default Dockerfile has only a build stage and a minimal runtime stage.

The image contains **no default routing configuration**, user infrastructure settings, service integration or supervisor. BIRD runs as PID 1 and logs to stderr. Linux kernel support and networking permissions remain the deployment's responsibility.

## Quick start

Create `bird.conf` (a safe configuration for trying the image without exchanging or installing routes):

```bird
log stderr all;
router id 192.0.2.1;
protocol device { }
protocol static { ipv4; }
protocol static { ipv6; }
```

```yaml
services:
  bird:
    image: ghcr.io/tensilq-app/bird3:3
    restart: unless-stopped
    volumes:
      - ./bird.conf:/etc/bird/bird.conf:ro
    healthcheck:
      test: ["CMD", "birdc", "-s", "/run/bird/bird.ctl", "show", "status"]
      interval: 30s
      timeout: 5s
      retries: 3
```

```sh
docker compose up -d
docker compose logs bird
docker compose exec bird birdc -s /run/bird/bird.ctl show status
docker compose exec bird birdc -s /run/bird/bird.ctl show protocols
docker compose exec bird birdc -s /run/bird/bird.ctl configure check
docker compose exec bird birdc -s /run/bird/bird.ctl configure
```

The entrypoint is `/usr/sbin/bird`; arguments replace the default `-d -c /etc/bird/bird.conf -s /run/bird/bird.ctl`:

```sh
docker run --rm ghcr.io/tensilq-app/bird3:3 --version
docker run --rm -v "$PWD/bird.conf:/etc/bird/bird.conf:ro" ghcr.io/tensilq-app/bird3:3 -p -c /etc/bird/bird.conf
docker buildx imagetools inspect ghcr.io/tensilq-app/bird3:3
```

Do not add `bird` before the arguments: it is already the entrypoint. For a shell, use `--entrypoint /bin/sh`.

### Operational routing example

For a Linux host whose routes BIRD should manage, the following Compose settings share the host network namespace and permit route operations. Review your configuration before enabling them: kernel protocol exports can change host connectivity.

```yaml
services:
  bird:
    image: ghcr.io/tensilq-app/bird3:3
    network_mode: host
    cap_drop: [ALL]
    cap_add: [NET_ADMIN, NET_RAW, NET_BIND_SERVICE]
    read_only: true
    tmpfs:
      - /run/bird:mode=0755
    volumes:
      - ./bird.conf:/etc/bird/bird.conf:ro
    restart: unless-stopped
```

Host networking has Linux-specific semantics. Bridge, macvlan, or another container's network namespace can also be used; choose the namespace containing the interfaces and routes you intend to control. IPv6, forwarding, multicast reachability, firewall policy and kernel features must be configured outside the image. Blanket `privileged: true` is unnecessary. The process uses root by default; reduce capabilities according to your protocols. The Unix control socket grants administrative access to BIRD: do not expose it to untrusted users or over TCP. `birdc -r` can restrict client commands, but socket filesystem permissions remain the primary access boundary.

## Tags and updates

| Tag | Meaning |
| --- | --- |
| `3.4.0` | Most recent successful build of that upstream version |
| `3.4` | Latest stable patch in the selected minor series |
| `3`, `latest` | Latest stable BIRD 3 |
| `3.4.0-rN.A` | Retained rebuild revision: workflow run number N, attempt A |
| `3.4.0-rN.A-amd64`, `3.4.0-rN.A-arm64` | Architecture staging indexes used for promotion |

Version examples are illustrative. All ordinary version aliases can move when dependencies are refreshed. Revision tags are not intentionally overwritten; registry administrators can still delete or change tags. **Pin the multi-platform digest** for immutable deployments:

```yaml
image: ghcr.io/tensilq-app/bird3@sha256:REPLACE_WITH_INDEX_DIGEST
```

The Release workflow runs **daily at 05:23 UTC**, after successful main-branch CI, and on manual dispatch. It selects the highest strictly numeric `3.x.y` version explicitly listed on the official release page; beta/RC/prerelease names are rejected. Every run rebuilds both platforms with fresh `alpine:3.24` pulls, disabled build cache, and `apk upgrade --no-cache` in both stages, even when BIRD has not changed. It never changes users' running containers. Alpine release-line changes require a reviewed repository change.

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

Actions artifacts include runtime logs, Trivy JSON, verified sources, source metadata, and tested OCI archives. Release logs and summaries contain the published index digest. After a successful release the workflow attempts to remove the known-invalid bootstrap revision `3.4.0-r3.1` and its architecture staging tags; package-administration permission failures appear as cleanup warnings. Do not deploy that revision from an old local cache. SBOM/provenance are registry attestations (additional `unknown/unknown` index entries are expected). These can be inspected with `docker buildx imagetools inspect` and tools supporting OCI attestations.

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

## Licensing and corresponding source

BIRD is maintained by **CZ.NIC and its contributors** and licensed under **GPL-2.0-or-later**. Its existing copyright and source notices remain intact. The BMP component's upstream license notice is retained. Repository packaging, automation and examples are MIT-licensed; see [LICENSE](LICENSE). MIT does not replace BIRD's GPL or any dependency license.

The **exact corresponding BIRD source archive** is included in every runtime image at `/usr/share/bird/source.tar.gz`, together with `/usr/share/bird/Dockerfile` build instructions. Extract it without launching the daemon:

```sh
id=$(docker create ghcr.io/tensilq-app/bird3:3)
docker cp "$id:/usr/share/bird/source.tar.gz" ./bird-source.tar.gz
docker cp "$id:/usr/share/bird/Dockerfile" ./Dockerfile
docker rm "$id"
```

Official sources are also available from [CZ.NIC GitLab](https://gitlab.nic.cz/labs/bird/) at the recorded signed tag/commit. The unmodified source, this Dockerfile and recorded build arguments describe the BIRD build. Included source intentionally adds a small amount to image size to keep it available with each distributed binary.

Third-party components keep their own licenses: Alpine/musl and ncurses use permissive licenses; BusyBox uses GPL-2.0; readline uses GPL-3.0-or-later; libssh uses LGPL-2.1-or-later; OpenSSL uses Apache-2.0; the CA certificate collection contains Mozilla-licensed material. Transitive packages may add other licenses. Consult the exact image's `/lib/apk/db/installed`, common license texts in `/usr/share/licenses`, SBOM, and [Alpine package/source records](https://pkgs.alpinelinux.org/) for the package versions and corresponding sources. These notices are informational and do not relicense third-party components.

## Security and support

Report packaging issues through [GitHub issues](https://github.com/tensilQ-app/bird3-docker/issues). Avoid publishing secrets or unpatched vulnerability details in public issues. For BIRD vulnerabilities use [upstream security reporting](https://bird.nic.cz/contact/); see [SECURITY.md](SECURITY.md) for container reports. Review release scan reports, upstream advisories and your routing policy before deployment. There is no security response SLA.

### Development

This project is independently maintained and uses AI-assisted development tools, including OpenAI ChatGPT, for code generation, review, testing, and documentation.

All project decisions, maintenance, and responsibility for published container images remain with the project maintainers.

This project is not affiliated with or endorsed by OpenAI or CZ.NIC.
