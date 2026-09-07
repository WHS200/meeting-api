from unittest.mock import patch
from mysql_support import MySQLTestCase


class NotificationsTest(MySQLTestCase):
    def test_owner_only_and_read_all(self):
        self.client.post('/api/friends/requests',json={'user_id':2})
        recipient=self.client_for(2)
        note=recipient.get('/api/notifications').json['notifications'][0]
        self.assertEqual(note['event_type'],'FRIEND_REQUEST')
        url=f"/api/notifications/{note['notification_id']}/read"
        self.assertEqual(self.client.post(url,json={'user_id':2}).status_code,404)
        self.assertEqual(recipient.get('/api/notifications/unread-count').json['count'],1)
        self.assertEqual(recipient.post(url).status_code,200)
        self.assertEqual(recipient.post(url).status_code,200)
        self.assertEqual(recipient.get('/api/notifications/unread-count').json['count'],0)
        self.client_for(3).post('/api/friends/requests',json={'user_id':2})
        self.client.post('/api/notifications/read-all')
        self.assertEqual(recipient.get('/api/notifications/unread-count').json['count'],1)

    def test_participation_and_report_events(self):
        meeting=self.meeting(approval='APPROVAL')
        self.client_for(2).post(f'/api/meetings/{meeting}/participants')
        self.client.post(f'/api/meetings/{meeting}/participants/2/approve')
        events=self.client_for(2).get('/api/notifications').json['notifications']
        self.assertEqual(events[0]['event_type'],'PARTICIPATION_APPROVED')
        report=self.client_for(2).post('/api/reports',json={'target_type':'USER','target_id':3,'reason':'Abuse'}).json['report_id']
        self.client_for(6).patch(f'/api/admin/reports/{report}',json={'status':'RESOLVED','process_note':'private review'})
        note=self.client_for(2).get('/api/notifications').json['notifications'][0]
        self.assertEqual(note['event_type'],'REPORT_PROCESSED')
        self.assertNotIn('private review',note['message'])

    def test_notification_failure_rolls_back_domain_change(self):
        with patch('app.codex_features.friends.notify',side_effect=RuntimeError('notification failure')):
            with self.assertRaises(RuntimeError):
                self.client.post('/api/friends/requests',json={'user_id':2})
        self.assertEqual(self.sql('SELECT * FROM friend_requests'),[])
