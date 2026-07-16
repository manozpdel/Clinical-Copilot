#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
DB_CONTAINER="${DB_CONTAINER:-clinical-copilot-postgres}"
DB_NAME="${POSTGRES_DB:-clinical_copilot}"
DB_USER="${POSTGRES_USER:-postgres}"

mkdir -p "$BACKUP_DIR"

echo "Backing up PostgreSQL database '$DB_NAME'..."
docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" --format=custom \
    > "$BACKUP_DIR/postgres_${TIMESTAMP}.dump"

echo "Backing up Chroma volume..."
docker run --rm \
    -v clinical-copilot_chroma_data:/data:ro \
    -v "$(pwd)/$BACKUP_DIR":/backup \
    alpine tar czf "/backup/chroma_${TIMESTAMP}.tar.gz" -C /data .

echo "Pruning backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -type f -mtime "+${RETENTION_DAYS}" -delete

echo "Backup complete: $BACKUP_DIR/postgres_${TIMESTAMP}.dump, $BACKUP_DIR/chroma_${TIMESTAMP}.tar.gz"