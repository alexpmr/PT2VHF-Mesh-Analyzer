"""Protocol-neutral regression tests for remote query state transitions."""
import threading
import unittest
from unittest.mock import Mock

from mesh_analyzer.remote_queries import NodeQueries


class FakeRadio:
    myInfo = {"my_node_num": 1234}
    def sendData(self, payload, **kwargs):
        self.last_payload = payload
        self.last_options = kwargs
        return {"id": 812345}

    def sendTraceRoute(self, destination, **kwargs):
        self.last_destination = destination
        return {"id": 812346}


class FakeManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._interfaces = {1: FakeRadio()}
        self.db = Mock()
        self.db.source.return_value = {"kind": "serial"}
        self.db.log.return_value = None


class RemoteQueryTests(unittest.TestCase):
    def setUp(self):
        self.manager = FakeManager()
        self.queries = NodeQueries(self.manager)

    def test_request_is_not_a_reply(self):
        result = self.queries.start(1, 5678, "position")
        self.assertEqual(result["state"], "awaiting_reply")
        from meshtastic.protobuf import mesh_pb2
        self.assertIsInstance(self.manager._interfaces[1].last_payload, mesh_pb2.Position)
        self.assertTrue(self.manager._interfaces[1].last_options["wantResponse"])

    def test_only_matching_response_completes(self):
        result = self.queries.start(1, 5678, "position")
        self.queries.observe(1, {"from": 9000, "decoded": {"portnum": "POSITION_APP"}})
        self.assertEqual(self.queries.status(5678)[0]["state"], "awaiting_reply")
        self.queries.observe(1, {"from": 5678, "decoded": {"portnum": "POSITION_APP",
                                "requestId": 812345, "position": {"latitude": -15}}})
        self.assertEqual(self.queries.status(5678)[0]["state"], "replied")

    def test_mqtt_never_transmits(self):
        self.manager.db.source.return_value = {"kind": "mqtt"}
        with self.assertRaisesRegex(ValueError, "MQTT"):
            self.queries.start(1, 5678, "position")

    def test_no_parallel_duplicate(self):
        self.queries.start(1, 5678, "position")
        with self.assertRaises(ValueError):
            self.queries.start(1, 5678, "position")

    def test_reject_broadcast(self):
        with self.assertRaises(ValueError):
            self.queries.start(1, 0xffffffff, "position")


if __name__ == "__main__":
    unittest.main()
