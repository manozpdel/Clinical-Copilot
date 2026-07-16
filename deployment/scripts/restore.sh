#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <postgres_dump_file> [chroma_tar_gz_file]"
    exit 1
fi

DUMP_FILE="$1"
CHROMA_ARCHIVE="${2:-}"
DB_CONTAINER="${DB_CONTAINER:-clinical-copilot-postgres}"
DB_NAME="${POSTGRES_DB:-clinical_copilot}"
DB_USER="${POSTGRES_USER:-postgres}"

if [ ! -f "$DUMP_FILE" ]; then
    echo "Error: dump file not found: $DUMP_FILE"
    exit 1
fi

echo "Restoring PostgreSQL database '$DB_NAME' from $DUMP_FILE..."
cat "$DUMP_FILE" | docker exec -i "$DB_CONTAINER" pg_restore \
    -U "$DB_USER" -d "$DB_NAME" --clean --if-exists

if [ -n "$CHROMA_ARCHIVE" ] && [ -f "$CHROMA_ARCHIVE" ]; then
    echo "Restoring Chroma volume from $CHROMA_ARCHIVE..."
    docker run --rm \
        -v clinical-copilot_chroma_data:/data \
        -v "$(pwd)":/backup \
        alpine sh -c "rm -rf /data/* && tar xzf /backup/$CHROMA_ARCHIVE -C /data"
fi

echo "Restore complete."