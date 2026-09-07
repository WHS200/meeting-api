"""Apply YANAWA SQL migrations once, in filename order.

Run from the repository root with the same DB_* environment variables as Flask:
    python database/migrate.py
Use --check for a read-only pre-deploy status check.
"""
import argparse
import hashlib
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = Path(__file__).resolve().parent / "migrations"


def connect():
    load_dotenv(ROOT / ".env")
    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        charset="utf8mb4",
        time_zone="+00:00",
    )


def migrations():
    return sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(connection):
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
        version VARCHAR(100) PRIMARY KEY,
        checksum CHAR(64) NOT NULL,
        applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    # Baseline databases created by the current init.sql; do not replay CREATE/ALTER statements.
    cursor.execute("""SELECT 1 FROM information_schema.tables
        WHERE table_schema = DATABASE() AND table_name = 'sport_proposals'""")
    if cursor.fetchone():
        for path in migrations():
            cursor.execute("""INSERT IGNORE INTO schema_migrations (version, checksum)
                VALUES (%s, %s)""", (path.name, digest(path)))
    else:
        # Older installations already contain the 001 column. Baseline only that migration.
        cursor.execute("""SELECT 1 FROM information_schema.columns
            WHERE table_schema = DATABASE() AND table_name = 'meetings'
            AND column_name = 'required_skill_level'""")
        if cursor.fetchone():
            first = migrations()[0]
            cursor.execute("""INSERT IGNORE INTO schema_migrations (version, checksum)
                VALUES (%s, %s)""", (first.name, digest(first)))
    connection.commit()
    cursor.close()


def preflight(cursor, filename):
    if filename.startswith("009_"):
        cursor.execute("SELECT COUNT(*) AS count FROM meetings WHERE meeting_time > '23:29:59'")
        count = cursor.fetchone()["count"]
        if count:
            raise RuntimeError(
                f"009 blocked: {count} legacy meeting(s) start after 23:29:59. "
                "Correct their times before adding same-day end_time."
            )
    if filename.startswith("010_"):
        cursor.execute("""SELECT REGEXP_REPLACE(TRIM(sport_name), '[[:space:]]+', ' ') AS name,
            COUNT(*) AS count FROM sports GROUP BY name HAVING count > 1 LIMIT 1""")
        duplicate = cursor.fetchone()
        if duplicate:
            raise RuntimeError(f"010 blocked: normalized sport name collision: {duplicate['name']!r}.")


def status(connection):
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""SELECT 1 FROM information_schema.tables
        WHERE table_schema = DATABASE() AND table_name = 'schema_migrations'""")
    has_table = cursor.fetchone() is not None
    if has_table:
        cursor.execute("SELECT version, checksum FROM schema_migrations")
        applied = {row["version"]: row["checksum"] for row in cursor.fetchall()}
    else:
        applied = {}
    cursor.close()
    result = []
    for path in migrations():
        current = digest(path)
        state = "pending" if path.name not in applied else "applied"
        if path.name in applied and applied[path.name] != current:
            state = "checksum-mismatch"
        result.append((path, state))
    return result


def apply(connection):
    prepare(connection)
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT GET_LOCK('yanawa_schema_migrations', 30) AS acquired")
    if cursor.fetchone()["acquired"] != 1:
        cursor.close()
        raise RuntimeError("Could not acquire migration lock.")
    try:
        for path, state in status(connection):
            if state == "checksum-mismatch":
                raise RuntimeError(f"Previously applied migration changed: {path.name}")
            if state == "applied":
                continue
            preflight(cursor, path.name)
            cursor.execute(path.read_text(encoding="utf-8"))
            while cursor.nextset():
                if cursor.with_rows:
                    cursor.fetchall()
            cursor.execute("INSERT INTO schema_migrations (version, checksum) VALUES (%s, %s)",
                           (path.name, digest(path)))
            connection.commit()
            print(f"applied {path.name}")
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.execute("SELECT RELEASE_LOCK('yanawa_schema_migrations')")
        cursor.fetchone()
        cursor.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="show migration status without applying")
    args = parser.parse_args()
    connection = connect()
    try:
        rows = status(connection)
        if args.check:
            for path, state in rows:
                print(f"{state:17} {path.name}")
            if any(state != "applied" for _, state in rows):
                raise SystemExit(1)
        else:
            apply(connection)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
