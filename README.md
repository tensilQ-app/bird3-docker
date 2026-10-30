# BIRD 3 Docker images

**Unofficial** multi-architecture container images of [BIRD Internet Routing Daemon](https://bird.nic.cz/), compiled from official CZ.NIC release archives. This project is not affiliated with or endorsed by CZ.NIC.

Image: `ghcr.io/tensilq-app/bird3` (after the first successful release and package visibility is set to public).

## Supported platforms and routing features

- `linux/amd64`, `linux/arm64`
- Upstream BIRD 3 routing features, including BGP, OSPFv2/v3, RIP, Babel, BFD, RPKI, static, direct, kernel, and IPv4/IPv6.
- Build includes libssh for RPKI support. No protocols are disabled using `--with-protocols`.
- Runtime contains BIRD, `birdc`, `birdcl`, and required shared libraries.

## Tags

- `3.4.0`: specific upstream version
- `3.4`: latest patch version in the 3.4 series
- `3`, `latest`: latest stable BIRD 3
- `3.4.0-rN`: explicitly requested image rebuild of a particular upstream release

The full-version tag is left unchanged on ordinary scheduled runs. Moving tags are updated only after both architectures pass container runtime tests. For reproducible deployments, pin a digest instead of a moving tag.

## Usage

Provide your own BIRD configuration at `/etc/bird/bird.conf`. There is **no bundled routing configuration**. Example Docker Compose configuration:

```yaml
services:
  bird:
    image: ghcr.io/tensilq-app/bird3:3
    restart: unless-stopped
    volumes:
      - ./bird.conf:/etc/bird/bird.conf:ro
```

This example deliberately does not prescribe a network mode, capabilities, or interfaces. Routing daemons generally need extra network permissions and a suitable network namespace for operational routing. Set these according to your environment and risk model. BIRD does not itself require `privileged: true` as a blanket setting.

The container runs `bird -d -c /etc/bird/bird.conf -s /run/bird/bird.ctl`. `-d` keeps it in foreground and logs diagnostics to stderr (visible in `docker logs`). The socket stays inside the container by default.

```sh
docker run --rm ghcr.io/tensilq-app/bird3:3 bird --version
docker image inspect ghcr.io/tensilq-app/bird3:3 --format '{{.Os}}/{{.Architecture}}'
docker exec <container> birdc -s /run/bird/bird.ctl show status
docker logs <container>
```

For multi-platform index inspection:

```sh
docker buildx imagetools inspect ghcr.io/tensilq-app/bird3:3
```

For a sidecar deployment, `network_mode: service:<name>` is possible but **must be configured by the user**, along with permissions and lifecycle coordination. For production, mount the configuration read-only and explicitly scope network access, privileges, and access to the control socket.

## How releases work

`Release` workflow checks the official [CZ.NIC release page](https://bird.nic.cz/get-bird/) on a daily schedule and on manual dispatch. It selects the highest strictly numeric `3.x.y` release listed by CZ.NIC (no RC, beta or prerelease), and downloads the tarball from CZ.NIC over HTTPS. It computes SHA-256 once and passes the digest to **every** Docker build; the Dockerfile verifies the archive bytes independently. The jobs compile and launch BIRD on both supported platforms and run `birdc` before publication. Publication requires both tests to pass.

**Source authenticity limitation:** The upstream release page does not currently expose an independently authenticated tarball SHA-256 or tarball signature verified by this workflow. TLS, the official download host, and consistent SHA-256 protect the download/build handoff but **do not constitute independent upstream signing**. The published upstream Git commit shown on the download page is informational, not a verified signature of tarball contents. Do not interpret this process as cryptographic proof of the upstream author's identity.

Manual release dispatch options:
- `version`: specific stable version already listed on CZ.NIC, or blank for latest.
- `rebuild`: opt in to republishing the same version to refresh base libraries. Use with care: an existing version tag may move; prefer a distinct revision tag for immutable deployments.

Builds depend on Debian base image and package repository versions, which can change. Image rebuilding is therefore not byte-for-byte reproducible by default. To rebuild against patched base libraries, run the release workflow with `rebuild=true`, review the results and consider pinning the image by digest. This project does not update users' running containers.

GitHub may disable scheduled workflows after prolonged inactivity; maintainers should review the Actions tab regularly. CI also tests changes on pull requests without publishing images. Publication needs `packages: write` on the release workflow.

## Licensing and upstream attribution

[BIRD](https://bird.nic.cz/) is maintained by CZ.NIC and its contributors and is distributed under **GNU General Public License version 2 or later (GPL-2.0-or-later)**. The BIRD code and notices are not authored by this project. Official source archives are available from [CZ.NIC downloads](https://bird.nic.cz/get-bird/); the source archive matching each image version can be retrieved from the upstream release site. Source code should remain available to recipients in compliance with the GPL, including corresponding build instructions.

This repository's packaging scripts, examples and automation are offered under MIT (see [LICENSE](LICENSE)); that license does **not** replace BIRD's GPL or the licenses of any included third-party components. Runtime images include Debian and library components, each subject to their respective licenses. Debian copyright/license metadata is retained in the image under `/usr/share/doc` where installed.

Report BIRD bugs to upstream; report container packaging and build issues to this repository.
