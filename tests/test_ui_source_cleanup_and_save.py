"""Source selector simplification and device dirty state regression."""
import unittest
from pathlib import Path
UI=(Path(__file__).resolve().parents[1]/"mesh_analyzer"/"ui.html").read_text(encoding="utf-8")
class UIRegression(unittest.TestCase):
 def test_removes_requested_source_selectors_without_null_access(self):
  for element in ("messageSource","trafficSource","statsSource"):
   self.assertNotIn(element,UI)
  self.assertIn('id="messageChannel"',UI)
  self.assertIn('id="trafficType"',UI)
  self.assertIn("source:'all'",UI)
 def test_ambiguous_transmitter_blocks_send(self):
  self.assertIn("if(choices.length>1)",UI)
  self.assertIn("const src=Number(choices[0].id)",UI)
  self.assertIn("showNoConnectionDialog();renderChat();return;",UI)
 def test_device_save_activation_tracks_edits(self):
  self.assertIn("form.oninput=updateDirty;form.onchange=updateDirty",UI)
  self.assertIn("$('loraSave').disabled=!dirty",UI)
  self.assertIn("if(row.type==='secret'){if(el.value)dirty=true;}",UI)
if __name__=="__main__":unittest.main()
