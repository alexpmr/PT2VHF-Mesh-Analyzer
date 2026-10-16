"""Regressions for map toolbar and honest message status indications."""
import unittest
from pathlib import Path
HTML=(Path(__file__).resolve().parents[1]/"mesh_analyzer"/"ui.html").read_text(encoding="utf-8")
class ToolbarAndMessageUX(unittest.TestCase):
 def test_no_map_source_dropdown(self):
  self.assertNotIn('id="mapSource"',HTML)
  self.assertNotIn("$('mapSource')",HTML)
  self.assertIn('id="mapVisibilityBtn"',HTML)
  for element in ('mapSearchInput','mapFit','mapRefresh'):
   self.assertIn('id="'+element+'"',HTML)
 def test_message_status_truthfulness(self):
  self.assertIn("m.state==='accepted_by_radio'",HTML)
  self.assertIn("'mesh_propagated','delivered','acknowledged'",HTML)
  self.assertIn('msgState accepted',HTML)
  self.assertIn('msgState delivered',HTML)
  self.assertIn('color:#34c759',HTML)
  self.assertIn('msgState working',HTML)
  self.assertIn('msgState error',HTML)
if __name__=="__main__":unittest.main()
