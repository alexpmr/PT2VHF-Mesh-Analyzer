"""RF timeout and recovery use monotonic time, independent of UI polling."""
import unittest
from unittest.mock import patch
from test_remote_queries import FakeManager, FakeRadio
from mesh_analyzer.remote_queries import NodeQueries


class QueryTimeoutTests(unittest.TestCase):
    def setUp(self):
        self.manager = FakeManager()
        self.queries = NodeQueries(self.manager)

    def test_all_types_retry_without_status_polling(self):
        for kind in ('nodeinfo', 'position', 'telemetry', 'traceroute'):
            with self.subTest(kind=kind):
                self.setUp()
                with patch('mesh_analyzer.remote_queries.time.monotonic', return_value=100):
                    first = self.queries.start(1, 5678, kind)
                with patch('mesh_analyzer.remote_queries.time.monotonic', return_value=129.99):
                    with self.assertRaisesRegex(ValueError, 'aguardando'):
                        self.queries.start(1, 5678, kind)
                with patch('mesh_analyzer.remote_queries.time.monotonic', return_value=130):
                    second = self.queries.start(1, 5678, kind)
                self.assertNotEqual(first['request_id'], second['request_id'])
                self.assertEqual(self.queries.pending[first['request_id']]['state'], 'timeout')

    def test_timeout_begins_when_send_finishes(self):
        clock = [100]
        radio = self.manager._interfaces[1]
        original = radio.sendData
        def slow_send(*args, **kwargs):
            clock[0] = 120
            return original(*args, **kwargs)
        radio.sendData = slow_send
        with patch('mesh_analyzer.remote_queries.time.monotonic', side_effect=lambda: clock[0]):
            self.queries.start(1, 5678, 'nodeinfo')
            clock[0] = 149
            self.assertEqual(self.queries.status()[0]['state'], 'awaiting_reply')
            clock[0] = 150
            self.assertEqual(self.queries.status()[0]['state'], 'timeout')

    def test_late_reply_does_not_revive_expired_request(self):
        with patch('mesh_analyzer.remote_queries.time.monotonic', return_value=100):
            self.queries.start(1, 5678, 'nodeinfo')
        with patch('mesh_analyzer.remote_queries.time.monotonic', return_value=130):
            self.queries.observe(1, {'from':5678, 'decoded':{'portnum':4, 'requestId':812345}})
            self.assertEqual(self.queries.status()[0]['state'], 'timeout')

    def test_replacement_connection_cannot_complete_old_request(self):
        self.queries.start(1, 5678, 'nodeinfo')
        self.manager._interfaces[1] = FakeRadio()
        self.queries.observe(1, {'from':5678, 'decoded':{'portnum':4, 'requestId':812345}})
        self.assertEqual(self.queries.status()[0]['state'], 'disconnected')

    def test_wall_clock_jump_does_not_change_deadline(self):
        with patch('mesh_analyzer.remote_queries.time.monotonic', return_value=100):
            self.queries.start(1, 5678, 'position')
        with patch('mesh_analyzer.remote_queries.time.monotonic', return_value=110), patch('mesh_analyzer.remote_queries.time.time', return_value=9999999999):
            self.assertEqual(self.queries.status()[0]['state'], 'awaiting_reply')

if __name__ == '__main__':
    unittest.main()
