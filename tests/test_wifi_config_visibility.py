"""Additional regression checks for Wi-Fi configuration and map layout."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from mesh_analyzer.device_config import editable_fields, prepare_all
def make_radio():
    try:
        from meshtastic.protobuf import config_pb2
    except ImportError:
        from meshtastic import config_pb2
    node=SimpleNamespace(localConfig=config_pb2.Config())
    return SimpleNamespace(localNode=node)

HTML=(Path(__file__).resolve().parents[1]/"mesh_analyzer"/"ui.html").read_text(encoding="utf-8")

class WiFiAndMapChecks(unittest.TestCase):
    def test_wifi_secret_has_no_readback_and_is_editable(self):
        radio=make_radio()
        cfg=radio.localNode.localConfig
        fields={f.name for f in cfg.network.DESCRIPTOR.fields}
        self.assertIn("wifi_psk",fields,"Meshtastic SDK installed in CI must expose wifi_psk")
        cfg.network.wifi_psk="RadioSecret987"
        output=editable_fields(cfg)
        rows={r["name"]:r for r in output["network"]}
        self.assertIn("wifi_ssid",rows)
        self.assertIn("wifi_psk",rows)
        self.assertEqual(rows["wifi_psk"]["value"],"")
        self.assertTrue(rows["wifi_psk"]["configured"])
        self.assertEqual(rows["wifi_psk"]["type"],"secret")
        self.assertNotIn("RadioSecret987",str(output))

    def test_wifi_secret_visible_without_expanding_collapsed_network(self):
        self.assertIn("section.open=['device','lora','network'].includes(group)",HTML)
        self.assertIn("if(row.type==='secret')",HTML)
        self.assertIn("el.type='password'",HTML)
        self.assertIn("Senha configurada",HTML)

    def test_map_two_bars_still_separate_and_issue_95_remains_open(self):
        self.assertIn('id="playback"',HTML)
        self.assertIn('id="summaryNodes"',HTML)
        self.assertIn('id="mapVisibilityBtn"',HTML)

if __name__=="__main__":unittest.main()
