"""RF automation regression tests; never need an attached radio."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from mesh_analyzer.automations import NodeEnrichment
from mesh_analyzer.database import Database


class FakeQueries:
    def __init__(self):
        self.sent = []
        self.replies = {}
        self.supported = ["nodeinfo", "position", "telemetry", "traceroute"]

    def capabilities(self, source_id):
        return {"ready": True, "supported": self.supported}

    def start(self, source_id, node, kind):
        rid = "rf-%d" % (len(self.sent)+1)
        self.sent.append((source_id, node, kind))
        self.replies[rid] = {"request_id": rid, "state": "awaiting_reply"}
        return {"request_id": rid, "state": "awaiting_reply"}

    def status(self):
        return list(self.replies.values())


class FakeSources:
    def __init__(self, sid):
        self.sid = sid
        self.queries = FakeQueries()
        self.extra = []

    def snapshot(self):
        s = {str(self.sid): {"status": "connected", "tx_capable": True,
                            "local_node_num": 100}}
        for sid in self.extra:
            s[str(sid)] = {"status": "connected", "tx_capable": True,
                           "local_node_num": 300}
        return s


class EnrichmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name)/"nodes.db")
        source = self.db.upsert_source({"name": "VHF0", "kind": "serial",
            "config": {"port": "COM3"}, "enabled": True})
        self.sid = source["id"]
        self.sources = FakeSources(self.sid)
        self.service = NodeEnrichment(self.db, self.sources)
        self.now = int(time.time()*1000)
        self.db.upsert_node(200, self.sid, timestamp_ms=self.now-600000,
                            observed=True)

    def tearDown(self):
        self.service.close()
        self.db.close()
        self.temp.cleanup()

    def test_disabled_by_default_and_no_accidental_rf(self):
        self.assertFalse(self.service.config()["enabled"])
        result = self.service.tick()
        self.assertFalse(result["sent"])
        self.assertEqual(self.sources.queries.sent, [])
        self.assertTrue(self.service.tick(dry_run=True)["queue"])

    def test_activation_sends_one_and_tracks_reply(self):
        self.service.save({"enabled": True, "max_per_hour": 6})
        result = self.service.tick()
        self.assertTrue(result["sent"])
        self.assertEqual(result["kind"], "nodeinfo")
        self.assertEqual(len(self.sources.queries.sent), 1)
        result = self.service.tick()
        self.assertFalse(result["sent"])
        self.assertEqual(len(self.sources.queries.sent), 1)
        rid = next(iter(self.sources.queries.replies))
        self.sources.queries.replies[rid]["state"] = "replied"
        with patch("mesh_analyzer.automations.time.time", return_value=time.time()+70):
            self.service.tick()
        attempts = self.db._rows("SELECT * FROM auto_node_queries")
        self.assertTrue(any(x["last_reply_ms"] > 0 for x in attempts))

    def test_persistence_after_restart_and_disabled_type(self):
        self.service.save({"enabled": True, "types": {"nodeinfo": False}})
        self.assertEqual(self.service.tick()["kind"], "position")
        other = NodeEnrichment(self.db, self.sources)
        self.assertTrue(other.config()["enabled"])
        self.assertFalse(other.config()["types"]["nodeinfo"])
        self.assertEqual(len(other._attempts(self.sid)), 1)

    def test_new_noderecord_has_passive_grace_period(self):
        self.db.upsert_node(201,self.sid,timestamp_ms=self.now,observed=True)
        plan = self.service.tick(dry_run=True)["queue"]
        self.assertNotIn(201, [q["node"] for q in plan])
        self.assertIn(200, [q["node"] for q in plan])

    def test_offline_records_are_preserved_not_queried(self):
        self.db.upsert_node(222,self.sid,timestamp_ms=self.now-15*86400000,
                            observed=True)
        plan = self.service.tick(dry_run=True)["queue"]
        self.assertNotIn(222, [q["node"] for q in plan])
        self.assertTrue(any(r["node_num"] == 222 for r in self.db.node_rows()))

    def test_mqtt_cannot_be_used_as_rf_source(self):
        mqtt = self.db.upsert_source({"name": "MQTT", "kind": "mqtt",
             "config": {"host": "test", "topic": "msh/+/2/e/#"}, "enabled": True})
        self.sources.extra = [mqtt["id"]]
        self.service.save({"enabled": True})
        result = self.service.tick()
        self.assertTrue(result["sent"])  # the only real radio is still used
        self.assertEqual(self.sources.queries.sent[0][0], self.sid)

    def test_multi_radio_ambiguity_pauses_automation(self):
        other = self.db.upsert_source({"name": "WiFi", "kind": "tcp",
                   "config": {"host": "192.168.1.23","port":4403}, "enabled": True})
        self.sources.extra = [other["id"]]
        self.service.save({"enabled": True})
        result = self.service.tick()
        self.assertFalse(result["sent"])
        self.assertIn("Mais de um rádio",result["reason"])
        self.assertFalse(self.sources.queries.sent)

    def test_simulation_never_transmits_even_when_enabled(self):
        self.service.save({"enabled": True, "max_per_hour": 2})
        result = self.service.tick(dry_run=True)
        self.assertFalse(result["sent"])
        self.assertTrue(result["pending_count"])
        self.assertEqual(self.sources.queries.sent, [])

    def test_validation_rejects_unreasonable_or_unknown_settings(self):
        for bad in ({"max_per_hour": 100}, {"min_gap_seconds": 1},
                    {"types": {"bad": True}}, {"enabled": "yes"}):
            with self.assertRaises(ValueError):
                self.service.save(bad)
        self.assertFalse(self.service.config()["enabled"])

    def test_passive_nodeinfo_and_telemetry_skip_completed_queries(self):
        self.db.upsert_node(200,self.sid,timestamp_ms=self.now-1000,observed=True,
               long_name="Remote",short_name="REMT",hw_model="HELTEC_V4",
               battery=86,voltage=4.08,latitude=-15.8,longitude=-47.8)
        queue = self.service.tick(dry_run=True)["queue"]
        self.assertFalse(queue)  # legacy known values, no forced RF refresh
        self.assertFalse(self.sources.queries.sent)


if __name__ == "__main__":
    unittest.main()
