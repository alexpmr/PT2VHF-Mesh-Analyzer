"""v0.6.45 (#185, etapa 1): rádios MeshCore Companion como fonte do app."""
import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from meshcore import EventType

from mesh_analyzer.database import Database
from mesh_analyzer.meshcore_driver import BROADCAST, MeshCoreInterface, name_num, node_num
from mesh_analyzer.transports import SourceManager

SELF_KEY = "a1b2c3d4" + "00" * 28
REPEATER_KEY = "0badcafe" + "11" * 28
FRIEND_KEY = "55667788" + "22" * 28


def event(kind, payload):
    return SimpleNamespace(type=kind, payload=payload, attributes={})


class FakeMeshCore:
    def __init__(self):
        self.subs = {}
        self.sent = []
        self.self_info = {"public_key": SELF_KEY, "name": "PT2VHF Base", "adv_lat": -15.79, "adv_lon": -47.88}
        contacts = {REPEATER_KEY: {"public_key": REPEATER_KEY, "type": 2, "adv_name": "Repetidor Torre", "last_advert": 1761000000,
                                   "adv_lat": -15.70, "adv_lon": -47.90, "out_path_len": 0},
                    FRIEND_KEY: {"public_key": FRIEND_KEY, "type": 1, "adv_name": "Maria", "last_advert": 1761000100,
                                 "adv_lat": 0.0, "adv_lon": 0.0, "out_path_len": 2}}
        fake = self

        class Commands:
            async def get_contacts(self):
                return event(EventType.CONTACTS, contacts)

            async def get_contact_by_key(self, key):
                return event(EventType.NEXT_CONTACT, {"public_key": key.hex(), "type": 4, "adv_name": "Sensor Rio",
                                                     "last_advert": 1761000200, "adv_lat": -15.6, "adv_lon": -47.7})

            async def send_msg(self, key, text):
                fake.sent.append(("dm", key, text))
                return event(EventType.MSG_SENT, {"expected_ack": bytes.fromhex("0a0b0c0d")})

            async def send_chan_msg(self, chan, text):
                fake.sent.append(("chan", chan, text))
                return event(EventType.OK, {})

        self.commands = Commands()

    def subscribe(self, kind, callback):
        self.subs[kind] = callback

    async def start_auto_message_fetching(self):
        return None

    async def disconnect(self):
        self.disconnected = True

    def fire(self, iface, kind, payload):
        asyncio.run_coroutine_threadsafe(self.subs[kind](event(kind, payload)), iface._loop).result(5)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "mesh-analyzer.sqlite3")
        self.source = self.db.upsert_source({"name": "MeshCore USB", "kind": "serial",
                                             "config": {"port": "COM9", "protocol": "meshcore"}, "enabled": False})
        self.manager = SourceManager(self.db)
        self.fake = FakeMeshCore()

        async def factory(kind, conf):
            return self.fake
        self.iface = MeshCoreInterface("serial", {"port": "COM9"}, on_packet=self.manager._on_packet,
                                       on_lost=self.manager._lost, factory=factory)
        sid = self.source["id"]
        self.manager._interfaces[sid] = self.iface
        self.manager._set(sid, "connected")
        self.manager.ingest.seed_from_interface(sid, self.iface)

    def tearDown(self):
        self.iface.close()
        self.manager.close()
        self.db.close()
        self.tmp.cleanup()

    def node(self, num):
        rows = self.db._rows("SELECT * FROM nodes WHERE node_num=?", (num,))
        return dict(rows[0]) if rows else None


class Identity(unittest.TestCase):
    def test_node_numbers(self):
        self.assertEqual(node_num(SELF_KEY), 0xA1B2C3D4)
        self.assertEqual(node_num("a1b2c3d4e5f6"), 0xA1B2C3D4)
        self.assertIsNone(node_num("ffffffff00"))
        self.assertIsNone(node_num("zz"))
        self.assertEqual(name_num("Maria"), name_num("Maria"))
        self.assertNotEqual(name_num("Maria"), name_num("João"))


