"""Unit tests for guarded local-node configuration; no radio hardware required."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mesh_analyzer.database import Database
from mesh_analyzer.transports import SourceManager
from mesh_analyzer.device_config import redact, read_device, prepare_lora


def make_radio():
    try:
        from meshtastic.protobuf import config_pb2
    except ImportError:
        from meshtastic import config_pb2
    class Node:
        def __init__(self):
            self.localConfig = config_pb2.Config()
            self.localConfig.lora.hop_limit = 3
            self.moduleConfig = None
            self.channels = []
            self.writes = []
        def writeConfig(self, name):
            self.writes.append(name)
    node = Node()
    return SimpleNamespace(localNode=node, metadata=SimpleNamespace(firmware_version="test"))


class ConfigTests(unittest.TestCase):
    def test_redaction_keeps_non_sensitive_fields(self):
        row = redact({"lora": {"region": "BR", "password": "value"},
                      "channels": [{"settings": {"psk": "abc", "name": "test"}}],
                      "security": {"private_key": "key-material"}})
        self.assertEqual(row["lora"]["region"], "BR")
        self.assertEqual(row["lora"]["password"], "[REDACTED]")
        self.assertEqual(row["channels"][0]["settings"]["psk"], "[REDACTED]")
        self.assertEqual(row["security"]["private_key"], "[REDACTED]")

    def test_read_modify_and_stale_revision(self):
        radio = make_radio()
        node = radio.localNode
        data = read_device(node, radio.metadata)
        fields = {f["name"]: f for f in data["fields"]}
        self.assertIn("hop_limit", fields)
        self.assertEqual(fields["hop_limit"]["value"], 3)
        before, changed = prepare_lora(node, data["revision"], {"hop_limit": 5})
        self.assertEqual(changed, ["hop_limit"])
        self.assertEqual(node.localConfig.lora.hop_limit, 5)
        node.localConfig.lora.CopyFrom(before)
        with self.assertRaisesRegex(ValueError, "limites"):
            prepare_lora(node, data["revision"], {"hop_limit": 40})
        self.assertEqual(node.localConfig.lora.hop_limit, 3)
        node.localConfig.lora.hop_limit = 4
        with self.assertRaisesRegex(ValueError, "alterada"):
            prepare_lora(node, data["revision"], {"hop_limit": 5})

    def test_radio_write_and_mqtt_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            db = Database(Path(d) / "test.sqlite3")
            manager = SourceManager(db)
            try:
                serial = db.upsert_source({"name": "Bench", "kind": "serial",
                    "config": {"port": "COM4"}, "enabled": False})
                mqtt = db.upsert_source({"name": "Broker", "kind": "mqtt",
                    "config": {"host": "example.org", "topic": "msh/+/2/e/#"}, "enabled": False})
                radio = make_radio()
                manager._interfaces[serial["id"]] = radio
                state = manager.radio_config(serial["id"])
                result = manager.update_lora(serial["id"], state["revision"], {"hop_limit": 4})
                self.assertEqual(result["state"], "write_requested")
                self.assertEqual(radio.localNode.writes, ["lora"])
                with self.assertRaisesRegex(ValueError, "MQTT"):
                    manager.update_lora(mqtt["id"], state["revision"], {"hop_limit": 5})
            finally:
                manager.close()
                db.close()


if __name__ == "__main__":
    unittest.main()
