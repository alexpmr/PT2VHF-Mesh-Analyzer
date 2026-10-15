"""Passive unicast topology, live animation, and update UX regressions for v0.6.5."""
import hashlib
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from mesh_analyzer.database import Database,now_ms
from mesh_analyzer.transports import PacketIngestor
from mesh_analyzer.updater import UpdateManager,deployment_mode,stream_verified,RUNNER_PS

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"mesh_analyzer"/"ui.html").read_text(encoding="utf-8")

class PassiveTrafficTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Database(Path(self.temp.name)/"mesh.sqlite3")
        self.ing=PacketIngestor(self.db)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def packet(self,ident,to=200,from_num=100):
        return {"from":from_num,"to":to,"id":ident,
                "rxTime":int(now_ms()/1000),
                "decoded":{"portnum":1,"text":"Teste de fluxo"}}

    def test_normal_packets_create_logical_flow_not_direct_rf_link(self):
        p=self.packet(1)
        self.assertTrue(self.ing.handle(1,p))
        self.assertFalse(self.ing.handle(1,p))
        self.assertTrue(self.ing.handle(1,self.packet(2)))
        flows=self.db.communication_rows()
        self.assertEqual(len(flows),1)
        self.assertEqual((flows[0]["source_id"],flows[0]["from_node"],flows[0]["to_node"]),(1,100,200))
        self.assertEqual(flows[0]["observations"],2)
        self.assertEqual(flows[0]["transport"],"radio")
        self.assertEqual(self.db.link_rows(),[])
        nodes={n["node_num"]:n for n in self.db.node_rows()}
        self.assertEqual(nodes[200]["last_seen_ms"],0,"destino não é receptor confirmado")
        self.assertEqual(self.db.topology_diagnostics(1)["stored"],0)

    def test_separate_sources_mqtt_and_broadcast_not_physical_links(self):
        self.ing.handle(1,self.packet(11))
        self.ing.handle(2,self.packet(12),via_mqtt=True)
        self.ing.handle(1,self.packet(13,to=0xffffffff))
        self.ing.handle(1,self.packet(14,to=100))
        flows=self.db.communication_rows()
        self.assertEqual(len(flows),2)
        self.assertEqual({f["transport"] for f in flows},{"radio","mqtt"})
        self.assertEqual({f["source_id"] for f in flows},{1,2})
        self.assertEqual(self.db.link_rows(),[])

    def test_zero_hop_rf_to_verified_local_receiver_only(self):
        pkt=self.packet(70,to=0xffffffff)
        pkt.update({"hopStart":7,"hopLimit":7,"rxSnr":6.5})
        self.ing.handle(1,pkt,local_node_num=500)
        link=self.db.link_rows()
        self.assertEqual(len(link),1)
        self.assertEqual((link[0]["a"],link[0]["b"]),(100,500))
        self.assertEqual(link[0]["quality"],"confirmed_direct_rf")
        self.assertEqual(self.db.communication_rows(),[],"broadcast não cria fluxo ponto a ponto")
        pkt2=self.packet(71,to=200)
        pkt2.update({"hopStart":7,"hopLimit":5,"rxSnr":3.2})
        self.ing.handle(1,pkt2,local_node_num=500)
        self.assertEqual(len(self.db.link_rows()),1,"duas retransmissões não confirmam salto A↔receptor")
        pkt3=self.packet(72,to=200)
        pkt3.update({"hopStart":7,"hopLimit":7,"rxSnr":3.2})
        self.ing.handle(2,pkt3,via_mqtt=True,local_node_num=500)
        self.assertEqual(len(self.db.link_rows()),1,"MQTT não comprova recepção RF")
        pkt4=self.packet(73,to=200)
        pkt4.update({"hopStart":7,"hopLimit":7,"rxSnr":3.2})
        self.ing.handle(3,pkt4)
        self.assertEqual(len(self.db.link_rows()),1,"sem receptor local conhecido não confirmar RF")

    def test_archival_replay_recovers_existing_packets_and_is_idempotent(self):
        stamp=now_ms()
        for i,to in [(1,200),(2,200),(3,0xffffffff)]:
            self.db.add_packet({"source_id":1,"source_packet_key":f"historic-{i}",
               "packet_id":str(i),"timestamp_ms":stamp-i*1000,"from_node":100,
               "to_node":to,"port":"TEXT_MESSAGE_APP"})
        result=self.db.reprocess_archived_communications(limit=20)
        self.assertEqual(result["processed"],3)
        self.assertEqual(result["communications"],2)
        self.assertEqual(self.db.communication_rows()[0]["observations"],2)
        result2=self.db.reprocess_archived_communications(limit=20)
        self.assertEqual(result2["processed"],0)
        self.assertEqual(result2["communications"],0)
        self.ing.handle(1,self.packet(4))
        self.assertEqual(self.db.communication_rows()[0]["observations"],3)

    def test_map_separates_logical_traffic_and_uses_packet_id(self):
        self.assertIn("api('/api/communications')",HTML)
        self.assertIn("activeCommunications=communications.filter",HTML)
        self.assertIn("Caminho físico não conhecido; NÃO comprova RF direto",HTML)
        self.assertIn("dashArray:'1 9'",HTML)
        self.assertIn("Number(p.id)>lastAnimatedPacketId",HTML)
        segment=HTML[HTML.index("function pulseNewPackets(current){"):HTML.index("function sourceMapNodes(){")]
        self.assertNotIn("mapHighlightSource",segment)
        self.assertIn("Sem posição disponível",segment)

    def test_one_click_update_and_relaunch_safety(self):
        self.assertIn("$('topUpdate').onclick=()=>monitorState?.available?beginUpdateDirect():checkUpdates(true)",HTML)
        self.assertNotIn("if(!confirm('Baixar",HTML)
        self.assertIn("api('/api/update/cancel',{})",HTML)
        self.assertIn("Start-Process -FilePath $exe -WorkingDirectory",RUNNER_PS)
        self.assertIn("WriteNotice 'failed' $reason",RUNNER_PS)
        self.assertIn("System.Windows.Forms.MessageBox",RUNNER_PS)

    def test_detached_runner_handshake_before_shutdown(self):
        import json
        from unittest.mock import Mock
        class Monitor:
            def status(self):return {"current":"0.6.4"}
        mgr=UpdateManager(self.temp.name,Monitor(),executable="C:/FakePT2VHF.exe")
        plan=Path(self.temp.name)/"plan.json"
        ready=Path(self.temp.name)/"runner_ready.json"
        plan.write_text(json.dumps({"run_nonce":"nonce-fixture","runner_ready":str(ready)}),encoding="utf-8")
        mgr._plan=(str(Path(self.temp.name)/"apply.ps1"),str(plan))
        mgr._phase="verified"
        def launched(*args,**kwargs):
            ready.write_text(json.dumps({"nonce":"nonce-fixture","status":"ready"}),encoding="utf-8")
            return Mock(poll=lambda:None)
        with patch("mesh_analyzer.updater.subprocess.Popen",side_effect=launched):
            with patch("mesh_analyzer.updater.os.name","nt"):
                self.assertEqual(mgr.launch()["phase"],"installing")
        self.assertIn("runner_ready",RUNNER_PS)
        self.assertIn("Detached updater ready",RUNNER_PS)

    def test_runner_absent_never_signals_install(self):
        import json
        from unittest.mock import Mock
        class Monitor:
            def status(self):return {"current":"0.6.4"}
        mgr=UpdateManager(self.temp.name,Monitor(),executable="C:/FakePT2VHF.exe")
        ready=Path(self.temp.name)/"never_ready.json"
        plan=Path(self.temp.name)/"plan.json"
        plan.write_text(json.dumps({"run_nonce":"nonce-fixture","runner_ready":str(ready)}),encoding="utf-8")
        mgr._plan=(str(Path(self.temp.name)/"apply.ps1"),str(plan))
        mgr._phase="verified"
        process=Mock(poll=lambda:None)
        with patch("mesh_analyzer.updater.subprocess.Popen",return_value=process):
            with patch("mesh_analyzer.updater.os.name","nt"):
                with patch("mesh_analyzer.updater.time.monotonic",side_effect=[0,13]):
                    with self.assertRaisesRegex(RuntimeError,"não confirmou"):
                        mgr.launch()
        process.terminate.assert_called_once()
        self.assertEqual(mgr.status()["phase"],"verified")

    def test_cancel_during_download_removes_partial_file(self):
        data=b"candidate-fixture"
        digest=hashlib.sha256(data).hexdigest()
        flag=threading.Event();flag.set()
        class FakeStream:
            headers={"Content-Length":str(len(data))}
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,size):return data
        dest=Path(self.temp.name)/"package.exe"
        with patch("urllib.request.urlopen",return_value=FakeStream()):
            with self.assertRaisesRegex(RuntimeError,"cancelado"):
                stream_verified("https://github.com/test",dest,digest,cancelled=flag)
        self.assertFalse(dest.exists())
        self.assertFalse(Path(str(dest)+".part").exists())

if __name__=="__main__":unittest.main()
