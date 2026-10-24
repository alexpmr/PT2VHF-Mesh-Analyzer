"""v0.6.46 (#190 MeshCore etapa 2 e #188 coleta periódica)."""
import asyncio
import json
import tempfile
import time
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from types import SimpleNamespace

from meshcore import EventType

from mesh_analyzer import survey
from mesh_analyzer.app import build_handler
from mesh_analyzer.database import Database
from mesh_analyzer.meshcore_data import MeshCoreAutomation
from mesh_analyzer.meshcore_driver import MeshCoreInterface, node_num, split_path
from mesh_analyzer.transports import SourceManager

SELF_KEY = "a1b2c3d4" + "00" * 28
REP_A = "0badcafe" + "11" * 28      # repetidor direto
REP_B = "0b112233" + "12" * 28      # mesmo 1º byte de REP_A: colisão
REP_HUB = "77665544" + "13" * 28    # repetidor com posição, usado nos caminhos
REP_FAR = "abcdef01" + "14" * 28    # repetidor alcançado via REP_HUB
FRIEND = "55667788" + "22" * 28


def event(kind, payload, attributes=None):
    return SimpleNamespace(type=kind, payload=payload, attributes=attributes or {})


def contact(key, kind, name, path="", plen=-1, lat=0.0, lon=0.0, advert=None):
    return {"public_key": key, "type": kind, "adv_name": name, "last_advert": advert or int(time.time()) - 60,
            "adv_lat": lat, "adv_lon": lon, "out_path": path, "out_path_len": plen, "out_path_hash_mode": 0}


