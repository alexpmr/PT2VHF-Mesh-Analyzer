"""v0.6.43 (#164): rádio Bluetooth sem PIN definido é incluído sem clique.

v0.6.47 (#191): a conexão é tentada antes sem parear, como no celular; o pareamento
só acontece quando o rádio exige (e o que pede PIN abre o campo de PIN)."""
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from mesh_analyzer import ble_pairing
from mesh_analyzer.database import Database
from mesh_analyzer.device_detection import DeviceWatcher

ADDR = "44:1B:F6:70:8A:69"
CAND = {"kind": "ble", "address": ADDR, "name": "VHF4_8a68", "config": {"address": ADDR}}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.db = Database(self.data / "mesh-analyzer.sqlite3")
        self.sources = Mock()
        self.sources.snapshot.return_value = {}
        self.sources.active_radio.return_value = None
        self.sources.queries.status.return_value = []
        self.pairs = []
        self.unpaired = []

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def watcher(self, pair_status, probe_ok=True):
        def pairer(address, pin):
            self.pairs.append((address, pin))
            return {"ok": pair_status in ("paired", "already_paired"), "status": pair_status,
                    "error": "Este rádio pede PIN" if pair_status == "pin_required" else ""}

        def prober(c):
            if not probe_ok:
                return {"ok": False, "error": "Sem resposta"}
            if pair_status == "pin_required":   # rádio com PIN: sem parear, a leitura é recusada
                return {"ok": False, "auth": True, "error": "Bluetooth: o rádio exige pareamento"}
            return {"ok": True, "node_num": 77, "long_name": "VHF4", "short_name": "V4"}
        pairing = SimpleNamespace(is_paired=lambda a: False, unpair=lambda a: self.unpaired.append(a) or True)
        return DeviceWatcher(self.db, self.sources, prober=prober, usb=lambda: [], ble=lambda **k: [dict(CAND)],
                             pairer=pairer, pairing=pairing)


class NoPinRadio(Base):
    def test_detected_radio_without_pin_is_added_without_click_and_without_pairing(self):
        w = self.watcher("paired")
        w._check_ble()
        self.assertEqual(self.pairs, [])          # #191: conecta direto, como o celular
        sources = self.db.sources()
        self.assertEqual([s["name"] for s in sources], ["VHF4 BLE"])
        self.assertEqual(w.notices()[0]["type"], "auto_added")
        self.sources.connect.assert_called_once_with(sources[0]["id"])
        w._check_ble()                       # já cadastrado: não duplica nem pareia de novo
        self.assertEqual(len(self.db.sources()), 1)
        self.assertEqual(self.pairs, [])

    def test_radio_asking_for_pin_shows_the_pin_field_instead(self):
        w = self.watcher("pin_required")
        w._check_ble()
        self.assertEqual(self.db.sources(), [])
        notice = w.notices()[0]
        self.assertEqual((notice["type"], notice["job"]["phase"], notice["job"]["needs_pin"]), ("detected", "failed", True))
        self.assertIn("PIN", notice["job"]["error"])

    def test_preference_off_keeps_the_click_notice(self):
        self.db.set_system_settings({"device_autoconnect": {"ble": False}})
        w = self.watcher("paired")
        w._check_ble()
        self.assertEqual(self.db.sources(), [])
        self.assertEqual(self.pairs, [])
        self.assertNotIn("job", w.notices()[0])

    def test_click_on_notice_adds_radio_without_pin(self):
        self.db.set_system_settings({"device_autoconnect": {"ble": False}})
        w = self.watcher("paired")
        w._offer(dict(CAND))
        w.accept(w.notices()[0]["id"], wait=True)
        job = w.notices()[0]["job"]
        self.assertEqual((job["phase"], job["source"]["name"]), ("done", "VHF4 BLE"))
        self.assertEqual(self.pairs, [])

    def test_failure_after_successful_pairing_does_not_ask_for_pin(self):
        self.db.set_system_settings({"device_autoconnect": {"ble": False}})
        w = self.watcher("paired", probe_ok=False)
        w._offer(dict(CAND))
        w.accept(w.notices()[0]["id"], wait=True)
        self.assertEqual((w.notices()[0]["job"]["phase"], w.notices()[0]["job"]["needs_pin"]), ("failed", False))
        self.assertEqual(self.pairs, [(ADDR, None)])   # tentou parear depois da falha...
        self.assertEqual(self.unpaired, [ADDR])         # ...e desfez o pareamento que não ajudou
        self.assertIn("pareado sem PIN", w.notices()[0]["job"]["error"])

    def test_pairing_with_typed_pin_does_not_pair_again_without_pin(self):
        self.db.set_system_settings({"device_autoconnect": {"ble": False}})
        w = self.watcher("paired")
        w._offer(dict(CAND))
        w.pair(w.notices()[0]["id"], "123456", pairer=lambda a, p: {"ok": True, "status": "paired"})
        end = time.time() + 3
        while w.notices()[0]["job"]["phase"] != "done" and time.time() < end:
            time.sleep(0.05)
        self.assertEqual(w.notices()[0]["job"]["phase"], "done")
        self.assertEqual(self.pairs, [])


class Migration(Base):
    def test_old_profiles_get_bluetooth_auto_add_once(self):
        self.db.set_system_settings({"device_autoconnect": {"ble": False, "tcp": True}})
        self.db._db.execute("DELETE FROM settings WHERE key='ble_autoconnect_v0643'")
        self.db._db.commit()
        self.db.close()
        self.db = Database(self.data / "mesh-analyzer.sqlite3")
        self.assertEqual(self.db.system_settings()["device_autoconnect"], {"serial": True, "tcp": True, "ble": True})
        self.db.set_system_settings({"device_autoconnect": {"ble": False}})
        self.db.close()
        self.db = Database(self.data / "mesh-analyzer.sqlite3")
        self.assertFalse(self.db.system_settings()["device_autoconnect"]["ble"])   # escolha posterior é respeitada


class Bluetoothctl(Base):
    def fake(self, body):
        script = self.data / "btctl.py"
        script.write_text("import sys\nfor line in sys.stdin:\n    line=line.strip()\n" + body +
                          "    if line=='quit': break\n")
        return (sys.executable, str(script))

    def test_linux_pairs_radio_without_pin(self):
        cmd = self.fake("    if line.startswith('pair'): print('Pairing successful', flush=True)\n")
        self.assertEqual(ble_pairing._pair_linux(ADDR, None, 10, command=cmd)["status"], "paired")

    def test_linux_reports_pin_required(self):
        cmd = self.fake("    if line.startswith('pair'): print('[agent] Enter passkey (number in 0-999999):', flush=True)\n")
        self.assertEqual(ble_pairing._pair_linux(ADDR, None, 10, command=cmd)["status"], "pin_required")

    def test_linux_confirms_just_works_request(self):
        cmd = self.fake("    if line.startswith('pair'): print('[agent] Request confirmation [yes/no]', flush=True)\n"
                        "    elif line=='yes': print('Pairing successful', flush=True)\n")
        self.assertTrue(ble_pairing._pair_linux(ADDR, None, 10, command=cmd)["ok"])

    def test_macos_without_pin_is_left_to_the_system(self):
        out = ble_pairing.pair(ADDR, None, platform="darwin")
        self.assertEqual((out["ok"], out["status"], out["error"]), (True, "system_dialog", ""))


if __name__ == "__main__":
    unittest.main()
