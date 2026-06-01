import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "data/history.db")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   DATETIME NOT NULL,
                vm_name     TEXT NOT NULL,
                vm_ip       TEXT NOT NULL,
                script_id   TEXT NOT NULL,
                script_name TEXT NOT NULL,
                parameters  TEXT NOT NULL,
                status      TEXT NOT NULL,
                stdout      TEXT,
                stderr      TEXT
            )
        """)
        conn.commit()


def save_run(vm_name, vm_ip, script_id, script_name, parameters, status, stdout, stderr):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO runs
               (timestamp, vm_name, vm_ip, script_id, script_name, parameters, status, stdout, stderr)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.utcnow().isoformat(), vm_name, vm_ip,
                script_id, script_name, json.dumps(parameters),
                status, stdout, stderr,
            ),
        )
        conn.commit()


def get_runs(vm_name=None, category=None, limit=100):
    query = "SELECT * FROM runs"
    conditions = []
    params = []
    if vm_name:
        conditions.append("vm_name = ?")
        params.append(vm_name)
    if category:
        conditions.append("script_id LIKE ?")
        params.append(f"{category}/%")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_run(run_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return dict(row) if row else None
