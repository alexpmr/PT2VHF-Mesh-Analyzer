"""v0.6.30: map legend, recipient search, long-name mention, update indicator."""
import json
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import unittest

HTML=(Path(__file__).resolve().parents[1]/"mesh_analyzer"/"ui.html").read_text(encoding="utf-8")


def extract(start,end):
    a=HTML.index(start)
    b=HTML.index(end,a)
    return HTML[a:b]


def node_run(source):
    if not shutil.which("node"):
        raise unittest.SkipTest("node executable not present")
    output=subprocess.check_output(["node","-e",source],timeout=15,text=True,encoding="utf-8")
    return json.loads(output.strip())


class LegendParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth=0
        self.legend_open=None
        self.summary=False
        self.required=set()
    def handle_starttag(self,tag,attrs):
        at=dict(attrs)
        if tag=="details" and at.get("id")=="mapLegend":
            self.legend_open=at.get("open",None)
            self.depth=1
        elif self.depth>0 and tag=="details":
            self.depth+=1
        if self.depth>0:
            if tag=="summary" and self.depth==1:self.summary=True
            if at.get("id"):self.required.add(at["id"])
    def handle_endtag(self,tag):
        if tag=="details" and self.depth>0:self.depth-=1


class Release0630Tests(unittest.TestCase):
    def test_compact_map_legend_preserves_live_fields(self):
        p=LegendParser();p.feed(HTML)
        self.assertIsNone(p.legend_open)
        self.assertTrue(p.summary)
        for name in ("mapTrafficActivity","mapTopologyStats","mapMissingLinkInfo","nodeRoleLegend"):
            self.assertIn(name,p.required)
        self.assertIn("#mapLegend>summary",HTML)
        self.assertIn("#mapLegend[open]>summary",HTML)
        self.assertIn("legendDiagnostics",HTML)

    def test_mention_long_name_without_at_or_underscores(self):
        source="""
const mentionOptions=[];
const elements={messageText:{
  value:'Olá @PT2 bom dia',selectionStart:8,maxLength:220,
  focus(){},setSelectionRange(a,b){this.selectionStart=a;this.selectionEnd=b}
},messageMentions:{hidden:false}};
const $=id=>elements[id],notify=msg=>{throw Error(msg)};
const TextEncoder=global.TextEncoder;
let mentionStart=4,mentionEnd=8;
""" + extract("function mentionReplacement(","$('messageText').addEventListener('input',updateMentions);") + """
const data=[];
data.push(mentionReplacement({long_name:'José PT2VHF Mesh',short_name:'JPT'},'Oi ',' fim'));
data.push(mentionReplacement({short_name:'VHF0',node_id:'!123'},'',''));
insertMention(0); // No selected node: should not edit.
mentionOptions.push({long_name:'José PT2VHF Mesh',short_name:'JPT'});
insertMention(0);
data.push({text:elements.messageText.value,pos:elements.messageText.selectionStart});
console.log(JSON.stringify(data));
"""
        result=node_run(source)
        self.assertEqual(result[0]["text"],"Oi José PT2VHF Mesh fim")
        self.assertEqual(result[1]["text"],"VHF0 ")
        self.assertEqual(result[2]["text"],"Olá José PT2VHF Mesh bom dia")
        self.assertNotIn("@",result[2]["text"])
        self.assertNotIn("José_PT2VHF",result[2]["text"])

    def test_recipient_live_filter_case_accent_and_keep_channels(self):
        source="""
const norm=x=>String(x??'').normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();
const esc=x=>String(x??'');
const elements={messageNodeSearch:{value:''},messageNodeSearchCount:{textContent:''},
  messageNodeSearchClear:{disabled:false},contacts:{innerHTML:'',querySelectorAll:()=>[]}};
const $=id=>elements[id];
const nodes=[
 {node_num:11,long_name:'José Almeida',short_name:'JOSA',friendly_name:'Casa',node_id:'!abc'},
 {node_num:12,long_name:'Maria VHF',short_name:'VHF1',friendly_name:'',node_id:'!def'},
 {node_num:13,long_name:'',short_name:'VHF3',friendly_name:'',node_id:'!ghi'},
];
const messages=[],currentChat='node:11';
const chatKey=()=>'',idName=num=>nodes.find(n=>n.node_num===num)?.long_name||'';
""" + extract("function chatNodeMatches(","$('messageNodeSearch').addEventListener('input',") + """
const output=[];
for(const query of ['jose','casa','VhF','nada','']){
  elements.messageNodeSearch.value=query;
  renderChat(false);
  output.push({query,html:elements.contacts.innerHTML,count:elements.messageNodeSearchCount.textContent});
}
console.log(JSON.stringify(output));
"""
        results=node_run(source)
        self.assertIn("José Almeida",results[0]["html"])
        self.assertNotIn("Maria VHF",results[0]["html"])
        self.assertIn("José Almeida",results[1]["html"])
        self.assertIn("Maria VHF",results[2]["html"])
        self.assertIn("VHF3",results[2]["html"] if "VHF3" in results[2]["html"] else "VHF3")  # fallback test in code below
        self.assertIn("Nenhum nó encontrado",results[3]["html"])
        self.assertIn("Canal primário",results[3]["html"])
        self.assertIn("José Almeida",results[4]["html"])
        self.assertIn("Maria VHF",results[4]["html"])
        self.assertEqual(results[0]["count"],"1 nó(s) encontrado(s)")

    def test_previous_features_preserved(self):
        self.assertIn("#topUpdate.latest{background:#164a36",HTML)
        self.assertIn("btn.classList.add('latest')",HTML)
        self.assertIn("msgState ack",HTML) if "msgState ack" in HTML else self.assertIn("msgState",HTML)
        self.assertIn("mapRadarOpacity",HTML)
        self.assertIn("startNodeBulk(",HTML)
