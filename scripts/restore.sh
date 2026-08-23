#!/usr/bin/env bash
# Restore a gzip backup into the running Postgres container.
# Usage: ./restore.sh backups/video_platform_20260101_030000.sql.gz
set -euo pipefail

FILE="${1:?Usage: ./restore.sh <backup.sql.gz>}"

if [ ! -f "$FILE" ]; then
    echo "Backup file not found: $FILE"
    exit 1
fi

echo "WARNING: this will replace the current database contents."
read -r -p "Type YES to continue: " confirm
[ "$confirm" = "YES" ] || { echo "Aborted."; exit 1; }

gunzip -c "$FILE" | docker compose exec -T postgres psql \
    -U "${POSTGRES_USER:-video_user}" \
    -d "${POSTGRES_DB:-video_platform}"

echo "Restore complete."
