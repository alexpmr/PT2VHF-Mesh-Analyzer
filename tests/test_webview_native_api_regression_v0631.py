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
        # pywebview enumerates public members recursively when exposing JS API.
        # Verify that the only public entry point is the expected callable.
        # Do not rely on unstable private pywebview.util module functions.
        exposed=[name for name in dir(bridge) if not name.startswith("_")]
        # v0.6.40 (#166): save_backup também é só um método; o perfil é privado.
        self.assertEqual(exposed, ["save_backup", "save_diagnostic", "save_pdf"])  # #198: diagnóstico .zip
        self.assertTrue(all(callable(getattr(bridge, name)) for name in exposed))

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
