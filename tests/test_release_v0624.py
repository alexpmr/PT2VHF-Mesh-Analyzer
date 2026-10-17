"""Release 0.6.24 safety regressions for RF node deletion and map radar controls."""
from pathlib import Path
import json
import subprocess
import unittest

HTML=(Path(__file__).parents[1]/"mesh_analyzer/ui.html").read_text(encoding="utf-8")


def node_json(source):
    return json.loads(subprocess.check_output(["node","-e",source],timeout=15,text=True))


class Release0624Tests(unittest.TestCase):
    def test_bulk_deletion_is_sequential_and_reports_partial_failure(self):
        start=HTML.index("const nodeDeleteValidTargets=")
        end=HTML.index("async function deleteNodeFromRadioAndDatabase(",start)
        script=HTML[start:end]
        code=r"""
const els={nodesBulkLine:{hidden:true},nodesBulkResults:{hidden:true},
 nodesBulkStatus:{textContent:''},nodesBulkResultRows:{innerHTML:''},
 nodesBulkCancel:{disabled:false}};
const $=name=>els[name],esc=x=>String(x),idName=x=>'node-'+x;
const nodeSelectedIds=new Set([11,12]);
let activeNodeDeleteBulk=null,activeNodeBulk=null,deletingNode=false;
const state={sources:[{id:4,name:'Radio',kind:'serial',enabled:true}],
 connections:{'4':{status:'connected',local_node_num:3}}};
const confirm=()=>true,prompt=()=> 'APAGAR';
const calls=[],messages=[];
const notify=(message,err)=>messages.push(message);
const refreshAll=async()=>{};
const api=async(path,args)=>{calls.push(args.node_num);if(args.node_num===12)throw Error('timeout');return {success:true,radio_confirmed:true}};
""" + script + """
(async()=>{
  const guards=nodeDeleteValidTargets([3,11,11,12,0,4294967295],[3]);
  await deleteSelectedNodesBulk([11,12]);
  const result={guards,calls,selection:[...nodeSelectedIds],summary:els.nodesBulkStatus.textContent,
    details:els.nodesBulkResultRows.innerHTML,locked:deletingNode};
  console.log(JSON.stringify(result));
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        result=node_json(code)
        self.assertEqual(result["guards"],[11,12])
        self.assertEqual(result["calls"],[11,12])
        self.assertEqual(result["selection"],[12])
        self.assertIn("1/2",result["summary"])
        self.assertIn("timeout",result["details"])
        self.assertFalse(result["locked"])

    def test_radar_deactivation_invalidates_inflight_update(self):
        start=HTML.index("function applyRadarOpacity(){")
        end=HTML.index("function updateHillshade(){",start)
        code=r"""
const els={mapRadar:{checked:false},mapRadarOpacity:{value:'65'},
 mapRadarOpacityValue:{textContent:''},radarStatus:{textContent:''}};
const $=name=>els[name];
let radarLayer=null,lastRadarPath='',radarRequestGeneration=0,radarAbort=null,
 mapPreferencesReady=true,requestResolve=null,callCount=0,created=0;
const map={removeLayer(){radarLayer=null;}};
const L={tileLayer:(url,opt)=>{created++;return {addTo:()=>({setOpacity:x=>{}})}}};
const fetch=async()=>{callCount++;return new Promise(resolve=>{requestResolve=resolve;});};
""" + HTML[start:end] + """
(async()=>{
 await updateRadar();
 const initial=callCount;
 els.mapRadar.checked=true;
 const pending=updateRadar();
 els.mapRadar.checked=false;
 await updateRadar();
 requestResolve({ok:true,json:async()=>({host:'https://example.test',radar:{past:[{path:'/test',time:1}]}})});
 await pending;
 const race={initial,created,radar:radarLayer===null};
 els.mapRadarOpacity.value='30';
 applyRadarOpacity();
 console.log(JSON.stringify({...race,percentage:els.mapRadarOpacityValue.textContent,callCount}));
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        r=node_json(code)
        self.assertEqual(r["initial"],0)
        self.assertEqual(r["created"],0)
        self.assertTrue(r["radar"])
        self.assertEqual(r["percentage"],"30%")
        self.assertEqual(r["callCount"],1)

    def test_map_regressions_and_preferences(self):
        self.assertIn("width:200px;min-width:180px",HTML)
        self.assertIn("addEventListener('input',applyRadarOpacity)",HTML)
        self.assertIn("generation!==radarRequestGeneration",HTML)
        self.assertIn("mapPreferencesReady=false",HTML)
        self.assertIn("let visible=0,missing=0,hiddenBySearch=0,missingNode=0",HTML)
        self.assertIn("pontas sem coordenadas",HTML)
        self.assertIn("linhas desenhadas: ",HTML)
        self.assertIn("const nodeById=new Map",HTML)
        self.assertIn("deleteSelectedNodesBulk(selected)",HTML)
        self.assertIn("prompt('Operação destrutiva em lote.",HTML)
