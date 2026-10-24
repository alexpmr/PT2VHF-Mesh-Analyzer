"""v0.6.49: contadores por conexão (#189/#194) e diagnóstico Bluetooth (#191)."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from mesh_analyzer import device_detection
from mesh_analyzer.database import Database
from mesh_analyzer.device_detection import AutoAdd


class Counts(unittest.TestCase):
    def test_counters_of_one_connection(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "x.sqlite3")
            try:
                with db._lock, db._db:
                    for i, sid in enumerate((26, 28, 28)):
                        db._db.execute("INSERT INTO packets(source_id,packet_id,source_packet_key,timestamp_ms,from_node) "
                                       "VALUES(?,?,?,?,1)", (sid, str(i), "k%d" % i, 1000 + i))
                db.upsert_node(5, 28, observed=True)
                db.upsert_node(6, 26, observed=True)
                db.upsert_node(7, 28, observed=True)
                self.assertEqual(db.stats()["packets"], 3)
                self.assertEqual((db.stats(28)["packets"], db.stats(28)["nodes"]), (2, 2))
                self.assertEqual((db.stats(26)["packets"], db.stats(26)["nodes"]), (1, 1))
            finally:
                db.close()


class Adapter(unittest.TestCase):
    def test_adapter_reported_only_when_bluetooth_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "x.sqlite3")
            try:
                calls = []
                ble = [{"kind": "ble", "address": "44:1B:F6:70:9C:25", "name": "M", "config": {"address": "44:1B:F6:70:9C:25"}}]
                sources = Mock()
                sources.snapshot.return_value = {}
                auto = AutoAdd(db, sources, watcher=None, prober=lambda c: {"ok": False, "error": "Unreachable"},
                               usb=lambda: [], ble=lambda **k: list(ble), mdns=lambda s: [],
                               adapter=lambda: calls.append(1) or {"present": True, "name": "Intel BT", "le": True, "central": True})
                auto.run()
                self.assertEqual(auto.status()["ble_adapter"]["name"], "Intel BT")
                ble.clear()
                auto.run()
                self.assertIsNone(auto.status()["ble_adapter"])
                self.assertEqual(calls, [1])
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
