"""v0.6.48: PIN informado num resultado do "Adicionar automaticamente" (#191)."""
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from mesh_analyzer.database import Database
from mesh_analyzer.device_detection import DeviceWatcher

ADDR = "44:1B:F6:70:9C:25"


class PinFromAutoAdd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "x.sqlite3")
        self.sources = Mock()
        self.sources.snapshot.return_value = {}
        self.sources.active_radio.return_value = None
        self.pairs = []
        self.w = DeviceWatcher(self.db, self.sources, prober=lambda c: {"ok": True, "node_num": 9, "long_name": "Base BLE"},
                               usb=lambda: [], ble=lambda **k: [],
                               pairing=SimpleNamespace(is_paired=lambda a: None, unpair=lambda a: False))

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def pairer(self, address, pin):
        self.pairs.append((address, pin))
        return {"ok": True, "status": "paired"}

    def test_pin_pairs_verifies_and_adds(self):
        self.w.pair_address(ADDR.lower(), "123456", "Meshtastic_9c25", pairer=self.pairer)
        end = time.time() + 3
        while (self.w.notices()[0].get("job") or {}).get("phase") != "done" and time.time() < end:
            time.sleep(0.05)
        self.assertEqual(self.pairs, [(ADDR, "123456")])
        self.assertEqual([s["name"] for s in self.db.sources()], ["Base BLE BLE"])  # nome do rádio + " BLE"

    def test_invalid_pin_and_already_configured(self):
        with self.assertRaises(ValueError):
            self.w.pair_address(ADDR, "12", pairer=self.pairer)
        self.db.upsert_source({"name": "Já", "kind": "ble", "config": {"address": ADDR}, "enabled": False})
        with self.assertRaises(ValueError):
            self.w.pair_address(ADDR, "123456", pairer=self.pairer)
        self.assertEqual(self.pairs, [])


if __name__ == "__main__":
    unittest.main()
