"""Discovery never connects, probes subnets or sends any RF traffic."""
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path

from mesh_analyzer.discovery import DeviceDiscovery
from mesh_analyzer.app import build_handler
from mesh_analyzer.database import Database
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import threading,json


class DiscoveryTests(unittest.TestCase):
    def test_serial_candidates_are_unverified_and_deduplicated(self):
        scan=DeviceDiscovery()
        ports=[SimpleNamespace(device="COM7",description="USB Radio"),
               SimpleNamespace(device="COM7",description="USB Radio")]
        with patch("serial.tools.list_ports.comports",return_value=ports),patch(
                  "bleak.BleakScanner.discover",side_effect=RuntimeError("adapter absent")):
            scan._scan()
        result=scan.snapshot()
        self.assertFalse(result["running"])
        c=[x for x in result["items"] if x["kind"]=="serial"]
        self.assertEqual(len(c),1)
        self.assertEqual(c[0]["config"],{"port":"COM7"})
        self.assertFalse(c[0]["verified"])

    def test_local_api_read_only_status_and_csrf_protected_start(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Database(Path(folder)/"db.sqlite3")
            discovery=DeviceDiscovery()
            manager=SimpleNamespace(snapshot=lambda:{})
            server=ThreadingHTTPServer(("127.0.0.1",0),
              build_handler(db,manager,"secret","<html></html>",discovery=discovery))
            worker=threading.Thread(target=server.serve_forever,daemon=True)
            worker.start()
            url=f"http://127.0.0.1:{server.server_port}"
            try:
                with urlopen(url+"/api/discovery") as response:
                    self.assertEqual(json.load(response)["data"]["items"],[])
                data=json.dumps({}).encode()
                req=Request(url+"/api/discovery/start",data,
                            {"Content-Type":"application/json"},method="POST")
                with self.assertRaises(HTTPError) as err:urlopen(req)
                self.assertEqual(err.exception.code,403)
            finally:
                server.shutdown();server.server_close();worker.join(2);db.close()


if __name__=="__main__":unittest.main()
