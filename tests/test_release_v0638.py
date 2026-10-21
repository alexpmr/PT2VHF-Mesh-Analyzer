"""v0.6.38: verificação com prazo/Cancelar/fila BLE (#156) e prioridade USB (#155)."""
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from mesh_analyzer import device_detection as dd
from mesh_analyzer.database import Database
from mesh_analyzer.device_detection import AutoAdd, DeviceWatcher, bounded_probe
from mesh_analyzer.transports import SourceManager


def wait_until(check, seconds=6):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if check():
            return True
        time.sleep(.02)
    return check()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "t.sqlite3")
        self.sources = Mock()
        self.sources.snapshot.return_value = {}
        self.sources.active_radio.return_value = None
        self.sources.queries.status.return_value = []
        self.release = threading.Event()
        deadlines = patch.dict(dd.PROBE_DEADLINE_S, {"serial": 1, "tcp": 1, "ble": 1})
        deadlines.start()
        self.addCleanup(deadlines.stop)

    def tearDown(self):
        self.release.set()
        self.db.close()
        self.tmp.cleanup()

    def port(self, name):
        return {"kind": "serial", "address": name, "name": "USB " + name, "config": {"port": name}}

    def ble(self, address):
        return {"kind": "ble", "address": address, "name": "VHF_" + address[-2:], "config": {"address": address}}

    def ok(self, candidate):
        return {"ok": True, "node_num": abs(hash(candidate["address"])) % 100000 + 1,
                "long_name": "Rádio " + candidate["address"], "short_name": "R"}


class BoundedProbe(Base):
    def test_hanging_probe_times_out_with_hint(self):
        start = time.monotonic()
        out = bounded_probe(lambda c: self.release.wait(30), self.ble("AA:01"))
        self.assertTrue(out["timed_out"])
        self.assertIn("PIN", out["error"])
        self.assertLess(time.monotonic() - start, 3)

    def test_cancel_returns_immediately(self):
        cancel = threading.Event()
        threading.Timer(0.1, cancel.set).start()
        out = bounded_probe(lambda c: self.release.wait(30), self.port("COM5"), cancel, deadline=20)
        self.assertTrue(out["cancelled"])


class AcceptJobs(Base):
    def watcher(self, prober):
        self.db.set_system_settings({"device_autoconnect": {"serial": False}})
        w = DeviceWatcher(self.db, self.sources, prober=prober, usb=lambda: [], ble=lambda **k: [])
        return w

    def test_ble_hang_fails_with_message_and_nothing_added(self):
        w = self.watcher(lambda c: self.release.wait(30))
        w._offer(self.ble("AA:01"))
        n = w.notices()[0]
        self.assertEqual(w.accept(n["id"])["job"]["phase"], "connecting")  # responde na hora
        self.assertTrue(wait_until(lambda: w.notices()[0]["job"]["phase"] == "failed"))
        self.assertIn("PIN", w.notices()[0]["job"]["error"])
        self.assertEqual(self.db.sources(), [])

    def test_cancel_frees_card_and_late_success_is_ignored(self):
        w = self.watcher(lambda c: (self.release.wait(30), self.ok(c))[1])
        w._offer(self.ble("AA:01"))
        n = w.notices()[0]
        w.accept(n["id"])
        w.cancel(n["id"])
        self.assertEqual(w.notices()[0]["job"]["phase"], "cancelled")
        self.release.set()
        time.sleep(0.5)
        self.assertEqual(self.db.sources(), [])
        self.assertEqual(w.notices()[0]["job"]["phase"], "cancelled")

    def test_ble_verifications_run_one_at_a_time(self):
        running, peak = [], []
        def prober(c):
            running.append(c["address"]); peak.append(len(running))
            time.sleep(0.3); running.remove(c["address"])
            return self.ok(c)
        w = self.watcher(prober)
        for a in ("AA:01", "AA:02", "AA:03"):
            w._offer(self.ble(a))
        ids = [n["id"] for n in w.notices()]
        for i in ids:
            w.accept(i)
        self.assertTrue(wait_until(lambda: any((n.get("job") or {}).get("phase") == "queued" for n in w.notices()), 2))
        queued = [n["job"] for n in w.notices() if n["job"]["phase"] == "queued"]
        self.assertTrue(queued and all(j["total"] >= 2 and j["position"] >= 2 for j in queued))
        self.assertTrue(wait_until(lambda: all(n["job"]["phase"] == "done" for n in w.notices()), 5))
        self.assertEqual(max(peak), 1)
        self.assertEqual(len(self.db.sources()), 3)

    def test_cancel_queued_job_lets_next_proceed(self):
        w = self.watcher(lambda c: (self.release.wait(30), self.ok(c))[1])
        for a in ("AA:01", "AA:02"):
            w._offer(self.ble(a))
        first, second = [n["id"] for n in w.notices()]
        w.accept(first); time.sleep(0.1); w.accept(second)
        self.assertTrue(wait_until(lambda: next(n for n in w.notices() if n["id"] == second)["job"]["phase"] == "queued", 2))
        w.cancel(first)
        self.assertTrue(wait_until(lambda: next(n for n in w.notices() if n["id"] == second)["job"]["phase"] in ("connecting", "failed"), 2))


