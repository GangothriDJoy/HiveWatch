#!/usr/bin/env bash
set -euo pipefail

# Label this scan, for example: before or after.
LABEL="${1:-scan}"

# Save evidence inside the project.
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EVIDENCE_DIR="$PROJECT_DIR/docs/evidence"
OUTPUT_FILE="$EVIDENCE_DIR/nmap_before_after.txt"

mkdir -p "$EVIDENCE_DIR"

{
    echo
    echo "========================================"
    echo "Scan label: $LABEL"
    echo "Date: $(date -Is)"
    echo "Target: 127.0.0.1, port 2222"
    echo "========================================"

    nmap -sV -p 2222 127.0.0.1
} 2>&1 | tee -a "$OUTPUT_FILE"
