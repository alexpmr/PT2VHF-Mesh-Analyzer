"""Regression coverage for messages, connection winner, favorite requests and RF ranking."""
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from mesh_analyzer.database import Database,now_ms
from mesh_analyzer.transports import SourceManager
from mesh_analyzer.analytics import calculate
from mesh_analyzer.task_status import snapshot

class Release34(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Database(Path(self.tmp.name)/'test.db')
    def tearDown(self):
        self.db._db.close();self.tmp.cleanup()
    def source(self,name='Fallback',enabled=True):
        return self.db.upsert_source(dict(name=name,kind='tcp',config={'host':'localhost'},enabled=enabled))['id']
    def test_first_success_wins_and_other_interface_is_closed(self):
        a,b=self.source('A'),self.source('B');manager=SourceManager(self.db)
        barrier=threading.Barrier(2);created=[]
        class Radio:
            def __init__(self,**kwargs):
                self.closed=False;self.localNode=SimpleNamespace(nodeNum=42)
                self.nodesByNum={42:{'user':{'longName':'Detected Device'}}}
                created.append(self);barrier.wait(timeout=3)
            def close(self):self.closed=True
        with patch('meshtastic.tcp_interface.TCPInterface',Radio),patch.object(manager,'_ensure_pubsub'):
            manager.start()
            end=time.monotonic()+4
            while time.monotonic()<end and not (len(created)==2 and any(x.closed for x in created)):
                threading.Event().wait(.01)
            with manager._lock:
                self.assertEqual(len(manager._interfaces),1)
                winner=next(iter(manager._interfaces))
            end=time.monotonic()+2
            while time.monotonic()<end and self.db.source(winner)['name']!='Detected Device':
                threading.Event().wait(.01)
            self.assertEqual(self.db.source(winner)['name'],'Detected Device')
            self.assertTrue(any(x.closed for x in created))
            manager._stop.set()
            for thread in list(manager._threads.values()):thread.join(3)
        self.assertTrue(all(x.closed for x in created))
    def test_multiple_saved_and_disabled_choice_persist(self):
        a,b=self.source(),self.source('B',False)
        reopened=Database(self.db.path)
        try:
            self.assertEqual(len(reopened.sources()),2)
            self.assertTrue(reopened.source(a)['enabled']);self.assertFalse(reopened.source(b)['enabled'])
        finally:reopened._db.close()
    def test_pending_unfavorite_survives_old_cache_and_restart(self):
        sid=self.source();self.db.upsert_node(42,sid,long_name='N')
        self.db.set_node_favorite_from_radio(sid,42,True)
        self.db.request_node_favorite(sid,42,False)
        self.db.set_node_favorite_from_radio(sid,42,True)
        reopened=Database(self.db.path)
        try:
            row=reopened.node_rows()[0]
            self.assertEqual(row['favorite_source_ids'],[])
            self.assertEqual(row['favorite_pending_source_ids'],[sid])
            reopened.set_node_favorite_from_radio(sid,42,False)
            self.assertEqual(reopened.node_rows()[0]['favorite_pending_source_ids'],[])
        finally:reopened._db.close()
    def test_ranking_uses_archived_positions_and_deduplicates_reverse_pair(self):
        sid=self.source();ts=now_ms()-86400000
        for num,lon in [(1,0),(2,1)]:
            self.db.upsert_node(num,sid,timestamp_ms=now_ms(),long_name=str(num),latitude=30,longitude=30)
            self.db.add_position(num,sid,ts,0,lon)
        self.db.add_link(sid,1,2,ts,'confirmed_direct_rf')
        self.db.add_link(sid+1,2,1,ts,'confirmed_direct_rf')
        self.db.add_link(sid,1,3,ts,'observed_route_unverified_rf')
        data=calculate(self.db,{'period':'all'})
        self.assertEqual(len(data['direct_rf_rank']),1)
        self.assertAlmostEqual(data['direct_rf_rank'][0]['distance_km'],111.195,places=2)
        self.assertEqual(calculate(self.db,{'period':'1h'})['direct_rf_rank'],[])
    def test_queue_snapshot_is_readonly_and_marks_automation_origin(self):
        # Snapshot contains actual query state; viewing never schedules a query.
        manager=SimpleNamespace(queries=SimpleNamespace(status=lambda:[{'request_id':'x','target':42,'state':'awaiting_reply'}]))
        before=self.db._db.total_changes
        result=snapshot(self.db,manager)
        self.assertEqual(result['data'][0]['origin'],'manual')
        self.assertEqual(self.db._db.total_changes,before)
