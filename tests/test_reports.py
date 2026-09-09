from concurrent.futures import ThreadPoolExecutor
from mysql_support import MySQLTestCase


class ReportsTest(MySQLTestCase):
    def test_target_validation_privacy_and_sliding_window(self):
        def report(kind, target, **extra):
            return self.client.post('/api/reports', json={'target_type':kind,'target_id':target,'reason':'Abuse',**extra})
        self.assertEqual(report('USER',1).status_code,409)
        self.assertEqual(report('USER',999).status_code,404)
        post = self.client.post('/api/community/posts',json={'board':'FREE','title':'Hello','content':'test'}).json['post_id']
        self.assertEqual(report('POST',post).status_code,409)
        self.assertEqual(report('USER',2,detail='x'*1001).status_code,400)
        response = report('USER',2, reporter_id=3, status='RESOLVED')
        self.assertEqual(response.status_code,201)
        report_id = response.json['report_id']
        self.assertEqual(report('USER',2).status_code,409)
        self.assertEqual(self.client_for(2).get('/api/reports/mine').json['reports'],[])
        self.assertNotIn('processed_by', self.client.get('/api/reports/mine').json['reports'][0])
        self.assertIn(self.client.patch(f'/api/reports/{report_id}',json={'status':'RESOLVED'}).status_code,(404,405))
        self.assertEqual(self.sql('SELECT reporter_id,status FROM reports')[0],{'reporter_id':1,'status':'OPEN'})
        self.sql('UPDATE reports SET created_at=CURRENT_TIMESTAMP()-INTERVAL 25 HOUR')
        self.assertEqual(report('USER',2).status_code,201)

    def test_daily_limit_and_concurrent_duplicate(self):
        def report(_):
            return self.client_for(1).post('/api/reports',json={'target_type':'USER','target_id':2,'reason':'Abuse'}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(report,range(2))),[201,409])
        for _ in range(9):
            self.sql("INSERT INTO reports (reporter_id,target_type,target_id,target_user_id,reason,created_at) VALUES (1,'USER',3,3,'fixture',CURRENT_TIMESTAMP())")
        self.assertEqual(self.client.post('/api/reports',json={'target_type':'USER','target_id':4,'reason':'Abuse'}).status_code,429)
