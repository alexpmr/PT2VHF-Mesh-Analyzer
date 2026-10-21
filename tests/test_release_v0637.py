"""v0.6.37: detecção de rádios (#149), adicionar automaticamente (#151) e seletor do rádio ativo (#152)."""
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from mesh_analyzer.database import Database
from mesh_analyzer.device_detection import AutoAdd, DeviceWatcher, Registry, device_key, probe
from mesh_analyzer.transports import SourceManager

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"mesh_analyzer"/"ui.html").read_text(encoding="utf-8")


def wait_until(check,seconds=6):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if check():return True
        time.sleep(.02)
    return check()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Database(Path(self.tmp.name)/"t.sqlite3")

    def tearDown(self):
        self.db.close();self.tmp.cleanup()

    def tcp(self,name,host,enabled=True):
        return self.db.upsert_source({"name":name,"kind":"tcp","config":{"host":host},"enabled":enabled})["id"]


def fake_tcp(fail_hosts=()):
    class Radio:
        def __init__(self,hostname,**kwargs):
            if hostname in fail_hosts:raise OSError("sem resposta")
            self.hostname=hostname;self.closed=False
            self.localNode=SimpleNamespace(nodeNum=abs(hash(hostname))%10000+1)
            self.nodesByNum={}
        def close(self):self.closed=True
    return Radio


class ActiveRadioSelector(Base):
    def manager(self):
        m=SourceManager(self.db);m.RETRY_WAIT_S=0.2
        return m

    def stop(self,m):
        m._stop.set()
        for t in list(m._threads.values()):t.join(3)

    def status(self,m,sid):
        return m.snapshot().get(str(sid),{}).get("status")

    def test_preferred_radio_wins_at_startup(self):
        a,b=self.tcp("A","a"),self.tcp("B","b")
        self.db.set_preferred_radio(b)
        m=self.manager()
        with patch("meshtastic.tcp_interface.TCPInterface",fake_tcp()),patch.object(m,"_ensure_pubsub"):
            m.start()
            self.assertTrue(wait_until(lambda:m.active_radio() is not None))
            self.assertEqual(m.active_radio(),b)
            self.stop(m)

    def test_switch_to_other_radio(self):
        a,b=self.tcp("A","a"),self.tcp("B","b")
        self.db.set_preferred_radio(a)
        m=self.manager()
        with patch("meshtastic.tcp_interface.TCPInterface",fake_tcp()),patch.object(m,"_ensure_pubsub"):
            m.start()
            self.assertTrue(wait_until(lambda:m.active_radio()==a))
            self.assertEqual(m.activate(b)["state"],"switching")
            self.assertTrue(wait_until(lambda:m.switch_status()["phase"]=="done"))
            self.assertEqual(m.active_radio(),b)
            self.assertEqual(self.db.preferred_radio(),b)
            self.assertTrue(wait_until(lambda:self.status(m,a)=="standby"))
            with m._lock:self.assertEqual(list(m._interfaces),[b])
            self.stop(m)

    def test_failed_switch_returns_to_previous_radio(self):
        a,b=self.tcp("A","a"),self.tcp("B","b")
        self.db.set_preferred_radio(a)
        m=self.manager()
        with patch("meshtastic.tcp_interface.TCPInterface",fake_tcp(fail_hosts=("b",))),patch.object(m,"_ensure_pubsub"):
            m.start()
            self.assertTrue(wait_until(lambda:m.active_radio()==a))
            m.activate(b)
            self.assertTrue(wait_until(lambda:m.switch_status()["phase"]=="failed"))
            self.assertIn("sem resposta",m.switch_status()["error"])
            self.assertTrue(wait_until(lambda:m.active_radio()==a))
            self.assertEqual(self.db.preferred_radio(),a)
            self.stop(m)

    def test_mqtt_and_disabled_cannot_be_activated(self):
        m=self.manager()
        q=self.db.upsert_source({"name":"Q","kind":"mqtt","config":{"host":"h","topic":"msh/#"},"enabled":True})["id"]
        off=self.tcp("Off","x",enabled=False)
        with self.assertRaises(ValueError):m.activate(q)
        with self.assertRaises(ValueError):m.activate(off)

    def test_available_lists_only_active_and_present(self):
        server=socket.socket();server.bind(("127.0.0.1",0));server.listen()
        closed=socket.socket();closed.bind(("127.0.0.1",0));closed_port=closed.getsockname()[1];closed.close()
        try:
            up=self.db.upsert_source({"name":"WiFi up","kind":"tcp","config":{"host":"127.0.0.1","port":server.getsockname()[1]},"enabled":True})["id"]
            self.db.upsert_source({"name":"WiFi down","kind":"tcp","config":{"host":"127.0.0.1","port":closed_port},"enabled":True})
            self.tcp("Off","127.0.0.1",enabled=False)
            usb=self.db.upsert_source({"name":"USB","kind":"serial","config":{"port":"COM5"},"enabled":True})["id"]
            self.db.upsert_source({"name":"USB fora","kind":"serial","config":{"port":"COM9"},"enabled":True})
            ble=self.db.upsert_source({"name":"BLE","kind":"ble","config":{"address":"AA:BB"},"enabled":True})["id"]
            self.db.upsert_source({"name":"BLE longe","kind":"ble","config":{"address":"CC:DD"},"enabled":True})
            err=self.db.upsert_source({"name":"Erro","kind":"serial","config":{"port":"COM7"},"enabled":True})["id"]
            m=self.manager()
            m._set(err,"error","falhou")
            ports=[SimpleNamespace(device=x) for x in ("COM5","COM7")]
            with patch("serial.tools.list_ports.comports",return_value=ports):
                names={r["name"] for r in m.available_radios(ble_seen=["aa:bb"])}
            self.assertEqual(names,{"WiFi up","USB","BLE"})
        finally:
            server.close()


