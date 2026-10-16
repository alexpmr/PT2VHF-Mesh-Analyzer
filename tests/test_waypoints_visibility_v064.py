"""Regressões de waypoints Meshtastic e menu VER do mapa (v0.6.4)."""
import tempfile
import time
import unittest
from pathlib import Path

from mesh_analyzer.database import Database, now_ms
from mesh_analyzer.transports import PacketIngestor, port_name, waypoint_from_decoded

ROOT=Path(__file__).resolve().parents[1]
UI=(ROOT/"mesh_analyzer"/"ui.html").read_text(encoding="utf-8")


class WaypointMapTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Database(Path(self.tmp.name)/"mesh-analyzer.sqlite3")
        self.ingest=PacketIngestor(self.db)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def packet(self, packet_id, waypoint_id=123, longitude=-47.882, expiry=0):
        return {"from":0x12345678,"to":0xffffffff,"id":packet_id,
                "rxTime":int(time.time()),
                "decoded":{"portnum":8,"waypoint":{"id":waypoint_id,
                    "latitudeI":int(-15.793*1e7),
                    "longitudeI":int(longitude*1e7),
                    "name":"Marco QTH", "description":"Ponto recebido pelo rádio",
                    "expire":expiry,"icon":0x1f4cd}}}

    def test_waypoint_id_and_source_provenance(self):
        self.assertEqual(port_name(8),"WAYPOINT_APP")
        self.assertTrue(self.ingest.handle(1,self.packet(101)))
        self.assertTrue(self.ingest.handle(2,self.packet(102)))
        rows=self.db.waypoint_rows()
        self.assertEqual(len(rows),2)
        self.assertEqual({row["source_id"] for row in rows},{1,2})
        self.assertEqual({row["waypoint_id"] for row in rows},{123})
        self.assertAlmostEqual(rows[0]["latitude"],-15.793,6)
        self.assertAlmostEqual(rows[0]["longitude"],-47.882,6)
        self.assertEqual(rows[0]["from_node"],0x12345678)
        self.assertEqual(rows[0]["name"],"Marco QTH")
        self.assertEqual(rows[0]["icon"],0x1f4cd)
        self.assertFalse(self.ingest.handle(1,self.packet(101)))
        self.assertEqual(self.db.stats()["waypoints"],2)

    def test_expired_and_invalid_waypoints_are_not_displayed(self):
        past=int(time.time())-60
        self.ingest.handle(1,self.packet(103,waypoint_id=103,expiry=past))
        self.assertEqual(self.db.waypoint_rows(),[])
        self.assertEqual(self.db.stats()["waypoints"],1)
        self.ingest.handle(1,self.packet(104,waypoint_id=104,expiry=int(time.time())+3600))
        self.assertEqual(len(self.db.waypoint_rows()),1)
        self.assertIsNone(waypoint_from_decoded({"waypoint":{"id":0,"latitudeI":10,"longitudeI":20}}))
        self.assertIsNone(waypoint_from_decoded({"waypoint":{"id":999,"latitudeI":0,"longitudeI":0}}))
        self.assertIsNone(waypoint_from_decoded({"waypoint":{"id":999,"latitudeI":910000000,"longitudeI":1000000}}))

    def test_binary_payload_protobuf(self):
        try:
            from meshtastic.protobuf import mesh_pb2
        except ImportError:
            self.skipTest("Meshtastic Python protobuf não disponível")
        waypoint=mesh_pb2.Waypoint()
        waypoint.id=120
        waypoint.latitude_i=-157930000
        waypoint.longitude_i=-478820000
        waypoint.name="Binario"
        waypoint.description="Via radio"
        d=waypoint_from_decoded({"payload":waypoint.SerializeToString()})
        self.assertEqual(d["waypoint_id"],120)
        self.assertAlmostEqual(d["latitude"],-15.793,6)
        self.assertEqual(d["name"],"Binario")

    def test_retention_is_explicit_and_never_by_default(self):
        self.db.upsert_waypoint(1,501,123,now_ms()-10*86400000,-15.8,-47.8)
        self.assertEqual(self.db.cleanup()["waypoints"],0)
        self.db.set_retention({"waypoints":7})
        self.assertEqual(self.db.cleanup()["waypoints"],1)

    def test_ver_menu_independent_and_no_duplicate_connection_status(self):
        for id in ("mapVisibilityBtn","mapVisibilityPanel","showMapNodes",
                   "showMapLinks","showMapWaypoints","showMapAnimate",
                   "mapShowAll","mapHideAll","mapWaypointsCount"):
            self.assertEqual(UI.count('id="'+id+'"'),1,id)
        self.assertNotIn('id="mapSourceState"',UI)
        self.assertNotIn("$('mapSourceState')",UI)
        self.assertIn("api('/api/waypoints')",UI)
        self.assertIn("waypointLayer=L.layerGroup().addTo(map)",UI)
        self.assertIn("w.source_id)===source",UI)
        self.assertIn("$('mapShowWaypointsSetting').checked",UI)
        self.assertIn("storeMapControls();renderMap();",UI)
        self.assertNotIn('id="mapSource"',UI)  # Removed by map toolbar redesign


if __name__=="__main__":
    unittest.main()
