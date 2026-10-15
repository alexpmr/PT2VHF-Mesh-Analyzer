"""Regression tests for update-readiness, SQLite backups, friendly names and activity."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from mesh_analyzer.database import Database
from mesh_analyzer.transports import SourceManager, PacketIngestor
from mesh_analyzer.updater import RUNNER_PS, UpdateManager


class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Database(Path(self.tmp.name)/"mesh-analyzer.sqlite3")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_live_backup_integrity_and_no_retention_change(self):
        self.db.upsert_node(0x12345678, 1, timestamp_ms=1234567890000, long_name="Test node")
        baseline=self.db.retention()
        self.assertEqual(self.db.health()["counts"]["nodes"], 1)
        self.assertIsNone(self.db.health()["integrity"])
        self.assertEqual(self.db.health(check=True)["integrity"], ["ok"])
        result=self.db.backup()
        destination=self.db.path.parent/"backups"/result["file"]
        self.assertTrue(destination.is_file())
        self.assertEqual(result["bytes"], destination.stat().st_size)
        saved=sqlite3.connect(str(destination))
        try:
            self.assertEqual(saved.execute("PRAGMA quick_check").fetchone()[0], "ok")
            self.assertEqual(saved.execute("SELECT COUNT(*) FROM nodes").fetchone()[0], 1)
        finally:
            saved.close()  # Windows cannot unlink an open SQLite file
        self.assertEqual(self.db.retention(), baseline)
        self.assertEqual(self.db.health()["last_backup"], result["file"])

    def test_nickname_is_local_and_preserved_after_radio_updates(self):
        self.db.upsert_node(0x12345678, 2, long_name="Radio original")
        response=self.db.set_node_friendly_name(0x12345678,"Casa VHF")
        self.assertEqual(response["friendly_name"],"Casa VHF")
        self.db.upsert_node(0x12345678, 2, long_name="New NodeDB name")
        node=self.db.node_rows()[0]
        self.assertEqual(node["friendly_name"], "Casa VHF")
        self.assertEqual(node["node_id"], "!12345678")
        self.db.set_node_friendly_name(0x12345678,"")
        self.assertEqual(self.db.node_rows()[0]["friendly_name"],"")
        with self.assertRaisesRegex(ValueError,"80"):
            self.db.set_node_friendly_name(0x12345678,"x"*81)

    def test_sequences_only_advance_on_new_radio_packet(self):
        source=self.db.upsert_source({"name":"Test source","kind":"serial",
                                     "config":{"port":"COM9"},"enabled":False})
        manager=SourceManager(self.db)
        sid=source["id"]
        manager._set(sid,"connected")
        self.assertEqual(manager.snapshot()[str(sid)]["rx_seq"],0)
        self.assertEqual(manager.snapshot()[str(sid)]["tx_seq"],0)
        self.assertEqual(manager.snapshot()[str(sid)]["mqtt_rx_seq"],0)
        manager._set(sid,"disconnected")
        self.assertEqual(manager.snapshot()[str(sid)]["rx_seq"],0)
        manager.close()

    def test_updater_success_is_after_new_health_check(self):
        self.assertIn("Invoke-RestMethod",RUNNER_PS)
        self.assertIn("$response.version -eq [string]$p.version",RUNNER_PS)
        self.assertIn("$response.ui_ready -eq $true",RUNNER_PS)
        self.assertIn("WriteNotice 'failed' $reason",RUNNER_PS)
        self.assertIn("WriteNotice 'installed' ''",RUNNER_PS)
        self.assertLess(RUNNER_PS.index("if (-not $healthy)"),
                        RUNNER_PS.index("WriteNotice 'installed' ''"))
        self.assertIn("Restored previous portable executable", RUNNER_PS)
        class Monitor:
            def status(self):return {"current":"0.6.2"}
        p=Path(self.tmp.name)/"update_complete.json"
        m=UpdateManager(self.tmp.name,Monitor(),executable="C:/fake.exe")
        p.write_text('{"version":"0.6.3","status":"failed","error":"No health"}',encoding="utf8")
        self.assertEqual(m.notice()["notice"]["status"],"failed")
        m.dismiss()
        self.assertFalse(p.exists())


if __name__ == "__main__":
    unittest.main()
