
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="${ROOT_DIR}/data/cowrie/cowrie.json"
DEST_DIR="${ROOT_DIR}/data/out"

mkdir -p "$DEST_DIR"

if [[ ! -f "$SOURCE" ]]; then
    echo "ERROR: Cowrie log not found: $SOURCE" >&2
    exit 1
fi

TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"
DEST="${DEST_DIR}/cowrie-${TIMESTAMP}.json"

cp "$SOURCE" "$DEST"
echo "Exported Cowrie log to: $DEST"
