"""v0.6.62: Ferramentas no menu superior, cobertura (marca/modelo, raio, nós sem cobertura, PDF),
defeitos do relevo, preferência USB → BLE → Wi-Fi, conteúdo no Tráfego, nomes curtos no mapa e
disponibilidade dos repetidores."""
import json
import math
import tempfile
import unittest
from array import array
from pathlib import Path
from unittest import mock

from mesh_analyzer import coverage as C
from mesh_analyzer import payload
from mesh_analyzer.database import Database, now_ms
from mesh_analyzer.survey import TerrainTiles, despike

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "mesh_analyzer" / "ui.html").read_text(encoding="utf-8")
CENTER = (-16.1, -47.9)


def flat(height=1000.0):
    tiles = TerrainTiles(None, getter=lambda url: (_ for _ in ()).throw(AssertionError("sem rede")))
    return tiles, mock.patch.object(C._Raster, "_load", lambda self, key: array("f", [height]) * 65536)


class TerrainDefects(unittest.TestCase):
    def test_spike_cluster_is_removed(self):
        grid = [1000.0] * 65536
        for (x, y), v in {(100, 100): 3418, (101, 100): 2023, (100, 99): 2126, (101, 99): 1459, (102, 98): 513}.items():
            grid[y * 256 + x] = v
        fixed = despike(grid)
        self.assertGreaterEqual(fixed, 4)
        self.assertLess(max(grid), 1100)
        self.assertGreater(min(grid), 900)

    def test_real_relief_is_kept(self):
        # Morro largo (raio ~20 px, 600 m acima da base) não é tratado como defeito.
        grid = [1000.0 + max(0.0, 600 - 30 * math.hypot(x - 128, y - 128)) for y in range(256) for x in range(256)]
        top = max(grid)
        self.assertEqual(despike(grid), 0)
        self.assertEqual(max(grid), top)


class CoverageRadiusAndNodes(unittest.TestCase):
    def test_default_and_limits(self):
        self.assertEqual(C.coverage_params({})["max_km"], 50)
        self.assertEqual(C.coverage_params({"max_km": 100})["max_km"], 100)
        with self.assertRaises(ValueError):
            C.coverage_params({"max_km": 101})
        with self.assertRaises(ValueError):
            C.coverage_params({"max_km": 60, "hires": True})

    def test_classify_nodes(self):
        tiles, patch = flat()
        with patch:
            r = C.coverage(tiles, CENTER, {"max_km": 10, "tx_height_m": 30, "rx_height_m": 10, "clutter_m": 0,
                                           "location_pct": 50, "time_pct": 50, "rx_sensitivity_dbm": -80})
        near = {"node_num": 1, "name": "Perto", "lat": CENTER[0] + 1 / 111.2, "lon": CENTER[1]}
        weak = {"node_num": 2, "name": "Fraco", "lat": CENTER[0] + 9 / 111.2, "lon": CENTER[1]}
        far = {"node_num": 3, "name": "Longe", "lat": CENTER[0] + 30 / 111.2, "lon": CENTER[1]}
        covered, uncovered, outside = C.classify_nodes(r, [near, weak, far, {"node_num": 4, "name": "sem posição"}])
        self.assertEqual([x["name"] for x in covered], ["Perto"])
        self.assertEqual([x["name"] for x in uncovered], ["Fraco"])
        self.assertGreater(uncovered[0]["missing_db"], 0)
        self.assertEqual([x["name"] for x in outside], ["Longe"])
        self.assertAlmostEqual(outside[0]["distance_km"], 30, delta=0.5)

    def test_coverage_pdf(self):
        from mesh_analyzer import survey_pdf
        tiles, patch = flat()
        with patch:
            r = C.coverage(tiles, CENTER, {"max_km": 5, "name": "Teste"})
        nodes = [{"node_num": 1, "name": "A", "lat": CENTER[0] + 0.01, "lon": CENTER[1]},
                 {"node_num": 2, "name": "B", "lat": CENTER[0] + 0.3, "lon": CENTER[1]}]
        body = survey_pdf.coverage_pdf(r, {"min": -130, "max": -80, "scale": "signal", "style": "contours"},
                                       "Teste", *C.classify_nodes(r, nodes))
        self.assertTrue(body.startswith(b"%PDF"))
        self.assertGreater(len(body), 5000)

    def test_interface(self):
        self.assertIn('id="coverageRadius" min="1" max="100"', HTML)
        self.assertIn("max_km:50", HTML)
        self.assertIn("Buscar ponto mais alto num raio de (km)", HTML)
        self.assertIn('id="coverageSearchKm" min="0.05" max="50"', HTML)
        self.assertIn("fetchToolPdf({kind:'coverage'", HTML)
        self.assertIn("Nós conhecidos sem cobertura (", HTML)
        self.assertIn("function coverageLinkTo(item){", HTML)
        self.assertIn("id=\"linkBackCoverage\"", HTML)
        app = (ROOT / "mesh_analyzer" / "app.py").read_text(encoding="utf-8")
        self.assertIn('payload.get("kind")=="coverage"', app)


