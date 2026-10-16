"""Regression: one map toolbar and safe automatic TX source selection."""
import unittest
from pathlib import Path
UI=(Path(__file__).resolve().parents[1]/"mesh_analyzer"/"ui.html").read_text(encoding="utf-8")
class ReleaseTests(unittest.TestCase):
    def test_single_toolbar_with_summary_metrics(self):
        start=UI.index('<section class="view active" id="viewMap">')
        toolbar=UI.index('<div id="playback">',start)
        summary=UI.index('<div id="summary">',toolbar)
        end=UI.index('</div>',summary)
        self.assertLess(summary,UI.index('id="mapVisibilityBtn"'))
        self.assertIn('id="summaryNodes"',UI[summary:toolbar+1500])
        self.assertIn('id="summaryLinks"',UI[summary:toolbar+1500])
        self.assertEqual(UI.count('id="summary"'),1)
        self.assertNotIn('id="messageSource"',UI)
    def test_tx_guard_multiple_radios(self):
        self.assertIn("if(choices.length>1)",UI)
        self.assertIn("Desative os demais",UI)
    def test_wifi_group_expanded(self):
        self.assertIn("section.open=['device','lora','network'].includes(group)",UI)
if __name__=="__main__":unittest.main()
