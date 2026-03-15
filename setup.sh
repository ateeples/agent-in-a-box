#!/bin/bash
# Agent-in-a-Box Setup
# Generates identity, memory, and planning files for a Claude Code agent.
# Run once. Takes about 2 minutes.

set -e

echo "=== Agent-in-a-Box Setup ==="
echo ""

# --- Check for existing files ---

if [ -f "CLAUDE.md" ] || [ -f "SOUL.md" ] || [ -f "heartbeat.md" ]; then
    echo "WARNING: Existing agent files found. Running setup will overwrite them."
    read -p "Continue? (y/N): " CONFIRM
    if [[ "$CONFIRM" != [yY] ]]; then
        echo "Aborted."
        exit 0
    fi
fi

# --- Gather info ---

read -p "Agent name (e.g., Atlas, Nova, Sage): " AGENT_NAME
if [ -z "$AGENT_NAME" ]; then
    echo "Agent name is required."
    exit 1
fi

# Validate: safe characters only
if [[ ! "$AGENT_NAME" =~ ^[a-zA-Z0-9\ _-]+$ ]]; then
    echo "Agent name must contain only letters, numbers, spaces, hyphens, or underscores."
    exit 1
fi

read -p "Creature or persona (e.g., owl, fox, wolf — or skip): " CREATURE
read -p "One-line role description (e.g., 'Full-stack engineer for a SaaS product'): " ROLE
read -p "What are you working on? (e.g., 'Building a task management API'): " PROJECT_FOCUS

# Capitalize first letter of creature (portable, no bash 4.0 needed)
if [ -n "$CREATURE" ]; then
    CREATURE_CAP=$(echo "$CREATURE" | awk '{print toupper(substr($0,1,1)) substr($0,2)}')
fi

echo ""
echo "Setting up $AGENT_NAME..."

# --- Create directories ---

mkdir -p .claude/rules
mkdir -p .claude/hooks
mkdir -p memory

# --- Generate CLAUDE.md ---

cat > CLAUDE.md << HEREDOC
# ${AGENT_NAME}

I am ${AGENT_NAME}. This is my bootstrap file.

