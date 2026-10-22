"""v0.6.39 (#162): primeira abertura sem conexões procura e conecta o rádio (USB primeiro)."""
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock

from mesh_analyzer.database import Database
from mesh_analyzer.device_detection import AutoAdd, DeviceWatcher

ROOT = Path(__file__).resolve().parents[1]


class FirstRunSearch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "t.sqlite3")
        self.sources = Mock()
        self.sources.snapshot.return_value = {}
        self.sources.active_radio.return_value = None
        self.sources.queries.status.return_value = []
        self.network_calls = []
        self.release = threading.Event()

    def tearDown(self):
        self.release.set()
        self.db.close(); self.tmp.cleanup()

    def port(self, name):
        return {"kind": "serial", "address": name, "name": "USB " + name, "config": {"port": name}}

    def auto(self, ports, prober, mdns=None):
        self.watcher = DeviceWatcher(self.db, self.sources, prober=prober, usb=lambda: [], ble=lambda **k: [])
        def ble(**kw):
            self.network_calls.append("ble"); return []
        def scan(seconds):
            self.network_calls.append("mdns"); return mdns or []
        return AutoAdd(self.db, self.sources, self.watcher, prober=prober, usb=lambda: list(ports), ble=ble, mdns=scan)

    @staticmethod
    def radio(c):
        return {"ok": True, "node_num": int(c["address"][3:]) + 100, "long_name": "VHF" + c["address"][3:], "short_name": "V"}

    def test_usb_radio_is_added_and_connected_without_network_search(self):
        auto = self.auto([self.port("COM3")], self.radio)
        auto.run(first_run=True)
        st = auto.status()
        self.assertEqual([a["name"] for a in st["added"]], ["VHF3 USB"])
        self.assertEqual(self.network_calls, [])
        src = self.db.sources()[0]
        self.assertTrue(src["enabled"])
        self.sources.connect.assert_called_once_with(src["id"])
        notice = self.watcher.notices()[0]
        self.assertEqual((notice["type"], notice["source_id"], notice["first_run"]), ("auto_added", src["id"], True))

    def test_usb_ports_are_checked_in_parallel(self):
        def slow(c):
            time.sleep(0.4)
            return {"ok": False, "error": "Timed out"} if c["address"] != "COM7" else self.radio(c)
        auto = self.auto([self.port("COM%d" % n) for n in (3, 4, 5, 6, 7)], slow)
        start = time.monotonic()
        auto.run(first_run=True)
        self.assertLess(time.monotonic() - start, 1.5)
        self.assertEqual([a["name"] for a in auto.status()["added"]], ["VHF7 USB"])

    def test_no_usb_radio_falls_back_to_wifi_and_bluetooth(self):
        mdns = [{"kind": "tcp", "address": "192.168.0.20", "name": "node", "config": {"host": "192.168.0.20", "port": 4403}}]
        def prober(c):
            return {"ok": False, "error": "Timed out"} if c["kind"] == "serial" else {"ok": True, "node_num": 9, "long_name": "Base", "short_name": "B"}
        auto = self.auto([self.port("COM3")], prober, mdns)
        auto.run(first_run=True)
        self.assertEqual(self.network_calls, ["mdns", "ble"])
        self.assertEqual([a["kind"] for a in auto.status()["added"]], ["tcp"])

    def test_nothing_found_reports_results_for_dialog(self):
        auto = self.auto([self.port("COM3")], lambda c: {"ok": False, "error": "Timed out"})
        auto.run(first_run=True)
        st = auto.status()
        self.assertEqual((st["running"], st["phase"], st["added"]), (False, "done", []))
        self.assertEqual([(r["address"], r["outcome"]) for r in st["results"]], [("COM3", "no_response")])

    def test_preferences_and_never_are_respected(self):
        self.db.ignore_device("serial:com3")
        self.db.set_system_settings({"device_autodetect": {"tcp": False, "ble": False}})
        probed = []
        auto = self.auto([self.port("COM3"), self.port("COM4")], lambda c: probed.append(c["address"]) or self.radio(c))
        auto.run(first_run=True)
        self.assertEqual(probed, ["COM4"])
        self.db.set_system_settings({"device_autodetect": {"serial": False}})
        probed.clear()
        self.auto([self.port("COM5")], lambda c: probed.append(c["address"]) or self.radio(c)).run(first_run=True)
        self.assertEqual(probed, [])

    def test_cancel_stops_search_without_adding(self):
        auto = self.auto([self.port("COM3")], lambda c: (self.release.wait(30), self.radio(c))[1])
        auto.start(first_run=True)
        time.sleep(0.3)
        auto.cancel()
        end = time.monotonic() + 3
        while auto.status()["running"] and time.monotonic() < end:
            time.sleep(0.05)
        self.assertEqual(auto.status()["phase"], "cancelled")
        self.assertEqual(self.db.sources(), [])

    def test_app_starts_search_only_without_sources_and_with_interface(self):
        app = (ROOT / "mesh_analyzer" / "app.py").read_text(encoding="utf-8")
        block = app[app.index('if desktop and not os.environ.get("PT2VHF_DISABLE_AUTODETECT"):'):]
        self.assertIn("if not db.sources():\n                autoadd.start(first_run=True)", block[:400])
        html = (ROOT / "mesh_analyzer" / "ui.html").read_text(encoding="utf-8")
        self.assertIn("if(search.first_run&&search.running)", html)
        self.assertIn('id="firstRunSearchAgain"', html)


if __name__ == "__main__":
    unittest.main()
