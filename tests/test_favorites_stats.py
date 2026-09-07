from mysql_support import MySQLTestCase


class FavoritesStatsTest(MySQLTestCase):
    def test_favorites_owner_uniqueness_and_meeting_delete_cascade(self):
        meeting=self.meeting()
        self.assertEqual(self.client.post(f'/api/favorites/{meeting}').status_code,201)
        self.assertEqual(self.client.post(f'/api/favorites/{meeting}').status_code,409)
        self.assertEqual(self.client_for(2).delete(f'/api/favorites/{meeting}').status_code,404)
        self.assertEqual(self.client_for(2).get('/api/favorites').json['favorites'],[])
        self.assertEqual(len(self.client.get('/api/favorites').json['favorites']),1)
        self.assertEqual(self.client.post('/api/favorites/999').status_code,404)
        self.client.delete(f'/api/meetings/{meeting}')
        self.assertEqual(self.client.get('/api/favorites').json['favorites'],[])

    def test_stats_are_aggregated_and_unmarked_attendance_not_in_denominator(self):
        for attendance in ['ATTENDED','NO_SHOW',None]:
            meeting=self.meeting()
            self.sql("INSERT INTO meeting_participants (meeting_id,user_id,participation_status,attendance_status) VALUES (%s,2,'APPROVED',%s)",(meeting,attendance))
        stats=self.client.get('/api/users/2/stats').json
        self.assertEqual(stats['participation_count'],3)
        self.assertEqual(stats['attended_count'],1)
        self.assertEqual(stats['no_show_count'],1)
        self.assertEqual(stats['attendance_rate'],50.0)
        self.assertEqual(self.client.get('/api/users/me/stats').json['hosted_count'],3)
        self.assertIsNone(self.client.get('/api/users/3/stats').json['attendance_rate'])
        self.assertEqual(self.client.get('/api/users/999/stats').status_code,404)
