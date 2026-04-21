#!/bin/bash
AUDIT_SCRIPT="$(dirname "$0")/audit.py"

if [[ $# -lt 1 ]]; then
  echo "Usage: $(basename "$0") <input file> [<output file>]"
  exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="${2:-$(dirname "$INPUT_FILE")/audit.out}"

python3 "$AUDIT_SCRIPT" --input-file "$INPUT_FILE" --output-file "$OUTPUT_FILE"