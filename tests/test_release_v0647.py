"""v0.6.47: conexão Bluetooth tolerante (#191) e visualização por conexão (#189)."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import meshtastic.ble_interface as mble

from mesh_analyzer import ble_link, device_detection
from mesh_analyzer.database import Database
from mesh_analyzer.device_detection import DeviceWatcher

ADDR = "10:20:BA:6A:8C:DD"
CAND = {"kind": "ble", "address": ADDR, "name": "Meshtastic_8cdd", "config": {"address": ADDR}}


class Scanner:
    def __init__(self, found=True):
        self.found, self.calls = found, []

    async def find_device_by_address(self, address, timeout):
        self.calls.append((address, timeout))
        return SimpleNamespace(address=address) if self.found else None


def fake_client_class(behaviours, created):
    """BLEClient falso: cada conexão segue o próximo comportamento da lista."""
    class FakeClient:
        def __init__(self, address=None, **kwargs):
            self.address, self.kwargs, self.closed = address, kwargs, False
            if address is not None:
                self.behaviour = behaviours.pop(0)
                created.append(self)

        def async_await(self, coro):
            return asyncio.run(coro)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            self.close()

        def connect(self):
            if self.behaviour == "timeout":
                raise TimeoutError()
            if self.behaviour == "unreachable":
                raise RuntimeError("Could not get GATT services: Unreachable")

        def read_gatt_char(self, uuid):
            if self.behaviour == "auth":
                raise RuntimeError("Protocol Error 0x05: Insufficient Authentication")
            return b""

        def disconnect(self):
            pass

        def close(self):
            self.closed = True
    return FakeClient


class Link(unittest.TestCase):
    def run_connect(self, behaviours, found=True, attempts=2):
        created, sleeps = [], []
        scanner = Scanner(found)
        with patch.object(mble, "BLEClient", fake_client_class(list(behaviours), created)):
            try:
                client = ble_link.connect_client(ADDR, lambda c: None, attempts=attempts, sleep=sleeps.append, bleak=scanner)
                error = None
            except ble_link.LinkError as exc:
                client, error = None, exc
        return client, error, created, scanner, sleeps

    def test_retry_after_timeout_connects_with_fresh_services_and_longer_timeout(self):
        client, error, created, scanner, sleeps = self.run_connect(["timeout", "ok"])
        self.assertIsNone(error)
        self.assertIs(client, created[1])
        self.assertEqual(created[0].kwargs["timeout"], ble_link.CONNECT_TIMEOUT_S)
        self.assertNotIn("winrt", created[0].kwargs)
        self.assertEqual(created[1].kwargs["winrt"], {"use_cached_services": False})
        self.assertTrue(created[0].closed)
        self.assertEqual(sleeps, [ble_link.RETRY_PAUSE_S])
        # Conecta pelo dispositivo encontrado, não pelo texto do endereço (evita outra varredura).
        self.assertEqual(created[1].address.address, ADDR)
        self.assertEqual(scanner.calls, [(ADDR, ble_link.FIND_TIMEOUT_S)] * 2)

    def test_errors_in_portuguese_with_stage(self):
        _, error, *_ = self.run_connect(["timeout", "unreachable"])
        self.assertEqual(str(error), "Bluetooth: falhou ao abrir a conexão — o Windows não alcançou o rádio (Unreachable); 2 tentativas")
        _, error, *_ = self.run_connect(["timeout"], attempts=1)
        self.assertEqual(str(error), "Bluetooth: falhou ao abrir a conexão — tempo esgotado (20 s)")
        _, error, *_ = self.run_connect([], found=False, attempts=1)
        self.assertEqual((error.stage, str(error)), ("find", "Bluetooth: falhou ao procurar o rádio — rádio não encontrado"))

    def test_radio_requiring_pairing_stops_at_once(self):
        _, error, created, _, sleeps = self.run_connect(["auth", "ok"])
        self.assertTrue(error.auth)
        self.assertEqual(len(created), 1)
        self.assertEqual(sleeps, [])
        self.assertIn("exige pareamento", str(error))

    def test_scans_wait_while_connecting(self):
        with ble_link.activity():
            self.assertTrue(ble_link.busy())
            with self.assertRaises(RuntimeError):
                device_detection.scan_ble()
        self.assertFalse(ble_link.busy())

    def test_probe_reports_pairing_requirement(self):
        def opener(c):
            raise ble_link.LinkError([("access", RuntimeError("Insufficient Authentication"))])
        result = device_detection._probe_meshtastic(dict(CAND), opener)
        self.assertEqual((result["ok"], result.get("auth")), (False, True))


class Verify(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "x.sqlite3")
        self.sources = Mock()
        self.sources.snapshot.return_value = {}
        self.calls = []

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def watcher(self, results, paired=False, pair_status="paired"):
        results = list(results)

        def prober(c):
            self.calls.append("probe")
            return results.pop(0)

        def pairer(a, pin):
            self.calls.append("pair")
            return {"ok": pair_status == "paired", "status": pair_status, "error": ""}
        state = {"paired": paired}

        def unpair(a):
            self.calls.append("unpair")
            state["paired"] = False
            return True
        pairing = SimpleNamespace(is_paired=lambda a: state["paired"], unpair=unpair)
        return DeviceWatcher(self.db, self.sources, prober=prober, usb=lambda: [], ble=lambda **k: [],
                             pairer=pairer, pairing=pairing)

    OK = {"ok": True, "node_num": 5}
    FAIL = {"ok": False, "error": "Bluetooth: falhou ao abrir a conexão — tempo esgotado (20 s)"}

    def test_connects_first_without_touching_pairing(self):
        self.assertTrue(self.watcher([self.OK]).verify(dict(CAND), "t")["ok"])
        self.assertEqual(self.calls, ["probe"])

    def test_existing_pairing_is_kept(self):
        # v0.6.49: remover o pareamento do sistema não ajudou em campo; agora ele fica.
        info = self.watcher([self.FAIL], paired=True).verify(dict(CAND), "t")
        self.assertEqual((info["ok"], info["paired"], self.calls), (False, True, ["probe"]))

    def test_pairing_kept_when_radio_has_a_saved_pin(self):
        cand = {**CAND, "config": {"address": ADDR, "pin": "123456"}}
        info = self.watcher([self.FAIL], paired=True).verify(cand, "t")
        self.assertEqual((info["ok"], self.calls), (False, ["probe"]))

    def test_radio_requiring_pairing_is_paired_then_connected(self):
        info = self.watcher([{**self.FAIL, "auth": True}, self.OK]).verify(dict(CAND), "t")
        self.assertTrue(info["ok"])
        self.assertEqual(self.calls, ["probe", "pair", "probe"])

    def test_radio_with_pin_opens_the_pin_field(self):
        info = self.watcher([{**self.FAIL, "auth": True}], pair_status="pin_required").verify(dict(CAND), "t")
        self.assertTrue(info["needs_pin"])

    def test_failed_pairing_is_reported_with_the_connection_error(self):
        info = self.watcher([self.FAIL], pair_status="failed").verify(dict(CAND), "t")
        self.assertIn("tempo esgotado", info["error"])
        self.assertIn("pareamento sem PIN", info["error"])


class ViewSource(unittest.TestCase):
    def test_packets_and_messages_of_one_connection(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "x.sqlite3")
            try:
                with db._lock, db._db:
                    for i in range(400):   # o MQTT sozinho enche os 300 mais recentes
                        sid = 28 if i >= 50 else 26
                        db._db.execute("INSERT INTO packets(source_id,packet_id,source_packet_key,timestamp_ms,from_node) "
                                       "VALUES(?,?,?,?,1)", (sid, str(i), "k%d" % i, 1000 + i))
                for sid, ts in ((26, 1), (28, 2)):
                    db.add_message({"source_id": sid, "packet_key": "m%d" % sid, "packet_id": str(sid), "timestamp_ms": ts,
                                    "from_node": 1, "to_node": 2, "channel": 0, "direction": "rx", "text": "oi", "state": "received"})
                self.assertEqual({r["source_id"] for r in db.packet_rows()}, {28})
                radio = db.packet_rows(source_id=26)
                self.assertEqual((len(radio), {r["source_id"] for r in radio}), (50, {26}))
                self.assertEqual([m["source_id"] for m in db.message_rows(source_id=26)], [26])
                self.assertEqual(len(db.message_rows()), 2)
            finally:
                db.close()

    def test_view_source_query(self):
        from mesh_analyzer.app import view_source
        self.assertEqual(view_source("/api/packets?source=28"), 28)
        self.assertIsNone(view_source("/api/packets"))
        self.assertIsNone(view_source("/api/packets?source=abc"))


if __name__ == "__main__":
    unittest.main()
