"""Regressões: primeira configuração, links por aba e apresentação da v0.6.3."""
import json
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from mesh_analyzer import __version__
from mesh_analyzer.app import build_handler
from mesh_analyzer.database import Database
from mesh_analyzer.transports import SourceManager

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "mesh_analyzer" / "ui.html").read_text(encoding="utf-8")


class FirstConnectionTests(unittest.TestCase):
    def test_dialog_checks_persisted_sources_not_online_status(self):
        self.assertIn('id="firstRunDialog"', HTML)
        self.assertIn('id="firstRunConnections"', HTML)
        self.assertIn('id="firstRunLater"', HTML)
        self.assertIn('let firstRunDialogChecked=false,updateNoticeChecked=false;', HTML)
        # v0.6.39 (#162): a busca automática roda antes do diálogo.
        self.assertIn('if(firstRunDialogChecked||firstRunSearchBusy||!updateNoticeChecked||!Array.isArray(state.sources))return;', HTML)
        self.assertIn("sessionStorage.setItem('mesh.firstRunShown','yes')", HTML)
        self.assertIn("sessionStorage.getItem('mesh.firstRunShown')", HTML)
        self.assertIn("if(state.sources.length>0){$('firstRunSearch').hidden=true;return;}", HTML)
        self.assertIn('state=results[0];showFirstRunDialogOnce();', HTML)
        self.assertIn("dismissFirstRunDialog();\n setView('settings');\n showSettings('sources');", HTML)
        self.assertIn("$('sourceName').focus();", HTML)
        self.assertNotIn('id="connectedStatus"', HTML)
        self.assertNotIn('id="summarySources"', HTML)

    def test_setting_routes_and_version_are_consistent(self):
        self.assertIn('settingsPaths={sources:\'conexoes\'', HTML)
        self.assertIn("viewPaths={map:'/mapa'", HTML)
        self.assertIn("settings:'/configuracoes/conexoes'", HTML)
        self.assertIn("showSettings(initialSettingsPanel,false)", HTML)
        self.assertIn('data-panel="sources">Conexões</button>', HTML)
        self.assertIn('class="brand-version">v'+__version__, HTML)
        self.assertEqual((ROOT/"VERSION").read_text().strip(), __version__)
        self.assertIn('#define AppVersion "'+__version__+'"',
                      (ROOT/"windows"/"installer.iss").read_text())

    def test_http_routes_and_disabled_connection_are_not_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp)/"test.sqlite3")
            manager = SourceManager(db)
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                build_handler(db, manager, "test-csrf", HTML)
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = "http://127.0.0.1:"+str(server.server_address[1])
            try:
                for route in ("/configuracoes/conexoes", "/configuracoes/dispositivo",
                              "/configuracoes/mapa", "/configuracoes/retencoes"):
                    with urllib.request.urlopen(base+route) as response:
                        self.assertEqual(response.status, 200)
                        self.assertIn(b'firstRunConnections', response.read())
                with urllib.request.urlopen(base+"/api/state") as response:
                    self.assertEqual(json.load(response)["sources"], [])
                db.upsert_source({"name":"USB desligado", "kind":"serial",
                                  "config":{"port":"COM8"}, "enabled":False})
                with urllib.request.urlopen(base+"/api/state") as response:
                    sources = json.load(response)["sources"]
                    self.assertEqual(len(sources), 1)
                    self.assertFalse(sources[0]["enabled"])
            finally:
                server.shutdown()
                server.server_close()
                manager.close()
                db.close()


if __name__ == "__main__":
    unittest.main()