class FakeMeshCore:
    def __init__(self):
        self.subs, self.calls = {}, []
        self.self_info = {"public_key": SELF_KEY, "name": "PT2VHF Base", "adv_lat": -15.79, "adv_lon": -47.88,
                          "radio_freq": 910.525, "radio_bw": 62.5, "radio_sf": 7, "tx_power": 20, "manual_add_contacts": False}
        self.contacts = {c["public_key"]: c for c in (
            contact(REP_A, 2, "Torre", plen=0, lat=-15.70, lon=-47.90),
            contact(REP_B, 2, "Morro", plen=0),
            contact(REP_HUB, 3, "Hub", plen=0, lat=-15.60, lon=-47.80),
            contact(REP_FAR, 2, "Longe", path="77", plen=1, lat=-15.50, lon=-47.70),
            contact(FRIEND, 1, "Maria", path="77", plen=1, advert=int(time.time()) - 90 * 86400))}
        self.fail = set()
        fake = self

        class Dispatcher:
            async def wait_for_event(self, kind, attribute_filters=None, timeout=None):
                fake.calls.append(("wait", kind.name, attribute_filters))
                if "trace" in fake.fail:
                    return None
                return event(EventType.TRACE_DATA, {"tag": attribute_filters["tag"], "path": [
                    {"hash": "77", "snr": 5.25}, {"hash": "ab", "snr": 3.0}, {"hash": "77", "snr": 4.5}, {"snr": 6.0}]})

        class Commands:
            def __getattr__(self, name):
                async def call(*args, **kwargs):
                    fake.calls.append((name, args, kwargs))
                    return await fake.answer(name, args, kwargs)
                return call

        self.commands, self.dispatcher = Commands(), Dispatcher()

    async def answer(self, name, args, kwargs):
        if name in self.fail:
            return None if name.endswith("_sync") else event(EventType.ERROR, {})
        if name == "get_contacts":
            return event(EventType.CONTACTS, self.contacts)
        if name == "send_device_query":
            return event(EventType.DEVICE_INFO, {"max_contacts": 100, "max_channels": 3, "model": "Heltec V3",
                                                 "ver": "1.9", "path_hash_mode": 0})
        if name == "send_path_discovery_sync":
            return event(EventType.PATH_RESPONSE, {"out_path": "0bad", "out_path_len": 1, "out_path_hash_len": 2})
        if name == "send_login_sync":
            return event(EventType.LOGIN_SUCCESS if args[1] == "secreta" else EventType.LOGIN_FAILED, {})
        if name == "req_status_sync":
            return {"bat": 4100, "noise_floor": -112, "uptime": 3600, "nb_recv": 50, "nb_sent": 20}
        if name == "req_telemetry_sync":
            return [{"channel": 1, "type": "voltage", "value": 4.05}, {"channel": 1, "type": "temperature", "value": 31.5}]
        if name == "req_neighbours_sync":
            return {"neighbours_count": 2, "neighbours": [{"pubkey": REP_HUB[:8], "secs_ago": 30, "snr": 7.5},
                                                          {"pubkey": "deadbeef", "secs_ago": 90, "snr": -3.0}]}
        if name == "send_cmd":
            key = args[0]["public_key"]
            loop = asyncio.get_running_loop()
            loop.call_later(0.05, lambda: asyncio.ensure_future(self.subs[EventType.CONTACT_MSG_RECV](event(
                EventType.CONTACT_MSG_RECV, {"pubkey_prefix": key[:12], "txt_type": 1, "text": "> 1.9.0 (2026)",
                                             "sender_timestamp": int(time.time())}))))
            return event(EventType.MSG_SENT, {})
        if name == "send_trace":
            return event(EventType.MSG_SENT, {"suggested_timeout": 4000})
        if name == "get_channel":
            names = ["Public", "#brasilia", ""]
            return event(EventType.CHANNEL_INFO, {"channel_idx": args[0], "channel_name": names[args[0]],
                                                  "channel_secret": b"\x01" * 16 if names[args[0]] else b"\x00" * 16})
        if name == "export_contact":
            return event(EventType.CONTACT_URI, {"uri": "meshcore://abc"})
        if name.startswith("get_stats_"):
            return event(EventType.OK, {"kind": name})
        return event(EventType.OK, {})

    def subscribe(self, kind, callback):
        self.subs[kind] = callback

    async def start_auto_message_fetching(self):
        return None

    async def disconnect(self):
        return None


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "mesh-analyzer.sqlite3")
        self.source = self.db.upsert_source({"name": "MeshCore USB", "kind": "serial",
                                             "config": {"port": "COM9", "protocol": "meshcore"}, "enabled": False})
        self.sid = self.source["id"]
        self.manager = SourceManager(self.db)
        self.fake = FakeMeshCore()

        async def factory(kind, conf):
            return self.fake
        self.iface = MeshCoreInterface("serial", {"port": "COM9"}, on_packet=self.manager._on_packet,
                                       on_lost=self.manager._lost, factory=factory,
                                       on_event=self.manager._on_meshcore_event, source_id=self.sid)
        self.manager._interfaces[self.sid] = self.iface
        self.manager._set(self.sid, "connected")
        self.manager.ingest.seed_from_interface(self.sid, self.iface)

    def tearDown(self):
        self.iface.close()
        self.manager.close()
        self.db.close()
        self.tmp.cleanup()

    def names(self, nums):
        return sorted(c["name"] for c in self.manager.meshcore.contacts(self.sid) if c["node_num"] in nums)


class Storage(Base):
    def test_contacts_device_and_occupancy_are_stored(self):
        ov = self.manager.meshcore.overview(self.sid)
        self.assertEqual(ov["contacts"], 5)
        self.assertEqual(ov["occupancy"], {"used": 5, "max": 100, "percent": 5})
        self.assertEqual(ov["by_type"], {"Repetidor": 3, "Room server": 1, "Companion": 1})
        self.assertEqual(ov["self"]["radio_sf"], 7)
        self.assertEqual([s["name"] for s in ov["stale"]], ["Maria"])

    def test_prefix_collisions_between_relays(self):
        groups = self.manager.meshcore.collisions(self.sid)
        self.assertEqual([(g["prefix"], g["bytes"]) for g in groups], [("0b", 1)])
        self.assertEqual(sorted(m["name"] for m in groups[0]["members"]), ["Morro", "Torre"])

    def test_paths_resolve_repeaters_with_positions(self):
        paths = {p["name"]: p for p in self.manager.meshcore.paths(self.sid)}
        self.assertEqual(paths["Torre"]["mode"], "direct")
        hop = paths["Maria"]["hops"][0]
        self.assertEqual((hop["hash"], hop["name"], hop["latitude"]), ("77", "Hub", -15.60))
        self.assertEqual(split_path("0bad77", 1), ["0b", "ad", "77"])
        self.assertEqual(split_path("0bad77aa", 2), ["0bad", "77aa"])

    def test_path_change_is_recorded_once_and_reset_goes_to_flood(self):
        self.iface.reset_path(node_num(FRIEND))
        self.iface.path_discovery(node_num(FRIEND))
        changes = self.manager.meshcore.path_changes(self.sid)
        self.assertEqual([(c["old_path"], c["new_path"], c["new_len"]) for c in changes][::-1],
                         [("77", "", -1)])  # sair do flood não é "mudança" de um caminho conhecido
        contact = {c["name"]: c for c in self.manager.meshcore.contacts(self.sid)}["Maria"]
        self.assertEqual((contact["out_path"], contact["out_path_len"], contact["hash_mode"]), ("0bad", 1, 1))


