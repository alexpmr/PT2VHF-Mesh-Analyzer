"""Run the real map style functions, rather than mirroring them in Python."""
import json
import subprocess
import unittest
from pathlib import Path
from mesh_analyzer.updater import RUNNER_PS

HTML = (Path(__file__).parents[1]/'mesh_analyzer/ui.html').read_text(encoding='utf-8')

class ReleaseTests(unittest.TestCase):
    def test_rf_styles_and_transport_isolation(self):
        functions=HTML[HTML.index('function topologyLineStyle('):HTML.index('function renderMap(){')]
        js=functions+'''\nconst s=q=>topologyLineStyle({quality:q},'#ffff00',2,'#ff3322',3);
const result={flowRadio:communicationLineStyle({transport:'radio'},'#ffff00',2,'#ff3322',3),flowMqtt:communicationLineStyle({transport:'mqtt'},'#ffff00',2,'#ff3322',3),rf:['confirmed_direct_rf','observed_route_unverified_rf','neighbor_reported_unverified_rf'].map(s),
 mqtt:s('observed_route_mqtt_non_rf'), unknown:s('unknown'),
 reverse:topologyPairKey(1,2,3,'radio')===topologyPairKey(2,1,3,'radio'),
 source:topologyPairKey(1,2,3,'radio')!==topologyPairKey(1,2,4,'radio'),
 transport:topologyPairKey(1,2,3,'radio')!==topologyPairKey(1,2,3,'mqtt'),
 duplicate:isTopologyFlowDuplicate({from_node:2,to_node:1,source_id:3,transport:'radio'},new Set([topologyPairKey(1,2,3,'radio')])),
 keepInternet:!isTopologyFlowDuplicate({from_node:2,to_node:1,source_id:3,transport:'mqtt'},new Set([topologyPairKey(1,2,3,'radio')]))};
console.log(JSON.stringify(result));'''
        r=json.loads(subprocess.check_output(['node','-e',js],text=True))
        for style in r['rf']:
            self.assertEqual(style['color'],'#ffff00')
            self.assertIsNone(style['dashArray'])
        self.assertEqual(r['mqtt']['color'],'#ff3322')
        self.assertIsNotNone(r['mqtt']['dashArray'])
        self.assertIsNotNone(r['unknown']['dashArray'])
        self.assertTrue(r['reverse'] and r['source'] and r['transport'])
        self.assertTrue(r['duplicate'] and r['keepInternet'])
        self.assertEqual(r['flowRadio']['color'],'#ffff00')
        self.assertIsNone(r['flowRadio']['dashArray'])
        self.assertEqual(r['flowMqtt']['color'],'#ff3322')
        self.assertIsNotNone(r['flowMqtt']['dashArray'])

    def test_runner_resets_before_launch_and_waits_for_bootloader(self):
        self.assertLess(RUNNER_PS.index("$env:PYINSTALLER_RESET_ENVIRONMENT = '1'"),RUNNER_PS.index("$child = Start-Process"))
        self.assertIn('Executable still held by original onefile processes',RUNNER_PS)
        self.assertIn("('/DIR=\"' + $installDir",RUNNER_PS)
        self.assertIn('update-setup.log',RUNNER_PS)
