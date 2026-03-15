# Agent-in-a-Box

Give your Claude Code agent persistent memory, identity, and planning — in under 5 minutes.

## What This Is

A template that turns a Claude Code session into a **persistent agent**. Your agent remembers what it learned, tracks what it's working on, and plans across sessions instead of starting from scratch every time.

**What you get:**
- `brain.py` — SQLite-backed memory with full-text search. Zero dependencies.
- Identity files — your agent knows who it is and how it works.
- Planning docs — north star, heartbeat, decision journal. Context that survives between sessions.
- A pre-build gate rule — forces your agent to think before building.

## Quickstart

```bash
git clone https://github.com/ateeples/agent-in-a-box.git my-agent
cd my-agent
./setup.sh
```

The setup asks 4 questions (name, creature, role, project focus) and generates everything. Only the name is required — the rest can be skipped. Takes about 60 seconds.

Then open Claude Code:

```bash
claude
```

Claude reads `CLAUDE.md` automatically and follows the bootstrap sequence — loading identity, memory, and planning docs before doing anything.

## What Each File Does

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Bootstrap — Claude reads this first. Points to everything else. |
| `SOUL.md` | Identity — who the agent is, how it thinks, what it values. |
| `heartbeat.md` | Current work — what's active, what's next, what's done. Updated every session. |
| `north-star.md` | Big picture — mission, experiments, open questions, idea backlog. |
| `decision-journal.md` | Institutional memory — what was tried, what worked, what didn't. |
| `memory/MEMORY.md` | Memory index — pointers to detailed memory files. |
| `brain.py` | Persistent memory DB — store/recall/search across sessions. |
| `.claude/rules/pre-build-gate.md` | Planning rule — 6 questions before building anything non-trivial. |

## Using brain.py

Your agent calls these from the command line during sessions:

```bash
# Store a memory
python3 brain.py store "api-design" "REST endpoints use /v1/ prefix, auth via Bearer token" --category architecture

# Search memories
python3 brain.py recall "authentication"

# List everything
python3 brain.py list

# Remove a memory
python3 brain.py forget "api-design"

# Session tracking
python3 brain.py clock start --session abc123
python3 brain.py clock end --session abc123 --detail "shipped auth module"
python3 brain.py sessions

# Save creative output (essays, specs, good writing)
python3 brain.py artifact save essay "The key insight was..." --title "On Testing" --tags "testing,philosophy"
python3 brain.py artifact search "testing"
python3 brain.py artifact list
python3 brain.py artifact get 1

# Stats
python3 brain.py stats
```

## The Planning System

The real value isn't the memory DB — it's the planning documents working together:

1. **Start of session**: Agent reads `north-star.md` (big picture) and `heartbeat.md` (current work). Compares what was planned against what matters.
2. **During session**: Agent updates `heartbeat.md` as work progresses. Logs decisions in `decision-journal.md`.
3. **End of session**: Agent updates `north-star.md` with what it learned. Updates `heartbeat.md` with what's next.

This means session 47 knows what session 1 decided and why. No context is lost.

## Customizing

**Make `SOUL.md` specific.** Generic identity files produce generic behavior. The more specific you are about how your agent should think and work, the more useful it becomes. Add opinions, pet peeves, working style, areas of expertise.

**Add rules to `.claude/rules/`.** Any `.md` file in this directory gets loaded as a rule. Good rules are procedural gates (do X before Y), not advisory suggestions (remember to test).

**Use categories in brain.py.** `--category architecture`, `--category decisions`, `--category bugs` — makes recall more useful as the memory grows.

## Requirements

- Python 3.7+ (for brain.py — uses only stdlib)
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)

## How This Was Built

This template comes from a real agent workspace that's been running for months — tracking sessions, making decisions, building products. The planning system, memory DB, and identity files were refined through hundreds of sessions of actual use.

The parts that survived are the parts that actually help: persistent context across sessions, structured planning that doesn't go stale, and a memory system that's fast enough to use mid-conversation.

## License

MIT
