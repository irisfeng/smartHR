#!/bin/bash
# Daily database backup, retain 7 days
set -e
cd "$(dirname "$0")/.."

BACKUP_DIR="${DATA_DIR:-/data}/backups"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/smarthr_${TIMESTAMP}.sql.gz"

docker compose exec -T db pg_dump -U smarthr smarthr | gzip > "$BACKUP_FILE"
echo "Backup saved: $BACKUP_FILE"

# Delete backups older than 7 days
find "$BACKUP_DIR" -name "smarthr_*.sql.gz" -mtime +7 -delete
echo "Old backups cleaned."
