"""v0.6.35: aviso de nova versão perguntando se deseja atualizar."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"mesh_analyzer"/"ui.html").read_text(encoding="utf-8")


class UpdatePrompt(unittest.TestCase):
    def test_version_detection_opens_update_dialog_once(self):
        state=HTML[HTML.index("function updateVersionState(info){"):HTML.index("async function checkUpdates(")]
        self.assertIn("maybePromptUpdate(info);",state)
        prompt=HTML[HTML.index("function maybePromptUpdate(info){"):HTML.index("function showUpdateDialog(")]
        self.assertIn("if(!info?.available||!info.latest||updateInstalling||updatePromptedFor===info.latest)return;",prompt)
        self.assertIn("showUpdateDialog(info);",prompt)
        self.assertIn("'Deseja atualizar agora? '",prompt)
        # Não abre sobre outro diálogo.
        for dialog in ("updateDialog","firstRunDialog","messageNoConnectionDialog"):
            self.assertIn(f"$('{dialog}')",prompt)

    def test_later_snoozes_same_version_for_24_hours(self):
        self.assertIn("const UPDATE_PROMPT_SNOOZE_MS=24*60*60*1000;",HTML)
        self.assertIn("localStorage.setItem('updatePromptSnooze.'+updatePromptedFor,String(Date.now()))",HTML)
        self.assertIn("$('updateApply').onclick=()=>{updatePromptOpen=false;beginUpdateDirect();};",HTML)


if __name__=="__main__":
    unittest.main()
