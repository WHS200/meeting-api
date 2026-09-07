from concurrent.futures import ThreadPoolExecutor

from mysql_support import MySQLTestCase


class SocialTest(MySQLTestCase):
    def request_friend(self, sender=1, recipient=2):
        response = self.client_for(sender).post("/api/friends/requests", json={"user_id": recipient})
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.json["request_id"]

    def test_request_ownership_and_reverse_duplicate(self):
        request_id = self.request_friend()
        self.assertEqual(self.client_for(3).post(f"/api/friends/requests/{request_id}/accept").status_code, 403)
        self.assertEqual(self.client.post(f"/api/friends/requests/{request_id}/accept").status_code, 403)
        self.assertEqual(self.client_for(2).post(f"/api/friends/requests/{request_id}/cancel").status_code, 403)
        self.assertEqual(self.client_for(2).post("/api/friends/requests", json={"user_id": 1}).status_code, 409)
        self.assertEqual(self.client_for(2).post(f"/api/friends/requests/{request_id}/accept").status_code, 200)
        self.assertEqual(self.client.post("/api/friends/requests", json={"user_id": 2}).status_code, 409)
        self.assertEqual(len(self.client.get("/api/friends").json["friends"]), 1)

    def test_block_clears_friendship_requests_and_owner_only_unblock(self):
        request_id = self.request_friend()
        self.assertEqual(self.client_for(2).post("/api/blocks/1").status_code, 201)
        self.assertEqual(self.client.post(f"/api/friends/requests/{request_id}/cancel").status_code, 409)
        self.assertEqual(self.client_for(3).delete("/api/blocks/1").status_code, 404)
        self.assertEqual(self.client_for(2).post("/api/blocks/1").status_code, 409)
        self.assertEqual(self.client.post("/api/friends/requests", json={"user_id": 2}).status_code, 403)
        self.assertEqual(self.client_for(2).delete("/api/blocks/1").status_code, 204)
        request_id = self.request_friend()
        self.client_for(2).post(f"/api/friends/requests/{request_id}/accept")
        self.client.post("/api/blocks/2")
        self.assertEqual(self.client.get("/api/friends").json["friends"], [])

    def test_validation_search_and_session_identity(self):
        self.assertEqual(self.client_for(None).get("/api/friends").status_code, 401)
        self.assertEqual(self.client.post("/api/blocks/1").status_code, 409)
        self.assertEqual(self.client.post("/api/friends/requests", json={"user_id": 9999}).status_code, 404)
        self.assertEqual(self.client.post("/api/friends/requests", json={"user_id": True}).status_code, 400)
        response = self.client.get("/api/friends/search", query_string={"nickname": "' OR 1=1 --"})
        self.assertEqual(response.json["users"], [])
        self.assertEqual(self.client.post("/api/friends/requests/99999/accept").status_code, 404)

    def test_concurrent_opposite_requests_create_one_pending_pair(self):
        def send(pair):
            return self.client_for(pair[0]).post("/api/friends/requests", json={"user_id": pair[1]}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(send, [(1, 2), (2, 1)]))
        self.assertEqual(sorted(statuses), [201, 409])