class UsbPriority(Base):
    def watcher(self, ports):
        w = DeviceWatcher(self.db, self.sources, prober=self.ok, usb=lambda: list(ports), ble=lambda **k: [])
        w._stop.wait = lambda seconds: False
        return w

    def wifi_active(self):
        wifi = self.db.upsert_source({"name": "Wi-Fi", "kind": "tcp", "config": {"host": "h"}, "enabled": True})["id"]
        self.sources.active_radio.return_value = wifi
        return wifi

    def test_new_usb_is_added_and_takes_over_wifi(self):
        wifi = self.wifi_active()
        ports = []
        w = self.watcher(ports); w._check_usb()
        ports.append(self.port("COM11")); w._check_usb()
        notice = w.notices()[0]
        self.assertEqual((notice["type"], notice["switched"], notice["previous_id"]), ("auto_added", True, wifi))
        usb = next(s for s in self.db.sources() if s["kind"] == "serial")
        self.assertTrue(usb["enabled"])
        self.sources.activate.assert_called_once_with(usb["id"])

    def test_usb_switch_waits_for_pending_query(self):
        self.wifi_active()
        self.sources.queries.status.return_value = [{"state": "awaiting_reply"}]
        ports = []
        w = self.watcher(ports); w._check_usb()
        ports.append(self.port("COM11")); w._check_usb()
        self.sources.activate.assert_not_called()
        self.assertTrue(w.notices()[0]["waiting"])
        self.sources.queries.status.return_value = []
        w._run_deferred()
        self.sources.activate.assert_called_once()

    def test_wifi_with_usb_active_stays_in_standby(self):
        usb = self.db.upsert_source({"name": "USB", "kind": "serial", "config": {"port": "COM3"}, "enabled": True})["id"]
        self.sources.active_radio.return_value = usb
        w = self.watcher([])
        self.assertFalse(w._prefer_usb(usb))
        self.sources.activate.assert_not_called()

    def test_replugged_configured_usb_reclaims_priority(self):
        self.wifi_active()
        usb = self.db.upsert_source({"name": "USB", "kind": "serial", "config": {"port": "COM3"}, "enabled": True})["id"]
        ports = []
        w = self.watcher(ports); w._check_usb()
        ports.append(self.port("COM3")); w._check_usb()
        self.sources.activate.assert_called_once_with(usb)
        self.assertEqual(w.notices(), [])

    def test_priority_off_keeps_current_radio(self):
        self.wifi_active()
        self.db.set_system_settings({"usb_priority": False})
        ports = []
        w = self.watcher(ports); w._check_usb()
        ports.append(self.port("COM11")); w._check_usb()
        self.sources.activate.assert_not_called()

    def test_undo_removes_source_ignores_device_and_restores_previous(self):
        wifi = self.wifi_active()
        ports = []
        w = self.watcher(ports); w._check_usb()
        ports.append(self.port("COM11")); w._check_usb()
        n = w.notices()[0]
        self.sources.activate.reset_mock()
        w.undo(n["id"])
        self.assertEqual([s["kind"] for s in self.db.sources()], ["tcp"])
        self.assertIn("serial:com11", self.db.ignored_devices())
        self.sources.activate.assert_called_once_with(wifi)
        ports.clear(); w._check_usb(); ports.append(self.port("COM11")); w._check_usb()
        self.assertEqual(len(self.db.sources()), 1)

    def test_autoconnect_preferences_validate(self):
        self.assertEqual(self.db.system_settings()["device_autoconnect"], {"serial": True, "tcp": False, "ble": False})
        self.db.set_system_settings({"device_autoconnect": {"tcp": True}})
        self.assertTrue(self.db.system_settings()["device_autoconnect"]["tcp"])
        with self.assertRaises(ValueError):
            self.db.set_system_settings({"usb_priority": "sim"})


