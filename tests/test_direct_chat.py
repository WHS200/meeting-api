from concurrent.futures import ThreadPoolExecutor
from mysql_support import MySQLTestCase


class DirectChatTest(MySQLTestCase):
    def test_pair_uniqueness_membership_and_blocked_socket_send(self):
        room = self.client.post('/api/chat/direct', json={'user_id': 2}).json['chat_room_id']
        self.assertEqual(self.client_for(2).post('/api/chat/direct', json={'user_id': 1}).json['chat_room_id'], room)
        self.assertEqual(self.client_for(3).get(f'/api/chat/rooms/{room}/messages').status_code, 403)
        self.assertEqual(self.client_for(3).get(f'/api/chat/rooms/{room}/members').status_code, 403)
        outsider = self.socketio.test_client(self.app, flask_test_client=self.client_for(3))
        sender = self.socketio.test_client(self.app, flask_test_client=self.client)
        try:
            outsider.emit('send_message', {'chat_room_id': room, 'content': 'intrusion'})
            self.assertTrue(any(e['name'] == 'error' for e in outsider.get_received()))
            sender.emit('send_message', {'chat_room_id': room, 'content': 'hello', 'sender_id': 3})
            self.assertEqual(self.client.get(f'/api/chat/rooms/{room}/messages').json['messages'][0]['sender_id'], 1)
            self.client_for(2).post('/api/blocks/1')
            self.assertEqual(self.client.post('/api/chat/direct', json={'user_id': 2}).status_code, 403)
            sender.emit('send_message', {'chat_room_id': room, 'content': 'blocked'})
            self.assertTrue(any(e['name'] == 'error' for e in sender.get_received()))
            self.assertEqual(len(self.client.get(f'/api/chat/rooms/{room}/messages').json['messages']), 1)
        finally:
            outsider.disconnect()
            sender.disconnect()

    def test_concurrent_direct_creation(self):
        def create(pair):
            response = self.client_for(pair[0]).post('/api/chat/direct', json={'user_id': pair[1]})
            return response.status_code, response.json.get('chat_room_id')
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(create, [(1, 2), (2, 1)]))
        self.assertEqual(sorted(code for code, _ in results), [200, 201])
        self.assertEqual(len({room for _, room in results}), 1)