class Receive(Base):
    def test_self_info_and_contacts_become_nodes_with_roles_and_positions(self):
        snap = self.manager.snapshot()[str(self.source["id"])]
        self.assertEqual(snap["local_node_num"], 0xA1B2C3D4)
        own = self.node(0xA1B2C3D4)
        self.assertEqual((own["long_name"], own["hw_model"]), ("PT2VHF Base", "MeshCore Companion"))
        rep = self.node(node_num(REPEATER_KEY))
        self.assertEqual((rep["long_name"], rep["role"], rep["hw_model"]), ("Repetidor Torre", "REPEATER", "MeshCore Repetidor"))
        self.assertAlmostEqual(rep["latitude"], -15.70)
        self.assertIsNone(self.node(node_num(FRIEND_KEY))["latitude"])  # 0,0 não é posição

    def test_new_advert_is_traffic_with_position_and_direct_rf_link(self):
        self.fake.fire(self.iface, EventType.NEW_CONTACT, {"public_key": "deadbeef" + "33" * 28, "type": 2, "adv_name": "Serra",
                                                           "last_advert": int(time.time()), "adv_lat": -15.5, "adv_lon": -47.6,
                                                           "out_path_len": 0})
        n = self.node(0xDEADBEEF)
        self.assertEqual((n["long_name"], n["role"]), ("Serra", "REPEATER"))
        self.assertAlmostEqual(n["longitude"], -47.6)
        ports = {r["port"] for r in self.db._rows("SELECT port FROM packets WHERE from_node=?", (0xDEADBEEF,))}
        self.assertEqual(ports, {"NODEINFO_APP", "POSITION_APP"})

    def test_advertisement_push_fetches_the_contact(self):
        self.fake.fire(self.iface, EventType.ADVERTISEMENT, {"public_key": "c0ffee00" + "44" * 28})
        n = self.node(0xC0FFEE00)
        self.assertEqual((n["long_name"], n["role"]), ("Sensor Rio", "SENSOR"))

    def test_direct_and_channel_messages(self):
        self.fake.fire(self.iface, EventType.CONTACT_MSG_RECV, {"type": "PRIV", "pubkey_prefix": FRIEND_KEY[:12], "path_len": 2,
                                                                "txt_type": 0, "sender_timestamp": int(time.time()), "text": "Oi, tudo bem?"})
        self.fake.fire(self.iface, EventType.CHANNEL_MSG_RECV, {"type": "CHAN", "channel_idx": 0, "path_len": 1, "txt_type": 0,
                                                                "sender_timestamp": int(time.time()), "text": "Repetidor Torre: bom dia rede"})
        self.fake.fire(self.iface, EventType.CHANNEL_MSG_RECV, {"type": "CHAN", "channel_idx": 1, "path_len": 0, "txt_type": 0,
                                                                "sender_timestamp": int(time.time()) + 1, "text": "Visitante: olá"})
        msgs = [dict(r) for r in self.db._rows("SELECT * FROM messages ORDER BY id")]
        self.assertEqual([(m["from_node"], m["to_node"], m["channel"], m["text"]) for m in msgs], [
            (node_num(FRIEND_KEY), 0xA1B2C3D4, 0, "Oi, tudo bem?"),
            (node_num(REPEATER_KEY), BROADCAST, 0, "bom dia rede"),
            (name_num("Visitante"), BROADCAST, 1, "olá")])
        self.assertEqual(self.node(name_num("Visitante"))["long_name"], "Visitante")

    def test_rx_log_counts_traffic_with_signal_and_hops(self):
        self.fake.fire(self.iface, EventType.RX_LOG_DATA, {"payload_typename": "ADVERT", "adv_key": REPEATER_KEY, "snr": 7.25,
                                                           "rssi": -88, "path_len": 0, "pkt_hash": "abc123", "recv_time": int(time.time())})
        row = dict(self.db._rows("SELECT * FROM packets WHERE port='MESHCORE_ADVERT'")[0])
        self.assertEqual((row["from_node"], row["rx_snr"], row["rx_rssi"], row["hop_start"], row["hop_limit"]),
                         (node_num(REPEATER_KEY), 7.25, -88, 0, 0))
        # Ouvido sem saltos pelo próprio rádio: evidência de enlace RF direto.
        links = self.db._rows("SELECT quality FROM links WHERE a=? AND b=?",
                              tuple(sorted((node_num(REPEATER_KEY), 0xA1B2C3D4))))
        self.assertEqual([r["quality"] for r in links], ["confirmed_direct_rf"])