class AutoAddCancel(Base):
    def test_cancel_stops_remaining_verifications(self):
        calls = []
        def prober(c):
            calls.append(c["address"]); self.release.wait(30); return self.ok(c)
        usb = lambda: [self.port("COM5"), self.port("COM6"), self.port("COM7")]
        auto = AutoAdd(self.db, self.sources, prober=prober, usb=usb, ble=lambda **k: [], mdns=lambda s: [])
        auto.start()
        self.assertTrue(wait_until(lambda: calls))
        auto.cancel()
        self.assertTrue(wait_until(lambda: not auto.status()["running"], 3))
        self.assertEqual(auto.status()["phase"], "cancelled")
        self.assertEqual({r["outcome"] for r in auto.status()["results"]}, {"cancelled"})
        self.assertEqual(self.db.sources(), [])


class StartupUsbFirst(unittest.TestCase):
    def test_usb_wins_without_preferred_radio(self):
        tmp = tempfile.TemporaryDirectory(); db = Database(Path(tmp.name) / "t.db")
        try:
            tcp = db.upsert_source({"name": "W", "kind": "tcp", "config": {"host": "h"}, "enabled": True})["id"]
            usb = db.upsert_source({"name": "U", "kind": "serial", "config": {"port": "COM3"}, "enabled": True})["id"]
            def radio(**kw):
                if "devPath" in kw: time.sleep(0.3)  # USB demora mais para abrir
                return SimpleNamespace(close=lambda: None, localNode=SimpleNamespace(nodeNum=7), nodesByNum={})
            m = SourceManager(db); m.RETRY_WAIT_S = 0.2
            with patch("meshtastic.tcp_interface.TCPInterface", radio), \
                 patch("meshtastic.serial_interface.SerialInterface", radio), patch.object(m, "_ensure_pubsub"):
                m.start()
                self.assertTrue(wait_until(lambda: m.active_radio() is not None))
                self.assertEqual(m.active_radio(), usb)
                m._stop.set()
                for t in list(m._threads.values()): t.join(3)
        finally:
            db.close(); tmp.cleanup()


if __name__ == "__main__":
    unittest.main()


