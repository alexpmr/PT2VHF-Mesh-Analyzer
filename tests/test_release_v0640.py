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


if __name__ == "__main__":
    unittest.main()