class Operations(Base):
    def test_status_telemetry_and_login(self):
        rep = node_num(REP_A)
        with self.assertRaises(RuntimeError):
            self.iface.login(rep, "errada")
        self.iface.login(rep, "secreta")
        self.assertEqual(self.iface.status(rep)["noise_floor"], -112)
        self.assertEqual(self.iface.telemetry(rep)["lpp"][1]["value"], 31.5)
        kinds = [r["kind"] for r in self.manager.meshcore.results(self.sid, rep)]
        self.assertEqual(kinds, ["telemetry", "status"])

    def test_neighbours_feed_the_topology(self):
        result = self.iface.neighbours(node_num(REP_A))
        self.assertEqual([n["node_num"] for n in result["neighbours"]], [node_num(REP_HUB), None])
        self.assertEqual(self.fake.calls[-1][2], {"pubkey_prefix_length": 4})
        ports = [r["port"] for r in self.db._rows("SELECT port FROM packets WHERE from_node=?", (node_num(REP_A),))]
        self.assertIn("NEIGHBORINFO_APP", ports)

    def test_trace_goes_out_and_back_through_the_path(self):
        result = self.iface.trace(node_num(REP_FAR))
        self.assertEqual(result["route"], ["77", "ab", "77"])
        sent = [c for c in self.fake.calls if c[0] == "send_trace"][0]
        self.assertEqual(sent[2]["path"], "77,ab,77")
        self.assertEqual([h.get("node_num") for h in result["path"][:3]], [node_num(REP_HUB), node_num(REP_FAR), node_num(REP_HUB)])
        self.assertEqual(result["path"][-1]["snr"], 6.0)
        self.assertTrue(self.db._rows("SELECT 1 FROM packets WHERE port='TRACEROUTE_APP'"))
        with self.assertRaises(ValueError):
            self.iface.trace(node_num(FRIEND))  # companion não repete o trace

    def test_cli_reply_goes_to_the_caller_not_to_the_chat(self):
        self.assertEqual(self.iface.cli(node_num(REP_A), "ver")["reply"], "> 1.9.0 (2026)")
        self.assertFalse(self.db._rows("SELECT 1 FROM messages"))

    def test_channels_uri_autoadd_advert_remove(self):
        chans = self.iface.channels()
        self.assertEqual([(c["name"], c["empty"]) for c in chans], [("Public", False), ("#brasilia", False), ("", True)])
        self.iface.set_channel(2, "#pt2vhf")
        self.assertIn(("set_channel", (2, "#pt2vhf"), {}), self.fake.calls)
        with self.assertRaises(ValueError):
            self.iface.set_channel(2, "x" * 40)
        self.assertEqual(self.iface.contact_uri()["uri"], "meshcore://abc")
        self.assertEqual(self.iface.autoadd(False), {"auto_add": False})
        self.iface.send_advert(flood=True)
        self.assertIn(("send_advert", (), {"flood": True}), self.fake.calls)
        self.iface.remove_contact(node_num(REP_B))
        self.assertEqual(self.manager.meshcore.overview(self.sid)["contacts"], 4)
        self.assertEqual(set(self.iface.stats()), {"core", "radio", "packets"})


