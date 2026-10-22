"""v0.6.40: backup (#166), busca (#175), alertas (#165) e demais recursos."""
import io
import json
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock

from mesh_analyzer import backup
from mesh_analyzer.alerts import AlertCenter
from mesh_analyzer.msgauto import MessageAutomation
from mesh_analyzer.database import Database, now_ms

ROOT = Path(__file__).resolve().parents[1]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.db = Database(self.data / "mesh-analyzer.sqlite3")

    def tearDown(self):
        try:
            self.db.close()
        except Exception:
            pass
        self.tmp.cleanup()


class Backup(Base):
    def test_export_validate_and_apply_on_next_start(self):
        self.db.upsert_source({"name": "Original", "kind": "tcp", "config": {"host": "h"}, "enabled": False})
        out = backup.export_backup(self.db, self.data)
        self.assertEqual(out["sources"], 1)
        zip_bytes = Path(out["path"]).read_bytes()
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            self.assertEqual(json.loads(zf.read("manifest.json"))["app"], backup.APP_NAME)
        self.db.upsert_source({"name": "Depois", "kind": "tcp", "config": {"host": "x"}, "enabled": False})
        meta = backup.stage_restore(self.data, io.BytesIO(zip_bytes), len(zip_bytes))
        self.assertEqual(meta["sources"], 1)
        self.assertIsNotNone(backup.pending_restore(self.data))
        self.db.close()
        result = backup.apply_pending_restore(self.data / "mesh-analyzer.sqlite3")
        self.assertEqual(result["status"], "applied")
        self.assertTrue((self.data / "backups" / result["safety_copy"]).is_file())
        self.db = Database(self.data / "mesh-analyzer.sqlite3")
        self.assertEqual([s["name"] for s in self.db.sources()], ["Original"])
        self.assertIsNone(backup.pending_restore(self.data))

    def test_invalid_upload_keeps_previous_pending_restore(self):
        out = backup.export_backup(self.db, self.data)
        good = Path(out["path"]).read_bytes()
        backup.stage_restore(self.data, io.BytesIO(good), len(good))
        bad = b"nao sou zip"
        with self.assertRaises(ValueError):
            backup.stage_restore(self.data, io.BytesIO(bad), len(bad))
        self.assertTrue((self.data / "restore" / "pending.sqlite3").is_file())

    def test_rejects_zip_from_other_app_and_bad_names(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("manifest.json", json.dumps({"app": "Outro"}))
            zf.writestr("mesh-analyzer.sqlite3", b"x")
        data = buf.getvalue()
        with self.assertRaises(ValueError):
            backup.stage_restore(self.data, io.BytesIO(data), len(data))
        with self.assertRaises(ValueError):
            backup.backup_file(self.data, "../mesh-analyzer.sqlite3")


class Search(Base):
    def add(self, mid, text, frm=10, to=0xffffffff, ch=0, direction="rx", ts=None):
        self.db.add_message({"source_id": 1, "packet_key": "k%d" % mid, "packet_id": str(mid), "timestamp_ms": ts or now_ms() - mid * 1000,
                             "from_node": frm, "to_node": to, "channel": ch, "direction": direction, "text": text, "state": "received"})

    def test_search_ignores_case_and_accents_and_filters(self):
        self.add(1, "Bateria fraca no repetidor")
        self.add(2, "ATENÇÃO: repetidor OK", frm=20)
        self.add(3, "nada a ver")
        self.add(4, "repetidor antigo", ts=now_ms() - 40 * 86400000)
        found = lambda **kw: sorted(m["text"] for m in self.db.search_messages(**kw))
        self.assertEqual(found(query="atencao"), ["ATENÇÃO: repetidor OK"])
        self.assertEqual(len(found(query="REPETIDOR")), 3)
        self.assertEqual(len(found(query="repetidor", days=30)), 2)
        self.assertEqual(found(query="repetidor", node=20), ["ATENÇÃO: repetidor OK"])
        with self.assertRaises(ValueError):
            self.db.search_messages(query="  ")

    def test_context_stays_in_same_conversation(self):
        for i in range(1, 6):
            self.add(i, "canal %d" % i, ts=1000 + i)
        self.add(10, "privado", frm=30, to=99, ts=1003)
        rows = self.db._rows("SELECT id FROM messages WHERE text='canal 3'")
        ctx = self.db.message_context(rows[0]["id"], around=2)
        self.assertEqual([m["text"] for m in ctx["messages"]], ["canal 1", "canal 2", "canal 3", "canal 4", "canal 5"])


class Alerts(Base):
    def setUp(self):
        super().setUp()
        self.sources = Mock()
        self.sources.snapshot.return_value = {"1": {"local_node_num": 99}}
        self.sent = []
        self.center = AlertCenter(self.db, self.sources, sender=lambda ch, a, cfg: self.sent.append((ch, a["title"])))

    def test_silent_favorite_alerts_once_and_resolves(self):
        now = now_ms()
        self.db.upsert_node(5, 1, timestamp_ms=now - 8 * 3600000, observed=True, long_name="Base Sul")
        self.db.set_app_favorite(5, True)
        first = self.center.evaluate(now)
        self.assertEqual([a["title"] for a in first], ["Favorito calado: Base Sul"])
        self.assertEqual(self.center.evaluate(now + 60000), [])  # não repete
        self.db.upsert_node(5, 1, timestamp_ms=now + 120000, observed=True)
        self.center.evaluate(now + 180000)
        self.assertTrue(self.center.list()["alerts"][0]["resolved_ms"])

    def test_battery_only_for_repeaters_and_favorites(self):
        now = now_ms()
        self.db.upsert_node(6, 1, timestamp_ms=now, observed=True, long_name="Repetidor", role="ROUTER", battery=12)
        self.db.upsert_node(7, 1, timestamp_ms=now, observed=True, long_name="Cliente", role="CLIENT", battery=12)
        self.db.upsert_node(8, 1, timestamp_ms=now, observed=True, long_name="Externo", role="ROUTER", battery=101)
        titles = [a["title"] for a in self.center.evaluate(now)]
        self.assertEqual(titles, ["Bateria baixa: Repetidor"])

    def test_channel_utilization_of_own_radio(self):
        self.db.add_rf_sample(1, 99, now_ms(), channel_util=42.0)
        self.assertEqual([a["kind"] for a in self.center.evaluate()], ["channel"])

    def test_direct_message_and_mention_but_not_history(self):
        self.db.upsert_node(99, 1, timestamp_ms=now_ms(), long_name="VHF3 Base", short_name="VHF3")
        add = lambda i, text, to: self.db.add_message({"source_id": 1, "packet_key": "m%d" % i, "packet_id": str(i), "timestamp_ms": now_ms(),
            "from_node": 50, "to_node": to, "channel": 0, "direction": "rx", "text": text, "state": "received"})
        add(1, "mensagem antiga", 99)
        self.assertEqual(self.center.evaluate(), [])  # histórico não gera alerta
        add(2, "oi, tudo bem?", 99)
        add(3, "alguém viu o vhf3 hoje?", 0xffffffff)
        add(4, "conversa geral", 0xffffffff)
        self.assertEqual(sorted(a["kind"] for a in self.center.evaluate()), ["dm", "mention"])

    def test_delivery_channels_and_secrets_hidden(self):
        self.center.save({"telegram": {"enabled": True, "token": "123:ABC", "chat_id": "42"}})
        self.assertEqual(self.center.config(public=True)["telegram"]["token"], "********")
        self.center.save({"telegram": {"token": "********", "chat_id": "43"}})
        self.assertEqual(self.center.config()["telegram"]["token"], "123:ABC")
        self.db.add_rf_sample(1, 99, now_ms(), channel_util=60.0)
        self.center.evaluate()
        time.sleep(0.3)
        self.assertEqual(self.sent, [("telegram", "Canal congestionado")])
        self.assertEqual(self.center.list()["alerts"][0]["delivery"], "telegram")

    def test_disabled_and_validation(self):
        self.center.save({"enabled": False})
        self.db.add_rf_sample(1, 99, now_ms(), channel_util=90.0)
        self.assertEqual(self.center.evaluate(), [])
        with self.assertRaises(ValueError):
            self.center.save({"battery_below": 150})
        with self.assertRaises(ValueError):
            self.center.save({"email": {"security": "starttls", "evil": 1}})



class MessageAuto(Base):
    def setUp(self):
        super().setUp()
        self.sources = Mock()
        self.sources.active_radio.return_value = 1
        self.sources.snapshot.return_value = {"1": {"local_node_num": 99}}
        self.sent = []
        self.sources.send_text.side_effect = lambda sid, to, text, ch: self.sent.append((to, text, ch))
        self.auto = MessageAutomation(self.db, self.sources, weather=lambda: "25°C")

    def msg(self, i, text, frm=50, to=0xffffffff, ts=None, snr=7.5):
        key = "1:%d:%d" % (frm, i)
        self.db.add_packet({"source_id": 1, "packet_id": str(i), "source_packet_key": key, "timestamp_ms": ts or now_ms(),
                            "from_node": frm, "to_node": to, "port": "TEXT_MESSAGE_APP", "channel": 0, "rx_snr": snr,
                            "rx_rssi": -90, "hop_start": 3, "hop_limit": 1, "via_mqtt": 0, "encrypted": 0, "direction": "rx",
                            "text_preview": text, "raw_json": "{}"})
        self.db.add_message({"source_id": 1, "packet_key": key, "packet_id": str(i), "timestamp_ms": ts or now_ms(),
                             "from_node": frm, "to_node": to, "channel": 0, "direction": "rx", "text": text, "state": "received"})

    def test_ping_reply_with_variables_and_cooldown(self):
        self.db.upsert_node(50, 1, timestamp_ms=now_ms(), long_name="Renato", short_name="RK")
        self.auto.save_reply({"trigger": "ping", "response": "PONG {nome}: SNR {snr}, {saltos} salto(s) {clima}"})
        self.auto.run_replies()          # primeira execução só marca o ponto de partida
        self.msg(1, "PING")
        self.msg(2, "Ping")
        self.auto.run_replies()
        self.assertEqual(self.sent, [(None, "PONG Renato: SNR 7.5 dB, 2 salto(s) 25°C", 0)])
        log = self.auto.overview()["log"]
        self.assertEqual([l["status"] for l in log], ["skipped", "sent"])

    def test_dm_reply_goes_private_and_scope_filters(self):
        self.auto.save_reply({"trigger": "clima", "response": "Tempo: {clima}", "scope": "dm"})
        self.auto.run_replies()
        self.msg(1, "clima", to=0xffffffff)
        self.msg(2, "clima", frm=51, to=99)
        self.auto.run_replies()
        self.assertEqual(self.sent, [(51, "Tempo: 25°C", 0)])

    def test_never_replies_to_history_or_itself(self):
        self.auto.save_reply({"trigger": "ping", "response": "pong"})
        self.auto.run_replies()
        self.msg(1, "ping", ts=now_ms() - 10 * 60000)
        self.msg(2, "ping", frm=99)
        self.auto.run_replies()
        self.assertEqual(self.sent, [])

    def test_hourly_budget(self):
        self.auto.save_config({"max_per_hour": 1})
        self.auto.save_reply({"trigger": "ping", "response": "pong", "cooldown_s": 30})
        self.auto.run_replies()
        self.msg(1, "ping", frm=60); self.msg(2, "ping", frm=61)
        self.auto.run_replies()
        self.assertEqual(len(self.sent), 1)
        self.assertIn("Limite", self.auto.overview()["log"][0]["error"])

    def test_schedules_daily_interval_and_once(self):
        now = now_ms()
        daily = self.auto.save_schedule({"kind": "daily", "text": "Bom dia {data}", "time_hhmm": "07:00", "weekdays": 127}, now)
        self.assertTrue(0 < daily["next_ms"] - now <= 86400000 + 3600000)
        once = self.auto.save_schedule({"kind": "once", "text": "Teste", "target": 77, "at_ms": now + 1000}, now)
        every = self.auto.save_schedule({"kind": "interval", "text": "Boletim", "interval_min": 30}, now)
        self.assertEqual(self.auto.run_schedules(now + 2000), 1)
        self.assertEqual(self.sent, [(77, "Teste", 0)])
        row = self.db._rows("SELECT * FROM scheduled_messages WHERE id=?", (once["id"],))[0]
        self.assertEqual((row["enabled"], row["next_ms"]), (0, 0))
        self.assertEqual(self.auto.run_schedules(now + 31 * 60000), 1)
        nxt = self.db._rows("SELECT next_ms FROM scheduled_messages WHERE id=?", (every["id"],))[0]["next_ms"]
        self.assertEqual(nxt, now + 31 * 60000 + 30 * 60000)

    def test_validation(self):
        with self.assertRaises(ValueError):
            self.auto.save_schedule({"kind": "interval", "text": "x", "interval_min": 5})
        with self.assertRaises(ValueError):
            self.auto.save_schedule({"kind": "once", "text": "x", "at_ms": 1})
        with self.assertRaises(ValueError):
            self.auto.save_reply({"trigger": "ping", "response": "x" * 300})
        self.assertTrue(MessageAutomation.matches({"trigger": "ATENÇÃO", "match": "starts"}, "atencao geral"))
        self.assertFalse(MessageAutomation.matches({"trigger": "ping", "match": "exact"}, "ping pong"))



class Channels(Base):
    def setUp(self):
        super().setUp()
        from meshtastic.protobuf import channel_pb2
        from mesh_analyzer.transports import SourceManager
        self.pb = channel_pb2
        chans = []
        for i in range(8):
            c = channel_pb2.Channel(index=i, role=channel_pb2.Channel.Role.PRIMARY if i == 0 else channel_pb2.Channel.Role.DISABLED)
            if i == 0:
                c.settings.psk = b"\x01"
            chans.append(c)
        self.written = []
        self.local = Mock(channels=chans)
        self.local.writeChannel.side_effect = lambda i: self.written.append(i)
        self.sid = self.db.upsert_source({"name": "R", "kind": "tcp", "config": {"host": "h"}, "enabled": True})["id"]
        self.m = SourceManager(self.db)
        self.m._interfaces[self.sid] = Mock(localNode=self.local)
        self.m._set(self.sid, "connected")

    def test_list_hides_keys_and_is_cached(self):
        out = self.m.channel_list()
        self.assertEqual(out["channels"][0], {"index": 0, "role": "PRIMARY", "name": "", "encryption": "default",
                                              "uplink": False, "downlink": False})
        self.assertNotIn("psk", json.dumps(out))
        self.m._interfaces.clear()
        self.assertFalse(self.m.channel_list(self.sid)["live"])
        self.assertEqual(len(self.m.channel_list(self.sid)["channels"]), 8)

    def test_enable_secondary_with_random_key_and_disable(self):
        out = self.m.set_channel(self.sid, 1, "Emergencia", True, "random")
        self.assertEqual(self.written, [1])
        ch = self.local.channels[1]
        self.assertEqual((ch.role, ch.settings.name, len(ch.settings.psk)), (self.pb.Channel.Role.SECONDARY, "Emergencia", 32))
        import base64
        self.assertEqual(base64.b64decode(out["shared_key"]), ch.settings.psk)
        self.m.set_channel(self.sid, 1, enabled=False)
        self.assertEqual(self.local.channels[1].role, self.pb.Channel.Role.DISABLED)

    def test_primary_and_invalid_values_are_refused(self):
        for args in ((0, "X"), (8, "X")):
            with self.assertRaises(ValueError):
                self.m.set_channel(self.sid, *args)
        with self.assertRaises(ValueError):
            self.m.set_channel(self.sid, 2, "nome comprido demais")
        with self.assertRaises(ValueError):
            self.m.set_channel(self.sid, 2, "ok", True, "custom", "abc")
        self.assertEqual(self.written, [])

    def test_failed_write_restores_channel(self):
        self.local.writeChannel.side_effect = RuntimeError("falhou")
        with self.assertRaises(RuntimeError):
            self.m.set_channel(self.sid, 3, "Teste", True, "default")
        self.assertEqual(self.local.channels[3].role, self.pb.Channel.Role.DISABLED)



class Insights(Base):
    def pkt(self, i, frm, ts, port="TEXT_MESSAGE_APP", snr=None, hops=(3, 3), raw="{}", to=0xffffffff, mqtt=0):
        self.db.add_packet({"source_id": 1, "packet_id": str(i), "source_packet_key": "p%d" % i, "timestamp_ms": ts,
                            "from_node": frm, "to_node": to, "port": port, "channel": 0, "rx_snr": snr, "rx_rssi": -100 if snr is not None else None,
                            "hop_start": hops[0], "hop_limit": hops[1], "via_mqtt": mqtt, "encrypted": 0, "direction": "rx",
                            "text_preview": "", "raw_json": raw})

    def test_node_timeline_series(self):
        from mesh_analyzer import insights
        now = now_ms()
        for h in range(5):
            self.db.add_rf_sample(1, 7, now - h * 3600000, battery=90 - h, voltage=4.0, channel_util=10 + h)
            self.pkt(h, 7, now - h * 3600000, snr=5.0 - h)
        t = insights.node_timeline(self.db, 7, 24, now)
        self.assertEqual(t["bucket_ms"], 1800000)
        self.assertEqual(len(t["battery"]), 5)
        self.assertEqual(sum(c for _, c in t["heard"]), 5)
        self.assertEqual(t["snr"][-1][1], 5.0)
        self.assertEqual(insights.node_timeline(self.db, 7, 720, now)["bucket_ms"], 43200000)

    def test_repeater_availability_and_route_count(self):
        from mesh_analyzer import insights
        now = now_ms()
        self.db.upsert_node(20, 1, timestamp_ms=now - 2 * 3600000, observed=True, long_name="Morro", role="ROUTER")
        with self.db._lock, self.db._db:
            self.db._db.execute("UPDATE nodes SET first_seen_ms=? WHERE node_num=20", (now - 10 * 3600000,))
        for h in (1, 3, 5, 7, 9):
            self.pkt(100 + h, 20, now - h * 3600000 - 1000)
        raw = json.dumps({"from": 30, "to": 10, "decoded": {"portnum": "TRACEROUTE_APP", "route": [20]}})
        self.pkt(200, 30, now - 600000, port="TRACEROUTE_APP", raw=raw, to=10)
        r = insights.repeaters(self.db, 24, now)["repeaters"][0]
        self.assertEqual((r["name"], r["route_hops"]), ("Morro", 1))
        self.assertAlmostEqual(r["availability"], 50.0, delta=10)

    def test_routes_and_bottlenecks(self):
        from mesh_analyzer import insights
        now = now_ms()
        for i, route in enumerate(([20], [20, 21], [21])):
            raw = json.dumps({"from": 30 + i, "to": 10, "decoded": {"portnum": "TRACEROUTE_APP", "route": route}})
            self.pkt(300 + i, 30 + i, now - 1000 * i, port="TRACEROUTE_APP", raw=raw, to=10)
        r = insights.routes(self.db, 24, now)
        self.assertEqual(r["total_routes"], 3)
        self.assertEqual({b["node"]: b["routes"] for b in r["bottlenecks"]}, {20: 2, 21: 2})

    def test_coverage_uses_only_direct_rf_with_position(self):
        from mesh_analyzer import insights
        now = now_ms()
        self.db.upsert_node(40, 1, timestamp_ms=now, latitude=-15.801, longitude=-47.889)
        self.db.upsert_node(41, 1, timestamp_ms=now)  # sem posição
        self.pkt(1, 40, now, snr=6.0, hops=(3, 3))
        self.pkt(2, 40, now, snr=-2.0, hops=(3, 3))
        self.pkt(3, 40, now, snr=9.0, hops=(3, 2))   # multissalto: não conta
        self.pkt(4, 40, now, snr=9.0, mqtt=1)          # MQTT: não conta
        self.pkt(5, 41, now, snr=1.0)
        c = insights.coverage(self.db, 24, 0.01, now)
        self.assertEqual(len(c["cells"]), 1)
        self.assertEqual((c["cells"][0]["snr"], c["cells"][0]["count"], c["cells"][0]["best_snr"]), (2.0, 2, 6.0))

    def test_terrain_profile_fresnel(self):
        from mesh_analyzer import insights
        flat = insights.terrain_profile((-15.8, -47.9), (-15.8, -47.85), 915, 30, 30, samples=20, elevations=lambda pts: [1000.0] * len(pts))
        self.assertIn("Visada livre", flat["verdict"])
        hill = insights.terrain_profile((-15.8, -47.9), (-15.8, -47.85), 915, 2, 2, samples=20,
                                        elevations=lambda pts: [1000.0 + (200 if 8 <= i <= 11 else 0) for i in range(len(pts))])
        self.assertIn("Sem visada", hill["verdict"])
        self.assertAlmostEqual(flat["distance_m"], 5355, delta=60)
        with self.assertRaises(ValueError):
            insights.terrain_profile((1, 1), (1, 1), elevations=lambda pts: [0] * len(pts))


if __name__ == "__main__":
    unittest.main()
