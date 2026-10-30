# syntax=docker/dockerfile:1
FROM alpine:3.24 AS build
ARG BIRD_VERSION
ARG BIRD_SHA256
RUN apk upgrade --no-cache && apk add --no-cache \
    build-base autoconf automake bison flex m4 pkgconf readline-dev ncurses-dev \
    libssh-dev openssl-dev linux-headers
# Ensure Alpine's compile-time hardening remains active without LTO.
RUN printf '#include <string.h>\n#if !defined(_FORTIFY_SOURCE) || _FORTIFY_SOURCE < 1\n#error Fortify must remain enabled\n#endif\n' | \
    cc -O2 -x c -fsyntax-only -
WORKDIR /src
COPY bird.tar.gz /tmp/bird.tar.gz
RUN test -n "$BIRD_VERSION" && test -n "$BIRD_SHA256" && \
    echo "$BIRD_SHA256  /tmp/bird.tar.gz" | sha256sum -c - && \
    tar -xzf /tmp/bird.tar.gz --strip-components=1 && \
    test "$(cat VERSION)" = "$BIRD_VERSION" && \
    autoreconf -fi && \
    ./configure --prefix=/usr --sysconfdir=/etc/bird --localstatedir=/var --enable-libssh --disable-lto && \
    make -j"$(nproc)" && make DESTDIR=/out install && \
    strip /out/usr/sbin/bird /out/usr/sbin/birdc /out/usr/sbin/birdcl && \
    mkdir -p /out/usr/share/licenses/bird && \
    cp /src/README /src/proto/bmp/LICENSE /out/usr/share/licenses/bird/

FROM alpine:3.24 AS runtime
ARG BIRD_VERSION
ARG BIRD_SHA256
ARG BIRD_COMMIT
RUN apk upgrade --no-cache && apk add --no-cache \
    readline ncurses-libs libssh ca-certificates && mkdir -p /etc/bird /run/bird
COPY --from=build /out/usr/sbin/ /usr/sbin/
COPY --from=build /out/usr/share/licenses/ /usr/share/licenses/
COPY bird.tar.gz /usr/share/bird/source.tar.gz
COPY Dockerfile /usr/share/bird/Dockerfile
COPY licenses/ /usr/share/licenses/common/
# Do not copy the example routing configuration installed by upstream.
LABEL org.opencontainers.image.authors="tensilQ-app <info@tensilq.app>" \
      org.opencontainers.image.vendor="tensilQ.app" \
      org.opencontainers.image.url="https://tensilq.app" \
      org.opencontainers.image.title="BIRD 3" \
      org.opencontainers.image.description="Unofficial BIRD 3 built from signature-verified CZ.NIC sources" \
      org.opencontainers.image.source="https://github.com/tensilQ-app/bird3-docker" \
      org.opencontainers.image.version="$BIRD_VERSION" \
      org.opencontainers.image.licenses="GPL-2.0-or-later" \
      cz.nic.bird.source.commit="$BIRD_COMMIT" \
      cz.nic.bird.source.sha256="$BIRD_SHA256"
STOPSIGNAL SIGTERM
ENTRYPOINT ["/usr/sbin/bird"]
CMD ["-d", "-c", "/etc/bird/bird.conf", "-s", "/run/bird/bird.ctl"]
