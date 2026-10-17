"""Offline regression tests for the Windows update safety checks."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mesh_analyzer.updater import (
    RELEASE_BASE, UpdateManager, approved_asset_url,
    parse_checksums, release_assets, stream_verified,
)


class UpdateTests(unittest.TestCase):
    def test_exact_release_assets_and_urls(self):
        items=release_assets("0.5.0")
        self.assertEqual(items["setup"],"PT2VHF-Mesh-Analyzer-v0.5.0-Setup-Win10-Win11-x64.exe")
        self.assertEqual(items["portable"],"PT2VHF-Mesh-Analyzer-v0.5.0-Portable-Win10-Win11-x64.zip")
        good=RELEASE_BASE+"v0.5.0/"+items["setup"]
        self.assertEqual(approved_asset_url(good,"0.5.0",items["setup"]),good)
        for bad in [good.replace("alexpmr","attacker"),
                    good.replace("v0.5.0","v0.4.0"),
                    good.replace("-Setup-","-Portable-")]:
            with self.assertRaises(ValueError):
                approved_asset_url(bad,"0.5.0",items["setup"])
        with self.assertRaises(ValueError):
            release_assets("../../latest")

    def test_checksum_rejects_missing_mismatch_and_partial_files(self):
        data=b"portable-image-fixture"
        checksum=hashlib.sha256(data).hexdigest()
        doc=checksum+"  PT2VHF-Mesh-Analyzer-v0.5.0-Portable-Win10-Win11-x64.zip\n"
        name="PT2VHF-Mesh-Analyzer-v0.5.0-Portable-Win10-Win11-x64.zip"
        self.assertEqual(parse_checksums(doc,name),checksum)
        with self.assertRaises(ValueError):
            parse_checksums(doc,name+".exe")
        class Response:
            def __init__(self,blob):self.blob=blob;self.at=0;self.headers={"Content-Length":str(len(blob))}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,size):
                b=self.blob[self.at:self.at+size];self.at+=len(b);return b
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/name
            with patch("urllib.request.urlopen",return_value=Response(data)):
                stream_verified("https://example.com/file",file,checksum)
            self.assertEqual(file.read_bytes(),data)
            file.unlink()
            with patch("urllib.request.urlopen",return_value=Response(data)):
                with self.assertRaisesRegex(ValueError,"SHA256"):
                    stream_verified("https://example.com/file",file,"0"*64)
            self.assertFalse(file.exists())
            self.assertFalse(Path(str(file)+".part").exists())

    def test_update_requires_checked_available_version(self):
        class FakeMonitor:
            _result={"assets":[]}
            def status(self):
                return {"current":"0.4.0","available":False,"latest":"0.5.0","error":None}
        with tempfile.TemporaryDirectory() as folder:
            manager=UpdateManager(folder,FakeMonitor(),executable="/tmp/program.exe")
            with self.assertRaisesRegex(ValueError,"Verifique"):
                manager.start("0.5.0")
            self.assertIsNone(manager.notice()["notice"])
            self.assertEqual(manager.dismiss(),{"success":True})


if __name__=="__main__":
    unittest.main()