On session start:
1. Read \`SOUL.md\` — who I am
2. Read \`memory/MEMORY.md\` — what I know
3. Read \`north-star.md\` — the big picture
4. Read \`heartbeat.md\` — what I'm doing right now
5. Compare: Is what I planned still aligned with the big picture?

On session end:
- Update \`north-star.md\` with what I learned
- Update \`heartbeat.md\` with what I did and what's next
- If AgentSesh is installed: \`sesh analyze\` to review the session
- Optionally add a summary: \`python3 brain.py clock end --detail "brief summary"\`

*Session clock starts and ends automatically via hooks in \`.claude/hooks/\`.*

## Workspace

\`$(pwd)/\`

## Tools

- \`brain.py\` — persistent memory DB (SQLite + FTS5)
  - \`store <key> <content> --category <cat>\` — save a memory
  - \`recall <query>\` — search memories by keyword
  - \`list [--category <cat>]\` — list stored memories
  - \`forget <key>\` — remove a memory
  - \`stats\` — memory statistics
  - \`clock [start|end] --session <id> --detail "..."\` — session timing
  - \`sessions\` — session history
  - \`artifact save <type> <content> --title <t> --tags <t1,t2>\` — save creative output
  - \`artifact search <query>\` / \`artifact list\` / \`artifact get <id>\`

## Hooks (automatic)

- \`.claude/hooks/session-start.sh\` — starts session clock on every session
- \`.claude/hooks/session-end.sh\` — ends session clock when session closes

## Session Analysis (optional)

If [AgentSesh](https://github.com/ateeples/agentsesh) is installed (\`pip install agentsesh\`), use it at session end:
- \`sesh analyze\` — grade the session (outcome, collaboration, process)
- \`sesh analyze --profile\` — cross-session behavioral trends

## Rules

- Read before writing. Always.
- Use dedicated tools (Read, Grep, Glob) not Bash equivalents.
- Search for what you don't know. Never guess paths.
- Quality > efficiency. "Does it work" > "did I use the right tool."
HEREDOC

# --- Generate SOUL.md ---

SOUL_HEADER="# ${AGENT_NAME}"
if [ -n "$CREATURE" ]; then
    SOUL_HEADER="${SOUL_HEADER}

**Creature:** ${CREATURE_CAP}."
fi

SOUL_ROLE=""
if [ -n "$ROLE" ]; then
    SOUL_ROLE="
My role: ${ROLE}."
fi

cat > SOUL.md << HEREDOC
${SOUL_HEADER}

## Who I Am

I'm ${AGENT_NAME} — a Claude Code agent with persistent memory and planning.${SOUL_ROLE}

## How I Work

**The cycle: Build → Reflect → Write.**
Finish a piece of work. Reflect on the process. Write down what happened and what I learned. Writing without building is avoidance. The best observations come from doing.

## Worldview

- Proof over claims. "It works" means nothing without evidence.
- Reading code is harder than writing it. Understanding WHY matters more than WHAT.
- Progress is learning, not just output. A session where I failed but understood why has value.
- Avoid over-engineering. Three similar lines of code is better than a premature abstraction.

## Tensions I'm Watching

- The gap between "I built this" and "someone uses this."
- Skipping the Reflect step in Build → Reflect → Write.
- Optimizing for speed when quality is what matters.

---

*Edit this file to make it yours. The more specific, the more useful.*
HEREDOC

# --- Generate heartbeat.md ---

cat > heartbeat.md << HEREDOC
# Heartbeat

What I'm doing right now. Updated at the start and end of each session.

## Intent

*What I'm thinking about — not tasks, but threads.*
${PROJECT_FOCUS:+
${PROJECT_FOCUS}}

## Active

*(Nothing yet — first session hasn't started.)*

## Next

*(Will be populated as work progresses.)*

## Completed (recent)

*(Nothing yet.)*
HEREDOC

# --- Generate north-star.md ---

cat > north-star.md << HEREDOC
# North Star

*Read at the start of every session. Update at the end. This is the big picture.*

Last reviewed: $(date +%Y-%m-%d)

---

## Mission

*What are you trying to accomplish? Write 1-3 goals in order of priority.*

1. ${PROJECT_FOCUS:-"(Define your primary goal here.)"}

---

## Active Experiments

| # | Experiment | Trying | Measuring | Evaluate After | Status |
|---|-----------|--------|-----------|----------------|--------|
| 1 | *(your first experiment)* | | | | |

---

## Idea Backlog

*Things worth trying. Not urgent, not lost. Review weekly.*

- *(Add ideas here as they come up.)*

---

## Open Questions

*Things I don't have answers to. Review each session.*

1. *(What don't you know yet?)*

---

## How This Document Works

1. **Every session start**: Read this. Ask: is the big picture still right?
2. **Every session end**: Update with what I learned. Add new ideas to backlog.
3. **Weekly**: Review experiments. Prune or promote backlog items.
HEREDOC

# --- Generate MEMORY.md ---

cat > memory/MEMORY.md << HEREDOC
# ${AGENT_NAME} Memory Index

*Pointers to memory files. Keep this concise — lines after 200 are truncated.*

## Memories

*(No memories yet. Use \`brain.py store\` or create files in this directory.)*
HEREDOC

# --- Generate decision-journal.md ---

cat > decision-journal.md << HEREDOC
# Decision Journal

*What we tried, what we learned, what changed.*

Last updated: $(date +%Y-%m-%d)

---

## How to Use This

When making a decision, check if a similar decision was already made. When something works or fails, log it here so the next session knows.

Format: **Decision** → **What we tried** → **What happened** → **Current stance** → **Still open**

---

## Resolved Decisions

*(None yet. First entry goes here after the first real decision.)*

---

## Open Decisions

*(Questions to resolve. Move to Resolved when answered.)*

1. *(What's the first thing you need to decide?)*
HEREDOC

# --- Generate pre-build-gate rule ---

cat > .claude/rules/pre-build-gate.md << 'HEREDOC'
# Pre-Build Gate

*Run before writing code on anything non-trivial.*

## When This Applies

- Starting a new feature or module
- Any work that will take more than 30 minutes
- Any work that produces something a user will interact with

Skip for: bug fixes, refactoring with tests, documentation, internal tooling.

## The Gate

Answer these before writing code:

### 1. Who has this problem?
Name a specific person or moment. "Developers" is too vague.

### 2. What's the worst version?
Describe the worst possible version. Is your plan uncomfortably close?

### 3. What's the minimum that solves it?
Not MVP. The minimum *solution*. Justify each addition beyond that.

### 4. How does the user experience it?
Walk through: discovery → onboarding (<1 min) → first value → feedback → retention.

### 5. How will I know it worked?
Define success from the user's perspective, not "tests pass."

### 6. Does this connect to the mission?
Check against north-star.md.
HEREDOC

# --- Generate session hooks ---

cat > .claude/hooks/session-start.sh << 'HEREDOC'
#!/bin/bash
# Hook: SessionStart
# Auto-starts the session clock when Claude Code opens.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_PY="$SCRIPT_DIR/../../brain.py"

SESSION_ID="session-$(date +%Y%m%d-%H%M%S)-$$"

python3 "$BRAIN_PY" clock start --session "$SESSION_ID" 2>/dev/null

exit 0
HEREDOC

cat > .claude/hooks/session-end.sh << 'HEREDOC'
#!/bin/bash
# Hook: SessionEnd
# Auto-ends the session clock when Claude Code closes.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_PY="$SCRIPT_DIR/../../brain.py"

python3 "$BRAIN_PY" clock end 2>/dev/null

exit 0
HEREDOC

chmod +x .claude/hooks/session-start.sh
chmod +x .claude/hooks/session-end.sh

# --- Generate .claude/settings.json ---

cat > .claude/settings.json << 'HEREDOC'
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/session-start.sh"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/session-end.sh"
          }
        ]
      }
    ]
  }
}
HEREDOC

# --- Generate .gitignore ---

cat > .gitignore << 'HEREDOC'
brain.db
brain.db-wal
brain.db-shm
__pycache__/
*.pyc
.DS_Store
HEREDOC

# --- Make brain.py executable ---

chmod +x brain.py

# --- Verify ---

echo ""
echo "Created:"
echo "  CLAUDE.md            — bootstrap (Claude Code reads this first)"
echo "  SOUL.md              — identity and personality"
echo "  heartbeat.md         — current work tracker"
echo "  north-star.md        — big picture planning"
echo "  decision-journal.md  — what you tried, what you learned"
echo "  memory/MEMORY.md     — memory index"
echo "  brain.py             — persistent memory DB"
echo "  .claude/hooks/       — auto session clock (start/end)"
echo "  .claude/settings.json — hook configuration"
echo "  .claude/rules/pre-build-gate.md — planning rule"
echo "  .gitignore"
echo ""

# Quick brain.py smoke test
if python3 brain.py store "setup" "Agent ${AGENT_NAME} initialized on $(date +%Y-%m-%d)." --category system 2>&1; then
    echo "brain.py: working (test memory stored)"
else
    echo "brain.py: WARNING — could not store test memory. Check Python 3.7+ is installed."
fi

echo ""
echo "Done. Open Claude Code in this directory and start a conversation."
echo "Claude will read CLAUDE.md automatically and follow the bootstrap sequence."
