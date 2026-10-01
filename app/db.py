import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "crm.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT NOT NULL,
            request TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'manual',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS lead_tags (
            lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
            tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY (lead_id, tag_id)
        );
        """
    )
    conn.commit()
    conn.close()


def create_lead(name: str, contact: str, request: str, source: str = "manual") -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO leads (name, contact, request, source, created_at) VALUES (?, ?, ?, ?, ?)",
        (name, contact, request, source, datetime.utcnow().isoformat(timespec="seconds")),
    )
    conn.commit()
    lead_id = cur.lastrowid
    conn.close()
    return lead_id


def list_leads(tag_filter: str | None = None):
    conn = get_conn()
    if tag_filter:
        rows = conn.execute(
            """
            SELECT leads.* FROM leads
            JOIN lead_tags ON lead_tags.lead_id = leads.id
            JOIN tags ON tags.id = lead_tags.tag_id
            WHERE tags.name = ?
            ORDER BY leads.created_at DESC
            """,
            (tag_filter,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM leads ORDER BY created_at DESC").fetchall()
    leads = [dict(r) for r in rows]
    for lead in leads:
        lead["tags"] = get_tags_for_lead(lead["id"], conn)
    conn.close()
    return leads


def get_tags_for_lead(lead_id: int, conn=None):
    own_conn = conn is None
    if own_conn:
        conn = get_conn()
    rows = conn.execute(
        """
        SELECT tags.id, tags.name FROM tags
        JOIN lead_tags ON lead_tags.tag_id = tags.id
        WHERE lead_tags.lead_id = ?
        ORDER BY tags.name
        """,
        (lead_id,),
    ).fetchall()
    if own_conn:
        conn.close()
    return [dict(r) for r in rows]


def all_tags():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM tags ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_tag_to_lead(lead_id: int, tag_name: str):
    tag_name = tag_name.strip()
    if not tag_name:
        return
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
    tag_row = conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name,)).fetchone()
    conn.execute(
        "INSERT OR IGNORE INTO lead_tags (lead_id, tag_id) VALUES (?, ?)",
        (lead_id, tag_row["id"]),
    )
    conn.commit()
    conn.close()


def remove_tag_from_lead(lead_id: int, tag_id: int):
    conn = get_conn()
    conn.execute(
        "DELETE FROM lead_tags WHERE lead_id = ? AND tag_id = ?", (lead_id, tag_id)
    )
    conn.commit()
    conn.close()


def get_lead(lead_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    lead = dict(row) if row else None
    if lead:
        lead["tags"] = get_tags_for_lead(lead_id, conn)
    conn.close()
    return lead
