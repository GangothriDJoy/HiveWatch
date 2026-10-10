#!/usr/bin/env bash
set +e

TARGET="${TARGET_HOST:-cowrie}"
PORT="${TARGET_PORT:-2222}"

USER_FILE="/tmp/hw_users.txt"
PASS_FILE="/tmp/hw_passwords.txt"
OUTPUT_FILE="/tmp/hw_hydra_output.txt"

printf "root\nadmin\ntestuser\n" > "$USER_FILE"
printf "password\n123456\nadmin123\n" > "$PASS_FILE"

hydra \
  -L "$USER_FILE" \
  -P "$PASS_FILE" \
  -t 2 \
  -f \
  -s "$PORT" \
  "ssh://${TARGET}" \
  -o /tmp/hw_hydra_results.txt \
  > "$OUTPUT_FILE" 2>&1

RESULT=$?

echo "[Hydra scenario] target=${TARGET}:${PORT}; hydra_exit=${RESULT}; output=${OUTPUT_FILE}"
exit 0
