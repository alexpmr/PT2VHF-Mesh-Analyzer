import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from mesh_analyzer.database import Database,now_ms
from mesh_analyzer.transports import SourceManager


class MessageReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.db=Database(Path(self.temp.name)/'m.db')
        self.source=self.db.upsert_source({'name':'USB','kind':'serial','config':{'port':'COM1'},'enabled':True})['id']
        self.manager=SourceManager(self.db)
        self.early=None;self.callback=None
        def send(*args,**kwargs):
            self.callback=kwargs['onResponse']
            self.assertTrue(kwargs['wantAck'])
            if self.early:self.callback(self.early)
            return {'id':777}
        self.manager._interfaces[self.source]=SimpleNamespace(myInfo={'my_node_num':100},sendText=send)

    def tearDown(self):self.db.close();self.temp.cleanup()

    def ack(self,sender=100,error=0,request=777):
        return {'from':sender,'decoded':{'portnum':'ROUTING_APP','requestId':request,'routing':{'errorReason':error}}}

    def state(self):return self.db.message_rows()[0]['state']

    def test_radio_accept_then_implicit_broadcast_ack(self):
        self.manager.send_text(self.source,'^all','Teste')
        self.assertEqual(self.state(),'accepted_by_radio')
        self.callback(self.ack())
        self.assertEqual(self.state(),'mesh_propagated')

    def test_early_ack_is_not_lost_before_database_insert(self):
        self.early=self.ack(sender=200)
        self.manager.send_text(self.source,200,'Private')
        self.assertEqual(self.state(),'delivered')

    def test_id_source_sender_and_transport_are_isolated(self):
        self.manager.send_text(self.source,200,'Private')
        for source,packet in [(self.source,self.ack(request=778)),(self.source+1,self.ack()),
            (self.source,self.ack(sender=300)),(self.source,{**self.ack(),'via_mqtt':True})]:
            self.manager.message_receipts.observe(source,packet)
            self.assertEqual(self.state(),'accepted_by_radio')
        self.callback(self.ack(sender=200))
        self.assertEqual(self.state(),'delivered')

    def test_old_interface_callback_cannot_confirm_new_connection(self):
        self.manager.send_text(self.source,'^all','Test')
        old_callback=self.callback
        self.manager._interfaces[self.source]=SimpleNamespace(myInfo={'my_node_num':100})
        old_callback(self.ack())
        self.assertEqual(self.state(),'accepted_by_radio')

    def test_nak_and_no_confirmation_become_failed(self):
        self.manager.send_text(self.source,'^all','Teste')
        self.callback(self.ack(error='NO_ROUTE'))
        self.assertEqual(self.state(),'failed')
        self.db._db.execute('DELETE FROM messages');self.db._db.commit()
        self.manager.send_text(self.source,200,'Private')
        with patch('mesh_analyzer.message_receipts.now_ms',return_value=now_ms()+180001):
            self.manager.message_receipts.expire()
        self.assertEqual(self.state(),'failed')
