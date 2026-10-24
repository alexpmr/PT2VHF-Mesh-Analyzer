"""v0.6.52: correções vistas no primeiro diagnóstico real (#198/#191)."""
import json
import tempfile
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import Mock, patch

from mesh_analyzer import diagnostics
from mesh_analyzer.app import build_handler
from mesh_analyzer.database import Database
from mesh_analyzer.meshcore_data import MeshCoreData


class MeshcoreResultsWithoutNode(unittest.TestCase):
    def test_latest_readings_list_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "x.sqlite3")
            sources = Mock()
            sources.meshcore = MeshCoreData(db)
            sources.meshcore_interface.return_value = (3, None)
            sources.meshcore.add_result(3, 0x0BADCAFE, "status", {"bat": 4100})
            server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(db, sources, "csrf", "<html/>"))
            Thread(target=server.serve_forever, daemon=True).start()
            try:
                body = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/api/meshcore/results?limit=15" % server.server_port,
                                                         timeout=10).read())
                self.assertEqual([r["kind"] for r in body["data"]], ["status"])
            finally:
                server.shutdown()
                server.server_close()
                db.close()


class Versions(unittest.TestCase):
    def test_frozen_app_falls_back_to_the_module(self):
        from importlib import metadata

        def missing(name):
            raise metadata.PackageNotFoundError(name)
        with patch.object(metadata, "version", missing):
            versions = diagnostics._versions()
        self.assertTrue(versions["meshtastic"])
        self.assertTrue(versions["bleak"])


if __name__ == "__main__":
    unittest.main()
