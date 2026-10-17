import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mesh_analyzer.database import Database
from mesh_analyzer.transports import SourceManager, PacketIngestor


class DeleteNodeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Database(Path(self.temp.name)/'nodes.sqlite3')
        self.src=self.db.upsert_source({'name':'USB','kind':'serial','config':{'port':'COM7'},'enabled':True})
        self.id=self.src['id']
        self.manager=SourceManager(self.db)
        self.node=SimpleNamespace(nodeNum=1234,removeNode=lambda n:None,ensureSessionKey=lambda:None)
        self.iface=SimpleNamespace(myInfo={'my_node_num':1234},localNode=self.node,
            nodesByNum={5678:{'user':{'longName':'Test'}}},nodes={'!0000162e':{}})
        self.manager._interfaces[self.id]=self.iface
        self.manager._states[self.id]={'status':'connected'}
        self.db.upsert_node(5678,self.id,long_name='Test')
        self.reply={'from':1234,'decoded':{'portnum':'ROUTING_APP','requestId':987,'routing':{'errorReason':'NONE'}}}
        self.sent=[]
        def send(command,**kwargs):
            self.sent.append(command.remove_by_nodenum)
            kwargs['onResponse'](self.reply)
            return {'id':987}
        self.node._sendAdmin=send

    def tearDown(self):
        self.db.close();self.temp.cleanup()

    def delete(self,**kwargs):
        return self.manager.node_deletion.delete(self.id,5678,confirmed=True,timeout=.02,**kwargs)

    def present(self):
        return any(n['node_num']==5678 for n in self.db.node_rows())

    def test_ack_then_catalog_only_removal_preserves_history_and_can_rediscover(self):
        ingest=PacketIngestor(self.db)
        ingest.handle(self.id,{'id':7,'from':5678,'to':0xffffffff,'decoded':{'portnum':1,'text':'history'}})
        before=(len(self.db.packet_rows()),len(self.db.message_rows()))
        self.assertTrue(self.delete()['radio_confirmed'])
        self.assertEqual(self.sent,[5678])
        self.assertFalse(self.present())
        self.assertNotIn(5678,self.iface.nodesByNum)
        self.assertEqual((len(self.db.packet_rows()),len(self.db.message_rows())),before)
        ingest.handle(self.id,{'id':8,'from':5678,'to':0xffffffff,'decoded':{'portnum':1,'text':'new'}})
        self.assertTrue(self.present())

    def test_implicit_default_error_enum_is_success(self):
        self.reply['decoded']['routing']={}
        self.assertTrue(self.delete()['success'])

    def test_nak_or_wrong_source_or_wrong_request_keeps_database(self):
        for field,value in [('reason','NOT_AUTHORIZED'),('from',9999),('request',986)]:
            with self.subTest(field=field):
                old={'from':1234,'decoded':{'portnum':5,'requestId':987,'routing':{}}}
                if field=='reason':old['decoded']['routing']['errorReason']=value
                elif field=='request':old['decoded']['requestId']=value
                else:old['from']=value
                self.reply=old
                with self.assertRaises(ValueError):self.delete()
                self.assertTrue(self.present())
                self.assertIn(5678,self.iface.nodesByNum)

    def test_confirmation_self_special_and_disconnected_guard(self):
        for target in (0,1,2,3,0xffffffff,1234):
            with self.assertRaises(ValueError):self.manager.node_deletion.delete(self.id,target,True,timeout=.01)
        with self.assertRaises(ValueError):self.manager.node_deletion.delete(self.id,5678,False)
        self.manager._states[self.id]['status']='disconnected'
        with self.assertRaises(ValueError):self.delete()
        self.assertEqual(self.sent,[])
        self.assertTrue(self.present())

    def test_mqtt_is_never_used_for_deletion(self):
        src=self.db.upsert_source({'name':'MQTT','kind':'mqtt','config':{'host':'test.local','topic':'msh/#'},'enabled':True})
        with self.assertRaises(ValueError):self.manager.node_deletion.delete(src['id'],5678,True)
        self.assertEqual(self.sent,[])

    def test_local_database_failure_reports_partial_state(self):
        with patch.object(self.db,'delete_node_catalog',side_effect=RuntimeError('disk full')):
            with self.assertRaisesRegex(ValueError,'Rádio confirmou.*banco falhou'):self.delete()
        self.assertTrue(self.present())

    def test_http_endpoint_requires_csrf_and_explicit_confirmation(self):
        import json, threading, urllib.request, urllib.error
        from http.server import ThreadingHTTPServer
        from mesh_analyzer.app import build_handler
        server=ThreadingHTTPServer(('127.0.0.1',0),build_handler(self.db,self.manager,'csrf','test'))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f'http://127.0.0.1:{server.server_port}/api/nodes/delete'
        def post(token,confirmed):
            headers={'Content-Type':'application/json','X-PT2VHF-CSRF':token}
            body=json.dumps({'source_id':self.id,'node_num':5678,'confirmed':confirmed}).encode()
            return urllib.request.urlopen(urllib.request.Request(url,data=body,headers=headers))
        try:
            with self.assertRaises(urllib.error.HTTPError) as ctx:post('bad',True)
            self.assertEqual(ctx.exception.code,403)
            with self.assertRaises(urllib.error.HTTPError):post('csrf',False)
            self.assertEqual(self.sent,[])
            with post('csrf',True) as response:self.assertTrue(json.load(response)['radio_confirmed'])
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)

    def test_no_simultaneous_deletion(self):
        self.manager.node_deletion._operation.acquire()
        try:
            with self.assertRaisesRegex(ValueError,'andamento'):self.delete()
        finally:self.manager.node_deletion._operation.release()
        self.assertEqual(self.sent,[])