class Automation(Base):
    def test_periodic_collection_with_budget_password_and_backoff(self):
        auto = MeshCoreAutomation(self.db, self.manager)
        rep, far = node_num(REP_A), node_num(REP_FAR)
        self.assertEqual(auto.tick()["reason"], "Coleta MeshCore desativada")
        auto.save({"enabled": True, "max_per_hour": 2, "min_gap_seconds": 30, "targets": [
            {"node_num": rep, "kind": "telemetry", "interval_minutes": 60},
            {"node_num": far, "kind": "status", "interval_minutes": 30}]})
        auto.set_password(rep, "secreta")
        now = int(time.time() * 1000)
        first = auto.tick(now)
        self.assertTrue(first["sent"])
        self.assertIn(("send_login_sync", (REP_A, "secreta"), {}), [(c[0], (c[1][0], c[1][1]) if len(c[1]) > 1 else c[1], c[2])
                                                                     for c in self.fake.calls if c[0] == "send_login_sync"])
        self.assertEqual(auto.tick(now + 1000)["reason"], "Intervalo mínimo entre consultas")
        self.fake.fail.add("req_status_sync")
        second = auto.tick(now + 60000)
        self.assertTrue(second["sent"])
        cfg = {t["node_num"]: t for t in auto.config()["targets"]}
        self.assertEqual(cfg[far]["failures"], 1)
        self.assertEqual(cfg[far]["next_ms"], now + 60000 + 30 * 60000)
        self.assertEqual(cfg[rep]["next_ms"], now + 60 * 60000)
        self.assertEqual(auto.tick(now + 120000)["reason"], "Limite de consultas MeshCore por hora")
        with self.assertRaises(ValueError):
            auto.save({"targets": [{"node_num": rep, "kind": "telemetry", "interval_minutes": 5}]})
        with self.assertRaises(ValueError):
            auto.set_password(rep, "x" * 20)

    def test_no_radio(self):
        self.manager._interfaces.clear()
        auto = MeshCoreAutomation(self.db, self.manager)
        auto.save({"enabled": True})
        self.assertEqual(auto.tick()["reason"], "Nenhum rádio MeshCore conectado")


class Planning(Base):
    def test_meshcore_presets_and_radio_defaults(self):
        self.assertEqual(survey.preset_sf_bw("MESHCORE_SF7_BW62.5"), (7, 62.5))
        self.assertEqual(survey.preset_sf_bw("meshcore_sf9_bw125"), (9, 125.0))
        self.assertIsNone(survey.preset_sf_bw("MESHCORE_SF20_BW125"))
        self.assertLess(survey.sensitivity_dbm("MESHCORE_SF7_BW62.5"), survey.sensitivity_dbm("SHORT_FAST"))
        d = survey.radio_defaults(self.manager)
        self.assertEqual((d["preset"], d["freq_mhz"], d["tx_power_dbm"], d["protocol"]),
                         ("MESHCORE_SF7_BW62.5", 910.525, 20.0, "meshcore"))


class Api(Base):
    def setUp(self):
        super().setUp()
        self.manager.meshcore_auto = MeshCoreAutomation(self.db, self.manager)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(self.db, self.manager, "csrf", "<html/>"))
        Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.server.server_port

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def call(self, path, body=None):
        req = urllib.request.Request(self.base + path, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "X-PT2VHF-CSRF": "csrf"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            return json.loads(e.read())

    def test_overview_actions_and_automation(self):
        ov = self.call("/api/meshcore")
        self.assertTrue(ov["connected"])
        self.assertEqual(ov["collisions"][0]["prefix"], "0b")
        status = self.call("/api/meshcore/action", {"action": "status", "node": "0x0badcafe"})
        self.assertEqual(status["data"]["bat"], 4100)
        self.assertEqual(self.call("/api/meshcore/results?node=0x0badcafe")["data"][0]["kind"], "status")
        bad = self.call("/api/meshcore/action", {"action": "explodir"})
        self.assertFalse(bad["success"])
        saved = self.call("/api/meshcore/automation", {"enabled": True, "targets": [
            {"node_num": 0x0BADCAFE, "kind": "telemetry", "interval_minutes": 60}]})
        self.assertTrue(saved["config"]["enabled"])
        pw = self.call("/api/meshcore/automation", {"node_num": 0x0BADCAFE, "password": "secreta"})
        self.assertEqual(pw["with_password"], [0x0BADCAFE])
        self.assertNotIn("secreta", json.dumps(self.call("/api/meshcore")))
        self.assertEqual(self.call("/api/survey/defaults")["radio"]["preset"], "MESHCORE_SF7_BW62.5")


if __name__ == "__main__":
    unittest.main()
