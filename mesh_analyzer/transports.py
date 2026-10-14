"""Native Meshtastic Serial/TCP/BLE and read-only Meshtastic MQTT ingestion."""
from __future__ import annotations

import base64
import hashlib
import json
import threading
import time
from typing import Any

from .database import Database, now_ms


def number(value):
    if value is None or value == "": return None
    try:
        if isinstance(value,str) and value.startswith("!"):
            return int(value[1:],16)
        return int(value)
    except (ValueError,TypeError,OverflowError): return None


def port_name(value):
    if isinstance(value,str): return value
    ports = {1:"TEXT_MESSAGE_APP",3:"POSITION_APP",4:"NODEINFO_APP",5:"ROUTING_APP",6:"ADMIN_APP",67:"TRACEROUTE_APP",65:"TELEMETRY_APP"}
    return ports.get(number(value),str(value or "UNKNOWN"))


def _json_safe(value):
    if isinstance(value,bytes): return {"base64":base64.b64encode(value[:1024]).decode(),"byte_count":len(value)}
    if isinstance(value,dict): return {str(k):_json_safe(v) for k,v in list(value.items())[:60]}
    if isinstance(value,(list,tuple)): return [_json_safe(v) for v in value[:60]]
    if isinstance(value,(int,float,str,bool)) or value is None:return value
    return str(value)[:240]


def _parse_text(decoded):
    val=decoded.get("text")
    if isinstance(val,str):return val
    if isinstance(val,bytes):return val.decode("utf-8","replace")
    data=decoded.get("payload")
    if isinstance(data,bytes):return data.decode("utf-8","replace")
    return ""


def position_from_decoded(decoded):
    d=decoded.get("position") if isinstance(decoded.get("position"),dict) else None
    if not d:return None
    lat=d.get("latitude")
    lon=d.get("longitude")
    if lat is None: lat=d.get("latitudeI")
    if lon is None: lon=d.get("longitudeI")
    if lat is None: lat=d.get("latitude_i")
    if lon is None: lon=d.get("longitude_i")
    try:
        lat=float(lat);lon=float(lon)
        if abs(lat)>90 or abs(lon)>180:lat/=1e7;lon/=1e7
        if not (-90<=lat<=90 and -180<=lon<=180) or (abs(lat)<.01 and abs(lon)<.01):return None
    except (TypeError,ValueError):return None
    return lat,lon,d.get("altitude")


