"""v0.6.32: distinguish failed install from unverified restart, and authenticate real launcher."""
import json
import tempfile
import unittest
from pathlib import Path

from mesh_analyzer.updater import RUNNER_PS, UpdateManager

ROOT=Path(__file__).parents[1]


class Monitor:
    def __init__(self,version):self.version=version
    def status(self):
        return {"current":self.version, "available":False, "latest":self.version,
                "error":None}


class PostUpdateStateTests(unittest.TestCase):
    def notice(self,installed_version,current_version,state):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"update_complete.json"
            path.write_text(json.dumps({"status":state, "version":installed_version,
                                        "error":"Original launcher exit=0"}),
                            encoding="utf-8")
            manager=UpdateManager(folder,Monitor(current_version),
                                  executable=Path(folder)/"app.exe")
            response=manager.notice()["notice"]
            return response

    def test_failed_notice_for_running_same_version_is_unverified_not_install_failure(self):
        notice=self.notice("0.6.31","0.6.31","failed")
        self.assertEqual(notice["status"],"unverified")
        self.assertEqual(notice["original_status"],"failed")
        self.assertFalse(notice["historical"])
        self.assertEqual(notice["current_version"],"0.6.31")
        self.assertIn("launcher",notice["error"].lower())

    def test_previous_version_failure_remains_failure_and_is_historical(self):
        notice=self.notice("0.6.30","0.6.31","failed")
        self.assertEqual(notice["status"],"failed")
        self.assertTrue(notice["historical"])

    def test_installed_notice_only_for_current_version(self):
        self.assertEqual(self.notice("0.6.31","0.6.31","installed")["status"],
                         "installed")
        self.assertIsNone(self.notice("0.6.30","0.6.31","installed"))

    def test_notice_is_dismissible_and_is_not_erased_automatically(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"update_complete.json"
            path.write_text(json.dumps({"status":"failed","version":"0.6.31"}),
                            encoding="utf-8")
            manager=UpdateManager(folder,Monitor("0.6.31"),
                                  executable=Path(folder)/"app.exe")
            self.assertEqual(manager.notice()["notice"]["status"],"unverified")
            self.assertTrue(path.exists())
            manager.dismiss()
            self.assertFalse(path.exists())

    def test_runner_never_accepts_process_exit_without_valid_health(self):
        ps=RUNNER_PS
        start=ps.index("$healthy = $false")
        end=ps.index("WriteNotice 'installed'",start)
        region=ps[start:end]
        self.assertIn("update_nonce -eq [string]$p.launch_nonce",region)
        self.assertIn("([string]$p.launch_nonce -ne '') -and",region)
        self.assertIn("$response.version -eq [string]$p.version",region)
        self.assertIn("$response.ui_ready -eq $true",region)
        self.assertIn("$healthy = $true",region)
        self.assertLess(region.index("Invoke-RestMethod"),region.index("$child.Refresh()"))
        self.assertIn("if (-not $healthy) { throw",region)
        self.assertNotIn("if ($child.ExitCode -eq 0) { $healthy = $true",region)

    def test_ui_distinguishes_unverified_install_from_failure(self):
        html=(ROOT/"mesh_analyzer"/"ui.html").read_text(encoding="utf-8")
        self.assertIn("['installed','failed','unverified']",html)
        self.assertIn("const failed=info.status==='failed',unverified=info.status==='unverified'",html)
        self.assertIn("instalada; reinício automático não confirmado",html)
        self.assertIn("Isso não significa que a instalação falhou.",html)
