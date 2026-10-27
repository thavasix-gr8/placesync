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


def upgrade_resume_feature(database_path: str) -> str | None:
    """Add resume versions and applicant counts without removing existing data."""
    path = Path(database_path)
    if not path.exists():
        return None

    with sqlite3.connect(path) as connection:
        tables = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if not {"users", "drives", "applications"}.issubset(tables):
            return None
        application_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(applications)")
        }
        drive_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(drives)")
        }
        resume_table_exists = "student_resumes" in tables
        needs_upgrade = (
            not resume_table_exists
            or "resume_id" not in application_columns
            or "applicant_count" not in drive_columns
            or "created_by_id" not in drive_columns
        )
        if not needs_upgrade:
            return None

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = path.with_name(path.name + f".pre_resume.{stamp}.bak")
    with sqlite3.connect(path) as source, sqlite3.connect(backup_path) as backup:
        source.backup(backup)
    with sqlite3.connect(backup_path) as backup:
        integrity = backup.execute("PRAGMA integrity_check").fetchone()[0]
        backup_tables = [
            row[0] for row in backup.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        backup_counts = {
            table: backup.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in backup_tables
        }
    with sqlite3.connect(path) as source:
        source_tables = [
            row[0] for row in source.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        source_counts = {
            table: source.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in source_tables
        }
    if integrity != "ok" or source_counts != backup_counts:
        backup_path.unlink(missing_ok=True)
        raise RuntimeError("The pre-resume database backup could not be verified.")

    with sqlite3.connect(path) as connection:
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS student_resumes (
                    id INTEGER PRIMARY KEY,
                    student_id INTEGER NOT NULL,
                    storage_name VARCHAR NOT NULL UNIQUE,
                    original_filename VARCHAR NOT NULL,
                    uploaded_at DATETIME NOT NULL,
                    FOREIGN KEY(student_id) REFERENCES users(id)
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS ix_student_resumes_student_id "
                "ON student_resumes(student_id)"
            )
            if "resume_id" not in application_columns:
                connection.execute(
                    "ALTER TABLE applications ADD COLUMN resume_id INTEGER "
                    "REFERENCES student_resumes(id)"
                )
            if "applicant_count" not in drive_columns:
                connection.execute(
                    "ALTER TABLE drives ADD COLUMN applicant_count INTEGER NOT NULL DEFAULT 0"
                )
            if "created_by_id" not in drive_columns:
                connection.execute(
                    "ALTER TABLE drives ADD COLUMN created_by_id INTEGER REFERENCES users(id)"
                )

            connection.execute(
                """UPDATE drives
                   SET applicant_count = (
                       SELECT COUNT(*) FROM applications
                       WHERE applications.drive_id = drives.id
                   )"""
            )
            admins = [
                row[0] for row in connection.execute(
                    "SELECT id FROM users WHERE role='admin' ORDER BY id"
                )
            ]
            if len(admins) == 1:
                connection.execute(
                    "UPDATE drives SET created_by_id = ? WHERE created_by_id IS NULL",
                    (admins[0],),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    with sqlite3.connect(path) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("The resume schema upgrade did not pass integrity_check.")
    return str(backup_path)
