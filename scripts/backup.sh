#!/usr/bin/env bash
# PostgreSQL backup script (plan §35)
# Usage: ./backup.sh [output_dir]
# Cron example: 0 3 * * * /srv/video-platform/scripts/backup.sh
set -euo pipefail

BACKUP_DIR="${1:-../backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
KEEP_DAYS="${KEEP_DAYS:-14}"
FILE="$BACKUP_DIR/video_platform_$STAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "Backing up database to $FILE ..."
docker compose exec -T postgres pg_dump \
    -U "${POSTGRES_USER:-video_user}" \
    -d "${POSTGRES_DB:-video_platform}" \
    --no-owner --clean \
    | gzip > "$FILE"

echo "Done ($(du -h "$FILE" | cut -f1))."

# Retention: remove archives older than KEEP_DAYS
find "$BACKUP_DIR" -name "video_platform_*.sql.gz" -type f -mtime +"$KEEP_DAYS" -delete
echo "Backups older than $KEEP_DAYS days removed."
