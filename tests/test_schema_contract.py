import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SchemaContractTest(unittest.TestCase):
    def test_common_schema_contains_integrated_columns(self):
        schema = (ROOT / "database" / "init.sql").read_text(encoding="utf-8")

        self.assertRegex(
            schema,
            r"(?s)CREATE TABLE meetings \(.*?meeting_time TIME NOT NULL.*?\);",
        )
        self.assertRegex(
            schema,
            r"(?s)CREATE TABLE chat_room_members \(.*?"
            r"joined_at DATETIME\s+NOT NULL DEFAULT CURRENT_TIMESTAMP.*?\);",
        )
        self.assertRegex(
            schema,
            r"(?s)CREATE TABLE chat_messages \(.*?"
            r"created_at DATETIME\s+NOT NULL DEFAULT CURRENT_TIMESTAMP.*?\);",
        )

    def test_chat_code_has_no_legacy_message_identifiers(self):
        chat_code = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "app" / "chat_dahyun").glob("*.py")
        )

        self.assertNotIn("FROM messages", chat_code)
        self.assertNotIn("INSERT INTO messages", chat_code)
        self.assertNotIn("sent_at", chat_code)


if __name__ == "__main__":
    unittest.main()
