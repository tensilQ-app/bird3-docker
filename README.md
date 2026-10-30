# BIRD 3 OCI images

Unofficial, independently maintained multi-architecture images of the [BIRD Internet Routing Daemon](https://bird.nic.cz/), built from **signature-verified official CZ.NIC sources** on Alpine Linux **3.24**. This project is not affiliated with or endorsed by CZ.NIC.

**Image:** `ghcr.io/tensilq-app/bird3` · [Packages](https://github.com/orgs/tensilQ-app/packages/container/package/bird3) · [CI](https://github.com/tensilQ-app/bird3-docker/actions/workflows/ci.yml) · [Releases](https://github.com/tensilQ-app/bird3-docker/actions/workflows/release.yml)

## Platforms and features

**Base image:** the [Docker Official Image `alpine:3.24`](https://hub.docker.com/_/alpine), used for both the build and runtime stages.

Native builds and runtime tests run on **linux/amd64** and **linux/arm64**. No emulation is used in release validation. All standard upstream protocols remain enabled, including BGP, OSPFv2/v3, Babel, BFD, RIP/RIPng, RPKI, IPv4/IPv6, kernel, direct and static; libssh support is explicitly required. The image contains `bird`, `birdc`, `birdcl`, their runtime libraries, license notices and corresponding BIRD source. Build tools are excluded from the runtime image.

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

Version examples are illustrative. All ordinary version aliases can move when dependencies are refreshed. Revision tags are not intentionally overwritten; registry administrators can still delete or change tags. **Pin the multi-platform digest** for immutable deployments:

```yaml
image: ghcr.io/tensilq-app/bird3@sha256:REPLACE_WITH_INDEX_DIGEST
```

Updates are checked daily. Images are rebuilt only when a stable BIRD 3 release, the Alpine 3.24 base image, resolved build/runtime packages, or packaging inputs change, or when a maintainer forces a rebuild. Unchanged images are not republished. Prereleases, beta and RC versions are excluded. The published image is scanned daily with a fresh Trivy vulnerability database, even when no rebuild is needed. To apply an update, pull the image and recreate the container.

## Security and verification

Official CZ.NIC source tags are verified using the pinned BIRD OpenPGP release key before building. Both architectures must pass native runtime tests and Trivy scanning before publication. HIGH/CRITICAL vulnerabilities with available fixes block publication; failed builds leave the existing `latest` unchanged.

Images include SPDX SBOMs and build provenance. Inspect the multi-platform manifest with:

```sh
docker buildx imagetools inspect ghcr.io/tensilq-app/bird3:3
```

Additional `unknown/unknown` entries contain attestations, not runnable images. No separate Cosign signature is provided. A successful scan does not guarantee the absence of vulnerabilities.

Runtime checks cover configuration parsing, daemon startup, the Unix socket, `birdc`, IPv4/IPv6 static routes and graceful shutdown. Live protocol adjacencies are not tested. Alpine package updates mean rebuilds are not byte-for-byte reproducible.

Build and release procedures are documented in [CONTRIBUTING.md](CONTRIBUTING.md).

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
