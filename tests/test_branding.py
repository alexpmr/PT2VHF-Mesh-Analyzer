"""Branding regressions: source image, offline UI and Windows packaging."""
from __future__ import annotations

import base64
import hashlib
import struct
import unittest
from pathlib import Path

from mesh_analyzer.branding import IMAGE, SHA256, brand_image_data_uri


ROOT = Path(__file__).resolve().parents[1]


class BrandingTests(unittest.TestCase):
    def test_logo_is_the_same_verified_png_used_by_ui_and_compiler(self):
        uri = brand_image_data_uri()
        self.assertTrue(uri.startswith("data:image/png;base64,"))
        raw = base64.b64decode(uri.split(",", 1)[1], validate=True)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), SHA256)
        self.assertEqual(raw[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", raw[16:24]), (128, 128))
        self.assertEqual(raw, base64.b64decode(IMAGE.read_text().strip()))

    def test_html_uses_one_logo_for_header_and_favicon(self):
        markup = (ROOT/"mesh_analyzer"/"ui.html").read_text(encoding="utf-8")
        self.assertEqual(markup.count("__PT2VHF_MESH_LOGO__"), 2)
        self.assertIn('rel="icon" type="image/png"', markup)
        self.assertIn('class="logo" src="__PT2VHF_MESH_LOGO__"', markup)

    def test_exe_and_installer_reference_branded_icon_and_group(self):
        workflow = (ROOT/".github"/"workflows"/"windows.yml").read_text(encoding="utf-8")
        installer = (ROOT/"windows"/"installer.iss").read_text(encoding="utf-8")
        self.assertIn("--icon branding/mesh-analyzer.ico", workflow)
        self.assertIn("SetupIconFile=..\\branding\\mesh-analyzer.ico", installer)
        self.assertEqual(installer.count('AppUserModelID: "PT2VHF.MeshAnalyzer"'), 2)
        self.assertIn("PT2VHF.MeshAnalyzer", (ROOT/"mesh_analyzer"/"desktop.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
