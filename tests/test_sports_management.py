from concurrent.futures import ThreadPoolExecutor
from mysql_support import MySQLTestCase


class SportsManagementTest(MySQLTestCase):
    def proposal(self,name='New Sport'):
        response=self.client.post('/api/sports/proposals',json={'sport_name':name,'status':'APPROVED','created_by':2})
        self.assertEqual(response.status_code,201,response.json)
        return response.json['proposal_id']

    def test_normalization_duplicates_limits_and_permissions(self):
        proposal=self.proposal('  Beach   Tennis  ')
        row=self.sql('SELECT * FROM sport_proposals')[0]
        self.assertEqual(row['sport_name'],'Beach Tennis')
        self.assertEqual(row['created_by'],1)
        self.assertEqual(row['status'],'PENDING_REVIEW')
        self.assertEqual(self.client.post('/api/sports/proposals',json={'sport_name':'beach tennis'}).status_code,409)
        self.assertEqual(self.client.post('/api/sports/proposals',json={'sport_name':'Tennis'}).status_code,409)
        self.assertEqual(self.client.post(f'/api/admin/sports/proposals/{proposal}/approve',json={'reason':'ok'}).status_code,403)
        for n in range(4):self.proposal('Sport '+str(n))
        self.assertEqual(self.client.post('/api/sports/proposals',json={'sport_name':'Sixth'}).status_code,429)
        self.assertEqual(self.client_for(2).get('/api/sports/proposals/mine').json['proposals'],[])

    def test_approve_reject_merge_and_target_skill_preserved(self):
        admin=self.client_for(6)
        proposal=self.proposal()
        sport=admin.post(f'/api/admin/sports/proposals/{proposal}/approve',json={'reason':'Valid sport'}).json['sport_id']
        self.assertEqual(admin.post(f'/api/admin/sports/proposals/{proposal}/approve',json={'reason':'repeat'}).status_code,409)
        self.sql("INSERT INTO user_sports (user_id,sport_id,skill_level) VALUES (2,1,'GOLD'),(2,%s,'SILVER'),(3,%s,'BRONZE')",(sport,sport))
        self.assertEqual(admin.post(f'/api/admin/sports/{sport}/merge',json={'target_sport_id':1,'reason':'Same sport'}).status_code,200)
        rows=self.sql('SELECT * FROM user_sports ORDER BY user_id')
        self.assertEqual(rows[0]['skill_level'],'GOLD')
        self.assertEqual(rows[1]['sport_id'],1)
        self.assertEqual(self.sql('SELECT status FROM sports WHERE sport_id=%s',(sport,))[0]['status'],'INACTIVE')
        rejected=self.proposal('Another')
        self.assertEqual(admin.post(f'/api/admin/sports/proposals/{rejected}/reject',json={'reason':'Not a sport'}).status_code,200)
        merged=self.proposal('Alias')
        self.assertEqual(admin.post(f'/api/admin/sports/proposals/{merged}/merge',json={'reason':'Alias','target_sport_id':999}).status_code,404)
        self.assertEqual(admin.post(f'/api/admin/sports/proposals/{merged}/merge',json={'reason':'Alias','target_sport_id':1}).status_code,200)

    def test_concurrent_normalized_duplicate(self):
        def propose(name):return self.client_for(1).post('/api/sports/proposals',json={'sport_name':name}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(propose,[' New Sport ','New  Sport'])),[201,409])
