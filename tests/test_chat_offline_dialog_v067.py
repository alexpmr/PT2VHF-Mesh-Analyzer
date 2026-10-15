"""UX contract: clicking Enviar with no TX connection presents a useful popup."""
import unittest
from pathlib import Path

UI=(Path(__file__).resolve().parents[1]/"mesh_analyzer"/"ui.html").read_text(encoding="utf-8")

class NoRadioDialogTests(unittest.TestCase):
    def test_single_accessible_dialog_and_actions(self):
        for elem in ("messageNoConnectionDialog","messageNoConnectionText",
                     "messageNoConnectionClose","messageNoConnectionSettings"):
            self.assertEqual(UI.count('id="'+elem+'"'),1,elem)
        self.assertIn('aria-labelledby="messageNoConnectionTitle"',UI)
        self.assertIn('aria-modal="true"',UI)
        self.assertIn("Não há conexão ativa com um rádio Meshtastic para enviar mensagens.",UI)
        self.assertIn("Ir para Conexões",UI)
        self.assertIn("function showNoConnectionDialog()",UI)
        self.assertIn("showSettings('sources')",UI)
        self.assertIn("if(e.key==='Escape')",UI)

    def test_send_remains_clickable_to_explain_disconnected_radio(self):
        self.assertNotIn("$('messageSend').disabled=!choices.length||messageSending;",UI)
        self.assertIn("$('messageSend').disabled=messageSending;",UI)
        code=UI.split("$('messageSend').onclick=async()=>{",1)[1].split("$('messageText').onkeydown",1)[0]
        self.assertLess(code.index("if(!txRadioSources().length){showNoConnectionDialog();return;}"),
                        code.index("const original=$('messageText').value"))
        self.assertIn("if(!txRadioSources().some(x=>x.id===src)){showNoConnectionDialog();renderChat();return;}",code)
        self.assertIn("if(messageSending)return;",code)

    def test_draft_is_preserved_when_go_to_connections(self):
        dialog=UI.split("function showNoConnectionDialog(){",1)[1].split("function txRadioSources(){",1)[0]
        self.assertNotIn("$('messageText').value=''",dialog)
        self.assertIn("setView('settings')",dialog)
        self.assertIn("showSettings('sources')",dialog)
        self.assertIn("missingTxPreviousFocus",dialog)
        self.assertIn("buttons[0].focus()",dialog)

if __name__=="__main__":
    unittest.main()
