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

    def test_local_http_controls_require_csrf_and_save(self):
        from http.server import ThreadingHTTPServer
        from urllib.error import HTTPError
        import urllib.request
        import threading
        from mesh_analyzer.app import build_handler
        server = ThreadingHTTPServer(("127.0.0.1",0),
            build_handler(self.db,self.sources,"safe-token","<html/>",
                          automation=self.service))
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        base="http://127.0.0.1:"+str(server.server_address[1])
        try:
            with urllib.request.urlopen(base+"/api/automation") as rsp:
                self.assertTrue(json.load(rsp)["config"]["enabled"])
            data=json.dumps({"enabled":True}).encode()
            request=urllib.request.Request(base+"/api/automation/settings",
                data=data,headers={"Content-Type":"application/json"},method="POST")
            with self.assertRaises(HTTPError) as e:
                urllib.request.urlopen(request)
            self.assertEqual(e.exception.code,403)
            request.add_header("X-PT2VHF-CSRF","safe-token")
            with urllib.request.urlopen(request) as rsp:
                self.assertTrue(json.load(rsp)["config"]["enabled"])
            self.assertTrue(self.service.config()["enabled"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_enabled_default_can_be_disabled_without_rf(self):
        self.assertTrue(self.service.config()["enabled"])
        self.assertTrue(all(self.service.config()["types"].values()))
        self.service.save({"enabled":False})
        self.assertFalse(self.service.config()["enabled"])
        result = self.service.tick()
        self.assertFalse(result["sent"])
        self.assertEqual(self.sources.queries.sent, [])
        self.assertTrue(self.service.tick(dry_run=True)["queue"])

    def test_default_migration_runs_once_then_respects_manual_disable(self):
        self.assertTrue(self.service.config()['enabled'])
        self.assertTrue(all(self.service.config()['types'].values()))
        self.service.save({'enabled':False,'types':{'traceroute':False}})
        restored=NodeEnrichment(self.db,self.sources)
        self.assertFalse(restored.config()['enabled'])
        self.assertFalse(restored.config()['types']['traceroute'])
        self.assertEqual(restored.config()['max_per_hour'],24)
        self.assertEqual(restored.config()['min_gap_seconds'],60)

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

    def test_nodes_heard_only_over_mqtt_are_not_rf_targets(self):
        mqtt = self.db.upsert_source({"name": "MQTT", "kind": "mqtt",
            "config": {"host": "test", "topic": "msh/+/2/e/#"}, "enabled": True})
        self.db.upsert_node(555, mqtt["id"], timestamp_ms=self.now-600000,
                            observed=True)
        queue = self.service.tick(dry_run=True)["queue"]
        self.assertNotIn(555, [q["node"] for q in queue])
        self.assertIn(200, [q["node"] for q in queue])

    def test_simulation_never_transmits_even_when_enabled(self):
        self.service.save({"enabled": True, "max_per_hour": 2})
        result = self.service.tick(dry_run=True)
        self.assertFalse(result["sent"])
        self.assertTrue(result["pending_count"])
        self.assertEqual(self.sources.queries.sent, [])

    def test_hourly_limit_uses_history_not_latest_job_only(self):
        self.service.save({"enabled": True, "max_per_hour": 1})
        first = self.service.tick()
        self.assertTrue(first["sent"])
        self.sources.queries.replies[first.get("request_id","rf-1")]["state"] = "replied"
        with patch("mesh_analyzer.automations.time.time",return_value=time.time()+100):
            next_result = self.service.tick()
        self.assertFalse(next_result["sent"])
        self.assertIn("Limite",next_result["reason"])
        self.assertEqual(len(self.sources.queries.sent),1)
        self.assertEqual(self.db._rows("SELECT COUNT(*) AS c FROM auto_query_transmissions")[0]["c"],1)

    def test_unanswered_rf_is_backed_off_without_immediate_retry(self):
        self.service.save({"enabled": True, "types": {"position": False, "telemetry": False,"traceroute":False}})
        self.assertTrue(self.service.tick()["sent"])
        with patch("mesh_analyzer.automations.time.time",return_value=time.time()+100):
            result = self.service.tick()
        self.assertFalse(result["sent"])
        attempts = self.db._rows("SELECT state,attempts,due_ms FROM auto_node_queries")
        self.assertEqual(attempts[0]["state"],"timeout")
        self.assertGreater(attempts[0]["due_ms"],int(time.time()*1000)+360000)

    def test_validation_rejects_unreasonable_or_unknown_settings(self):
        for bad in ({"max_per_hour": 100}, {"min_gap_seconds": 1},
                    {"types": {"bad": True}}, {"enabled": "yes"}):
            with self.assertRaises(ValueError):
                self.service.save(bad)
        self.assertTrue(self.service.config()["enabled"])

    def test_unknown_age_data_is_eligible_for_freshness_refresh(self):
        self.db.upsert_node(200,self.sid,timestamp_ms=self.now-1000,observed=True,
               long_name="Remote",short_name="REMT",hw_model="HELTEC_V4",
               battery=86,voltage=4.08,latitude=-15.8,longitude=-47.8)
        queue = self.service.tick(dry_run=True)["queue"]
        self.assertIn("nodeinfo", [x["kind"] for x in queue])
        self.assertIn("telemetry", [x["kind"] for x in queue])
        self.assertNotIn("position", [x["kind"] for x in queue])
        self.assertFalse(self.sources.queries.sent)


if __name__ == "__main__":
    unittest.main()
