"""Taskbar icon packaging regression tests (Win11 pywebview WinForms)."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from mesh_analyzer.desktop import native_window_icon

ROOT = Path(__file__).resolve().parents[1]


class TaskbarIconTests(unittest.TestCase):
    def test_onefile_uses_bundled_ico_under_meipass(self):
        with tempfile.TemporaryDirectory() as tmp:
            expected = Path(tmp) / "branding" / "mesh-analyzer.ico"
            expected.parent.mkdir(parents=True)
            expected.write_bytes(b"icon-fixture")
            with patch.object(sys, "_MEIPASS", tmp, create=True), \
                 patch.object(sys, "frozen", True, create=True):
                self.assertEqual(native_window_icon(), expected)
                expected.unlink()
                with self.assertRaisesRegex(RuntimeError, "Ícone nativo PT2VHF"):
                    native_window_icon()

    def test_setup_prefers_same_stable_icon_as_shortcuts(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            installed = base/"install"/"branding"/"mesh-analyzer.ico"
            installed.parent.mkdir(parents=True)
            installed.write_bytes(b"installed-current-ico")
            embedded = base/"unpack"/"branding"/"mesh-analyzer.ico"
            embedded.parent.mkdir(parents=True)
            embedded.write_bytes(b"embedded-portable-ico")
            with patch.object(sys, "_MEIPASS", str(base/"unpack"), create=True), \\
                 patch.object(sys, "frozen", True, create=True), \\
                 patch.object(sys, "executable", str(base/"install"/"PT2VHF-Mesh-Analyzer.exe")):
                self.assertEqual(native_window_icon(), installed)
                installed.unlink()
                self.assertEqual(native_window_icon(), embedded)

    def test_source_checkout_does_not_require_generated_ico(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(sys, "_MEIPASS", tmp, create=True), \
                 patch.object(sys, "frozen", False, create=True):
                self.assertIsNone(native_window_icon())

    def test_runtime_and_both_builds_include_the_same_ico(self):
        desktop = (ROOT/"mesh_analyzer"/"desktop.py").read_text(encoding="utf-8")
        workflow = (ROOT/".github"/"workflows"/"windows.yml").read_text(encoding="utf-8")
        local_build = (ROOT/"build_windows.ps1").read_text(encoding="utf-8")
        requirements = (ROOT/"requirements.txt").read_text(encoding="utf-8")
        installer = (ROOT/"windows"/"installer.iss").read_text(encoding="utf-8")

        self.assertIn('icon=str(icon_path) if icon_path else None', desktop)
        self.assertIn('mesh-analyzer.ico', desktop)
        self.assertIn("pywebview>=6.2,<7", requirements)
        for script in (workflow, local_build):
            self.assertIn("--icon branding/mesh-analyzer.ico", script)
            self.assertIn("--add-data 'branding/mesh-analyzer.ico;branding'", script)
        self.assertIn("AppUserModelID: \"PT2VHF.MeshAnalyzer\"", installer)
        self.assertIn('Source: "..\\branding\\mesh-analyzer.ico"; DestDir: "{app}\\branding"', installer)
        self.assertEqual(installer.count('IconFilename: "{app}\\branding\\mesh-analyzer.ico"'), 2)
        self.assertIn("UninstallDisplayIcon={app}\\branding\\mesh-analyzer.ico", installer)
        self.assertNotIn('IconFilename: "{app}\\PT2VHF-Mesh-Analyzer.exe"', installer)


if __name__ == "__main__":
    unittest.main()
