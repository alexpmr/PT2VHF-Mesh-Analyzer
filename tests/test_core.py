"""Offline tests: SQLite, sources, retention, packet decoding, localhost API."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from mesh_analyzer.database import Database, now_ms
from mesh_analyzer.transports import PacketIngestor, SourceManager, position_from_decoded
from mesh_analyzer.app import build_handler


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Database(Path(self.temp.name)/"test.sqlite3")

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_sources_and_credentials_redacted(self):
        usb=self.db.upsert_source({"name":"VHF3","kind":"serial","config":{"port":"COM4"},"enabled":False})
        self.assertEqual(usb["id"],1)
        self.assertEqual(self.db.source(1)["config"]["port"],"COM4")
        wifi=self.db.upsert_source({"name":"WIFI","kind":"tcp","config":{"host":"192.168.0.5"},"enabled":False})
        self.assertEqual(self.db.source(wifi["id"])["config"]["port"],4403)
        self.db.upsert_source({"name":"BLE","kind":"ble","config":{"address":"AA:BB"},"enabled":False})
        m=self.db.upsert_source({"name":"MQTT","kind":"mqtt","config":{"host":"mqtt.example.org","topic":"msh/+/2/e/#","password":"secret"},"enabled":False})
        self.assertEqual(m["config"]["password"],"********")
        self.assertEqual(self.db.source(m["id"])["config"]["password"],"secret")
        self.db.upsert_source({"id":m["id"],"name":"MQTT","kind":"mqtt","config":{"password":"********","host":"mqtt.example.org"},"enabled":False})
        self.assertEqual(self.db.source(m["id"])["config"]["password"],"secret")
        self.db.delete_source(usb["id"])
        self.assertEqual(len(self.db.sources()),3)

    def test_retention_never_default_and_per_category(self):
        self.assertTrue(all(v==0 for v in self.db.retention().values()))
        self.db.upsert_node(123,1,timestamp_ms=now_ms()-12*86400000,long_name="Antigo")
        self.db.add_message({"source_id":1,"packet_key":"old-msg","packet_id":"1","timestamp_ms":now_ms()-12*86400000,
            "from_node":123,"to_node":0xffffffff,"channel":0,"direction":"rx","text":"oi","state":"received"})
        self.db.add_packet({"source_id":1,"source_packet_key":"old-pkt","packet_id":"1","timestamp_ms":now_ms()-12*86400000})
        self.assertTrue(all(n==0 for n in self.db.cleanup().values()))
        self.db.set_retention({"messages":7,"packets":1})
        removed=self.db.cleanup()
        self.assertEqual(removed["messages"],1)
        self.assertEqual(removed["packets"],1)
        self.assertEqual(removed["nodes"],0)
        self.assertEqual(self.db.stats()["nodes"],1)
        self.db.set_retention({"nodes":7})
        self.assertEqual(self.db.cleanup()["nodes"],1)

    def test_position_validation(self):
        self.assertIsNone(position_from_decoded({"position":{"latitudeI":0,"longitudeI":0}}))
        p=position_from_decoded({"position":{"latitudeI":-157900000,"longitudeI":-478800000,"altitude":1110}})
        self.assertAlmostEqual(p[0],-15.79)
        self.assertAlmostEqual(p[1],-47.88)

    def test_node_aliases_and_historical_position(self):
        self.db.upsert_node(789,1,long_name="Meshtastic original",short_name="ABCD",latitude=-15.79,longitude=-47.88)
        self.db.upsert_node(789,2,long_name="PT2VHF personalizado",short_name="VHF3")
        n=self.db.node_rows()[0]
        self.assertIn("Meshtastic original",n["aliases"])
        self.assertIn("PT2VHF personalizado",n["aliases"])
        self.assertAlmostEqual(n["latitude"],-15.79)
        self.assertEqual(n["last_source_id"],2)

    def test_receive_and_dedup_private_and_broadcast(self):
        ing=PacketIngestor(self.db)
        pkt={"from":0x1234,"to":0xffffffff,"id":1900,"rxTime":int(now_ms()/1000),"channel":0,
             "rxSnr":-6.5,"decoded":{"portnum":"TEXT_MESSAGE_APP","text":"Olá malha"}}
        self.assertTrue(ing.handle(1,pkt))
        self.assertFalse(ing.handle(1,pkt))
        self.assertTrue(ing.handle(2,pkt))  # Another receiver is distinct evidence.
        self.assertEqual(self.db.stats()["packets"],2)
        self.assertEqual(self.db.stats()["messages"],2)
        self.assertEqual(self.db.message_rows()[0]["text"],"Olá malha")
        private={"from":0x5678,"to":0x1234,"id":1901,"channel":0,"decoded":{"portnum":"TEXT_MESSAGE_APP","payload":b"mensagem privada"}}
        self.assertTrue(ing.handle(1,private))
        self.assertEqual(self.db.stats()["messages"],3)

    def test_cached_nodedb_does_not_mark_offline_node_as_recent(self):
        class MockIface:
            nodesByNum={321:{"user":{"longName":"No antigo","shortName":"OLD"},
                             "lastHeard":1_699_999_900}}
        PacketIngestor(self.db).seed_from_interface(1,MockIface())
        row=self.db.node_rows()[0]
        self.assertLess(row["last_seen_ms"], now_ms()-365*86400000)
        self.assertEqual(row["long_name"],"No antigo")

    def test_direct_rf_not_invented_from_traceroute(self):
        ing=PacketIngestor(self.db)
        packet={"from":100,"to":300,"id":98,"decoded":{"portnum":"TRACEROUTE_APP","route":[200]}}
        self.assertTrue(ing.handle(1,packet))
        self.assertEqual(self.db.stats()["traces"],1)
        links=self.db.link_rows()
        self.assertEqual(len(links),2)
        self.assertTrue(all(l["quality"]=="observed_route_unverified_rf" for l in links))

    def test_send_text_to_selected_radio(self):
        row=self.db.upsert_source({"name":"TCP","kind":"tcp","config":{"host":"127.0.0.1"},"enabled":False})
        driver=SourceManager(self.db)
        class Radio:
            myInfo=None
            def sendText(self,*args,**kwargs):
                self.sent=(args,kwargs)
                return {"id":777}
        fake=Radio()
        driver._interfaces[row["id"]]=fake
        output=driver.send_text(row["id"],"!00001234","Mensagem teste",0)
        self.assertTrue(output["success"])
        self.assertEqual(fake.sent[1]["destinationId"],"!00001234")
        self.assertTrue(fake.sent[1]["wantAck"])
        self.assertEqual(self.db.message_rows()[0]["state"],"accepted_by_radio")
        with self.assertRaisesRegex(ValueError,"220 bytes"):
            driver.send_text(row["id"],"^all","texto "*50,0)
        driver.close()


class APITests(unittest.TestCase):
    setUp=DatabaseTests.setUp
    tearDown=DatabaseTests.tearDown
    def test_localhost_security_and_persistence(self):
        manager=SourceManager(self.db)
        ui=Path(__file__).resolve().parents[1]/"mesh_analyzer"/"ui.html"
        server=ThreadingHTTPServer(("127.0.0.1",0),build_handler(self.db,manager,"known-csrf",ui.read_text(encoding="utf-8")))
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        url=f"http://127.0.0.1:{server.server_address[1]}"
        try:
            with urllib.request.urlopen(url+"/health") as resp:
                self.assertEqual(json.loads(resp.read())["version"],"0.1.1")
            with urllib.request.urlopen(url+"/") as resp:
                self.assertIn(b"id=\"settingsRetention\"",resp.read())
            body=json.dumps({"name":"USB bench","kind":"serial","config":{"port":"COM5"},"enabled":False}).encode()
            req=urllib.request.Request(url+"/api/sources/save",data=body,headers={"Content-Type":"application/json"},method="POST")
            with self.assertRaises(urllib.error.HTTPError) as cm:urllib.request.urlopen(req)
            self.assertEqual(cm.exception.code,403)
            req.add_header("X-PT2VHF-CSRF","known-csrf")
            with urllib.request.urlopen(req) as resp:self.assertTrue(json.loads(resp.read())["success"])
            with urllib.request.urlopen(url+"/api/state") as resp:
                self.assertEqual(len(json.loads(resp.read())["sources"]),1)
        finally:
            server.shutdown();server.server_close()
            manager.close()


if __name__=="__main__":unittest.main()