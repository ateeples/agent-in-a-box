#!/bin/bash
# Hook: SessionStart
# Auto-starts the session clock when Claude Code opens.
# Generates a session ID from the current timestamp.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_PY="$SCRIPT_DIR/../../brain.py"

SESSION_ID="session-$(date +%Y%m%d-%H%M%S)-$$"

python3 "$BRAIN_PY" clock start --session "$SESSION_ID" 2>/dev/null

exit 0
