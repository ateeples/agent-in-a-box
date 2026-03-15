#!/usr/bin/env python3
"""
Agent Brain — SQLite-backed persistent memory for Claude Code agents.

Zero dependencies. Just Python 3.7+ and SQLite (built-in).

Usage:
  brain.py store <key> <content> [--category <cat>]
  brain.py recall <query> [--limit <n>]
  brain.py list [--category <cat>]
  brain.py forget <key>
  brain.py stats
  brain.py clock [start|end] [--session <id>] [--detail "..."]
  brain.py sessions [--limit <n>]
  brain.py artifact save <type> <content> [--title <t>] [--tags <t1,t2>]
  brain.py artifact search <query>
  brain.py artifact list [--type <type>]
  brain.py artifact get <id>
"""

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "brain.db"


def _parse_iso(ts):
    """Parse ISO timestamp as UTC, compatible with Python 3.7+."""
    if ts.endswith("+00:00"):
        ts = ts[:-6]
    # Return as UTC-aware datetime
    return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)


def _sanitize_fts(query):
    """Escape user input for safe use in FTS5 MATCH."""
    escaped = query.replace('"', '""')
    return f'"{escaped}"'


def _escape_like(query):
    """Escape LIKE wildcards in user input."""
    return query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _pop_flag(args, flag):
    """Extract a --flag value from args list. Returns (value, remaining_args) or (None, args)."""
    if flag not in args:
        return None, args
    idx = args.index(flag)
    if idx + 1 >= len(args):
        print(f"Error: {flag} requires a value.")
        sys.exit(1)
    value = args[idx + 1]
    return value, args[:idx] + args[idx + 2:]


def _pop_flag_int(args, flag, default):
    """Extract a --flag integer value. Returns (int_value, remaining_args)."""
    val, args = _pop_flag(args, flag)
    if val is None:
        return default, args
    try:
        return int(val), args
    except ValueError:
        print(f"Error: {flag} requires a number, got '{val}'.")
        sys.exit(1)


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            access_count INTEGER DEFAULT 0,
            last_accessed TEXT
        )
    """)

    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            key, content, category,
            content=memories,
            content_rowid=id
        )
    """)

    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
            INSERT INTO memories_fts(rowid, key, content, category)
            VALUES (new.id, new.key, new.content, new.category);
        END
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, key, content, category)
            VALUES ('delete', old.id, old.key, old.content, old.category);
        END
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, key, content, category)
            VALUES ('delete', old.id, old.key, old.content, old.category);
            INSERT INTO memories_fts(rowid, key, content, category)
            VALUES (new.id, new.key, new.content, new.category);
        END
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_clock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            event TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            detail TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            artifact_type TEXT NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            tags TEXT,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS artifacts_fts USING fts5(
            title, content, artifact_type, tags,
            content=artifacts,
            content_rowid=id
        )
    """)

    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS artifacts_ai AFTER INSERT ON artifacts BEGIN
            INSERT INTO artifacts_fts(rowid, title, content, artifact_type, tags)
            VALUES (new.id, new.title, new.content, new.artifact_type, new.tags);
        END
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS artifacts_ad AFTER DELETE ON artifacts BEGIN
            INSERT INTO artifacts_fts(artifacts_fts, rowid, title, content, artifact_type, tags)
            VALUES ('delete', old.id, old.title, old.content, old.artifact_type, old.tags);
        END
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS artifacts_au AFTER UPDATE ON artifacts BEGIN
            INSERT INTO artifacts_fts(artifacts_fts, rowid, title, content, artifact_type, tags)
            VALUES ('delete', old.id, old.title, old.content, old.artifact_type, old.tags);
            INSERT INTO artifacts_fts(rowid, title, content, artifact_type, tags)
            VALUES (new.id, new.title, new.content, new.artifact_type, new.tags);
        END
    """)

    conn.commit()
    return conn


# --- Memory operations ---

