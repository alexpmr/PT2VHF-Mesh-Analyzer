"""Regression tests for correct Meshtastic protobuf ports and source-scoped map."""
import base64
import json
import tempfile
import unittest
from pathlib import Path

from mesh_analyzer.database import Database,now_ms
from mesh_analyzer.transports import PacketIngestor,port_name
from mesh_analyzer.topology import extract_topology


class TopologyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Database(Path(self.temp.name)/"topology.db")
        self.ing=PacketIngestor(self.db)

    def tearDown(self):
        self.db.close();self.temp.cleanup()

    def test_actual_official_meshtastic_portnums(self):
        self.assertEqual(port_name(67),"TELEMETRY_APP")
        self.assertEqual(port_name(70),"TRACEROUTE_APP")
        self.assertEqual(port_name(71),"NEIGHBORINFO_APP")
        self.assertEqual(port_name(65),"STORE_FORWARD_APP")

    def test_protobuf_route_forward_and_back(self):
        from meshtastic.protobuf import mesh_pb2
        msg=mesh_pb2.RouteDiscovery()
        msg.route.extend([200])
        msg.route_back.extend([400])
        packet={"from":300,"to":100,"id":882,"rxTime":int(now_ms()/1000),
                "decoded":{"portnum":70,"payload":msg.SerializeToString()}}
        self.assertTrue(self.ing.handle(1,packet))
        link=self.db.link_rows()
        self.assertEqual({(e["a"],e["b"]) for e in link},
                         {(100,200),(200,300),(100,400),(300,400)})
        self.assertTrue(all(e["quality"]=="observed_route_unverified_rf" for e in link))
        self.assertEqual(self.db.stats()["traces"],1)
        self.assertFalse(self.ing.handle(1,packet))  # unique reception
        self.assertEqual(self.db.stats()["links"],4)
        self.assertEqual(self.db.stats()["traces"],1)

    def test_invalid_intermediate_does_not_connect_across_gap(self):
        # Traffic Analyzer semantics: an unknown intermediate breaks the leg.
        packet={"from":300,"to":100,"id":880,
                "decoded":{"portnum":70,"route":[200,0xffffffff,400]}}
        self.assertTrue(self.ing.handle(1,packet))
        links={(x["a"],x["b"]) for x in self.db.link_rows()}
        self.assertEqual(links,{(100,200),(300,400)})
        self.assertNotIn((200,400),links)

    def test_forward_return_asymmetry_preserved(self):
        packet={"from":300,"to":100,"id":881,"decoded":{
                 "portnum":"TRACEROUTE_APP","route":[200],
                 "routeBack":[500,600]}}
        self.assertTrue(self.ing.handle(1,packet))
        links={(x["a"],x["b"]) for x in self.db.link_rows()}
        self.assertEqual(links,{(100,200),(200,300),(300,500),
                                (500,600),(100,600)})

    def test_snr_without_intermediates_must_not_fabricate_direct_rf(self):
        packet={"from":300,"to":100,"id":883,"decoded":{
                 "portnum":"TRACEROUTE_APP","route":[],
                 "snrTowards":[26],"snrBack":[28]}}
        self.assertTrue(self.ing.handle(1,packet))
        self.assertEqual(self.db.link_rows(),[])

    def test_full_pipeline_archived_trace_sqlite_and_api(self):
        from http.server import ThreadingHTTPServer
        from mesh_analyzer.app import build_handler
        from mesh_analyzer.transports import SourceManager
        import threading,urllib.request
        # Source positions must already exist to draw an edge.
        for num,lat,lon in [(100,-15.80,-47.80),(200,-15.82,-47.82),(300,-15.84,-47.84)]:
            self.db.upsert_node(num,1,timestamp_ms=now_ms(),observed=True,
                                latitude=lat,longitude=lon)
        packet={"from":300,"to":100,"id":990,"decoded":{
                 "portnum":"TRACEROUTE_APP","route":[200]}}
        self.assertTrue(self.ing.handle(1,packet))
        self.assertEqual(self.db.topology_diagnostics()["drawable"],2)
        mgr=SourceManager(self.db)
        server=ThreadingHTTPServer(("127.0.0.1",0),
            build_handler(self.db,mgr,"csrf","<html/>"))
        worker=threading.Thread(target=server.serve_forever,daemon=True)
        worker.start()
        try:
            base="http://127.0.0.1:"+str(server.server_address[1])
            with urllib.request.urlopen(base+"/api/links") as rsp:
                edges=json.load(rsp)["data"]
            with urllib.request.urlopen(base+"/api/nodes") as rsp:
                known=json.load(rsp)["data"]
            lookup={n["node_num"]:n for n in known}
            self.assertEqual(len(edges),2)
            self.assertEqual({(e["a"],e["b"]) for e in edges},
                             {(100,200),(200,300)})
            self.assertTrue(all(lookup[e["a"]]["latitude"] is not None and
                                lookup[e["b"]]["longitude"] is not None for e in edges))
        finally:
            server.shutdown();server.server_close();worker.join(timeout=2)
            mgr.close()

    def test_missing_position_explains_undrawable_edges(self):
        packet={"from":300,"to":100,"id":991,"decoded":{
                 "portnum":"TRACEROUTE_APP","route":[200]}}
        self.ing.handle(1,packet)
        diag=self.db.topology_diagnostics()
        self.assertEqual(diag["stored"],2)
        self.assertEqual(diag["drawable"],0)
        self.assertEqual(diag["missing_positions"],2)

    def test_traffic_packet_direction_and_legacy_rx(self):
        self.db.add_packet({"source_id":1,"packet_id":"tx1","source_packet_key":"tx:1:one",
            "timestamp_ms":now_ms(),"from_node":100,"to_node":200,
            "port":"NODEINFO_APP","direction":"tx"})
        self.db.add_packet({"source_id":1,"packet_id":"rx1","source_packet_key":"rx:1:one",
            "timestamp_ms":now_ms(),"from_node":200,"to_node":100,
            "port":"NODEINFO_APP"})
        packets=self.db.packet_rows()
        self.assertEqual(len(packets),2)
        self.assertEqual({(p["from_node"],p["to_node"],p["direction"]) for p in packets},
                         {(100,200,"tx"),(200,100,"rx")})

    def test_telemetry_is_not_traceroute(self):
        self.ing.handle(1,{"from":100,"to":200,"id":10,
             "decoded":{"portnum":67,"route":[150],"telemetry":{"deviceMetrics":{"batteryLevel":67}}}})
        self.assertEqual(self.db.stats()["links"],0)
        self.assertEqual(self.db.stats()["traces"],0)

    def test_empty_route_does_not_make_direct_link(self):
        self.ing.handle(1,{"from":300,"to":100,"id":1,
            "decoded":{"portnum":"TRACEROUTE_APP","route":[]}})
        self.assertEqual(self.db.stats()["links"],0)

    def test_neighbor_reported_not_directly_confirmed(self):
        pkt={"from":100,"to":0xffffffff,"id":78,
             "decoded":{"portnum":71,"neighborinfo":{"neighbors":[{"nodeId":200},{"nodeId":300}]}}}
        self.ing.handle(1,pkt)
        self.assertEqual(self.db.stats()["links"],2)
        self.assertEqual({x["quality"] for x in self.db.link_rows()},
                         {"neighbor_reported_unverified_rf"})

    def test_source_scoped_nodes_and_no_coordinates_diagnostic(self):
        self.ing.handle(1,{"from":100,"to":0xffffffff,"id":21,
            "decoded":{"portnum":1,"text":"hi"}})
        self.ing.handle(2,{"from":200,"to":0xffffffff,"id":22,
            "decoded":{"portnum":1,"text":"hi"}})
        seen={(s["source_id"],s["node_num"]) for s in self.db.node_source_rows() if s["observed"]}
        self.assertIn((1,100),seen);self.assertIn((2,200),seen)
        self.assertNotIn((1,200),seen)
        self.ing.handle(1,{"from":100,"to":300,"id":23,
            "decoded":{"portnum":70,"route":[200]}})
        d=self.db.topology_diagnostics(1)
        self.assertEqual(d["stored"],2)
        self.assertEqual(d["drawable"],0)
        self.assertEqual(d["missing_positions"],2)

    def test_old_archived_traceroute_replay_is_idempotent(self):
        from meshtastic.protobuf import mesh_pb2
        m=mesh_pb2.RouteDiscovery();m.route.extend([200])
        pkt={"from":300,"to":100,"id":34,
            "decoded":{"portnum":70,"payload":{"base64":base64.b64encode(m.SerializeToString()).decode()}}}
        payload={"source_id":1,"source_packet_key":"old-trace","packet_id":"34",
                 "timestamp_ms":now_ms(),"from_node":300,"to_node":100,
                 "port":"TRACEROUTE_APP","raw_json":json.dumps(pkt)}
        self.assertTrue(self.db.add_packet(payload))
        one=self.db.reprocess_archived_topology(extract_topology)
        self.assertEqual(one["processed"],1)
        self.assertEqual(self.db.stats()["links"],2)
        two=self.db.reprocess_archived_topology(extract_topology)
        self.assertEqual(two["processed"],0)
        self.assertEqual(self.db.stats()["links"],2)


if __name__=="__main__":unittest.main()