class Send(Base):
    def test_direct_message_is_sent_to_the_contact_key_and_ack_marks_delivered(self):
        result = self.manager.send_text(self.source["id"], node_num(FRIEND_KEY), "Teste MeshCore")
        self.assertEqual(self.fake.sent[-1], ("dm", FRIEND_KEY, "Teste MeshCore"))
        self.assertEqual(result["packet_id"], str(0x0A0B0C0D))
        self.fake.fire(self.iface, EventType.ACK, {"code": "0a0b0c0d"})
        state = self.db._rows("SELECT state FROM messages WHERE direction='tx'")[0]["state"]
        self.assertEqual(state, "delivered")

    def test_channel_message(self):
        self.manager.send_text(self.source["id"], None, "Alô canal", channel=1)
        self.assertEqual(self.fake.sent[-1], ("chan", 1, "Alô canal"))

    def test_unknown_contact_is_refused(self):
        with self.assertRaises(ValueError):
            self.manager.send_text(self.source["id"], 0x12345678, "x")


class Config(unittest.TestCase):
    def test_protocol_validation_and_meshcore_tcp_default_port(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "x.sqlite3")
            try:
                s = db.upsert_source({"name": "MC Wi-Fi", "kind": "tcp", "config": {"host": "10.0.0.5", "protocol": "meshcore"}})
                self.assertEqual((s["config"]["protocol"], s["config"]["port"]), ("meshcore", 5000))
                m = db.upsert_source({"name": "MT Wi-Fi", "kind": "tcp", "config": {"host": "10.0.0.6"}})
                self.assertEqual((m["config"]["protocol"], m["config"]["port"]), ("meshtastic", 4403))
                b = db.upsert_source({"name": "MC BLE", "kind": "ble", "config": {"address": "AA:BB:CC:DD:EE:FF", "protocol": "meshcore", "pin": "123456"}})
                self.assertEqual(b["config"]["pin"], "123456")
                with self.assertRaises(ValueError):
                    db.upsert_source({"name": "X", "kind": "serial", "config": {"port": "COM1", "protocol": "lora"}})
                with self.assertRaises(ValueError):
                    db.upsert_source({"name": "X", "kind": "ble", "config": {"address": "A", "protocol": "meshcore", "pin": "12"}})
            finally:
                db.close()


class Detection(unittest.TestCase):
    def test_usb_probe_tries_meshcore_then_meshtastic(self):
        from mesh_analyzer.device_detection import probe
        cand = {"kind": "serial", "address": "COM7", "name": "USB", "config": {"port": "COM7"}}
        found = probe(cand, opener=lambda c: None,
                      meshcore_prober=lambda c: {"ok": True, "node_num": 5, "long_name": "MC", "protocol": "meshcore"})
        self.assertTrue(found["ok"])
        self.assertEqual(cand["config"]["protocol"], "meshcore")
        fallback = probe({"kind": "serial", "address": "COM8", "name": "USB", "config": {"port": "COM8"}},
                         opener=lambda c: SimpleNamespace(getMyNodeInfo=lambda: {"num": 9, "user": {"longName": "MT"}}, close=lambda: None),
                         meshcore_prober=lambda c: {"ok": False, "error": "não é MeshCore"})
        self.assertEqual((fallback["ok"], fallback["node_num"]), (True, 9))

    def test_meshcore_ble_candidate_never_falls_back_to_meshtastic(self):
        from mesh_analyzer.device_detection import probe
        calls = []
        out = probe({"kind": "ble", "address": "AA", "name": "MeshCore-1234", "config": {"address": "AA", "protocol": "meshcore"}},
                    opener=lambda c: calls.append(c), meshcore_prober=lambda c: {"ok": False, "error": "sem resposta"})
        self.assertFalse(out["ok"])
        self.assertEqual(calls, [])

    def test_registry_stores_protocol_and_label(self):
        from unittest.mock import Mock
        from mesh_analyzer.device_detection import Registry
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "x.sqlite3")
            try:
                sources = Mock(); sources.snapshot.return_value = {}
                src = Registry(db, sources).add({"kind": "serial", "address": "COM7", "name": "USB", "config": {"port": "COM7"}},
                                                {"node_num": 5, "long_name": "Base", "protocol": "meshcore"})
                self.assertEqual((src["name"], src["config"]["protocol"]), ("Base MeshCore USB", "meshcore"))
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
