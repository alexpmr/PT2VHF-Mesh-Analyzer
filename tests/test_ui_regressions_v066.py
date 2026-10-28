"""v0.6.6 — map display, broadcast, user labels and measured hop regressions."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from mesh_analyzer.database import Database
from mesh_analyzer.transports import SourceManager

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"mesh_analyzer"/"ui.html").read_text(encoding="utf-8")

class DisplayRegression(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Database(Path(self.tmp.name)/"mesh.sqlite3")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def packet(self,key,src,num=123,ts=1700000000000,hs=7,hl=5,mqtt=0):
        return {"source_id":src,"source_packet_key":key,"packet_id":key,
           "timestamp_ms":ts,"from_node":num,"to_node":4294967295,
           "port":"TEXT_MESSAGE_APP","hop_start":hs,"hop_limit":hl,
           "via_mqtt":mqtt}

    def test_hops_use_rf_packet_and_are_source_scoped(self):
        self.db.add_packet(self.packet("one",1,ts=1000,hs=7,hl=6))
        self.db.add_packet(self.packet("two",1,ts=2000,hs=7,hl=4))
        self.db.add_packet(self.packet("other",2,ts=1000,hs=7,hl=7))
        self.db.add_packet(self.packet("mqtt",1,ts=8000,hs=7,hl=0,mqtt=1))
        self.db.add_packet(self.packet("bad",1,ts=10000,hs=2,hl=5))
        self.db.add_packet(self.packet("unknown",3,ts=10000,hs=None,hl=None))
        records=self.db.node_hop_rows()
        self.assertEqual({(r["source_id"],r["hops"]) for r in records},{(1,3),(2,0)})
        self.assertEqual(self.db.node_hop_rows(),records)

    def test_snapshot_recognizes_dict_myinfo_and_send_capability(self):
        m=SourceManager(self.db)
        class Radio:
            myInfo={"my_node_num":12345}
            localNode=None
            def sendText(self,*args,**kwargs):pass
        m._interfaces[1]=Radio()
        m._states[1]={"status":"connected"}
        d=m.snapshot()["1"]
        self.assertEqual(d["local_node_num"],12345)
        self.assertTrue(d["tx_capable"])
        m._interfaces.clear()
        m.close()

    def test_broadcast_renders_without_changing_database_data(self):
        self.assertIn("function isBroadcastNode",HTML)
        self.assertIn("if(isBroadcastNode(num))return 'broadcast';",HTML)
        self.assertIn("idName(p.to_node)",HTML)
        self.assertIn("trafficName(p.port)",HTML)

    def test_unified_ver_panel_single_layer_controls(self):
        for token in ('id="mapVisibilityPanel"','id="showMapNodes"','id="showMapLinks"',
                      'id="showMapWaypoints"','id="mapRadar"','id="mapRadarOpacity"',
                      'id="mapTerrain"'):
            self.assertEqual(HTML.count(token),1,token)
        for removed in ('id="mapLayersPanel"','id="layersBtn"','id="closeLayers"',"$('layersBtn')"):
            self.assertNotIn(removed,HTML)
        self.assertIn("function toggleVisibilityPanel",HTML)
        self.assertIn("Selecionar tudo",HTML)
        self.assertIn("Remover tudo",HTML)

    def test_chat_requires_real_tx_and_no_fake_read_receipt(self):
        self.assertIn("tx_capable===true",HTML)
        self.assertIn("id=\"messageTxStatus\"",HTML)
        self.assertIn("accepted_by_radio",HTML)
        self.assertIn("Entrega e leitura não confirmadas",HTML)
        self.assertNotIn("m.state==='read'?'✓✓'",HTML)

    def test_context_menu_in_all_three_views(self):
        self.assertIn("marker.on('contextmenu'",HTML)
        self.assertIn("el.oncontextmenu=",HTML)
        self.assertIn("el.addEventListener('contextmenu'",HTML)
        self.assertIn("function openNodeContext",HTML)
        self.assertIn("consultas remotas",HTML.lower())


if __name__=="__main__":unittest.main()
