#!/usr/bin/env bash
cd /root/moshahdat

echo "=== can frontend container reach nginx? ==="
docker compose exec -T frontend wget -q -O- "http://nginx/api/v1/videos?page_size=1" 2>&1 | head -c 150
echo
echo "=== frontend logs (last errors) ==="
docker compose logs frontend --tail=25 2>&1 | grep -iA2 "error\|fetch" | head -20

echo "=== video page with ENCODED slug ==="
ENC=$(python3 -c "import urllib.parse;print(urllib.parse.quote('video/sintel-فيلم-قصير-مفتوح-المصدر'))")
curl -s -o /dev/null -w '%{http_code}\n' "http://localhost:6688/$ENC"

echo "=== direct next (bypass nginx) with encoded slug ==="
docker compose exec -T frontend wget -q -O- --header='Accept: text/html' "http://localhost:3000/video/sintel-%D9%81%D9%8A%D9%84%D9%85-%D9%82%D8%B5%D9%8A%D8%B1-%D9%85%D9%81%D8%AA%D9%88%D8%AD-%D8%A7%D9%84%D9%85%D8%B5%D8%AF%D8%B1" 2>&1 | head -c 120
echo
