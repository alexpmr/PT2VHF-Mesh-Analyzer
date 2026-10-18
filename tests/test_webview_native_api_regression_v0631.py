"""Regression for v0.6.31: js_api must not recurse into native WebView2 objects."""
import unittest
from pathlib import Path

from mesh_analyzer.desktop import PDFExportBridge
from mesh_analyzer.updater import RUNNER_PS


class ExplosiveNativeWindow:
    """Simulates .NET native properties that fail during attribute inspection."""
    @property
    def native(self):
        raise AssertionError("JS API recursively walked the native WinForms object")

    def create_file_dialog(self, *args, **kwargs):
        return None


class NativeBridgeSafetyTests(unittest.TestCase):
    def test_webview_bridge_only_exposes_callable_save_method(self):
        bridge=PDFExportBridge()
        bridge._window=ExplosiveNativeWindow()
        self.assertFalse(hasattr(bridge, "window"))
        self.assertTrue(hasattr(bridge, "_window"))
        # Exercise pywebview's reflective scanner, not only simple attribute names.
        # A public window field would traverse native COM and fail.
        from webview.util import get_functions
        exposed=get_functions(bridge)
        self.assertIn("save_pdf", exposed)
        self.assertTrue(all(not key.startswith("window") and
                            not key.startswith("_window") for key in exposed))

    def test_desktop_window_reference_is_private(self):
        content=(Path(__file__).parents[1]/"mesh_analyzer"/"desktop.py").read_text(encoding="utf-8")
        self.assertIn("pdf_bridge._window = window",content)
        self.assertNotIn("pdf_bridge.window = window",content)

    def test_updater_checks_nonce_and_health_before_launcher_exit(self):
        ps=RUNNER_PS
        start=ps.index("while ([DateTime]::UtcNow -lt $deadline)")
        end=ps.index("if (-not $healthy)",start)
        region=ps[start:end]
        self.assertLess(region.index("Invoke-RestMethod"),region.index("$child.Refresh()"))
        self.assertIn("$response.update_nonce -eq [string]$p.launch_nonce",region)
        self.assertIn("$response.version -eq [string]$p.version",region)
        self.assertIn("$response.ui_ready -eq $true",region)
        self.assertIn("$child.ExitCode -ne 0",region)
        self.assertNotIn("Updated application exited early: 0",region)
        self.assertIn("Initial launcher exited with code 0; awaiting verified /health",region)
