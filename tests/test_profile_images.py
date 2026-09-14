import unittest
from unittest.mock import MagicMock, patch

from flask import Flask

from app.codex_features.community import community_bp
from app.codex_features.waitlist import waitlist_bp
from app.meetings_gyudong.meetings import meetings_bp
from app.participation_euna.participation import participation_bp
from mysql_support import MySQLTestCase


class ProfileImageApiTest(unittest.TestCase):
    """Exercise response serialization with the real S3 URL helper, without AWS."""

    def setUp(self):
        app = Flask(__name__)
        app.config.update(TESTING=True, SECRET_KEY="test-secret")
        for blueprint in (meetings_bp, participation_bp, waitlist_bp, community_bp):
            app.register_blueprint(blueprint)
        self.client = app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 1
        self.cursor = MagicMock()
        self.connection = MagicMock()
        self.connection.cursor.return_value = self.cursor
        self.s3 = MagicMock()
        self.s3.generate_presigned_url.return_value = "https://images.example/avatar?signed=1"
        for target, value in (
            ("app.shared.s3.get_s3_client", self.s3),
            ("app.shared.s3.get_s3_bucket_name", "test-avatar-bucket"),
        ):
            patcher = patch(target, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def assert_image(self, row, field, key):
        expected = self.s3.generate_presigned_url.return_value if key else None
        self.assertEqual(row[field], expected)
        if key:
            self.s3.generate_presigned_url.assert_any_call(
                "get_object", Params={"Bucket": "test-avatar-bucket", "Key": key}, ExpiresIn=3600
            )
        else:
            self.s3.generate_presigned_url.assert_not_called()

    def assert_selected(self, column):
        self.assertTrue(any(column in args[0] for args, _ in self.cursor.execute.call_args_list))

    def test_meeting_list_and_detail_include_signed_host_image_and_keep_fields(self):
        for key in (None, "profile/host.png"):
            for path in ("/api/meetings", "/api/meetings/10"):
                with self.subTest(key=key, path=path):
                    self.s3.reset_mock()
                    original = dict(meeting_id=10, host_id=1, host_name="Host", max_participants=4,
                                    approved_count=1, status="RECRUITING")
                    row = dict(original, host_profile_image=key)
                    self.cursor.fetchone.return_value = row
                    self.cursor.fetchall.return_value = [row]
                    with patch("app.meetings_gyudong.meetings.get_db_connection", return_value=self.connection), \
                         patch("app.meetings_gyudong.meetings.expire_meeting_if_needed"):
                        response = self.client.get(path)
                    self.assertEqual(response.status_code, 200)
                    result = response.json["meetings"][0] if path == "/api/meetings" else response.json
                    self.assert_image(result, "host_profile_image", key)
                    self.assertEqual({k: result[k] for k in original}, original)
                    self.assertEqual(result["participant_count"], 2)
                    self.assert_selected("u.profile_image AS host_profile_image")

    def check_participants(self, suffix, context, status):
        for key in (None, "profile/participant.png"):
            with self.subTest(key=key):
                self.s3.reset_mock()
                original = dict(user_id=2, nickname="Participant", skill_level="SILVER",
                                participation_status=status, attendance_status="ATTENDED")
                self.cursor.fetchall.return_value = [dict(original, profile_image=key)]
                with patch("app.participation_euna.participation." + context, return_value=(
                    self.connection, self.cursor, {"sport_id": 1}, 1, None
                )):
                    response = self.client.get("/api/meetings/10/participants" + suffix)
                self.assertEqual(response.status_code, 200)
                row = response.json["participants"][0]
                self.assert_image(row, "profile_image", key)
                self.assertEqual({k: row[k] for k in original}, original)
                self.assert_selected("u.profile_image")

    def test_pending_participant_image(self):
        self.check_participants("", "get_host_context", "PENDING")

    def test_approved_participant_image(self):
        self.check_participants("/approved", "get_meeting_context", "APPROVED")

    def test_waitlist_signs_only_visible_users_and_preserves_ranking(self):
        for viewer in (1, 2):
            for key in (None, "profile/waiter.png"):
                with self.subTest(viewer=viewer, key=key):
                    self.s3.reset_mock()
                    with self.client.session_transaction() as session:
                        session["user_id"] = viewer
                    self.cursor.fetchone.return_value = {"host_id": 1}
                    self.cursor.fetchall.return_value = [
                        dict(user_id=3, nickname="First", waiting_at="first", profile_image=key),
                        dict(user_id=2, nickname="Second", waiting_at="second", profile_image=key),
                    ]
                    with patch("app.codex_features.waitlist.transaction") as transaction:
                        transaction.return_value.__enter__.return_value = self.cursor
                        response = self.client.get("/api/meetings/10/waitlist")
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json["total"], 2)
                    rows = response.json["waitlist"]
                    self.assertEqual([r["user_id"] for r in rows], [3, 2] if viewer == 1 else [2])
                    self.assertEqual(rows[-1]["position"], 2)
                    self.assertEqual(rows[-1]["waiting_at"], "second")
                    for row in rows:
                        self.assert_image(row, "profile_image", key)
                    self.assertEqual(self.s3.generate_presigned_url.call_count, len(rows) if key else 0)
                    self.assert_selected("u.profile_image")

    def test_community_list_signs_author_image_and_keeps_post_fields(self):
        for key in (None, "profile/author.png"):
            with self.subTest(key=key):
                self.s3.reset_mock()
                original = dict(post_id=10, author_id=1, author_nickname="Writer", title="Title", board="FREE")
                self.cursor.fetchall.return_value = [dict(original, author_profile_image=key)]
                with patch("app.codex_features.community.transaction") as transaction:
                    transaction.return_value.__enter__.return_value = self.cursor
                    response = self.client.get("/api/community/posts")
                self.assertEqual(response.status_code, 200)
                row = response.json["posts"][0]
                self.assert_image(row, "author_profile_image", key)
                self.assertEqual({k: row[k] for k in original}, original)
                self.assert_selected("u.profile_image AS author_profile_image")

    def test_community_detail_signs_post_and_comment_images(self):
        for key in (None, "profile/writer.png"):
            with self.subTest(key=key):
                self.s3.reset_mock()
                self.cursor.fetchone.return_value = dict(post_id=10, author_id=1, author_nickname="Writer",
                                                          author_profile_image=key, content="<script>post</script>")
                self.cursor.fetchall.return_value = [dict(comment_id=20, author_id=2, author_nickname="Reader",
                                                          author_profile_image=key, content="<b>comment</b>")]
                with patch("app.codex_features.community.transaction") as transaction:
                    transaction.return_value.__enter__.return_value = self.cursor
                    response = self.client.get("/api/community/posts/10")
                self.assertEqual(response.status_code, 200)
                self.assert_image(response.json["post"], "author_profile_image", key)
                self.assert_image(response.json["comments"][0], "author_profile_image", key)
                self.assertEqual(response.json["post"]["content"], "<script>post</script>")
                self.assertEqual(response.json["comments"][0]["content"], "<b>comment</b>")
                self.assertEqual(self.s3.generate_presigned_url.call_count, 2 if key else 0)
                self.assert_selected("u.profile_image AS author_profile_image")