def store(key, content, category="general"):
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    try:
        conn.execute(
            "INSERT INTO memories (key, content, category, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (key, content, category, now, now),
        )
    except sqlite3.IntegrityError:
        conn.execute(
            "UPDATE memories SET content=?, category=?, updated_at=? WHERE key=?",
            (content, category, now, key),
        )
    conn.commit()
    conn.close()
    print(f"Stored: {key} [{category}]")


def recall(query, limit=5):
    conn = get_db()
    safe_query = _sanitize_fts(query)
    try:
        rows = conn.execute(
            """SELECT m.key, m.content, m.category, m.updated_at, bm25(memories_fts) as score
               FROM memories_fts f JOIN memories m ON m.id = f.rowid
               WHERE memories_fts MATCH ? ORDER BY score LIMIT ?""",
            (safe_query, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []

    if not rows:
        like_q = f"%{_escape_like(query)}%"
        rows = conn.execute(
            """SELECT key, content, category, updated_at, 0.0 as score
               FROM memories WHERE key LIKE ? ESCAPE '\\' OR content LIKE ? ESCAPE '\\'
               ORDER BY updated_at DESC LIMIT ?""",
            (like_q, like_q, limit),
        ).fetchall()

    for row in rows:
        conn.execute(
            "UPDATE memories SET access_count = access_count + 1, last_accessed = ? WHERE key = ?",
            (datetime.now(timezone.utc).isoformat(), row[0]),
        )
    conn.commit()

    if not rows:
        print("No memories found.")
    else:
        for key, content, category, updated, score in rows:
            print(f"\n--- {key} [{category}] (updated: {updated[:10]}) ---")
            print(content[:500])
            if len(content) > 500:
                print(f"  ... ({len(content)} chars total)")
    conn.close()


def list_memories(category=None):
    conn = get_db()
    if category:
        rows = conn.execute(
            "SELECT key, category, length(content), access_count, updated_at FROM memories WHERE category=? ORDER BY updated_at DESC",
            (category,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT key, category, length(content), access_count, updated_at FROM memories ORDER BY category, updated_at DESC"
        ).fetchall()

    if not rows:
        print("No memories stored.")
    else:
        current_cat = None
        for key, cat, size, access, updated in rows:
            if cat != current_cat:
                print(f"\n[{cat}]")
                current_cat = cat
            print(f"  {key} ({size} chars, {access} accesses, updated {updated[:10]})")
    conn.close()


def forget(key):
    conn = get_db()
    cursor = conn.execute("DELETE FROM memories WHERE key=?", (key,))
    conn.commit()
    if cursor.rowcount:
        print(f"Forgotten: {key}")
    else:
        print(f"Not found: {key}")
    conn.close()


def stats():
    conn = get_db()
    mem_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    art_count = conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
    sess_count = conn.execute("SELECT COUNT(*) FROM session_clock WHERE event='start'").fetchone()[0]

    cats = conn.execute(
        "SELECT category, COUNT(*) FROM memories GROUP BY category ORDER BY COUNT(*) DESC"
    ).fetchall()

    total_chars = conn.execute("SELECT COALESCE(SUM(length(content)), 0) FROM memories").fetchone()[0]

    most_accessed = conn.execute(
        "SELECT key, access_count FROM memories ORDER BY access_count DESC LIMIT 3"
    ).fetchall()

    print(f"Memories: {mem_count} ({total_chars:,} chars)")
    print(f"Artifacts: {art_count}")
    print(f"Sessions logged: {sess_count}")

    if cats:
        print("\nBy category:")
        for cat, count in cats:
            print(f"  {cat}: {count}")

    if most_accessed and most_accessed[0][1] > 0:
        print("\nMost accessed:")
        for key, count in most_accessed:
            if count > 0:
                print(f"  {key}: {count} accesses")

    conn.close()


# --- Session clock ---

def clock(event="check", session_id=None, detail=None):
    conn = get_db()
    now = datetime.now(timezone.utc)
    now_local = datetime.now()
    now_iso = now.isoformat()

    if event == "check":
        print(f"Current time: {now_local.strftime('%Y-%m-%d %H:%M:%S')} local")
        last = conn.execute(
            "SELECT timestamp, detail FROM session_clock WHERE event='end' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if last:
            last_dt = _parse_iso(last[0])
            hours = (now - last_dt).total_seconds() / 3600
            if hours < 1:
                print(f"Last session ended: {(now - last_dt).total_seconds() / 60:.0f} minutes ago")
            elif hours < 24:
                print(f"Last session ended: {hours:.1f} hours ago")
            else:
                print(f"Last session ended: {hours / 24:.1f} days ago")
    else:
        conn.execute(
            "INSERT INTO session_clock (session_id, event, timestamp, detail) VALUES (?, ?, ?, ?)",
            (session_id or "unknown", event, now_iso, detail),
        )
        conn.commit()
        if event == "start":
            print(f"Session started: {now_local.strftime('%Y-%m-%d %H:%M:%S')}")
            last = conn.execute(
                "SELECT timestamp FROM session_clock WHERE event='end' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if last:
                hours = (now - _parse_iso(last[0])).total_seconds() / 3600
                if hours < 1:
                    print(f"Gap: {(now - _parse_iso(last[0])).total_seconds() / 60:.0f} minutes")
                elif hours < 24:
                    print(f"Gap: {hours:.1f} hours")
                else:
                    print(f"Gap: {hours / 24:.1f} days")
        elif event == "end":
            start = conn.execute(
                "SELECT timestamp FROM session_clock WHERE event='start' AND session_id=? ORDER BY id DESC LIMIT 1",
                (session_id or "unknown",),
            ).fetchone()
            if start:
                mins = (now - _parse_iso(start[0])).total_seconds() / 60
                print(f"Session ended: {now_local.strftime('%Y-%m-%d %H:%M:%S')} ({mins:.0f} min)")
            else:
                print(f"Session ended: {now_local.strftime('%Y-%m-%d %H:%M:%S')}")
            if detail:
                print(f"  Summary: {detail}")
    conn.close()


def sessions(n=10):
    conn = get_db()
    starts = conn.execute(
        "SELECT session_id, timestamp, detail FROM session_clock WHERE event='start' ORDER BY id DESC LIMIT ?",
        (n,),
    ).fetchall()

    if not starts:
        print("No sessions logged yet.")
        conn.close()
        return

    print("# Recent Sessions\n")
    for sid, ts, detail in starts:
        start_dt = _parse_iso(ts)
        end_row = conn.execute(
            "SELECT timestamp, detail FROM session_clock WHERE event='end' AND session_id=? AND timestamp > ? ORDER BY id ASC LIMIT 1",
            (sid, ts),
        ).fetchone()
        if end_row:
            dur = (_parse_iso(end_row[0]) - start_dt).total_seconds() / 60
            print(f"  {start_dt.strftime('%Y-%m-%d %H:%M')} — {dur:.0f}min — {end_row[1] or ''}".rstrip())
        else:
            print(f"  {start_dt.strftime('%Y-%m-%d %H:%M')} — (active or no end logged)")
    conn.close()


# --- Artifacts ---

def save_artifact(artifact_type, content, title=None, session_id=None, tags=None):
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    tags_str = ",".join(tags) if tags else None
    cursor = conn.execute(
        "INSERT INTO artifacts (session_id, artifact_type, title, content, tags, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, artifact_type, title, content, tags_str, now),
    )
    conn.commit()
    aid = cursor.lastrowid
    conn.close()
    label = f'"{title}"' if title else f"#{aid}"
    print(f"Artifact saved: {label} [{artifact_type}] ({len(content)} chars)")
    return aid


def search_artifacts(query, limit=5):
    conn = get_db()
    safe_query = _sanitize_fts(query)
    try:
        rows = conn.execute(
            """SELECT a.id, a.title, a.artifact_type, a.content, a.tags, a.created_at, bm25(artifacts_fts) as score
               FROM artifacts_fts f JOIN artifacts a ON a.id = f.rowid
               WHERE artifacts_fts MATCH ? ORDER BY score LIMIT ?""",
            (safe_query, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []

    if not rows:
        like_q = f"%{_escape_like(query)}%"
        rows = conn.execute(
            """SELECT id, title, artifact_type, content, tags, created_at, 0.0
               FROM artifacts WHERE title LIKE ? ESCAPE '\\' OR content LIKE ? ESCAPE '\\'
               ORDER BY created_at DESC LIMIT ?""",
            (like_q, like_q, limit),
        ).fetchall()

    if not rows:
        print("No artifacts found.")
    else:
        for aid, title, atype, content, tags, created, score in rows:
            print(f"\n--- #{aid}: {title or '(untitled)'} [{atype}] ({created[:10]}) ---")
            if tags:
                print(f"  Tags: {tags}")
            print(content[:300])
            if len(content) > 300:
                print(f"  ... ({len(content)} chars total)")
    conn.close()


def list_artifacts(artifact_type=None):
    conn = get_db()
    if artifact_type:
        rows = conn.execute(
            "SELECT id, title, artifact_type, length(content), tags, created_at FROM artifacts WHERE artifact_type=? ORDER BY created_at DESC",
            (artifact_type,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, title, artifact_type, length(content), tags, created_at FROM artifacts ORDER BY created_at DESC"
        ).fetchall()

    if not rows:
        print("No artifacts saved.")
    else:
        for aid, title, atype, size, tags, created in rows:
            tag_str = f" [{tags}]" if tags else ""
            print(f"  #{aid}: {title or '(untitled)'} [{atype}] {size} chars{tag_str} ({created[:10]})")
    conn.close()


def get_artifact(artifact_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id, title, artifact_type, content, tags, created_at FROM artifacts WHERE id=?",
        (artifact_id,),
    ).fetchone()
    if not row:
        print(f"Artifact #{artifact_id} not found.")
    else:
        aid, title, atype, content, tags, created = row
        print(f"# {title or '(untitled)'} [{atype}]")
        print(f"Created: {created}")
        if tags:
            print(f"Tags: {tags}")
        print(f"\n{content}")
    conn.close()


# --- CLI ---

def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "store" and len(args) >= 3:
        cat, args = _pop_flag(args, "--category")
        cat = cat or "general"
        store(args[1], " ".join(args[2:]), cat)

    elif cmd == "recall" and len(args) >= 2:
        limit, args = _pop_flag_int(args, "--limit", 5)
        recall(" ".join(args[1:]), limit)

    elif cmd == "list":
        cat, args = _pop_flag(args, "--category")
        list_memories(cat)

    elif cmd == "forget" and len(args) >= 2:
        forget(args[1])

    elif cmd == "stats":
        stats()

    elif cmd == "clock":
        event = args[1] if len(args) > 1 and not args[1].startswith("--") else "check"
        sid, args = _pop_flag(args, "--session")
        detail, args = _pop_flag(args, "--detail")
        clock(event, sid, detail)

    elif cmd == "sessions":
        n, args = _pop_flag_int(args, "--limit", 10)
        sessions(n)

    elif cmd == "artifact" and len(args) >= 2:
        subcmd = args[1]
        if subcmd == "save" and len(args) >= 4:
            title, args = _pop_flag(args, "--title")
            tags_str, args = _pop_flag(args, "--tags")
            tags = tags_str.split(",") if tags_str else None
            save_artifact(args[2], " ".join(args[3:]), title=title, tags=tags)

        elif subcmd == "search" and len(args) >= 3:
            search_artifacts(" ".join(args[2:]))

        elif subcmd == "list":
            atype, args = _pop_flag(args, "--type")
            list_artifacts(atype)

        elif subcmd == "get" and len(args) >= 3:
            try:
                get_artifact(int(args[2]))
            except ValueError:
                print(f"Error: artifact ID must be a number, got '{args[2]}'.")

        else:
            print("Usage: brain.py artifact [save|search|list|get] ...")

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
