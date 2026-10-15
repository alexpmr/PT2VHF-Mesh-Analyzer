"""v0.6.7 regressions: radio status, offline message dialog and link details."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
UI=(ROOT/"mesh_analyzer"/"ui.html").read_text(encoding="utf-8")
INSTALLER=(ROOT/"windows"/"installer.iss").read_text(encoding="utf-8")
SCRIPT=(ROOT/"windows"/"close_running_mesh.ps1").read_text(encoding="utf-8")

class DesktopRegressionTests(unittest.TestCase):
    def test_radio_status_from_live_local_connections_only(self):
        self.assertEqual(UI.count('id="radioConnectionStatus"'),1)
        self.assertIn('function updateRadioConnectionIndicator(){',UI)
        self.assertIn("String(s.kind||'').toLowerCase()!=='mqtt'",UI)
        self.assertIn("c.status==='connected'?'Conectado'",UI)
        self.assertIn("pill.dataset.status=yes?'connected':'disconnected'",UI)
        self.assertIn("state=results[0];showFirstRunDialogOnce();updateRadioConnectionIndicator();",UI)

    def test_offline_tx_popup_with_actions_without_draft_loss(self):
        self.assertEqual(UI.count('id="messageNoConnectionDialog"'),1)
        self.assertEqual(UI.count('id="messageNoConnectionSettings"'),1)
        self.assertIn("setView('settings');",UI)
        self.assertIn("showSettings('sources');",UI)
        self.assertIn("$('messageSend').disabled=messageSending;",UI)
        self.assertIn("if(!txRadioSources().length){showNoConnectionDialog();return;}",UI)
        between=UI.split("function showNoConnectionDialog(){",1)[1].split("function txRadioSources(){",1)[0]
        self.assertNotIn("$('messageText').value=''",between)

    def test_link_popup_for_observed_and_rf_without_fabricated_quality(self):
        self.assertIn('function linkPopupHtml(link,kind){',UI)
        self.assertIn('function attachLinkPopup(layer,link,kind){',UI)
        self.assertIn("attachLinkPopup(line,edge,'link');",UI)
        self.assertIn("attachLinkPopup(flowLine,flow,'communication');",UI)
        self.assertIn('RSSI',UI)
        self.assertIn('SNR',UI)
        self.assertIn("Caminho físico",UI) if "Caminho físico" in UI else self.assertIn("caminho físico desconhecido",UI)
        self.assertIn("data-link-node",UI)
        self.assertIn('Number(n.position_ms)>0',UI)

    def test_installer_process_handoff_is_explicit_and_scoped(self):
        self.assertIn("CloseApplications=no",INSTALLER)
        self.assertIn('ExtractTemporaryFile(\'close_running_mesh.ps1\')',INSTALLER)
        self.assertIn("TargetExe",INSTALLER)
        self.assertIn("Win32_Process",SCRIPT)
        self.assertIn("GetOwnerSid",SCRIPT)
        self.assertIn("OrdinalIgnoreCase",SCRIPT)
        self.assertIn("CloseMainWindow()",SCRIPT)
        self.assertIn("Stop-Process -Id $id",SCRIPT)
        self.assertIn("installer-close.log",SCRIPT)

if __name__=="__main__": unittest.main()
