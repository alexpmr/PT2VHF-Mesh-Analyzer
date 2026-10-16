"""Connection configuration UX checks (no real radio needed)."""
import unittest
from pathlib import Path
HTML=(Path(__file__).resolve().parents[1]/"mesh_analyzer"/"ui.html").read_text(encoding="utf-8")

class AutomaticConnectionUX(unittest.TestCase):
    def test_source_form_initially_hidden_when_saved_connections_exist(self):
        self.assertIn("id=\"sourceFormCard\"",HTML)
        self.assertIn("card.hidden=sources.length>0",HTML)
        self.assertIn("if(card&&!$('sourceId').value)",HTML)

    def test_edit_or_manual_add_reveals_form(self):
        self.assertIn("id=\"sourceAddManual\"",HTML)
        self.assertIn("$('sourceAddManual').onclick",HTML)
        self.assertIn("function editSource(id)",HTML)
        self.assertIn("$('sourceFormCard').hidden=false",HTML)

    def test_automatic_discovery_manual_review(self):
        self.assertIn("Configuração Automática</button>",HTML)
        self.assertIn("/api/discovery/start",HTML)
        self.assertIn("Não verificado pelo protocolo",HTML)
        self.assertIn("$('sourceEnabled').checked=false",HTML)

if __name__=="__main__":unittest.main()
