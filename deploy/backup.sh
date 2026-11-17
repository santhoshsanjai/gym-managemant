#!/usr/bin/env sh
# Nightly PostgreSQL backup with 14-day retention. Run from cron on the VPS:
#   15 2 * * * /opt/gym/deploy/backup.sh >> /var/log/gym-backup.log 2>&1
# Restore test: gunzip -c FILE | docker compose exec -T db psql -U gym -d gym_restore_test
set -eu
cd "$(dirname "$0")/.."
DEST=${BACKUP_DIR:-/var/backups/gym}
mkdir -p "$DEST"
FILE="$DEST/gym-$(date +%Y%m%d-%H%M%S).sql.gz"
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-gym}" -d "${POSTGRES_DB:-gym}" --no-owner | gzip > "$FILE"
find "$DEST" -name 'gym-*.sql.gz' -mtime +14 -delete
echo "$(date -Is) backup written: $FILE ($(du -h "$FILE" | cut -f1))"
