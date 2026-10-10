#!/usr/bin/env bash
set -Eeuo pipefail
archive="$(realpath "$1")"
image="reikjv-snav:0.3.0-beta.3"
data=/usr/blueos/extensions/reikjv-snav

# Only the daemon architecture report is substituted. Images and Docker operations
# are real; ARM instructions run through QEMU on the amd64 GitHub runner.
sed 's/^ARCH=.*/ARCH="arm"/' install.sh > /tmp/install-ci.sh

echo 'Unsupported architecture must stop before loading or creating containers.'
if sudo bash install.sh --archive "$archive"; then exit 1; fi
if docker container inspect reikjv-snav >/dev/null 2>&1; then exit 1; fi

echo 'A corrupt download must be rejected.'
printf 'corrupt' > /tmp/corrupt-image.tar.gz
if sudo bash /tmp/install-ci.sh --archive /tmp/corrupt-image.tar.gz; then exit 1; fi
if docker container inspect reikjv-snav >/dev/null 2>&1; then exit 1; fi

echo 'Install with a simulated BlueOS terminal still occupying 8088.'
python3 -m http.server 8088 --bind 127.0.0.1 >/tmp/terminal.log 2>&1 &
terminal_pid=$!
trap 'kill "$terminal_pid" || true' EXIT
sleep 1
sudo bash /tmp/install-ci.sh --archive "$archive"
curl -fsS http://127.0.0.1:8088/ >/dev/null
docker exec reikjv-snav python -c 'import json,urllib.request; s=json.load(urllib.request.urlopen("http://127.0.0.1:8099/api/status")); assert not any(s["selection"].values()); assert not s["vehicle"]["connected"]; assert "nucleus_password" not in s["config"]'
previous="$(docker inspect --format '{{.Id}}' reikjv-snav)"

echo 'Selected sources must block replacement and leave the old container running.'
docker run --rm -v "$data:/data" "$image" python -c 'import json; json.dump({"selection":{"heading":True}},open("/data/state.json","w")); open("/data/preserve.txt","w").write("keep")'
if sudo bash /tmp/install-ci.sh --archive "$archive"; then exit 1; fi
test "$(docker inspect --format '{{.Id}}' reikjv-snav)" = "$previous"
test "$(docker inspect --format '{{.State.Running}}' reikjv-snav)" = true

echo 'Pending transactions must also block replacement.'
docker run --rm -v "$data:/data" "$image" python -c 'import json; json.dump({"selection":{},"pending":{"operation":"test"}},open("/data/state.json","w"))'
if sudo bash /tmp/install-ci.sh --archive "$archive"; then exit 1; fi
test "$(docker inspect --format '{{.Id}}' reikjv-snav)" = "$previous"
docker run --rm -v "$data:/data" "$image" python -c 'import json; json.dump({"selection":{}},open("/data/state.json","w"))'

echo 'Update must preserve the data and keep the old container stopped.'
sudo bash /tmp/install-ci.sh --archive "$archive"
test "$(docker inspect --format '{{.Id}}' reikjv-snav)" != "$previous"
test "$(docker inspect --format '{{.State.Running}}' "$previous")" = false
docker exec reikjv-snav python -c 'assert open("/data/preserve.txt").read()=="keep"'

echo 'A startup failure must restore the previous working container.'
current="$(docker inspect --format '{{.Id}}' reikjv-snav)"
sed 's/python -m snav.app --data-dir/python -m snav.nonexistent --data-dir/' /tmp/install-ci.sh > /tmp/install-broken.sh
if sudo bash /tmp/install-broken.sh --archive "$archive"; then exit 1; fi
test "$(docker inspect --format '{{.Id}}' reikjv-snav)" = "$current"
test "$(docker inspect --format '{{.State.Running}}' reikjv-snav)" = true
for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:8099/health; then break; fi
  sleep 1
done
curl -fsS http://127.0.0.1:8099/health
curl -fsS http://127.0.0.1:8088/ >/dev/null
echo 'All installer checks passed. This is emulation, not a hardware/EKF test.'
