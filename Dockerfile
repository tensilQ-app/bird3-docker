# syntax=docker/dockerfile:1
FROM alpine:3.24 AS build
ARG BIRD_VERSION
ARG BIRD_SHA256
RUN apk upgrade --no-cache && apk add --no-cache \
    build-base bison flex m4 pkgconf readline-dev ncurses-dev libssh-dev \
    openssl-dev linux-headers ca-certificates
WORKDIR /src
COPY bird.tar.gz /tmp/bird.tar.gz
RUN test -n "$BIRD_VERSION" && test -n "$BIRD_SHA256" && \
    echo "$BIRD_SHA256  /tmp/bird.tar.gz" | sha256sum -c - && \
    tar -xzf /tmp/bird.tar.gz --strip-components=1 && \
    ./configure --prefix=/usr --sysconfdir=/etc/bird --localstatedir=/var && \
    make -j"$(nproc)" && \
    make DESTDIR=/out install && \
    test -x /out/usr/sbin/bird && test -x /out/usr/sbin/birdc

FROM alpine:3.24
RUN apk upgrade --no-cache && apk add --no-cache \
    readline ncurses-libs libssh ca-certificates && \
    mkdir -p /etc/bird /run/bird
COPY --from=build /out/usr/sbin/bird /usr/sbin/bird
COPY --from=build /out/usr/sbin/birdc /usr/sbin/birdc
COPY --from=build /out/usr/sbin/birdcl /usr/sbin/birdcl
LABEL org.opencontainers.image.title="BIRD 3" \
      org.opencontainers.image.description="Unofficial multi-architecture BIRD 3 built from CZ.NIC source" \
      org.opencontainers.image.source="https://github.com/tensilQ-app/bird3-docker" \
      org.opencontainers.image.licenses="GPL-2.0-or-later"
STOPSIGNAL SIGTERM
ENTRYPOINT ["/usr/sbin/bird"]
CMD ["-d", "-c", "/etc/bird/bird.conf", "-s", "/run/bird/bird.ctl"]
