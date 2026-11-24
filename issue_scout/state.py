"""SQLite persistence for repository scan cursors and sent alerts."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class StateStore:
    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(database_path)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS repositories (
                name TEXT PRIMARY KEY,
                last_issue_number INTEGER NOT NULL,
                initialized INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS notified_issues (
                repo TEXT NOT NULL,
                issue_number INTEGER NOT NULL,
                notified_at TEXT NOT NULL,
                PRIMARY KEY (repo, issue_number)
            )
            """
        )
        self.connection.commit()

    def get_cursor(self, repo: str) -> int | None:
        row = self.connection.execute(
            "SELECT last_issue_number FROM repositories WHERE name = ? AND initialized = 1",
            (repo,),
        ).fetchone()
        return int(row[0]) if row is not None else None

    def initialize_repo(self, repo: str, last_issue_number: int) -> None:
        self.connection.execute(
            """
            INSERT INTO repositories (name, last_issue_number, initialized)
            VALUES (?, ?, 1)
            ON CONFLICT(name) DO UPDATE SET
                last_issue_number = excluded.last_issue_number,
                initialized = 1
            """,
            (repo, last_issue_number),
        )
        self.connection.commit()

    def update_cursor(self, repo: str, last_issue_number: int) -> None:
        self.connection.execute(
            "UPDATE repositories SET last_issue_number = ? WHERE name = ? AND initialized = 1",
            (last_issue_number, repo),
        )
        self.connection.commit()

    def was_notified(self, repo: str, issue_number: int) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM notified_issues WHERE repo = ? AND issue_number = ?",
            (repo, issue_number),
        ).fetchone()
        return row is not None

    def mark_notified(self, repo: str, issue_number: int) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        self.connection.execute(
            "INSERT OR IGNORE INTO notified_issues (repo, issue_number, notified_at) VALUES (?, ?, ?)",
            (repo, issue_number, timestamp),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
