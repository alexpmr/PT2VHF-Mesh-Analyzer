"""Regression tests for safe radio reconnect serialization."""
import threading
import unittest
from unittest.mock import Mock

from mesh_analyzer.transports import SourceManager


class RestartTests(unittest.TestCase):
    def manager(self):
        manager = SourceManager.__new__(SourceManager)
        manager.db = Mock()
        manager.db.source.return_value = {"enabled": True, "kind": "serial"}
        manager._lock = threading.RLock()
        manager._threads = {}
        manager._interfaces = {}
        manager._stop_sources = set()
        manager._states = {}
        manager._stop = threading.Event()
        return manager

    def test_reconnect_starts_after_old_worker_gone(self):
        manager = self.manager()
        events = []
        manager.disconnect = Mock(side_effect=lambda sid: events.append("disconnect"))
        manager.connect = Mock(side_effect=lambda sid: events.append("connect"))
        out = manager.restart(12)
        self.assertEqual(events, ["disconnect", "connect"])
        self.assertEqual(out["state"], "connecting")

    def test_mqtt_rejected(self):
        manager = self.manager()
        manager.db.source.return_value = {"enabled": True, "kind": "mqtt"}
        with self.assertRaises(ValueError):
            manager.restart(12)

    def test_disabled_rejected(self):
        manager = self.manager()
        manager.db.source.return_value = {"enabled": False, "kind": "serial"}
        with self.assertRaises(ValueError):
            manager.restart(12)


if __name__ == "__main__":
    unittest.main()
