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
| `brain.py` | Persistent memory DB — store, recall, reflect, track sessions. |
| `.claude/hooks/` | Session hooks — auto-start/end the clock when Claude opens and closes. |
| `.claude/settings.json` | Hook configuration — wires hooks to Claude Code events. |
| `.claude/rules/pre-build-gate.md` | Planning rule — 6 questions before building anything non-trivial. |

## Using brain.py

Your agent calls these from the command line during sessions:

```bash
# Session startup — what happened since last time?
python3 brain.py reflect

# Store a memory
python3 brain.py store "api-design" "REST endpoints use /v1/ prefix, auth via Bearer token" --category architecture

# Search memories
python3 brain.py recall "authentication"

# List everything
python3 brain.py list

# Remove a memory
python3 brain.py forget "api-design"

# Session tracking (hooks handle start/end automatically)
python3 brain.py clock                        # check current time + last session gap
python3 brain.py clock end --detail "shipped auth module"  # add a summary to current session
python3 brain.py sessions                     # list recent sessions with durations

# Save creative output (essays, specs, good writing)
python3 brain.py artifact save essay "The key insight was..." --title "On Testing" --tags "testing,philosophy"
python3 brain.py artifact search "testing"
python3 brain.py artifact list
python3 brain.py artifact get 1

# Stats
python3 brain.py stats
```

## Session Hooks

The template includes [Claude Code hooks](https://docs.anthropic.com/en/docs/claude-code/hooks) that automatically track session timing:

- **Session start**: Creates a timestamped session ID and starts the clock via `brain.py`
- **Session end**: Finds the active session and records when it ended

This happens silently in the background — no manual `clock start` / `clock end` needed. Your agent can still call `brain.py sessions` to see session history and durations.

The hooks live in `.claude/hooks/` and are configured in `.claude/settings.json`. You can add your own hooks (e.g., auto-running tests, checking git status) by adding scripts and wiring them in settings.json.

## Session Analysis (optional)

If you want to analyze your agent's behavior across sessions, install [AgentSesh](https://github.com/ateeples/agentsesh):

```bash
pip install agentsesh
```

Then at the end of a session (or any time):

```bash
# Grade a single session
sesh analyze

# See behavioral trends across sessions
sesh analyze --profile
```

AgentSesh scores sessions on outcome (did it ship?), collaboration (how well did human and AI work together?), and process (testing, commit cadence, tool usage). The CLAUDE.md template already includes `sesh analyze` in the session-end routine.

## What This Looks Like Across Sessions

The cold start problem: every Claude Code session starts from zero. By session 3, here's what happens instead.

### Session 1 — Starting fresh

You run `./setup.sh`, name your agent "Atlas", say it's building a task management API. Claude opens, reads `CLAUDE.md`, follows the bootstrap sequence:

```
> python3 brain.py reflect
# Reflect — 2026-03-15 14:30

**First session** — no prior sessions found.

## Stats
- **Memories:** 0
- **Artifacts:** 0
- **Sessions:** 0
```

Nothing yet. But by the end of the session, Atlas has:
- Designed the database schema and stored the decision in `brain.py`
- Updated `heartbeat.md` with what was built and what's next
- Logged "chose PostgreSQL over SQLite for concurrent access" in `decision-journal.md`

### Session 2 — Context carries forward

Next day. Claude opens, runs reflect:

```
> python3 brain.py reflect
# Reflect — 2026-03-16 09:15

**Last session ended:** 18.7 hours ago
**Last session summary:** designed task schema, chose PostgreSQL

## Recent Sessions
- 2026-03-15 14:30 (62min) designed task schema, chose PostgreSQL

## Stats
- **Memories:** 2
- **Artifacts:** 0
- **Sessions:** 1

## Recent Memories
- `db-schema` [architecture] (updated 2026-03-15)
- `auth-approach` [decisions] (updated 2026-03-15)
```

Then reads `heartbeat.md` — sees "Next: implement CRUD endpoints" from yesterday. Reads `north-star.md` — the mission is still "ship MVP by Friday." Picks up exactly where it left off. No re-explaining the project.

### Session 3 — The gap narrows

```
> python3 brain.py reflect
# Reflect — 2026-03-16 13:00

**Last session ended:** 3.2 hours ago
**Last session summary:** CRUD endpoints done, tests passing

## Recent Sessions
- 2026-03-16 09:15 (45min) CRUD endpoints done, tests passing
- 2026-03-15 14:30 (62min) designed task schema, chose PostgreSQL

## Stats
- **Memories:** 5
- **Artifacts:** 0
- **Sessions:** 2

## Recent Memories
- `endpoint-patterns` [architecture] (updated 2026-03-16)
- `test-strategy` [decisions] (updated 2026-03-16)
- `auth-approach` [decisions] (updated 2026-03-15)
- `db-schema` [architecture] (updated 2026-03-15)
- `setup` [system] (updated 2026-03-15)
```

Atlas recalls the PostgreSQL decision from session 1 and the endpoint patterns from session 2. When you say "add filtering to the list endpoint," it doesn't ask what framework you're using, what your schema looks like, or how auth works. It knows.

**Without this template**, session 3 starts the same as session 1 — blank slate, 20 minutes of context-setting before useful work.

## The Planning System

The real value isn't the memory DB — it's the planning documents working together:

1. **Start of session**: Agent runs `brain.py reflect` (time gap, last summary, memory stats). Reads `north-star.md` (big picture) and `heartbeat.md` (current work). Compares what was planned against what matters.
2. **During session**: Agent updates `heartbeat.md` as work progresses. Logs decisions in `decision-journal.md`. Stores reusable knowledge in `brain.py`.
3. **End of session**: Agent updates `north-star.md` with what it learned. Updates `heartbeat.md` with what's next.

Session 47 knows what session 1 decided and why. No context is lost.

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
