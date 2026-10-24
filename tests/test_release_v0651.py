"""v0.6.51 (#198): diagnóstico para suporte em .zip, sem segredos nem conteúdo pessoal."""
import io
import json
import logging
import os
import tempfile
import unittest
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import Mock, patch

from mesh_analyzer import diagnostics
from mesh_analyzer.app import build_handler
from mesh_analyzer.database import Database


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "x.sqlite3")
        self.db.upsert_source({"name": "MQTT casa", "kind": "mqtt", "enabled": False,
                               "config": {"host": "mqtt.local", "topic": "msh/BR/#", "username": "alex", "password": "segredo-mqtt"}})
        self.db.upsert_source({"name": "Rádio BLE", "kind": "ble", "enabled": False,
                               "config": {"address": "44:1B:F6:70:8A:69", "pin": "123456"}})
        self.db.add_message({"source_id": 1, "packet_key": "m1", "packet_id": "1", "timestamp_ms": 1, "from_node": 1,
                             "to_node": 2, "channel": 0, "direction": "rx", "text": "texto pessoal da mensagem", "state": "received"})
        self.db.log("Falha em fonte 2: TimeoutError", "error", 2)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def unzip(self, data):
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            return {name: zf.read(name).decode("utf-8") for name in zf.namelist()}


class Build(Base):
    def test_zip_has_the_files_and_no_secrets_or_messages(self):
        autoadd = Mock()
        autoadd.status.return_value = {"results": [{"kind": "ble", "address": "44:1B:F6:70:8A:69", "outcome": "no_response",
                                                    "detail": "Unreachable"}], "ble_adapter": {"model": "Realtek Bluetooth 4.2 Adapter"}}
        with patch("mesh_analyzer.ble_pairing.adapter_info", return_value={"present": True, "model": "Realtek Bluetooth 4.2 Adapter"}):
            files = self.unzip(diagnostics.build(self.db, autoadd=autoadd, scan=False))
        self.assertEqual(set(files), {"resumo.txt", "conexoes.json", "bluetooth.json", "usb.json", "configuracao.json",
                                      "banco.json", "eventos.txt", "log.txt"})
        everything = "\n".join(files.values())
        for secret in ("segredo-mqtt", "123456", "texto pessoal da mensagem"):
            self.assertNotIn(secret, everything)
        conns = json.loads(files["conexoes.json"])
        self.assertEqual(conns[1]["config"]["pin"], "***")
        self.assertIn("Realtek Bluetooth 4.2 Adapter", files["bluetooth.json"])
        self.assertIn("TimeoutError", files["eventos.txt"])
        self.assertIn("app:", files["resumo.txt"])

    def test_clean_keeps_ping_and_masks_secrets(self):
        self.assertEqual(diagnostics.clean({"types": {"ping": True}, "psk": "abc", "api_key": "k", "pin": "", "password": None}),
                         {"types": {"ping": True}, "psk": "***", "api_key": "***", "pin": "", "password": None})

    def test_verbose_switches_debug_and_back(self):
        ring = diagnostics.RingLog()
        ring.verbose(1)
        self.assertEqual(logging.getLogger("bleak").level, logging.DEBUG)
        self.assertTrue(ring.status()["verbose"])
        ring._quiet()
        self.assertEqual(logging.getLogger("bleak").level, logging.INFO)

    def test_saved_files_rotate_and_names_are_validated(self):
        folder = Path(self.tmp.name) / "perfil"
        for i in range(7):
            (diagnostics.diagnostics_dir(folder) / ("PT2VHF-Diagnostico-2026010%d-000000.zip" % i)).write_bytes(b"x")
        saved = diagnostics.save(folder, b"zip")
        self.assertEqual(len(list(diagnostics.diagnostics_dir(folder).glob("*.zip"))), 5)
        self.assertEqual(diagnostics.diagnostic_file(folder, saved.name), saved)
        with self.assertRaises(ValueError):
            diagnostics.diagnostic_file(folder, "../x.sqlite3")


class Api(Base):
    def test_build_and_download(self):
        profile = Path(self.tmp.name) / "perfil"
        server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(self.db, Mock(snapshot=Mock(return_value={})), "csrf", "<html/>"))
        Thread(target=server.serve_forever, daemon=True).start()
        base = "http://127.0.0.1:%d" % server.server_port
        try:
            with patch.dict(os.environ, {"PT2VHF_MESH_DATA": str(profile)}), \
                 patch("mesh_analyzer.ble_pairing.adapter_info", return_value=None):
                req = urllib.request.Request(base + "/api/diagnostics/build", data=json.dumps({"scan": False}).encode(),
                                             headers={"Content-Type": "application/json", "X-PT2VHF-CSRF": "csrf"})
                built = json.loads(urllib.request.urlopen(req, timeout=20).read())
                body = urllib.request.urlopen(base + "/api/diagnostics/download?file=" + built["file"], timeout=20).read()
            self.assertTrue(built["success"])
            self.assertIn("conexoes.json", self.unzip(body))
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