class Detection(Base):
    def setUp(self):
        super().setUp()
        self.sources=Mock()
        self.sources.snapshot.return_value={}
        self.sources.active_radio.return_value=None
        self.ports=[]
        self.probed=[]

    def prober(self,candidate):
        self.probed.append(candidate["address"])
        if candidate["address"]=="COM9":return {"ok":False,"error":"Timed out"}
        return {"ok":True,"node_num":100+len(self.probed),"long_name":"Rádio "+candidate["address"],"short_name":"R"}

    def watcher(self):
        w=DeviceWatcher(self.db,self.sources,prober=self.prober,usb=lambda:list(self.ports),ble=lambda **k:[])
        w._stop.wait=lambda seconds:False
        return w

    def port(self,name):
        return {"kind":"serial","address":name,"name":"USB Serial "+name,"config":{"port":name}}

    def test_usb_plug_offers_verified_radio_and_accept_adds_connected(self):
        self.ports=[self.port("COM3")]
        w=self.watcher();w._check_usb()
        self.assertEqual(w.notices(),[])  # já presente ao iniciar: linha de base
        self.ports.append(self.port("COM5"));w._check_usb()
        notice=w.notices()[0]
        self.assertEqual((notice["address"],notice["name"],notice["verified"]),("COM5","Rádio COM5",True))
        out=w.accept(notice["id"])
        src=self.db.source(out["source"]["id"])
        self.assertTrue(src["enabled"])
        self.assertEqual(src["config"]["port"],"COM5")
        self.assertIn("node_num",src["config"])
        self.sources.connect.assert_called_once_with(src["id"])
        self.assertEqual(w.notices(),[])
        self.assertFalse(out["other_active"])

    def test_non_meshtastic_port_is_not_offered(self):
        w=self.watcher();w._check_usb()
        self.ports=[self.port("COM9")];w._check_usb()
        self.assertEqual(w.notices(),[])

    def test_configured_port_is_never_opened(self):
        self.db.upsert_source({"name":"Meu","kind":"serial","config":{"port":"COM5"},"enabled":True})
        w=self.watcher();w._check_usb()
        self.ports=[self.port("COM5")];w._check_usb()
        self.assertEqual(self.probed,[])

    def test_never_persists_and_later_waits_for_replug(self):
        w=self.watcher();w._check_usb()
        self.ports=[self.port("COM5"),self.port("COM6")];w._check_usb()
        by={n["address"]:n["id"] for n in w.notices()}
        w.dismiss(by["COM5"],never=True);w.dismiss(by["COM6"])
        self.assertIn(device_key("serial","COM5"),self.db.ignored_devices())
        self.ports=[];w._check_usb()
        self.ports=[self.port("COM5"),self.port("COM6")];w._check_usb()
        self.assertEqual([n["address"] for n in w.notices()],["COM6"])

    def test_accept_when_other_radio_active_reports_standby(self):
        self.sources.active_radio.return_value=999
        w=self.watcher();w._check_usb()
        self.ports=[self.port("COM5")];w._check_usb()
        self.assertTrue(w.accept(w.notices()[0]["id"])["other_active"])

    def test_autodetect_preference_per_type(self):
        self.db.set_system_settings({"device_autodetect":{"serial":False}})
        self.assertEqual(self.db.system_settings()["device_autodetect"],{"serial":False,"tcp":True,"ble":True})
        w=self.watcher();w._check_usb()
        self.ports=[self.port("COM5")];w._check_usb()
        self.assertEqual(w.notices(),[])
        with self.assertRaises(ValueError):
            self.db.set_system_settings({"device_autodetect":{"usb":True}})

    def test_auto_add_adds_new_verified_radios_once(self):
        self.db.upsert_source({"name":"Meu","kind":"serial","config":{"port":"COM3"},"enabled":True})
        usb=lambda:[self.port("COM3"),self.port("COM5"),self.port("COM9")]
        mdns=lambda seconds:[{"kind":"tcp","address":"192.168.0.20","name":"node","config":{"host":"192.168.0.20","port":4403}}]
        def ble(**kwargs):raise OSError("Bluetooth desligado")
        auto=AutoAdd(self.db,self.sources,prober=self.prober,usb=usb,ble=ble,mdns=mdns)
        auto.run()
        outcome={r["address"]:r["outcome"] for r in auto.status()["results"]}
        self.assertEqual(outcome,{"COM3":"configured","COM5":"added","COM9":"no_response","192.168.0.20":"added"})
        self.assertIn("Bluetooth",auto.status()["errors"][0])
        self.assertEqual(len(self.db.sources()),3)
        auto.run()
        self.assertEqual(len(self.db.sources()),3)
        self.assertEqual({r["outcome"] for r in auto.status()["results"]},{"configured","no_response"})

    def test_same_radio_on_other_transport_is_not_duplicated(self):
        self.db.upsert_source({"name":"Meu","kind":"tcp","config":{"host":"h","node_num":101},"enabled":True})
        registry=Registry(self.db,self.sources)
        with self.assertRaises(LookupError):
            registry.add(self.port("COM5"),{"node_num":101,"long_name":"Meu"})

    def test_probe_reads_identity_and_always_closes(self):
        closed=[]
        class Iface:
            def getMyNodeInfo(self):return {"num":42,"user":{"longName":"VHF3","shortName":"V3"}}
            def close(self):closed.append(True)
        info=probe(self.port("COM5"),opener=lambda c:Iface())
        self.assertEqual((info["ok"],info["node_num"],info["long_name"]),(True,42,"VHF3"))
        def boom(c):raise TimeoutError("Timed out waiting for connection completion")
        self.assertFalse(probe(self.port("COM5"),opener=boom)["ok"])
        self.assertEqual(closed,[True])


class Interface(unittest.TestCase):
    def test_buttons_and_selector_present(self):
        self.assertIn('id="sourceAddManual">Adicionar conexão manualmente</button><button type="button" id="sourceAddAuto"',HTML)
        self.assertIn(">Detectar automaticamente</button>",HTML)
        self.assertIn('id="radioMenu"',HTML)
        self.assertIn("api('/api/radios/available')",HTML)
        self.assertIn("api('/api/devices/accept',{id})",HTML)
        self.assertIn("Nunca para este dispositivo",HTML)


if __name__=="__main__":
    unittest.main()
