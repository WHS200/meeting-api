import shutil
import subprocess
import unittest
from pathlib import Path


@unittest.skipUnless(shutil.which("node"), "Node.js is required for avatar behavior tests")
class AvatarFrontendTest(unittest.TestCase):
    def run_behavior(self, name):
        result = subprocess.run(
            [shutil.which("node"), str(Path(__file__).with_name("avatar_frontend.cjs")), name],
            capture_output=True, text=True, encoding="utf-8", timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_avatar_escapes_url_alt_nickname_and_handles_missing_values(self):
        self.run_behavior("escaping")

    def test_failed_avatar_becomes_text_without_affecting_other_images(self):
        self.run_behavior("failure")

    def test_upload_refreshes_cache_header_and_profile_without_reload(self):
        self.run_behavior("profile")

    def test_chat_rooms_members_history_and_live_messages_use_avatars(self):
        self.run_behavior("chat")
