import sqlite3
import threading
from datetime import datetime, timezone
from config import DB_PATH

_lock = threading.Lock()


def _connect():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS peers (
            hostname TEXT PRIMARY KEY,
            address TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            status TEXT DEFAULT 'offline'
        );

        CREATE TABLE IF NOT EXISTS connection_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT NOT NULL,
            event TEXT NOT NULL,
            timestamp TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


def insert_message(sender: str, content: str) -> dict:
    with _lock:
        conn = _connect()
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.execute(
            "INSERT INTO messages (sender, content, timestamp) VALUES (?, ?, ?)",
            (sender, content, ts),
        )
        msg_id = cur.lastrowid
        conn.commit()
        conn.close()
        return {"id": msg_id, "sender": sender, "content": content, "timestamp": ts}


def get_messages(limit: int = 100, before_id: int | None = None) -> list[dict]:
    with _lock:
        conn = _connect()
        if before_id:
            rows = conn.execute(
                "SELECT * FROM messages WHERE id < ? ORDER BY id DESC LIMIT ?",
                (before_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM messages ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]


def upsert_peer(hostname: str, address: str, status: str = "online"):
    with _lock:
        conn = _connect()
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            """INSERT INTO peers (hostname, address, last_seen, status)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(hostname) DO UPDATE SET
                   address=excluded.address,
                   last_seen=excluded.last_seen,
                   status=excluded.status""",
            (hostname, address, ts, status),
        )
        conn.commit()
        conn.close()


def update_peer_status(hostname: str, status: str):
    with _lock:
        conn = _connect()
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE peers SET status=?, last_seen=? WHERE hostname=?",
            (status, ts, hostname),
        )
        conn.commit()
        conn.close()


def get_peers() -> list[dict]:
    with _lock:
        conn = _connect()
        rows = conn.execute("SELECT * FROM peers ORDER BY hostname").fetchall()
        conn.close()
        return [dict(r) for r in rows]


def log_connection(target: str, event: str):
    with _lock:
        conn = _connect()
        conn.execute(
            "INSERT INTO connection_log (target, event) VALUES (?, ?)",
            (target, event),
        )
        conn.commit()
        conn.close()


def get_connection_log(limit: int = 50) -> list[dict]:
    with _lock:
        conn = _connect()
        rows = conn.execute(
            "SELECT * FROM connection_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]
