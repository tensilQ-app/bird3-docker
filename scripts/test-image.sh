#!/usr/bin/env bash
set -euo pipefail
image="${1:?image required}"
platform="${2:?platform required}"
version="${3:?version required}"
dir="$(mktemp -d)"
name="bird3-test-$$-$RANDOM"
cleanup() {
  docker rm -f "$name" >/dev/null 2>&1 || true
  rm -rf "$dir"
}
trap cleanup EXIT
cat > "$dir/bird.conf" <<'CONF'
log stderr all;
router id 192.0.2.1;
protocol device { }
protocol static test_static { ipv4; }
CONF
docker run --rm --platform "$platform" --entrypoint /usr/sbin/bird "$image" --version | grep -F "$version"
docker run --rm --platform "$platform" --entrypoint /usr/sbin/bird "$image" -p -c /etc/bird/bird.conf -s /run/bird/bird.ctl -d >/dev/null 2>&1 && {
  echo "Unexpected success without mounted configuration" >&2; exit 1;
} || true
docker run --rm --platform "$platform" -v "$dir/bird.conf:/etc/bird/bird.conf:ro" \
  --entrypoint /usr/sbin/bird "$image" -p -c /etc/bird/bird.conf
docker run -d --name "$name" --platform "$platform" \
  -v "$dir/bird.conf:/etc/bird/bird.conf:ro" "$image" >/dev/null
for n in $(seq 1 30); do
  if docker exec "$name" /usr/sbin/birdc -s /run/bird/bird.ctl 'show status' > "$dir/status" 2>&1; then
    grep -F "BIRD" "$dir/status"
    docker exec "$name" /usr/sbin/birdc -s /run/bird/bird.ctl 'show protocols' > "$dir/protocols"
    grep -F "test_static" "$dir/protocols"
    docker stop -t 10 "$name" >/dev/null
    test "$(docker inspect -f '{{.State.ExitCode}}' "$name")" = 0
    echo "PASS: $platform"
    exit 0
  fi
  sleep 1
done
docker logs "$name"
cat "$dir/status"
exit 1