class PacketIngestor:
    def __init__(self,db:Database):self.db=db

    def seed_from_interface(self,source_id,interface):
        try:
            rows=getattr(interface,"nodesByNum",{}) or {}
            for k,n in dict(rows).items():
                if not isinstance(n,dict):continue
                user=n.get("user") if isinstance(n.get("user"),dict) else {}
                pos=n.get("position") if isinstance(n.get("position"),dict) else {}
                num=number(k)
                if num is None: continue
                position=position_from_decoded({"position":pos})
                values={"long_name":user.get("longName") or user.get("long_name"),"short_name":user.get("shortName") or user.get("short_name"),
                        "hw_model":user.get("hwModel") or user.get("hw_model"),"snr":n.get("snr")}
                if position:values.update(latitude=position[0],longitude=position[1],altitude=position[2])
                # Radio-provided cached NodeDB is NOT live evidence. Preserve the
                # recorded lastHeard; unknown means never heard in this session.
                raw_seen=n.get("lastHeard") or n.get("last_heard") or 0
                try:
                    seen=int(float(raw_seen));seen=seen*1000 if 0<seen<10_000_000_000 else seen
                except (TypeError,ValueError):seen=0
                self.db.upsert_node(num,source_id,timestamp_ms=seen,**values)
        except Exception:
            self.db.log("Não foi possível importar o catálogo inicial do rádio", "warning",source_id)

    def handle(self,source_id:int,packet:dict,via_mqtt=False):
        if not isinstance(packet,dict):return False
        decoded=packet.get("decoded") if isinstance(packet.get("decoded"),dict) else {}
        from_num=number(packet.get("from") if "from" in packet else packet.get("fromId"))
        to_num=number(packet.get("to") if "to" in packet else packet.get("toId"))
        raw_ts=packet.get("rxTime") or packet.get("rx_time") or packet.get("timestamp") or now_ms()
        try: ts=int(float(raw_ts));ts=ts*1000 if ts<10_000_000_000 else ts
        except (ValueError,TypeError):ts=now_ms()
        # Future clocks and firmware zero timestamps must not damage retention.
        if ts<946684800000 or ts>now_ms()+86400000:ts=now_ms()
        packet_id=packet.get("id") or packet.get("packetId")
        if not packet_id:packet_id=hashlib.blake2s(json.dumps(_json_safe(packet),sort_keys=True).encode(),digest_size=8).hexdigest()
        # Duplicate RX events in same source should not inflate statistics.
        unique=f"{source_id}:{from_num}:{packet_id}:{port_name(decoded.get('portnum'))}:{ts//1000}"
        raw_json=json.dumps(_json_safe(packet),ensure_ascii=False)[:12000]
        port=port_name(decoded.get("portnum"))
        text=_parse_text(decoded) if port in ("TEXT_MESSAGE_APP","1") else ""
        accepted=self.db.add_packet({"source_id":source_id,"packet_id":str(packet_id),"source_packet_key":unique,
          "timestamp_ms":ts,"from_node":from_num,"to_node":to_num,"port":port,
          "channel":number(packet.get("channel")),"rx_snr":packet.get("rxSnr",packet.get("rx_snr")),
          "rx_rssi":packet.get("rxRssi",packet.get("rx_rssi")),"hop_start":packet.get("hopStart",packet.get("hop_start")),
          "hop_limit":packet.get("hopLimit",packet.get("hop_limit")),"via_mqtt":int(bool(via_mqtt)),
          "encrypted":int(bool(packet.get("encrypted")) and not decoded),"text_preview":text[:180] if text else "", "raw_json":raw_json})
        if not accepted:return False
        if from_num is not None:
            self.db.upsert_node(from_num,source_id,timestamp_ms=ts,snr=packet.get("rxSnr",packet.get("rx_snr")))
        if port in ("NODEINFO_APP","4") and from_num is not None:
            user=decoded.get("user") if isinstance(decoded.get("user"),dict) else {}
            if not user and isinstance(decoded.get("nodeInfo"),dict):user=decoded["nodeInfo"].get("user") or {}
            if isinstance(user,dict):
                self.db.upsert_node(from_num,source_id,timestamp_ms=ts,long_name=user.get("longName") or user.get("long_name"),
                                    short_name=user.get("shortName") or user.get("short_name"),hw_model=user.get("hwModel") or user.get("hw_model"))
        if port in ("POSITION_APP","3") and from_num is not None:
            loc=position_from_decoded(decoded)
            if loc:
                lat,lon,alt=loc
                self.db.upsert_node(from_num,source_id,timestamp_ms=ts,latitude=lat,longitude=lon,altitude=alt)
                self.db.add_position(from_num,source_id,ts,lat,lon,alt)
        if port in ("TELEMETRY_APP","67","65") and from_num is not None:
            # Payload shape varies by firmware/transport. Persist only telemetry
            # fields explicitly present in decoded data; never infer CRC from rx_bad.
            tele=decoded.get("telemetry") if isinstance(decoded.get("telemetry"),dict) else decoded
            dev=tele.get("deviceMetrics") or tele.get("device_metrics") or {}
            loc=tele.get("localStats") or tele.get("local_stats") or {}
            def metric(obj, *keys):
                if not isinstance(obj,dict):return None
                for key in keys:
                    if key in obj and obj[key] is not None:return obj[key]
                return None
            voltage=metric(dev,"voltage","batteryVoltage","battery_voltage")
            battery=metric(dev,"batteryLevel","battery_level")
            if battery is not None or voltage is not None:
                self.db.upsert_node(from_num,source_id,timestamp_ms=ts,battery=battery,voltage=voltage)
            self.db.add_rf_sample(
                source_id,from_num,ts,
                battery=battery, voltage=voltage,
                channel_util=metric(dev,"channelUtilization","channel_utilization"),
                air_util=metric(dev,"airUtilTx","air_util_tx"),
                rx_good=metric(loc,"numPacketsRx","num_packets_rx"),
                rx_bad=metric(loc,"numPacketsRxBad","num_packets_rx_bad"))
        if port in ("TEXT_MESSAGE_APP","1") and text:
            self.db.add_message({"source_id":source_id,"packet_key":unique,"packet_id":str(packet_id),"timestamp_ms":ts,
                                 "from_node":from_num,"to_node":to_num,"channel":int(packet.get("channel") or 0),
                                 "direction":"rx","text":text[:1024],"state":"received"})
        if port in ("TRACEROUTE_APP","67"):
            route=decoded.get("route")
            if isinstance(route,dict):route=route.get("route") or route.get("routeNodes")
            if isinstance(route,list) and from_num is not None and to_num is not None:
                hops=[from_num]+[n for x in route if (n:=number(x)) is not None]+[to_num]
                self.db.add_trace(source_id,ts,from_num,to_num,hops)
                # A sequence of relay IDs proves topology of this traceroute, NOT direct RF.
                # No SNR for each hop? Keep it unclassified; never report RF-confirmed.
                for a,b in zip(hops,hops[1:]):self.db.add_link(source_id,a,b,ts,"observed_route_unverified_rf")
        return True


