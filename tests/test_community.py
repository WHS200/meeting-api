from mysql_support import MySQLTestCase


class CommunityTest(MySQLTestCase):
    def test_post_comment_ownership_and_admin(self):
        data = {'board': 'FREE', 'title': 'Hello', 'content': '<script>alert(1)</script>'}
        post = self.client.post('/api/community/posts', json=data).json['post_id']
        url = f'/api/community/posts/{post}'
        self.assertEqual(self.client_for(2).put(url, json=data).status_code, 403)
        self.assertEqual(self.client_for(2).delete(url).status_code, 403)
        comment = self.client_for(2).post(url+'/comments', json={'content': 'Reply'}).json['comment_id']
        self.assertEqual(self.client.delete(f'/api/community/comments/{comment}').status_code, 403)
        self.assertEqual(self.client_for(6).delete(f'/api/community/comments/{comment}').status_code, 204)
        self.assertEqual(self.client_for(6).put(url, json=data).status_code, 200)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url+'/comments', json={'content': 'Reply'}).status_code, 404)

    def test_notice_input_and_nonexistent(self):
        data = {'board': 'NOTICE', 'title': 'Notice', 'content': 'Hello'}
        self.assertEqual(self.client.post('/api/community/posts', json=data).status_code, 403)
        self.assertEqual(self.client_for(6).post('/api/community/posts', json=data).status_code, 201)
        data.update(board='FREE', title='x')
        self.assertEqual(self.client.post('/api/community/posts', json=data).status_code, 400)
        data.update(title='xx', content='x'*10001)
        self.assertEqual(self.client.post('/api/community/posts', json=data).status_code, 400)
        self.assertEqual(self.client.delete('/api/community/comments/99999').status_code, 404)
        self.assertEqual(self.client.get('/api/community/posts?keyword=%27%20OR%201=1').json['posts'], [])
