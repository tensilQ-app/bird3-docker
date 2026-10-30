#!/usr/bin/env bash
set -euo pipefail
image="${1:?image required}"
platform="${2:?platform required}"
version="${3:?version required}"
dir="$(mktemp -d)"
name="bird3-test-$$-$RANDOM"
cleanup() {
  result=$?
  if [ "$result" -ne 0 ]; then
    docker image inspect --format 'Entrypoint={{json .Config.Entrypoint}} Cmd={{json .Config.Cmd}}' "$image" || true
    docker inspect --format 'Path={{.Path}} Args={{json .Args}} State={{json .State}}' "$name" || true
    docker logs "$name" 2>&1 || true
    [ ! -f "$dir/status" ] || cat "$dir/status"
  fi
  docker rm -f "$name" >/dev/null 2>&1 || true
  rm -rf "$dir"
}
trap cleanup EXIT
cat > "$dir/bird.conf" <<'CONF'
log stderr all;
router id 192.0.2.1;
protocol device { }
protocol static test_static { ipv4; route 198.51.100.0/24 blackhole; }
protocol static test_static6 { ipv6; route 2001:db8::/32 blackhole; }
protocol direct { disabled; ipv4; ipv6; }
protocol kernel { disabled; ipv4; }
protocol kernel { disabled; ipv6; }
protocol bgp { disabled; local as 64512; neighbor 192.0.2.2 as 64513; ipv4 { import all; export all; }; ipv6 { import all; export all; }; }
protocol ospf v2 { disabled; ipv4; area 0 { interface "lo"; }; }
protocol ospf v3 { disabled; ipv6; area 0 { interface "lo"; }; }
protocol babel { disabled; ipv4; ipv6; interface "lo"; }
protocol bfd { disabled; interface "*"; }
protocol rip { disabled; ipv4; interface "lo"; }
protocol rip ng { disabled; ipv6; interface "lo"; }
roa4 table rpki4;
roa6 table rpki6;
protocol rpki { disabled; roa4 { table rpki4; }; roa6 { table rpki6; }; remote "192.0.2.2" port 323; }
CONF
docker run --rm --platform "$platform" "$image" --version 2>&1 | grep -Fx "BIRD version $version"
if docker run --rm --platform "$platform" "$image" -p -c /etc/bird/bird.conf; then
  echo 'Unexpected success without configuration' >&2; exit 1
fi
printf 'invalid syntax;\n' > "$dir/invalid.conf"
if docker run --rm --platform "$platform" -v "$dir/invalid.conf:/tmp/invalid.conf:ro" "$image" -p -c /tmp/invalid.conf; then
  echo 'Invalid configuration was accepted' >&2; exit 1
fi
docker run --rm --platform "$platform" -v "$dir/bird.conf:/etc/bird/bird.conf:ro" "$image" -p -c /etc/bird/bird.conf
docker run -d --name "$name" --platform "$platform" -v "$dir/bird.conf:/etc/bird/bird.conf:ro" "$image" >/dev/null
for n in $(seq 1 30); do
  if docker exec "$name" birdc -s /run/bird/bird.ctl show status > "$dir/status" 2>&1; then
    grep -F 'Daemon is up and running' "$dir/status"
    docker exec "$name" test -S /run/bird/bird.ctl
    docker exec "$name" birdc -s /run/bird/bird.ctl show protocols | tee "$dir/protocols"
    grep -F 'test_static' "$dir/protocols"
    docker exec "$name" birdc -s /run/bird/bird.ctl show route table master4 | tee "$dir/routes"
    docker exec "$name" birdc -s /run/bird/bird.ctl show route table master6 | tee -a "$dir/routes"
    grep -F '198.51.100.0/24' "$dir/routes"
    grep -F '2001:db8::/32' "$dir/routes"
    docker exec "$name" birdc -s /run/bird/bird.ctl configure check
    docker stop -t 10 "$name" >/dev/null
    test "$(docker inspect -f '{{.State.ExitCode}}' "$name")" = 0
    echo "PASS: $platform BIRD $version (parse, protocols, IPv4/IPv6 routes, socket, birdc, shutdown)"
    exit 0
  fi
  if [ "$(docker inspect -f '{{.State.Running}}' "$name")" != true ]; then
    echo 'BIRD container exited before birdc became ready' >&2
    exit 1
  fi
  sleep 1
done
docker logs "$name"
cat "$dir/status"
exit 1
