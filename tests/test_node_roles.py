import base64
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest

from mesh_analyzer.database import Database
from mesh_analyzer.node_roles import ROLES,normalize_role,decoded_user
from mesh_analyzer.transports import PacketIngestor

HTML=(Path(__file__).parents[1]/'mesh_analyzer/ui.html').read_text(encoding='utf-8')

class NodeRoleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Database(Path(self.tmp.name)/'n.db')
        self.ing=PacketIngestor(self.db)

    def tearDown(self):self.db.close();self.tmp.cleanup()

    def test_schema_roles_include_zero_and_unknown_is_not_client(self):
        from meshtastic.protobuf import config_pb2
        actual=[v.name for v in config_pb2.Config.DeviceConfig.Role.DESCRIPTOR.values]
        self.assertEqual(list(ROLES),actual)
        self.assertEqual(normalize_role(0),'CLIENT')
        self.assertEqual(normalize_role('0'),'CLIENT')
        self.assertEqual(normalize_role('client-base'),'CLIENT_BASE')
        for value in (None,'',False,True,99,'99','<script>','new_future_role'):
            self.assertIsNone(normalize_role(value))

    def test_snapshot_uses_each_nodes_role_including_client_zero(self):
        iface=SimpleNamespace(nodesByNum={100:{'user':{'longName':'Base','role':'CLIENT_BASE'},'lastHeard':1000},
            200:{'user':{'longName':'Client','role':0},'lastHeard':2000}})
        self.ing.seed_from_interface(1,iface)
        rows={n['node_num']:n for n in self.db.node_rows()}
        self.assertEqual(rows[100]['role'],'CLIENT_BASE');self.assertEqual(rows[200]['role'],'CLIENT')
        self.assertEqual(rows[100]['last_seen_ms'],1000000)

    def test_nodeinfo_wire_and_base64_persist_role_and_names(self):
        from meshtastic.protobuf import mesh_pb2
        for num,role in ((100,2),(200,0),(300,12)):
            msg=mesh_pb2.User(id=f'!{num:08x}',long_name='Node',role=role)
            payload=msg.SerializeToString()
            if num==200:payload=base64.b64encode(payload).decode()
            self.ing.handle(1,{'from':num,'id':num,'decoded':{'portnum':4,'payload':payload}})
        rows={n['node_num']:n for n in self.db.node_rows()}
        self.assertEqual([rows[n]['role'] for n in (100,200,300)],['ROUTER','CLIENT','CLIENT_BASE'])
        self.assertTrue(all(row['long_name']=='Node' for row in rows.values()))
        self.ing.handle(1,{'from':100,'id':101,'decoded':{'portnum':4,'user':{'longName':'Renamed'}}})
        self.assertEqual({n['node_num']:n for n in self.db.node_rows()}[100]['role'],'ROUTER')
        self.assertNotIn('role',decoded_user({'payload':b''}))

    def test_history_backfill_does_not_fake_reception_or_overwrite_known_role(self):
        self.db.upsert_node(100,1,timestamp_ms=1000)
        self.db.upsert_node(200,1,timestamp_ms=2000,role='CLIENT_BASE')
        for num in (100,200):
            raw={'decoded':{'user':{'role':'ROUTER'}}}
            self.db.add_packet({'source_id':1,'packet_id':str(num),'source_packet_key':str(num),
                'timestamp_ms':5000,'from_node':num,'port':'NODEINFO_APP','raw_json':json.dumps(raw)})
        self.assertEqual(self.db.recover_node_roles(),1)
        rows={n['node_num']:n for n in self.db.node_rows()}
        self.assertEqual((rows[100]['role'],rows[100]['last_seen_ms']),('ROUTER',1000))
        self.assertEqual((rows[200]['role'],rows[200]['last_seen_ms']),('CLIENT_BASE',2000))
        self.assertEqual(self.db.recover_node_roles(),0)

    def test_real_javascript_icons_are_unique_and_preserve_handlers(self):
        start=HTML.index('const NODE_ROLE_META=')
        end=HTML.index('function renderMap(){',start)
        js=HTML[start:end]+'''const L={divIcon:x=>x};
 const n=NODE_ROLE_META.map(([role])=>({role,svg:nodeRoleSvg(role,'#2ecc71')}));
 const meta=v=>nodeRoleMeta(v)[0];
 console.log(JSON.stringify({icons:n,zero:meta(0),text:meta('client_base'),unknown:meta('<img src=x>'),
 recent:nodeRoleIcon({role:'ROUTER',last_seen_ms:Date.now()}),old:nodeRoleIcon({role:'ROUTER',last_seen_ms:1})}));'''
        data=json.loads(subprocess.check_output(['node','-e',js],text=True))
        self.assertEqual(len(data['icons']),13)
        self.assertEqual(len(set(x['svg'] for x in data['icons'])),13)
        self.assertEqual((data['zero'],data['text'],data['unknown']),('CLIENT','CLIENT_BASE','UNKNOWN'))
        self.assertIn('#2ecc71',data['recent']['html']);self.assertIn('#e9a94d',data['old']['html'])
        self.assertEqual(data['recent']['iconAnchor'],[17,17])
        self.assertIn("marker.on('click',()=>{if(mapToolNodeClick(n))return;showNode(n);})",HTML)
        self.assertIn("marker.on('contextmenu'",HTML)
        self.assertIn('L.marker(point,{icon:nodeRoleIcon(n)',HTML)