class RadioCatalog(unittest.TestCase):
    def test_brands_and_models(self):
        catalog = HTML[HTML.index("const RADIO_CATALOG=["):HTML.index("const radioModel=")]
        for brand in ("Heltec", "LilyGO", "RAKwireless", "Seeed Studio", "B&Q Consulting", "Elecrow", "Nordic / Adafruit"):
            self.assertIn("['" + brand + "',", catalog)
        for hw in ("HELTEC_V3", "TBEAM", "RAK4631", "TRACKER_T1000_E", "STATION_G2", "T_ECHO"):
            self.assertIn("'" + hw + "'", catalog)
        self.assertIn("deviceSelectorHtml('coverageDevice'", HTML)
        self.assertIn("deviceSelectorHtml('linkDevA'", HTML)
        self.assertIn("deviceSelectorHtml('linkDevB'", HTML)
        self.assertIn("radioModelForHw(connectedRadioHw())", HTML)


class ToolsInTopMenu(unittest.TestCase):
    def test_tools_button_between_automations_and_settings(self):
        nav = HTML[HTML.index('<button class="navbtn active" data-view="map">'):HTML.index('data-view="settings"')]
        self.assertTrue(nav.rstrip().endswith('Ferramentas ▾</button><button class="navbtn"'))
        self.assertIn('id="mapToolsBtn"', nav)
        self.assertLess(nav.index('data-view="automations"'), nav.index('id="mapToolsBtn"'))
        # O painel fica fora das abas para abrir de qualquer uma.
        self.assertLess(HTML.index('<div id="mapToolsPanel"'), HTML.index('<section class="view active" id="viewMap">'))
        self.assertIn("document.querySelectorAll('.navbtn[data-view]').forEach(b=>b.addEventListener('click'", HTML)


class ConnectionPreference(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "t.db")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def add(self, kind, config, name="PT2VHF-4"):
        return self.db.upsert_source({"name": name, "kind": kind, "enabled": True, "config": config})["id"]

    def test_rank_and_startup_order(self):
        from mesh_analyzer.transports import SourceManager, radio_rank
        self.assertEqual([radio_rank({"kind": k}) for k in ("serial", "ble", "tcp")], [0, 1, 2])
        wifi = self.add("tcp", {"host": "192.168.0.10", "port": 4403})
        ble = self.add("ble", {"address": "AA:BB:CC:DD:EE:FF"})
        usb = self.add("serial", {"port": "COM5"})
        sm = SourceManager(self.db)
        order = []
        with mock.patch.object(sm, "connect", side_effect=order.append):
            sm.start()
        self.assertEqual(order, [usb, ble, wifi])
        # Ao iniciar, Wi-Fi espera USB e BLE terminarem de tentar; BLE espera só a USB.
        sm._started_at = __import__("time").monotonic()
        sm._states = {usb: {"status": "connecting"}, ble: {"status": "connecting"}, wifi: {"status": "connecting"}}
        self.assertTrue(sm._blocked_by_priority(wifi))
        self.assertTrue(sm._blocked_by_priority(ble))
        self.assertFalse(sm._blocked_by_priority(usb))

    def test_better_radio_for_same_node(self):
        from mesh_analyzer.transports import SourceManager
        wifi = self.add("tcp", {"host": "192.168.0.10", "port": 4403, "node_num": 0x1234})
        usb = self.add("serial", {"port": "COM5", "node_num": 0x1234})
        other = self.add("serial", {"port": "COM7", "node_num": 0x9999}, "Outro")
        sm = SourceManager(self.db)
        sm._interfaces = {wifi: object()}
        sm._states = {wifi: {"status": "connected"}, usb: {"status": "standby"}, other: {"status": "standby"}}
        present = lambda s: True
        self.assertEqual(sm.better_radio(present)["id"], usb)
        self.assertIsNone(sm.better_radio(lambda s: False))
        # Escolha manual do Wi-Fi no indicador continua valendo.
        self.db.set_preferred_radio(wifi, manual=True)
        self.assertIsNone(sm.better_radio(present))
        self.db.set_preferred_radio(wifi, manual=False)
        self.assertEqual(sm.better_radio(present)["id"], usb)

    def test_watcher_switches_without_opening_port(self):
        from mesh_analyzer import device_detection as dd
        watcher = dd.DeviceWatcher.__new__(dd.DeviceWatcher)
        watcher.sources = mock.Mock()
        watcher.db = self.db
        watcher._settings = lambda: {"usb_priority": True}
        watcher._radio_busy = lambda: False
        usb = {"id": 7, "name": "PT2VHF-4", "kind": "serial", "config": {"port": "COM5"}}
        captured = {}

        def better(present):
            captured["present"] = present(usb)
            return usb
        watcher.sources.better_radio.side_effect = better
        port = mock.Mock(device="COM5")
        with mock.patch("serial.tools.list_ports.comports", return_value=[port]):
            watcher._prefer_better()
        self.assertTrue(captured["present"])
        watcher.sources.activate.assert_called_once_with(7, manual=False)


