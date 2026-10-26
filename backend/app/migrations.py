"""Small additive SQLite migrations for the college project."""

from datetime import datetime, timezone
import sqlite3
from pathlib import Path


def upgrade_microsoft_identity(database_path: str) -> str | None:
    """Create the identity-link table, backing up an existing database first."""
    path = Path(database_path)
    if not path.exists():
        return None

    with sqlite3.connect(path) as connection:
        table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='microsoft_identities'"
        ).fetchone()
        nonce_table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='microsoft_auth_nonces'"
        ).fetchone()
    if table_exists and nonce_table_exists:
        return None

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = path.with_name(path.name + f".pre_microsoft.{stamp}.bak")
    # SQLite's backup API gives a consistent copy even if the DB is open.
    with sqlite3.connect(path) as source, sqlite3.connect(backup_path) as backup:
        source.backup(backup)
    with sqlite3.connect(backup_path) as backup:
        if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            backup_path.unlink(missing_ok=True)
            raise RuntimeError("The pre-migration SQLite backup did not pass integrity_check.")

    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """CREATE TABLE IF NOT EXISTS microsoft_identities (
                id INTEGER PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                object_id VARCHAR NOT NULL,
                user_id INTEGER NOT NULL UNIQUE,
                FOREIGN KEY(user_id) REFERENCES users(id),
                UNIQUE(tenant_id, object_id)
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS microsoft_auth_nonces (
                nonce VARCHAR PRIMARY KEY,
                expires_at DATETIME NOT NULL
            )"""
        )
        connection.commit()
    return str(backup_path)
