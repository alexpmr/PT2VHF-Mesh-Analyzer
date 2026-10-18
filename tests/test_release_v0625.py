"""v0.6.25 — PDF download, native Save As, System theme and statistics defaults."""
import base64
import json
import sys
import tempfile
import threading
import types
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from mesh_analyzer.app import build_handler
from mesh_analyzer.database import Database
from mesh_analyzer.desktop import PDFExportBridge
from mesh_analyzer.reporting import generate
from mesh_analyzer.transports import SourceManager

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "mesh_analyzer" / "ui.html").read_text(encoding="utf-8")


class Release0625Tests(unittest.TestCase):
    def test_system_themes_are_validated_and_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mesh.db"
            db = Database(path)
            self.assertEqual(db.system_settings()["theme"], "dark")
            for theme in ("dark", "gray", "light"):
                self.assertEqual(db.set_system_settings({"theme": theme})["theme"], theme)
                self.assertEqual(db.system_settings()["theme"], theme)
            for invalid in ("rainbow", "", 123, None):
                with self.assertRaises(ValueError):
                    db.set_system_settings({"theme": invalid})
            db._db.close()
            new_db = Database(path)
            self.assertEqual(new_db.system_settings()["theme"], "light")
            new_db._db.close()

    def test_pdf_generation_and_authenticated_http_route_with_no_radio(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "mesh.db")
            content = generate(db, {"period": "all", "source": "all", "node": "all"}, {})
            self.assertTrue(content.startswith(b"%PDF-"))
            self.assertIn(b"%%EOF", content[-2048:])
            self.assertGreater(len(content), 2000)
            manager = SourceManager(db)
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                build_handler(db, manager, "test-csrf", HTML)
            )
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                url = f"http://127.0.0.1:{server.server_address[1]}/api/report/pdf"
                data = json.dumps({"period":"all", "node":"all","source":"all"}).encode()
                request = urllib.request.Request(url, data=data, method="POST", headers={
                    "Content-Type": "application/json",
                    "X-PT2VHF-CSRF": "test-csrf"
                })
                with urllib.request.urlopen(request, timeout=20) as response:
                    self.assertEqual(response.status, 200)
                    self.assertIn("application/pdf", response.headers.get("Content-Type", ""))
                    result = response.read()
                    self.assertTrue(result.startswith(b"%PDF-"))
                    self.assertIn(b"%%EOF", result[-2048:])
            finally:
                server.shutdown()
                server.server_close()
                db._db.close()

    def test_desktop_pdf_save_dialog_and_cancel(self):
        pdf = b"%PDF-1.4\n" + b"0" * 2048 + b"\n%%EOF\n"
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "sample.pdf"
            mock_webview = types.SimpleNamespace(SAVE_DIALOG="save")
            bridge = PDFExportBridge()
            class Window:
                def __init__(self):
                    self.saved = str(destination)
                def create_file_dialog(self, *_args, **_kwargs):
                    return self.saved
            bridge._window = Window()
            with patch.dict(sys.modules, {"webview": mock_webview}):
                data = base64.b64encode(pdf).decode("ascii")
                result = bridge.save_pdf(data, "PT2VHF-Mesh-Analyzer.pdf")
                self.assertTrue(result["saved"])
                self.assertEqual(destination.read_bytes(), pdf)
                bridge._window.saved = None
                self.assertTrue(bridge.save_pdf(data, "report.pdf")["cancelled"])
                with self.assertRaises(ValueError):
                    bridge.save_pdf("not-base64", "report.pdf")

    def test_html_theme_and_stats_regression(self):
        self.assertIn('id="systemTheme"', HTML)
        self.assertIn('value="dark">Escuro (#202126)', HTML)
        self.assertIn('value="gray">Cinza (#333438)', HTML)
        self.assertIn('value="light">Claro', HTML)
        self.assertIn(":root[data-theme=\"gray\"]", HTML)
        self.assertIn(":root[data-theme=\"light\"]", HTML)
        self.assertIn("applySystemTheme(", HTML)
        self.assertIn("theme:$('systemTheme').value", HTML)
        self.assertIn('<option value="all" selected>Todo</option>', HTML)
        self.assertNotIn('<option value="24h" selected>24 h</option>', HTML)
        self.assertIn("window.pywebview.api.save_pdf(payload,filename)", HTML)
        self.assertIn("document.body.appendChild(link)", HTML)