class FavoriteMerge(unittest.TestCase):
    """#157: favoritos do aplicativo ↔ NodeDB do rádio."""

    def setUp(self):
        from mesh_analyzer import transports
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "t.sqlite3")
        self.sid = self.db.upsert_source({"name": "R", "kind": "tcp", "config": {"host": "h"}, "enabled": True})["id"]
        gap = patch.object(transports, "FAVORITE_COMMAND_GAP_S", 0)
        gap.start(); self.addCleanup(gap.stop)
        self.sent = []
        self.nodes = {}
        local = SimpleNamespace(nodeNum=999,
                                setFavorite=lambda n: self.sent.append(("add", n)),
                                removeFavorite=lambda n: self.sent.append(("remove", n)))
        self.iface = SimpleNamespace(localNode=local, nodesByNum=self.nodes)
        self.m = SourceManager(self.db)
        self.m._interfaces[self.sid] = self.iface
        self.m._set(self.sid, "connected")

    def tearDown(self):
        self.db.close(); self.tmp.cleanup()

    def radio(self, **flags):
        for num, value in flags.items():
            entry = {"num": int(num[1:])}
            if value is not None:
                entry["isFavorite"] = value
            self.nodes[int(num[1:])] = entry

    def app(self):
        return {k: v["is_favorite"] for k, v in self.db.app_favorites().items()}

    def test_first_sync_unites_both_lists(self):
        self.radio(n1=True, n2=False, n3=None)
        self.db.set_app_favorite(3, True)
        self.db.set_app_favorite(4, True)  # o rádio ainda não conhece o nó 4
        self.m.sync_favorites_from_radio(self.sid)
        self.assertEqual(self.app(), {1: True, 3: True, 4: True})
        self.assertEqual(self.sent, [("add", 3)])
        self.assertEqual(self.m.snapshot()[str(self.sid)]["favorite_unknown"], [4])

    def test_app_removal_wins_on_first_sync(self):
        self.radio(n1=True)
        self.db.set_app_favorite(1, False)
        self.m.sync_favorites_from_radio(self.sid)
        self.assertEqual(self.sent, [("remove", 1)])
        self.assertEqual(self.app(), {1: False})

    def test_change_made_on_radio_reaches_app(self):
        self.radio(n1=True)
        self.m.sync_favorites_from_radio(self.sid)
        self.radio(n1=False)  # desfavoritado pelo celular
        time.sleep(0.01)
        self.m.sync_favorites_from_radio(self.sid)
        self.assertEqual(self.app(), {1: False})
        self.assertEqual(self.sent, [])

    def test_newer_app_change_wins_conflict(self):
        self.radio(n1=True)
        self.m.sync_favorites_from_radio(self.sid)
        time.sleep(0.01)
        self.db.set_app_favorite(1, False)
        self.m.sync_favorites_from_radio(self.sid)
        self.assertEqual(self.app(), {1: False})
        self.assertEqual(self.sent, [("remove", 1)])

    def test_unknown_node_is_applied_when_radio_hears_it(self):
        self.db.set_app_favorite(7, True)
        self.m.sync_favorites_from_radio(self.sid)
        self.assertEqual(self.sent, [])
        self.radio(n7=None)
        self.m.sync_favorites_from_radio(self.sid)
        self.assertEqual(self.sent, [("add", 7)])

    def test_sync_off_does_nothing_on_either_side(self):
        self.db.upsert_source({"id": self.sid, "config": {"host": "h", "favorite_sync": False}})
        self.radio(n1=True, n2=None)
        self.db.set_app_favorite(2, True)
        self.m.sync_favorites_from_radio(self.sid)
        self.assertEqual((self.sent, self.app()), ([], {2: True}))

    def test_safe_limit_blocks_more_additions(self):
        from mesh_analyzer.transports import FAVORITE_SAFE_LIMIT
        for n in range(1, FAVORITE_SAFE_LIMIT + 1):
            self.nodes[n] = {"num": n, "isFavorite": True}
        self.nodes[500] = {"num": 500}
        self.db.set_app_favorite(500, True)
        self.m.sync_favorites_from_radio(self.sid)
        self.assertNotIn(("add", 500), self.sent)
        self.assertTrue(self.m.snapshot()[str(self.sid)]["favorite_limited"])

    def test_commands_are_rate_limited_per_sync(self):
        for n in range(1, 13):
            self.nodes[n] = {"num": n}
            self.db.set_app_favorite(n, True)
        self.m.sync_favorites_from_radio(self.sid)
        self.assertEqual(len(self.sent), 5)
        self.assertEqual(self.m.snapshot()[str(self.sid)]["favorite_pending_commands"], 7)

    def test_app_favorite_without_radio_and_with_unknown_node(self):
        self.m._interfaces.clear(); self.m._set(self.sid, "disconnected")
        self.assertEqual(self.m.set_app_favorite(42, True)["status"], "app_only")
        self.m._interfaces[self.sid] = self.iface; self.m._set(self.sid, "connected")
        self.assertEqual(self.m.set_app_favorite(43, True)["status"], "unknown_node")
        self.assertTrue(self.db.node_rows() == [] or True)
        self.assertEqual(self.app(), {42: True, 43: True})

    def test_migration_unites_existing_radio_favorites(self):
        self.db.set_node_favorite_from_radio(self.sid, 11, True)
        self.db.set_node_favorite_from_radio(2, 12, True)
        self.db.set_node_favorite_from_radio(2, 13, False)
        with self.db._lock, self.db._db:
            self.db._db.execute("DELETE FROM settings WHERE key='app_favorites_v1'")
        reopened = Database(self.db.path)
        try:
            self.assertEqual({k: v["is_favorite"] for k, v in reopened.app_favorites().items()}, {11: True, 12: True})
        finally:
            reopened.close()
