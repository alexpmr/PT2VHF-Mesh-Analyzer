"""Behavioral Node.js and static regression checks for nodes bulk RF UI (#105)."""
import json
from pathlib import Path
import subprocess
import unittest

HTML = (Path(__file__).parents[1] / "mesh_analyzer" / "ui.html").read_text(encoding="utf-8")


def run_node(js):
    return json.loads(subprocess.check_output(["node", "-e", js], text=True, timeout=15))


class NodeBulkUIRegression(unittest.TestCase):
    def test_selection_and_bulk_flow_run_real_js(self):
        start = HTML.index("const nodeSelectedIds=new Set();")
        end = HTML.index("function renderNodes(){", start)
        script = HTML[start:end]
        # Keep unit tests fast: substitute only inter-TX intervals in the test VM.
        script = script.replace("NODE_BULK_GAP_MS=60000", "NODE_BULK_GAP_MS=3")
        script = script.replace("NODE_BULK_WAIT_MS=1500", "NODE_BULK_WAIT_MS=1")
        js = r"""
const elements={
 nodesRows:{querySelectorAll:()=>[]}, nodesSelectionCount:{textContent:''},
 nodesBulkLine:{hidden:true},nodesBulkStatus:{textContent:''},
 nodesBulkCancel:{disabled:false},
 nodesBulkResults:{hidden:true},nodesBulkResultRows:{innerHTML:''}
};
const $=id=>elements[id];
const nodes=[1,2,3,4,5].map(node_num=>({node_num}));
const RF_QUERY_TYPES=[['nodeinfo','NodeInfo'],['position','Posição'],
 ['telemetry','Telemetria'],['traceroute','Traceroute']];
const state={sources:[{id:8,name:'Radio',kind:'serial',enabled:true}],
 connections:{'8':{status:'connected',tx_capable:true,local_node_num:99}}};
let sent=[],notice=[],view='nodes';
const idName=n=>String(n);
const notify=(msg,error)=>notice.push({msg,error});
const confirm=()=>true;
const api=async(path,data)=>{
 if(path==='/api/queries/send'){
   sent.push({node:data.node,kind:data.kind});
   return {data:{request_id:'req-'+data.node}};
 }
 if(path.startsWith('/api/queries?node=')){
   const node=Number(path.split('=')[1]);
   return {data:[{request_id:'req-'+node,state:'replied'}]};
 }
 throw Error(path);
};
""" + script + r"""
(async()=>{
const single=nodeSelectionNext([], [1,2,3,4,5], 2,null,false,false);
const ctrl=nodeSelectionNext(single,[1,2,3,4,5],4,2,true,false);
const toggle=nodeSelectionNext(ctrl,[1,2,3,4,5],2,2,true,false);
const range=nodeSelectionNext(single,[1,2,3,4,5],5,2,false,true);
const addRange=nodeSelectionNext([1],[1,2,3,4,5],4,2,true,true);
nodeVisibleOrder=[2,4];nodeSelectedIds.add(1);
selectAllFilteredNodes();
const selectAll=[...nodeSelectedIds];
await startNodeBulk('nodeinfo',[1,2,2,3]);
const run1={sent:[...sent],state:elements.nodesBulkStatus.textContent,hidden:elements.nodesBulkLine.hidden};
sent=[];
state.sources.push({id:10,name:'Radio2',kind:'tcp',enabled:true});
state.connections['10']={status:'connected',tx_capable:true,local_node_num:90};
await startNodeBulk('position',[4,5]);
const ambiguous=sent.length===0&&notice.some(v=>v.msg.includes('exatamente um rádio'));
console.log(JSON.stringify({single,ctrl,toggle,range,addRange,selectAll,run1,ambiguous}));
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        r = run_node(js)
        self.assertEqual(r["single"], [2])
        self.assertEqual(r["ctrl"], [2, 4])
        self.assertEqual(r["toggle"], [4])
        self.assertEqual(r["range"], [2, 3, 4, 5])
        self.assertEqual(r["addRange"], [1, 2, 3, 4])
        self.assertEqual(r["selectAll"], [2, 4])
        self.assertEqual([x["node"] for x in r["run1"]["sent"]], [1, 2, 3])
        self.assertTrue(all(x["kind"] == "nodeinfo" for x in r["run1"]["sent"]))
        self.assertIn("3/3", r["run1"]["state"])
        self.assertIn("3 respostas", r["run1"]["state"])
        self.assertFalse(r["run1"]["hidden"])
        self.assertTrue(r["ambiguous"])

    def test_interaction_and_rf_guardrails(self):
        self.assertIn("el.onclick=ev=>selectNodeRow(id,ev)", HTML)
        self.assertIn("el.ondblclick=()=>", HTML)
        self.assertIn("nodeSelectAnchor=id", HTML)
        self.assertIn("selectAllFilteredNodes();", HTML)
        self.assertIn("if(!nodeSelectedIds.has(id))", HTML)
        self.assertIn("NODE_BULK_GAP_MS=60000", HTML)
        self.assertIn("NODE_BULK_REPLY_MS=35000", HTML)
        self.assertIn("await waitBulkReply(job,node,requestId)", HTML)
        self.assertIn("if(job.cancelled)break", HTML)
        self.assertIn("job.cancelled=true", HTML)
        self.assertIn("Não executa exclusão em massa", HTML)
        self.assertIn("NODE_BULK_HOURLY_CAP=6", HTML)
        self.assertIn("nodesBulkResultRows", HTML)
        self.assertIn("job.results.map", HTML)
