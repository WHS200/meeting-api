import subprocess

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
        baseline = subprocess.check_output(
            ["git", "show", "HEAD:database/init.sql"], cwd=migrate.ROOT
        ).decode("utf-8")
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
