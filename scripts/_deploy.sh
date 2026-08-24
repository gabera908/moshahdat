#!/usr/bin/env bash
set -e
cd /root/moshahdat
git pull --ff-only 2>&1 | tail -1
docker compose up -d --build frontend 2>&1 | tail -1
sleep 8

echo "=== verify the fix is in the served bundle ==="
CHUNK=$(curl -s http://localhost:6688/ | grep -o '/_next/static/chunks/[a-z0-9-]*\.js' | head -3 | tail -1)
echo "checking chunk: $CHUNK"

echo "=== video pages ==="
for s in "video/bjuguv" "video/cosmos-laundromat-أول-فيلم-مفتوح-المصدر"; do
  ENC=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$s")
  echo "$s -> $(curl -s -o /dev/null -w '%{http_code}' http://localhost:6688/$ENC)"
done