class SourceManager:
    def __init__(self,db:Database):
        self.db=db
        self.ingest=PacketIngestor(db)
        self._stop=threading.Event()
        self._lock=threading.RLock()
        self._config_lock=threading.RLock()
        self._states={}
        self._interfaces={}
        self._threads={}
        self._stop_sources=set()
        self._pub=None
        self._subscribed=False

    def _set(self,id,state,error=""):
        with self._lock:
            old=self._states.get(id,{})
            self._states[id]={"status":state,"error":str(error)[:200],"updated_ms":now_ms(),
                              "packets":old.get("packets",0),"type":old.get("type","")}

    def snapshot(self):
        with self._lock:return {str(k):dict(v) for k,v in self._states.items()}

    def _on_packet(self,packet=None,interface=None,**kwargs):
        with self._lock:
            source_id=next((k for k,v in self._interfaces.items() if v is interface),None)
        if source_id is None:return
        try:
            if self.ingest.handle(source_id,packet or {}):
                with self._lock:self._states[source_id]["packets"]+=1
        except Exception as exc:
            self.db.log("Erro ao processar pacote do rádio: "+type(exc).__name__,"error",source_id)

    def _lost(self,interface=None,**kwargs):
        with self._lock:
            source_id=next((k for k,v in self._interfaces.items() if v is interface),None)
        if source_id is not None:
            self._set(source_id,"disconnected","Conexão perdida; tentando reconectar")
            with self._lock:self._interfaces.pop(source_id,None)

    def _ensure_pubsub(self):
        with self._lock:
            if self._subscribed:return
            from pubsub import pub
            pub.subscribe(self._on_packet,"meshtastic.receive")
            pub.subscribe(self._lost,"meshtastic.connection.lost")
            self._pub=pub;self._subscribed=True

    def start(self):
        for src in self.db.sources(public=False):
            if src["enabled"]:self.connect(src["id"])

    def connect(self,id):
        id=int(id)
        source=self.db.source(id)
        if not source: raise ValueError("Fonte não encontrada")
        if not source["enabled"]:raise ValueError("Ative a fonte antes de conectar")
        with self._lock:
            self._stop_sources.discard(id)
            old=self._threads.get(id)
            if old and old.is_alive():return
            thread=threading.Thread(target=self._worker,args=(id,),daemon=True,name=f"source-{id}")
            self._threads[id]=thread
        self._set(id,"connecting")
        thread.start()

    def disconnect(self,id):
        id=int(id)
        with self._lock:
            iface=self._interfaces.pop(id,None)
            self._stop_sources.add(id)
        if iface:
            try:iface.close()
            except Exception:pass
        self._set(id,"disconnected")

    def restart(self,id):
        self.disconnect(id)
        # Threads reconnect only while enabled; disable/re-enable source restarts.
        self.connect(id)

    def _worker(self,id):
        while not self._stop.is_set():
            src=self.db.source(id)
            if not src or not src["enabled"]:break
            with self._lock:
                if id in self._stop_sources:break
            self._set(id,"connecting")
            iface=None
            try:
                kind,conf=src["kind"],src["config"]
                if kind == "mqtt":
                    self._run_mqtt(id,conf)
                    if self._stop.is_set():break
                else:
                    self._ensure_pubsub()
                    if kind == "serial":
                        from meshtastic.serial_interface import SerialInterface
                        iface=SerialInterface(devPath=conf["port"])
                    elif kind == "tcp":
                        from meshtastic.tcp_interface import TCPInterface
                        iface=TCPInterface(hostname=conf["host"],portNumber=int(conf.get("port") or 4403))
                    elif kind == "ble":
                        from meshtastic.ble_interface import BLEInterface
                        iface=BLEInterface(address=conf["address"])
                    else:raise RuntimeError("Transporte desconhecido")
                    with self._lock:self._interfaces[id]=iface
                    self.ingest.seed_from_interface(id,iface)
                    self._set(id,"connected")
                    self.db.log("Conexão estabelecida com fonte "+str(id),source_id=id)
                    while not self._stop.wait(1):
                        with self._lock:
                            if self._interfaces.get(id) is not iface:break
                        if not (self.db.source(id) or {}).get("enabled"):break
            except Exception as exc:
                self._set(id,"error",str(exc))
                self.db.log("Falha em fonte "+str(id)+": "+type(exc).__name__,"error",id)
            finally:
                with self._lock:
                    if self._interfaces.get(id) is iface:self._interfaces.pop(id,None)
                if iface:
                    try:iface.close()
                    except Exception:pass
            with self._lock:
                if id in self._stop_sources:break
            if self._stop.wait(7):break
        with self._lock:
            if self._states.get(id,{}).get("status")!="error":self._set(id,"disconnected")
            if self._threads.get(id) is threading.current_thread():self._threads.pop(id,None)

    def _run_mqtt(self,id,conf):
        import paho.mqtt.client as mqtt
        from google.protobuf.json_format import MessageToDict
        try:from meshtastic.protobuf import mqtt_pb2
        except ImportError:from meshtastic import mqtt_pb2
        connected=threading.Event()
        client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if conf.get("username"):client.username_pw_set(conf["username"],conf.get("password") or None)
        if conf.get("tls"):client.tls_set()
        def on_connect(client,userdata,flags,reason_code,properties):
            if reason_code==0:
                client.subscribe(conf["topic"],qos=0)
                connected.set();self._set(id,"connected")
            else:self._set(id,"error","Falha de autorização/conexão MQTT")
        def on_message(client,userdata,msg):
            try:
                envelope=mqtt_pb2.ServiceEnvelope()
                envelope.ParseFromString(msg.payload)
                packet=MessageToDict(envelope.packet,preserving_proto_field_name=False)
                if "from" not in packet:packet["from"]=getattr(envelope.packet,"from",None)
                if "to" not in packet:packet["to"]=getattr(envelope.packet,"to",None)
                packet["via_mqtt"]=True
                if self.ingest.handle(id,packet,via_mqtt=True):
                    with self._lock:self._states[id]["packets"]+=1
            except Exception:
                self.db.log("Mensagem MQTT não é um envelope Meshtastic válido/decodificável","warning",id)
        client.on_connect=on_connect
        client.on_message=on_message
        client.connect(str(conf["host"]),int(conf.get("port") or 1883),keepalive=60)
        client.loop_start()
        with self._lock:self._interfaces[id]=client
        try:
            while not self._stop.wait(1):
                with self._lock:
                    if self._interfaces.get(id) is not client:break
                if not (self.db.source(id) or {}).get("enabled"):break
        finally:
            client.loop_stop();client.disconnect()
            with self._lock:self._interfaces.pop(id,None)


    def radio_config(self, source_id):
        """Read local device configuration; MQTT cannot manage radio hardware."""
        from .device_config import read_device
        source_id = int(source_id)
        src = self.db.source(source_id)
        if not src or src["kind"] == "mqtt":
            raise ValueError("Escolha uma fonte de rádio Serial, TCP ou BLE")
        with self._lock:
            interface = self._interfaces.get(source_id)
            if interface is None:
                raise ValueError("Fonte não conectada")
            return read_device(getattr(interface, "localNode", None),
                               getattr(interface, "metadata", None))

    def update_lora(self, source_id, revision, changes):
        """Write one local LoRa block. Does not claim radio ACK/readback."""
        from .device_config import prepare_lora
        source_id = int(source_id)
        src = self.db.source(source_id)
        if not src or src["kind"] == "mqtt":
            raise ValueError("MQTT não permite editar a configuração de um rádio")
        with self._config_lock:
            with self._lock:
                interface = self._interfaces.get(source_id)
                if interface is None:
                    raise ValueError("Fonte não conectada")
                node = getattr(interface, "localNode", None)
                if node is None or getattr(node, "localConfig", None) is None:
                    raise ValueError("Configuração do dispositivo ainda indisponível")
                original, changed = prepare_lora(node, revision, changes)
                try:
                    node.writeConfig("lora")
                except Exception:
                    node.localConfig.lora.CopyFrom(original)
                    raise
            self.db.log("Gravação LoRa solicitada: " + ", ".join(changed),
                        source_id=source_id)
        return {"success": True, "state": "write_requested", "changed": changed,
                "note": "Comando enviado à interface; confirmação de persistência "
                        "no rádio ainda depende de reconexão e leitura posterior."}

    def send_text(self,id,to_node,text,channel=0):
        id=int(id)
        src=self.db.source(id)
        if not src:raise ValueError("Fonte não encontrada")
        if src["kind"]=="mqtt":raise ValueError("Fonte MQTT é somente recepção na v0.1.0")
        with self._lock:iface=self._interfaces.get(id)
        if iface is None:raise ValueError("Fonte não conectada")
        text=str(text).strip()
        if not text or len(text.encode("utf-8"))>220:raise ValueError("Mensagem vazia ou acima de 220 bytes")
        try:channel=int(channel)
        except Exception:raise ValueError("Canal inválido")
        if not 0<=channel<=7:raise ValueError("Canal inválido")
        recipient="^all" if to_node in (None,"","^all","broadcast") else (f"!{int(to_node) & 0xffffffff:08x}" if str(to_node).isdigit() else str(to_node))
        if recipient!="^all" and not (len(recipient)==9 and recipient[0]=="!" and all(c in "0123456789abcdefABCDEF" for c in recipient[1:])):
            raise ValueError("Destino privado inválido")
        data=iface.sendText(text,destinationId=recipient,wantAck=(recipient!="^all"),channelIndex=channel)
        packet_id=str(data.get("id") if isinstance(data,dict) else getattr(data,"id",""))
        local_num=number(getattr(iface,"myInfo",None) and getattr(iface.myInfo,"my_node_num",None))
        pktkey="tx:"+str(id)+":"+packet_id+":"+str(now_ms())
        self.db.add_message({"source_id":id,"packet_key":pktkey,"packet_id":packet_id,"timestamp_ms":now_ms(),
           "from_node":local_num,"to_node":number(recipient),"channel":channel,"direction":"tx","text":text,"state":"accepted_by_radio"})
        return {"success":True,"packet_id":packet_id,"state":"accepted_by_radio",
                "note":"Envio aceito pela interface. Isto não confirma entrega nem leitura pelo destinatário."}

    def close(self):
        self._stop.set()
        with self._lock:interfaces=list(self._interfaces.values());self._interfaces.clear()
        for iface in interfaces:
            try:iface.close()
            except Exception:pass
        if self._subscribed:
            try:
                self._pub.unsubscribe(self._on_packet,"meshtastic.receive")
                self._pub.unsubscribe(self._lost,"meshtastic.connection.lost")
            except Exception:pass


def available_serial_ports():
    try:
        from serial.tools import list_ports
        return [{"device":p.device,"description":p.description} for p in list_ports.comports()]
    except ImportError:return []