class TrafficPayload(unittest.TestCase):
    def raw(self, decoded):
        return json.dumps({"decoded": decoded})

    def test_telemetry_position_nodeinfo_routing(self):
        s, f = payload.describe("TELEMETRY_APP", self.raw({"telemetry": {"deviceMetrics": {
            "batteryLevel": 87, "voltage": 4.12, "channelUtilization": 12.3, "airUtilTx": 1.5, "uptimeSeconds": 7260}}}))
        self.assertEqual(s, "🔋 87% · 4,12 V · canal 12,3%")
        self.assertIn(("Ligado há", "2 h 01 min"), f)
        s, _ = payload.describe("TELEMETRY_APP", self.raw({"telemetry": {"deviceMetrics": {"batteryLevel": 101}}}))
        self.assertEqual(s, "🔋 EXT")
        s, f = payload.describe("POSITION_APP", self.raw({"position": {"latitudeI": -157090000, "longitudeI": -478216000,
                                                                      "altitude": 1102, "satsInView": 9}}))
        self.assertEqual(s, "📍 -15.70900, -47.82160 · 1102 m · 9 sat.")
        s, f = payload.describe("NODEINFO_APP", self.raw({"user": {"longName": "PT2VHF-4 - Móvel", "shortName": "VHF4",
                                                                   "hwModel": "HELTEC_V3", "role": "CLIENT"}}))
        self.assertIn("PT2VHF-4 - Móvel", s)
        self.assertIn(("Nome curto", "VHF4"), f)
        s, f = payload.describe("TRACEROUTE_APP", self.raw({"traceroute": {"route": [0x10, 0x20], "snrTowards": [24, -8]}}))
        self.assertEqual(s, "2 salto(s)")
        self.assertIn(("SNR por salto (dB)", "6 · -2"), f)
        s, _ = payload.describe("ROUTING_APP", self.raw({"routing": {"errorReason": "NONE"}}))
        self.assertEqual(s, "✔ entregue (ACK)")
        s, _ = payload.describe("TEXT_MESSAGE_APP", self.raw({"text": "Bom dia"}), "Bom dia")
        self.assertEqual(s, "💬 Bom dia")

    def test_packet_rows_summary_and_detail(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "t.db")
            raw = self.raw({"portnum": "TELEMETRY_APP", "telemetry": {"deviceMetrics": {"batteryLevel": 50, "voltage": 3.9}}})
            db.add_packet({"source_id": 1, "packet_id": "1", "source_packet_key": "k1", "timestamp_ms": now_ms(),
                           "from_node": 5, "to_node": 0xffffffff, "port": "TELEMETRY_APP", "channel": 0, "rx_snr": 5,
                           "rx_rssi": -90, "hop_start": 3, "hop_limit": 3, "via_mqtt": 0, "encrypted": 0,
                           "direction": "rx", "text_preview": "", "raw_json": raw})
            row = db.packet_rows()[0]
            self.assertNotIn("raw_json", row)
            self.assertEqual(row["summary"], "🔋 50% · 3,9 V")
            detail = db.packet_detail(row["id"])
            self.assertIn({"label": "Bateria", "value": "50%"}, detail["fields"])
            self.assertIn('"batteryLevel": 50', detail["json"])
            db.close()

    def test_interface(self):
        self.assertIn("<th>Tipo</th><th>Conteúdo</th>", HTML)
        self.assertIn("api('/api/packet?id='+encodeURIComponent(p.id))", HTML)
        self.assertIn("Ver JSON completo", HTML)


class ShortNamesAndRepeaters(unittest.TestCase):
    def test_short_name_label_on_by_default(self):
        self.assertIn('<input id="showNames" type="checkbox" checked>', HTML)
        self.assertIn('<input id="mapShowNamesSetting" type="checkbox" checked>', HTML)
        self.assertIn("marker.bindTooltip(esc(shortLabel),{permanent:true,direction:'top',offset:[0,-4],className:'nodeShortLabel'})", HTML)
        self.assertIn("mesh.shortNamesDefault.v0662", HTML)

    def test_presence_heard_after_ping_and_no_data(self):
        from mesh_analyzer import insights
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "t.db")
            now = now_ms()
            db.upsert_node(20, 1, timestamp_ms=now - 60000, observed=True, long_name="Morro", role="ROUTER")
            r = insights.repeaters(db, 24, now)["repeaters"][0]
            self.assertIsNone(r["availability"])          # app quase não ouviu: "sem dados"
            if insights._has_table(db, "auto_node_queries"):
                with db._lock, db._db:
                    db._db.execute("""INSERT INTO auto_node_queries(source_id,node_num,kind,request_id,state,sent_ms,due_ms,attempts,error)
                                      VALUES(1,20,'ping','x','timeout',?,?,1,'')""", (now - 3600000, now))
                self.assertEqual(insights.repeaters(db, 24, now)["repeaters"][0]["presence"], "heard_after")
            db.close()


if __name__ == "__main__":
    unittest.main()
