"""System preferences, multi-group device writes and desktop packaging guards."""
import tempfile
import unittest
from pathlib import Path

from mesh_analyzer.database import Database
from mesh_analyzer.device_config import editable_fields,prepare_all,read_device
from mesh_analyzer.transports import SourceManager


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"system.sqlite3"
        self.db=Database(self.path)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_safe_system_defaults_and_persistence(self):
        d=self.db.system_settings()
        self.assertEqual(d["update_minutes"],15)
        self.assertFalse(d["open_browser_on_start"])
        self.assertFalse(d["allow_lan_access"])
        cfg=self.db.set_system_settings({"update_minutes":37,"open_browser_on_start":True})
        self.assertEqual(cfg["update_minutes"],37)
        self.db.close()
        self.db=Database(self.path)
        self.assertEqual(self.db.system_settings()["update_minutes"],37)
        self.assertTrue(self.db.system_settings()["open_browser_on_start"])
        with self.assertRaisesRegex(ValueError,"LAN"):
            self.db.set_system_settings({"allow_lan_access":True})
        self.assertFalse(self.db.system_settings()["allow_lan_access"])
        for invalid in [2,0,1441,False,"15",15.0]:
            with self.assertRaises(ValueError):
                self.db.set_system_settings({"update_minutes":invalid})

    def test_device_multi_group_and_stale_config(self):
        try:from meshtastic.protobuf import config_pb2
        except ImportError:from meshtastic import config_pb2
        class Node:
            def __init__(self):
                self.localConfig=config_pb2.Config()
                self.localConfig.lora.hop_limit=3
                self.channels=[]
                self.moduleConfig=None
                self.writes=[]
            def writeConfig(self,group):
                self.writes.append(group)
        node=Node()
        fields=editable_fields(node.localConfig)
        self.assertIn("lora",fields)
        self.assertIn("hop_limit",{x["name"] for x in fields["lora"]})
        original=read_device(node)
        self.assertIn("full_revision",original)
        self.assertIn("editable_sections",original)
        backup,edits=prepare_all(node,original["full_revision"],{"lora":{"hop_limit":4}})
        self.assertEqual([x["group"] for x in edits],["lora"])
        self.assertEqual(node.localConfig.lora.hop_limit,4)
        with self.assertRaisesRegex(ValueError,"mudou"):
            prepare_all(node,original["full_revision"],{"lora":{"hop_limit":5}})
        node.localConfig.CopyFrom(backup)
        with self.assertRaises(ValueError):
            prepare_all(node,original["full_revision"],{"security":{"private_key":"a"}})
        self.assertEqual(node.localConfig.lora.hop_limit,3)

    def test_apply_failure_is_reported_not_falsely_successful(self):
        try:from meshtastic.protobuf import config_pb2
        except ImportError:from meshtastic import config_pb2
        source=self.db.upsert_source({"name":"Bench","kind":"serial",
             "config":{"port":"COM9"},"enabled":False})
        class Radio:
            def __init__(self):
                self.localConfig=config_pb2.Config()
                self.localConfig.lora.hop_limit=3
                self.channels=[]
                self.moduleConfig=None
                self.writes=[]
            def writeConfig(self,group):
                self.writes.append(group)
                raise RuntimeError("serial disconnected")
            def close(self):pass
        radio=Radio()
        manager=SourceManager(self.db)
        manager._interfaces[source["id"]]=type("Iface",(),{"localNode":radio,"close":lambda self:None})()
        try:
            snapshot=manager.radio_config(source["id"])
            result=manager.update_device(source["id"],snapshot["full_revision"],
                      {"lora":{"hop_limit":4}})
            self.assertFalse(result["success"])
            self.assertEqual(result["state"],"partial_or_failed")
            self.assertEqual(radio.localConfig.lora.hop_limit,3)
        finally:
            manager.close()


if __name__=="__main__":
    unittest.main()
