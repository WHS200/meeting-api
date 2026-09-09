from mysql_support import MySQLTestCase


class AdminTest(MySQLTestCase):
    def test_every_admin_boundary_and_role_injection(self):
        for url in ['/api/admin/users','/api/admin/users/1','/api/admin/meetings','/api/admin/posts','/api/admin/reports','/api/admin/reports/1']:
            self.assertEqual(self.client_for(None).get(url).status_code,401,url)
            self.assertEqual(self.client.get(url).status_code,403,url)
        self.client.patch('/api/users/me',json={'role':'ADMIN','nickname':'new name'})
        self.assertEqual(self.sql('SELECT role FROM users WHERE user_id=1')[0]['role'],'USER')
        self.assertEqual(self.client_for(6).get('/api/admin/users/999').status_code,404)
        self.assertEqual(self.client_for(6).get('/api/admin/users?status=invalid').status_code,400)

    def test_suspension_login_existing_session_and_socket(self):
        socket = self.socketio.test_client(self.app, flask_test_client=self.client)
        self.assertTrue(socket.is_connected())
        admin = self.client_for(6)
        self.assertEqual(admin.post('/api/admin/users/1/suspend',json={'days':3,'reason':'Policy'}).status_code,200)
        self.assertFalse(socket.is_connected())
        self.assertEqual(self.client.get('/api/users/me').status_code,403)
        self.assertEqual(self.client.get('/api/meetings').status_code,403)
        self.assertFalse(self.socketio.test_client(self.app,flask_test_client=self.client).is_connected())
        self.assertEqual(self.client_for(None).post('/api/auth/login',json={'login_id':'user1','password':'password123'}).status_code,403)
        self.assertEqual(admin.post('/api/admin/users/1/unsuspend',json={'reason':'Appeal accepted'}).status_code,200)
        self.assertEqual(self.client.get('/api/users/me').status_code,200)
        admin.post('/api/admin/users/1/suspend',json={'days':1,'reason':'Policy'})
        self.sql('UPDATE users SET suspended_until=CURRENT_TIMESTAMP()-INTERVAL 1 SECOND WHERE user_id=1')
        self.assertEqual(self.client.get('/api/users/me').status_code,200)
        self.assertEqual(self.sql('SELECT status FROM users WHERE user_id=1')[0]['status'],'ACTIVE')

    def test_report_action_is_bound_to_stored_target_and_atomic(self):
        report = self.client.post('/api/reports',json={'target_type':'USER','target_id':2,'reason':'Abuse'}).json['report_id']
        payload={'status':'RESOLVED','process_note':'Checked','action':'SUSPEND_USER','days':2,'user_id':3,'target_id':3}
        self.assertEqual(self.client.patch(f'/api/admin/reports/{report}',json=payload).status_code,403)
        admin=self.client_for(6)
        invalid={**payload,'action':'DELETE_POST'}
        self.assertEqual(admin.patch(f'/api/admin/reports/{report}',json=invalid).status_code,400)
        self.assertEqual(self.sql('SELECT status FROM reports')[0]['status'],'OPEN')
        self.assertEqual(admin.patch(f'/api/admin/reports/{report}',json=payload).status_code,200)
        self.assertEqual(self.sql('SELECT status FROM users WHERE user_id=2')[0]['status'],'SUSPENDED')
        self.assertEqual(self.sql('SELECT status FROM users WHERE user_id=3')[0]['status'],'ACTIVE')
        row=self.sql('SELECT * FROM reports')[0]
        self.assertEqual(row['processed_by'],6)
        self.assertIsNotNone(row['processed_at'])
        self.assertEqual(admin.patch(f'/api/admin/reports/{report}',json=payload).status_code,409)
        self.assertEqual(admin.patch('/api/admin/reports/999',json=payload).status_code,404)

    def test_moderation_records_reasons(self):
        meeting=self.meeting()
        admin=self.client_for(6)
        self.assertEqual(admin.post(f'/api/admin/meetings/{meeting}/cancel',json={'reason':'Policy'}).status_code,200)
        self.assertEqual(self.sql('SELECT status,moderation_reason FROM meetings')[0],{'status':'CANCELED','moderation_reason':'Policy'})
        post=admin.post('/api/admin/notices',json={'title':'Notice','content':'Welcome'}).json['post_id']
        self.assertEqual(admin.delete(f'/api/admin/posts/{post}',json={'reason':'Outdated'}).status_code,204)
        self.assertEqual(self.client.get(f'/api/community/posts/{post}').status_code,404)

    def test_meeting_report_actions_complete_the_report(self):
        meeting = self.meeting()
        admin = self.client_for(6)
        dismissed = self.client.post('/api/reports', json={'target_type':'MEETING','target_id':meeting,'reason':'Abuse'}).json['report_id']
        response = admin.patch(f'/api/admin/reports/{dismissed}', json={
            'status':'IN_REVIEW', 'action':'DISMISS_REPORT', 'process_note':'No violation'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'DISMISSED')
        self.assertEqual(self.sql('SELECT status FROM reports WHERE report_id=%s', (dismissed,))[0]['status'], 'DISMISSED')

        second_meeting = self.meeting(start='12:00', end='13:00')
        report = self.client.post('/api/reports', json={'target_type':'MEETING','target_id':second_meeting,'reason':'Abuse 2'}).json['report_id']
        response = admin.patch(f'/api/admin/reports/{report}', json={
            'status':'IN_REVIEW', 'action':'CANCEL_MEETING', 'process_note':'Policy violation'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'RESOLVED')
        self.assertEqual(self.sql('SELECT status FROM reports WHERE report_id=%s', (report,))[0]['status'], 'RESOLVED')
