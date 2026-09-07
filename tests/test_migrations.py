from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from database import migrate
from mysql_support import DB_NAME, MySQLTestCase, connect, execute_script


class MigrationTest(MySQLTestCase):
    def test_main_baseline_migrates_to_current_schema(self):
        migration_db = "yanawa_codex_migration_test"
        root = connect(None)
        cursor = root.cursor()
        cursor.execute("DROP DATABASE IF EXISTS yanawa_codex_migration_test")
        cursor.execute("CREATE DATABASE yanawa_codex_migration_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
        cursor.close()
        root.close()
        connection = mysql_connection(migration_db)
        baseline = (migrate.ROOT / "tests" / "fixtures" / "baseline_init.sql").read_text(encoding="utf-8")
        execute_script(connection, baseline)
        migrate.apply(connection)

        expected = schema_signature(connect(), DB_NAME)
        actual = schema_signature(connection, migration_db)
        # schema_migrations exists only on upgraded DBs and is deliberately excluded.
        self.assertEqual(actual, expected)
        states = migrate.status(connection)
        self.assertTrue(all(state == "applied" for _, state in states))
        # Re-running is a no-op.
        migrate.apply(connection)
        connection.close()

    def test_latest_init_sql_is_explicitly_baselined(self):
        database = "yanawa_codex_init_migration_test"
        root = connect(None)
        cursor = root.cursor()
        cursor.execute(f"DROP DATABASE IF EXISTS `{database}`")
        cursor.execute(f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
        cursor.close()
        root.close()
        connection = mysql_connection(database)
        execute_script(connection, (migrate.ROOT / "database" / "init.sql").read_text(encoding="utf-8"))
        states = migrate.status(connection)
        self.assertTrue(all(state == "applied" for _, state in states))
        migrate.prepare(connection)
        migrate.apply(connection)
        self.assertTrue(all(state == "applied" for _, state in migrate.status(connection)))
        connection.close()

    def test_init_baseline_leaves_future_migration_pending(self):
        connection = connect()
        cursor = connection.cursor()
        cursor.execute("INSERT INTO schema_migrations (version, checksum) VALUES (%s, %s)",
                       ("__INIT_SQL_BASELINE__:010_sports_management.sql", "0" * 64))
        connection.commit()
        cursor.close()
        with TemporaryDirectory() as directory:
            future = Path(directory) / "011_future.sql"
            future.write_text("SELECT 1;", encoding="utf-8")
            with patch.object(migrate, "migrations", return_value=migrate.migrations() + [future]):
                states = dict((path.name, state) for path, state in migrate.status(connection))
        self.assertEqual(states["010_sports_management.sql"], "applied")
        self.assertEqual(states["011_future.sql"], "pending")
        connection.close()

    def test_partial_sport_proposals_does_not_baseline_all(self):
        database = "yanawa_codex_partial_migration_test"
        root = connect(None)
        cursor = root.cursor()
        cursor.execute(f"DROP DATABASE IF EXISTS `{database}`")
        cursor.execute(f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
        cursor.close()
        root.close()
        connection = mysql_connection(database)
        execute_script(connection, (migrate.ROOT / "tests" / "fixtures" / "baseline_init.sql").read_text(encoding="utf-8"))
        execute_script(connection, (migrate.ROOT / "database" / "migrations" / "001_add_meeting_required_skill_level.sql").read_text(encoding="utf-8"))
        cursor = connection.cursor()
        cursor.execute("CREATE TABLE sport_proposals (proposal_id INT PRIMARY KEY)")
        connection.commit()
        cursor.close()
        migrate.prepare(connection)
        states = dict((path.name, state) for path, state in migrate.status(connection))
        self.assertEqual(states["001_add_meeting_required_skill_level.sql"], "applied")
        self.assertEqual(states["010_sports_management.sql"], "pending")
        connection.close()


def mysql_connection(database):
    import os
    import mysql.connector
    return mysql.connector.connect(
        host="127.0.0.1", port=int(os.getenv("TEST_MYSQL_PORT", "3307")),
        user="root", password=os.getenv("TEST_MYSQL_PASSWORD", ""),
        database=database, charset="utf8mb4", time_zone="+00:00"
    )


def schema_signature(connection, database):
    cursor = connection.cursor()
    cursor.execute("""SELECT table_name, column_name, column_type, is_nullable, column_default,
        extra FROM information_schema.columns WHERE table_schema = %s
        AND table_name <> 'schema_migrations' ORDER BY table_name, ordinal_position""", (database,))
    columns = cursor.fetchall()
    cursor.execute("""SELECT table_name, index_name, non_unique,
        GROUP_CONCAT(column_name ORDER BY seq_in_index) FROM information_schema.statistics
        WHERE table_schema = %s AND table_name <> 'schema_migrations'
        GROUP BY table_name,index_name,non_unique ORDER BY table_name,index_name""", (database,))
    indexes = cursor.fetchall()
    cursor.execute("""SELECT table_name, constraint_name, constraint_type FROM information_schema.table_constraints
        WHERE table_schema = %s AND table_name <> 'schema_migrations'
        ORDER BY table_name,constraint_name""", (database,))
    constraints = cursor.fetchall()
    cursor.close()
    return columns, indexes, constraints