class ProfileImageMySQLTest(MySQLTestCase):
    def test_images_survive_real_joins_for_meetings_participants_waitlist_and_community(self):
        self.sql("UPDATE users SET profile_image = 'profile/test.png' WHERE user_id IN (1, 2)")
        signed = "https://images.example/test.png?signature=test"
        with patch("app.shared.s3.get_s3_client") as s3, \
             patch("app.shared.s3.get_s3_bucket_name", return_value="test-avatar-bucket"):
            s3.return_value.generate_presigned_url.return_value = signed
            meeting_id = self.meeting(maximum=2, approval="APPROVAL")
            base = f"/api/meetings/{meeting_id}"
            self.assertEqual(self.client.get(base).json["host_profile_image"], signed)
            self.assertEqual(self.client.get("/api/meetings").json["meetings"][0]["host_profile_image"], signed)
            for user_id in (2, 3):
                self.assertEqual(self.client_for(user_id).post(base + "/participants").status_code, 201)
            pending = self.client.get(base + "/participants").json["participants"]
            self.assertEqual({r["user_id"]: r["profile_image"] for r in pending}, {2: signed, 3: None})
            # Fill the meeting with the user without an image, then queue the image owner.
            for user_id in (3, 2):
                self.assertEqual(self.client.post(base + f"/participants/{user_id}/approve").status_code, 200)
            approved = self.client.get(base + "/participants/approved").json["participants"]
            self.assertIsNone(approved[0]["profile_image"])
            self.assertEqual(self.client.get(base + "/waitlist").json["waitlist"][0]["profile_image"], signed)
            self.client_for(3).delete(base + "/participants/me")
            approved = self.client.get(base + "/participants/approved").json["participants"]
            self.assertEqual(approved[0]["profile_image"], signed)

            post_id = self.client.post("/api/community/posts", json={
                "board": "FREE", "title": "Avatar test", "content": "Post body"
            }).json["post_id"]
            post_url = f"/api/community/posts/{post_id}"
            for user_id in (2, 3):
                self.assertEqual(self.client_for(user_id).post(post_url + "/comments", json={"content": "Reply"}).status_code, 201)
            self.assertEqual(self.client.get("/api/community/posts").json["posts"][0]["author_profile_image"], signed)
            detail = self.client.get(post_url).json
            self.assertEqual(detail["post"]["author_profile_image"], signed)
            self.assertEqual([r["author_profile_image"] for r in detail["comments"]], [signed, None])
            s3.return_value.generate_presigned_url.assert_any_call(
                "get_object", Params={"Bucket": "test-avatar-bucket", "Key": "profile/test.png"}, ExpiresIn=3600
            )

