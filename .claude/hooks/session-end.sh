#!/bin/bash
# Hook: SessionEnd
# Auto-ends the session clock when Claude Code closes.
# Finds the active session and closes it.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_PY="$SCRIPT_DIR/../../brain.py"

python3 "$BRAIN_PY" clock end 2>/dev/null

exit 0
