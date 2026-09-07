from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from mysql_support import MySQLTestCase


class WaitlistScheduleTest(MySQLTestCase):
    def join(self, meeting, user):
        return self.client_for(user).post(f'/api/meetings/{meeting}/participants')

    def test_concurrent_capacity_fifo_chat_and_notification(self):
        meeting=self.meeting(maximum=2)
        with ThreadPoolExecutor(max_workers=4) as pool:
            responses=list(pool.map(lambda user:self.join(meeting,user),[2,3,4,5]))
        self.assertEqual([r.status_code for r in responses],[201]*4)
        states=[r.json['participation_status'] for r in responses]
        self.assertEqual(states.count('APPROVED'),1)
        self.assertEqual(states.count('WAITING'),3)
        rows=self.sql("SELECT user_id,participation_status FROM meeting_participants WHERE meeting_id=%s ORDER BY waiting_at,user_id",(meeting,))
        approved=next(r['user_id'] for r in rows if r['participation_status']=='APPROVED')
        waiting=[r['user_id'] for r in rows if r['participation_status']=='WAITING']
        self.assertEqual(self.client_for(approved).delete(f'/api/meetings/{meeting}/participants/me').status_code,200)
        promoted=self.sql("SELECT user_id FROM meeting_participants WHERE participation_status='APPROVED'")[0]['user_id']
        self.assertEqual(promoted,waiting[0])
        self.assertEqual(self.client_for(promoted).get('/api/chat/rooms').json['chat_rooms'][0]['meeting_id'],meeting)
        events=self.client_for(promoted).get('/api/notifications').json['notifications']
        self.assertEqual(events[0]['event_type'],'WAITLIST_PROMOTED')
        self.assertEqual(self.client_for(approved).get('/api/chat/rooms').json['chat_rooms'],[])
        # A waiter can cancel only themselves; another user's endpoint is host-only.
        self.assertEqual(self.client_for(waiting[1]).delete(f'/api/meetings/{meeting}/participants/{waiting[2]}').status_code,403)
        self.assertEqual(self.client_for(waiting[1]).delete(f'/api/meetings/{meeting}/participants/me').status_code,200)
        self.assertEqual(len(self.client_for(waiting[2]).get(f'/api/meetings/{meeting}/waitlist').json['waitlist']),1)

    def test_approval_waitlist_and_kick_promotion(self):
        meeting=self.meeting(maximum=2,approval='APPROVAL')
        self.assertEqual(self.join(meeting,2).json['participation_status'],'PENDING')
        self.client.post(f'/api/meetings/{meeting}/participants/2/approve')
        self.assertEqual(self.join(meeting,3).json['participation_status'],'PENDING')
        self.assertEqual(self.client.post(f'/api/meetings/{meeting}/participants/3/approve').json['participation_status'],'WAITING')
        self.client.delete(f'/api/meetings/{meeting}/participants/2')
        self.assertEqual(self.sql('SELECT participation_status FROM meeting_participants WHERE user_id=3')[0]['participation_status'],'APPROVED')
        self.assertEqual(self.join(meeting,2).status_code,409)  # kicked user cannot bypass host

    def test_overlap_excludes_pending_and_touching_intervals(self):
        first=self.meeting(approval='APPROVAL')
        second=self.meeting(host=3,start='10:30',end='11:30')
        adjacent=self.meeting(host=4,start='11:30',end='12:30')
        self.assertEqual(self.join(first,2).status_code,201)
        self.assertEqual(self.join(second,2).status_code,201)
        self.assertEqual(self.client.post(f'/api/meetings/{first}/participants/2/approve').status_code,409)
        self.assertEqual(self.join(adjacent,2).status_code,201)
        self.client_for(2).delete(f'/api/meetings/{second}/participants/me')
        self.assertEqual(self.client.post(f'/api/meetings/{first}/participants/2/approve').status_code,200)

    def test_cross_meeting_concurrent_join_cannot_bypass_overlap(self):
        first=self.meeting()
        second=self.meeting(host=3)
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(lambda meeting:self.join(meeting,2),[first,second]))
        self.assertEqual(sorted(r.status_code for r in responses),[201,409])

    def test_concurrent_host_meeting_creation_cannot_overlap(self):
        payload={'sport_id':1,'title':'Host schedule','description':'Exercise','meeting_date':'2027-01-02',
                 'meeting_time':'10:00','end_time':'12:00','location':'Seoul','max_participants':3,
                 'approval_type':'INSTANT','status':'RECRUITING'}
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(lambda _: self.client.post('/api/meetings',json=payload),[1,2]))
        self.assertEqual(sorted(r.status_code for r in responses),[201,409])

    def test_duration_capacity_reduction_and_edit_conflict(self):
        first=self.meeting(maximum=3)
        second=self.meeting(host=3,start='12:00',end='13:00')
        self.join(first,2);self.join(second,2)
        payload={'sport_id':1,'title':'Changed meeting','description':'Exercise','meeting_date':'2027-01-02','meeting_time':'12:30',
                 'end_time':'13:30','location':'Seoul','max_participants':3,'approval_type':'INSTANT','status':'RECRUITING'}
        self.assertEqual(self.client.put(f'/api/meetings/{first}',json=payload).status_code,409)
        payload.update(meeting_time='10:00',end_time='10:20')
        self.assertEqual(self.client.put(f'/api/meetings/{first}',json=payload).status_code,400)
        payload.update(meeting_time='10:00',end_time='23:00')
        self.assertEqual(self.client.post('/api/meetings',json=payload).status_code,400)
        payload.update(meeting_time='10:00',end_time='11:00')
        self.join(first,4)
        payload['max_participants']=2
        self.assertEqual(self.client.put(f'/api/meetings/{first}',json=payload).status_code,409)
        payload['max_participants']=3
        self.assertEqual(self.client.put(f'/api/meetings/{first}',json=payload).status_code,200)
        self.assertTrue(any(n['event_type']=='MEETING_CHANGED' for n in self.client_for(2).get('/api/notifications').json['notifications']))

    def test_promotion_rechecks_overlap_and_rolls_back_on_failure(self):
        first=self.meeting(maximum=2)
        second=self.meeting(host=4)
        self.join(first,2);self.join(first,3);self.join(first,5)
        self.join(second,3)
        with patch('app.codex_features.waitlist.notify',side_effect=RuntimeError('fail')):
            with self.assertRaises(RuntimeError):
                self.client_for(2).delete(f'/api/meetings/{first}/participants/me')
        self.assertEqual(self.sql('SELECT participation_status FROM meeting_participants WHERE meeting_id=%s AND user_id=2',(first,))[0]['participation_status'],'APPROVED')
        self.client_for(2).delete(f'/api/meetings/{first}/participants/me')
        states={r['user_id']:r['participation_status'] for r in self.sql('SELECT user_id,participation_status FROM meeting_participants WHERE meeting_id=%s',(first,))}
        self.assertEqual(states[3],'WAITING')
        self.assertEqual(states[5],'APPROVED')
