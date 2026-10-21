"""Native Meshtastic Serial/TCP/BLE and read-only Meshtastic MQTT ingestion."""
from __future__ import annotations

import base64
import hashlib
import json
import threading
import time
from typing import Any

from .database import Database, now_ms
from .node_roles import normalize_role, decoded_user
from .topology import extract_topology


def number(value):
    if value is None or value == "": return None
    try:
        if isinstance(value,str) and value.startswith("!"):
            return int(value[1:],16)
        return int(value)
    except (ValueError,TypeError,OverflowError): return None


def port_name(value):
    if isinstance(value,str): return value
    ports = {1:"TEXT_MESSAGE_APP",3:"POSITION_APP",4:"NODEINFO_APP",
             5:"ROUTING_APP",6:"ADMIN_APP",8:"WAYPOINT_APP",65:"STORE_FORWARD_APP",
             67:"TELEMETRY_APP",70:"TRACEROUTE_APP",71:"NEIGHBORINFO_APP"}
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


def waypoint_from_decoded(decoded):
    """Decode actual Meshtastic WAYPOINT_APP data, never infer a marker from a node."""
    if not isinstance(decoded, dict): return None
    data = decoded.get("waypoint")
    if not isinstance(data, dict):
        payload = decoded.get("payload")
        if isinstance(payload,dict) and isinstance(payload.get("base64"),str):
            try: payload = base64.b64decode(payload["base64"],validate=True)
            except (ValueError,TypeError): payload = None
        if not isinstance(payload,bytes) or len(payload)>8192: return None
        try:
            from meshtastic.protobuf import mesh_pb2
        except ImportError:
            from meshtastic import mesh_pb2
        msg=mesh_pb2.Waypoint()
        msg.ParseFromString(payload)
        data={"id":msg.id,"latitude_i":msg.latitude_i,"longitude_i":msg.longitude_i,
              "name":msg.name,"description":msg.description,"icon":msg.icon,
              "expire":msg.expire}
    ident=number(data.get("id"))
    lat=data.get("latitude_i",data.get("latitudeI"))
    lon=data.get("longitude_i",data.get("longitudeI"))
    if lat is None or lon is None or ident is None: return None
    try:
        # latitude_i/longitude_i are fixed-point integers in units of 1e-7 degree.
        lat=float(lat)/1e7
        lon=float(lon)/1e7
        if not 0<ident<2**32 or not (-90<=lat<=90 and -180<=lon<=180):return None
        if abs(lat)<0.000001 and abs(lon)<0.000001:return None
        expire=int(data.get("expire") or 0)
        if expire<0:return None
        icon=int(data.get("icon") or 0)
        return {"waypoint_id":ident,"latitude":lat,"longitude":lon,
                "name":str(data.get("name") or "")[:30],
                "description":str(data.get("description") or "")[:100],
                "expires_ms":expire*1000 if expire else 0,"icon":icon}
    except (ValueError,TypeError,OverflowError): return None


# #144: rxTime vem do relógio do rádio, que pode estar alguns minutos defasado
# do PC; isso fazia toda mensagem recém-chegada aparecer como "há 3 minutos".
# Dentro desta janela a recepção é ao vivo e vale o relógio local; fora dela
# (histórico reenviado pelo rádio) preserva-se o horário original do pacote.
LIVE_CLOCK_SKEW_MS=15*60*1000


def message_timestamp(radio_ms:int,received_ms:int)->int:
    if abs(int(radio_ms)-int(received_ms))<=LIVE_CLOCK_SKEW_MS:return int(received_ms)
    return min(int(radio_ms),int(received_ms))


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
                        "hw_model":user.get("hwModel") or user.get("hw_model"),"role":normalize_role(user.get("role",n.get("role"))),"snr":n.get("snr")}
                if position:values.update(latitude=position[0],longitude=position[1],altitude=position[2])
                # Radio-provided cached NodeDB is NOT live evidence. Preserve the
                # recorded lastHeard; unknown means never heard in this session.
                raw_seen=n.get("lastHeard") or n.get("last_heard") or 0
                try:
                    seen=int(float(raw_seen));seen=seen*1000 if 0<seen<10_000_000_000 else seen
                except (TypeError,ValueError):seen=0
                self.db.upsert_node(num,source_id,timestamp_ms=seen,**values)
                # Only trust explicit boolean values received in the radio NodeDB.
                # Missing flags mean unknown, NOT false.
                favorite=n.get("isFavorite",n.get("is_favorite",
                         user.get("isFavorite",user.get("is_favorite"))))
                if type(favorite) is bool:
                    self.db.set_node_favorite_from_radio(source_id,num,favorite)
        except Exception:
            self.db.log("Não foi possível importar o catálogo inicial do rádio", "warning",source_id)

    def handle(self,source_id:int,packet:dict,via_mqtt=False,local_node_num=None):
        if not isinstance(packet,dict):return False
        decoded=packet.get("decoded") if isinstance(packet.get("decoded"),dict) else {}
        from_num=number(packet.get("from") if "from" in packet else packet.get("fromId"))
        to_num=number(packet.get("to") if "to" in packet else packet.get("toId"))
        received_ms=now_ms()
        raw_ts=packet.get("rxTime") or packet.get("rx_time") or packet.get("timestamp") or received_ms
        try: ts=int(float(raw_ts));ts=ts*1000 if ts<10_000_000_000 else ts
        except (ValueError,TypeError):ts=received_ms
        # Future clocks and firmware zero timestamps must not damage retention.
        if ts<946684800000 or ts>received_ms+86400000:ts=received_ms
        radio_ts=ts
        packet_id=packet.get("id") or packet.get("packetId")
        if not packet_id:packet_id=hashlib.blake2s(json.dumps(_json_safe(packet),sort_keys=True).encode(),digest_size=8).hexdigest()
        # Duplicate RX events in same source should not inflate statistics.
        # Retransmissions/repeated callbacks with the same Meshtastic packet ID
        # must remain idempotent even when an API retry crosses a second boundary.
        # A UTC day bucket avoids conflating genuinely recycled IDs months apart.
        unique=f"{source_id}:{from_num}:{packet_id}:{port_name(decoded.get('portnum'))}:{ts//86400000}"
        raw_json=json.dumps(_json_safe(packet),ensure_ascii=False)[:12000]
        port=port_name(decoded.get("portnum"))
        text=_parse_text(decoded) if port in ("TEXT_MESSAGE_APP","1") else ""
        accepted=self.db.add_packet({"source_id":source_id,"packet_id":str(packet_id),"source_packet_key":unique,
          "timestamp_ms":ts,"from_node":from_num,"to_node":to_num,"port":port,
          "channel":number(packet.get("channel")),"rx_snr":packet.get("rxSnr",packet.get("rx_snr")),
          "rx_rssi":packet.get("rxRssi",packet.get("rx_rssi")),"hop_start":packet.get("hopStart",packet.get("hop_start")),
          "hop_limit":packet.get("hopLimit",packet.get("hop_limit")),"via_mqtt":int(bool(via_mqtt) or packet.get("viaMqtt") is True or packet.get("via_mqtt") is True),
          "encrypted":int(bool(packet.get("encrypted")) and not decoded),"text_preview":text[:180] if text else "", "raw_json":raw_json})
        if not accepted:return False
        # Persist communication as a logical relationship; it is NOT a direct RF link.
        self.db.record_communication(unique,source_id,ts,from_num,to_num,
            bool(via_mqtt) or packet.get("viaMqtt") is True or packet.get("via_mqtt") is True)
        # A packet with zero relays and a valid local radio receiver provides
        # evidence of one RF hop from its origin to that particular receiver.
        # A remote logical destination is never used as RF receiver.
        local=number(local_node_num)
        hs=number(packet.get("hopStart",packet.get("hop_start")))
        hl=number(packet.get("hopLimit",packet.get("hop_limit")))
        raw_snr=packet.get("rxSnr",packet.get("rx_snr"))
        try: snr=float(raw_snr) if raw_snr is not None else None
        except (ValueError,TypeError): snr=None
        is_rf=not (via_mqtt or packet.get("viaMqtt") is True or packet.get("via_mqtt") is True)
        if (is_rf and local is not None and from_num is not None and local!=from_num and
            hs is not None and hl is not None and hs==hl and
            snr is not None and snr>-32 and -35<snr<35):
            self.db.add_link(source_id,from_num,local,ts,"confirmed_direct_rf")
        if from_num is not None:
            self.db.upsert_node(from_num,source_id,timestamp_ms=ts,observed=True,snr=packet.get("rxSnr",packet.get("rx_snr")))
        if port in ("NODEINFO_APP","4") and from_num is not None:
            user=decoded_user(decoded)
            if isinstance(user,dict):
                self.db.upsert_node(from_num,source_id,timestamp_ms=ts,observed=True,long_name=user.get("longName") or user.get("long_name"),
                                    short_name=user.get("shortName") or user.get("short_name"),hw_model=user.get("hwModel") or user.get("hw_model"),role=normalize_role(user.get("role")))
        if port in ("WAYPOINT_APP","8"):
            try:
                wp=waypoint_from_decoded(decoded)
                if wp:self.db.upsert_waypoint(source_id,from_node=from_num,ts=ts,**wp)
            except (ValueError,TypeError,ImportError) as exc:
                self.db.log("Waypoint inválido ou protobuf indisponível: "+type(exc).__name__,"warning",source_id)
        if port in ("POSITION_APP","3") and from_num is not None:
            loc=position_from_decoded(decoded)
            if loc:
                lat,lon,alt=loc
                self.db.upsert_node(from_num,source_id,timestamp_ms=ts,observed=True,latitude=lat,longitude=lon,altitude=alt)
                self.db.add_position(from_num,source_id,ts,lat,lon,alt)
        if port in ("TELEMETRY_APP","67") and from_num is not None:
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
                self.db.upsert_node(from_num,source_id,timestamp_ms=ts,observed=True,battery=battery,voltage=voltage)
            self.db.add_rf_sample(
                source_id,from_num,ts,
                battery=battery, voltage=voltage,
                channel_util=metric(dev,"channelUtilization","channel_utilization"),
                air_util=metric(dev,"airUtilTx","air_util_tx"),
                rx_good=metric(loc,"numPacketsRx","num_packets_rx"),
                rx_bad=metric(loc,"numPacketsRxBad","num_packets_rx_bad"))
        if port in ("TEXT_MESSAGE_APP","1") and text:
            self.db.add_message({"source_id":source_id,"packet_key":unique,"packet_id":str(packet_id),
                                 "timestamp_ms":message_timestamp(radio_ts,received_ms),
                                 "radio_time_ms":radio_ts,
                                 "from_node":from_num,"to_node":to_num,"channel":int(packet.get("channel") or 0),
                                 "direction":"rx","text":text[:1024],"state":"received"})
        kind,edges=extract_topology(packet)
        if kind is not None:
            self.db.record_topology(unique,source_id,ts,edges or [],
               trace={"from":from_num,"to":to_num,"type":kind} if kind=="traceroute" and edges else None)
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
        from .remote_queries import NodeQueries
        self.queries=NodeQueries(self)
        from .node_deletion import NodeDeletion
        self.node_deletion=NodeDeletion(self)
        from .message_receipts import MessageReceipts
        self.message_receipts=MessageReceipts(db)

    def _set(self,id,state,error=""):
        with self._lock:
            old=self._states.get(id,{})
            self._states[id]={"status":state,"error":str(error)[:200],"updated_ms":now_ms(),
                              "packets":old.get("packets",0),"type":old.get("type",""),
                               "rx_seq":old.get("rx_seq",0),"tx_seq":old.get("tx_seq",0),
                               "last_rx_ms":old.get("last_rx_ms",0),"last_tx_ms":old.get("last_tx_ms",0),
                               "mqtt_rx_seq":old.get("mqtt_rx_seq",0)}

    def snapshot(self):
        with self._lock:
            result={str(k):dict(v) for k,v in self._states.items()}
            for sid,interface in self._interfaces.items():
                info=getattr(interface,"myInfo",None)
                local=getattr(interface,"localNode",None)
                values=info if isinstance(info,dict) else {}
                own=number(values.get("my_node_num") or values.get("myNodeNum") or
                           getattr(info,"my_node_num",None) or
                           getattr(local,"nodeNum",None) or
                           getattr(interface,"myNodeNum",None))
                if str(sid) in result:
                    if own:result[str(sid)]["local_node_num"]=own
                    result[str(sid)]["tx_capable"]=callable(getattr(interface,"sendText",None))
            return result

    def _on_packet(self,packet=None,interface=None,**kwargs):
        with self._lock:
            source_id=next((k for k,v in self._interfaces.items() if v is interface),None)
        if source_id is None:return
        try:
            self.queries.observe(source_id,packet or {})
            self.message_receipts.observe(source_id,packet or {})
            info=getattr(interface,"myInfo",None)
            radio_info=info if isinstance(info,dict) else {}
            own=number(radio_info.get("my_node_num") or radio_info.get("myNodeNum") or
                       getattr(info,"my_node_num",None) or
                       getattr(getattr(interface,"localNode",None),"nodeNum",None) or
                       getattr(interface,"myNodeNum",None))
            if self.ingest.handle(source_id,packet or {},local_node_num=own):
                with self._lock:
                    state=self._states.get(source_id)
                    if state is not None:
                        state["packets"]+=1
                        state["rx_seq"]+=1
                        state["last_rx_ms"]=now_ms()
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

    def _update_device_name(self,source_id,iface):
        local=getattr(iface,"localNode",None)
        info=getattr(iface,"myInfo",None)
        own=getattr(local,"nodeNum",None) or getattr(info,"my_node_num",None)
        entries=getattr(iface,"nodesByNum",{})
        node=entries.get(own,{}) if isinstance(entries,dict) else {}
        user=node.get("user",{}) if isinstance(node,dict) else {}
        name=str(user.get("longName") or user.get("long_name") or "").strip()[:72]
        if name:
            with self.db._lock,self.db._db:
                self.db._db.execute("UPDATE sources SET name=?,updated_ms=? WHERE id=?",
                                    (name,now_ms(),int(source_id)))

    def sync_favorites_from_radio(self,source_id):
        """Import only explicit favorite flags from the connected radio NodeDB."""
        with self._lock:
            iface=self._interfaces.get(int(source_id))
        if iface is None:return 0
        entries=getattr(iface,"nodesByNum",None)
        if not isinstance(entries,dict):return 0
        changed=0
        for key,n in list(entries.items()):
            if not isinstance(n,dict):continue
            value=n.get("isFavorite",n.get("is_favorite"))
            num=number(n.get("num",key))
            if type(value) is bool and num and self.db.set_node_favorite_from_radio(source_id,num,value):
                changed+=1
        return changed

    def set_favorite(self,source_id,node_num,is_favorite):
        """Request a NodeDB favorite change on ONE connected local Meshtastic radio.

        A successful SDK call is only command submission. Never claim the
        radio has confirmed the favorite until the NodeDB itself reports it.
        """
        if type(is_favorite) is not bool:
            raise ValueError("Escolha Favoritar ou Desfavoritar")
        sid=number(source_id)
        num=number(node_num)
        if not sid or not num or not (0<num<0xffffffff):
            raise ValueError("Fonte ou número do nó inválido")
        source=self.db.source(sid)
        if not source or not source.get("enabled") or source.get("kind") not in ("serial","tcp","ble"):
            raise ValueError("Favoritos exigem rádio Meshtastic local conectado (USB, TCP ou BLE)")
        with self._lock:
            iface=self._interfaces.get(sid)
            status=self._states.get(sid,{}).get("status")
        if iface is None or status!="connected":
            raise RuntimeError("Rádio desconectado; nenhuma alteração foi enviada")
        local=getattr(iface,"localNode",None)
        method=getattr(local,"setFavorite" if is_favorite else "removeFavorite",None)
        if not callable(method):
            raise RuntimeError("Firmware/SDK deste rádio não oferece comando de favoritos")
        method(num)
        self.db.request_node_favorite(sid,num,is_favorite)
        # Read back without fabricating ACK, even if local admin command returned.
        self.sync_favorites_from_radio(sid)
        entries=getattr(iface,"nodesByNum",None)
        current=entries.get(num) if isinstance(entries,dict) else None
        flag=current.get("isFavorite",current.get("is_favorite")) if isinstance(current,dict) else None
        confirmed=type(flag) is bool and flag==is_favorite
        return {"success":True,"source_id":sid,"node_num":num,
                "requested_favorite":is_favorite,"confirmed":confirmed,
                "status":"confirmed" if confirmed else "awaiting_nodedb"}

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
        """Restart without racing a still-running worker for the same COM port."""
        id=int(id)
        src=self.db.source(id)
        if not src or not src["enabled"]:
            raise ValueError("Conexão inexistente ou desativada")
        if src["kind"] == "mqtt":
            raise ValueError("Reconexão forçada do rádio exige USB, TCP ou BLE")
        with self._lock:
            old=self._threads.get(id)
        self.disconnect(id)
        if old and old is not threading.current_thread() and old.is_alive():
            old.join(timeout=10)
            if old.is_alive():
                self._set(id,"error","A conexão anterior ainda não liberou o dispositivo")
                raise RuntimeError("Porta ainda ocupada pelo worker anterior; tente novamente")
        self.connect(id)
        return {"source_id":id,"state":"connecting"}

    def _worker(self,id):
        while not self._stop.is_set():
            src=self.db.source(id)
            if not src or not src["enabled"]:break
            with self._lock:
                if id in self._stop_sources:break
            if src["kind"] != "mqtt":
                with self._lock:
                    occupied=any(k!=id and self._states.get(k,{}).get("status")=="connected"
                                 and (self.db.source(k) or {}).get("kind")!="mqtt" for k in self._interfaces)
                if occupied:
                    self._set(id,"standby","Outra conexão de rádio está ativa")
                    if self._stop.wait(1):break
                    continue
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
                        iface=SerialInterface(devPath=conf["port"],timeout=20)
                    elif kind == "tcp":
                        from meshtastic.tcp_interface import TCPInterface
                        iface=TCPInterface(hostname=conf["host"],portNumber=int(conf.get("port") or 4403),timeout=20)
                    elif kind == "ble":
                        from meshtastic.ble_interface import BLEInterface
                        iface=BLEInterface(address=conf["address"],timeout=20)
                    else:raise RuntimeError("Transporte desconhecido")
                    with self._lock:
                        occupied=any(k!=id and self._states.get(k,{}).get("status")=="connected"
                                     and (self.db.source(k) or {}).get("kind")!="mqtt" for k in self._interfaces)
                        cancelled=id in self._stop_sources or self._stop.is_set()
                        if not occupied and not cancelled:
                            self._interfaces[id]=iface
                            self._set(id,"connected")
                    if occupied or cancelled:
                        self._set(id,"standby" if occupied else "disconnected")
                        continue
                    self.ingest.seed_from_interface(id,iface)
                    self.sync_favorites_from_radio(id)
                    self._update_device_name(id,iface)
                    self.db.log("Conexão estabelecida com fonte "+str(id),source_id=id)
                    next_favorite_sync=time.monotonic()+15
                    while not self._stop.wait(1):
                        with self._lock:
                            if self._interfaces.get(id) is not iface:break
                        if not (self.db.source(id) or {}).get("enabled"):break
                        if time.monotonic()>=next_favorite_sync:
                            try:
                                self.sync_favorites_from_radio(id)
                                self._update_device_name(id,iface)
                            except Exception:pass
                            next_favorite_sync=time.monotonic()+15
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
                    with self._lock:
                        state=self._states.get(id)
                        if state is not None:
                            state["packets"]+=1
                            state["mqtt_rx_seq"]+=1
                            state["rx_seq"]+=1
                            state["last_rx_ms"]=now_ms()
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

    def update_device(self, source_id, revision, changes):
        """Apply validated groups sequentially: multiple radio writes, not atomic."""
        from .device_config import prepare_all
        source_id=int(source_id)
        src=self.db.source(source_id)
        if not src or src["kind"]=="mqtt":
            raise ValueError("Conecte um rádio Serial/USB, BLE ou Wi-Fi/TCP")
        with self._config_lock:
            with self._lock:
                iface=self._interfaces.get(source_id)
                if iface is None:raise ValueError("Fonte não conectada")
                node=getattr(iface,"localNode",None)
                if node is None or getattr(node,"localConfig",None) is None:
                    raise ValueError("Configuração não disponível; sincronize antes")
                original, changed=prepare_all(node,revision,changes)
                result=[]
                for i,section in enumerate(changed):
                    group=section["group"]
                    try:
                        node.writeConfig(group)
                        result.append({"group":group,"fields":section["fields"],
                                       "state":"write_requested"})
                    except Exception as exc:
                        # Restore groups not yet sent only; a previously sent write
                        # may already have been accepted and must not be hidden.
                        for pending in changed[i:]:
                            name=pending["group"]
                            getattr(node.localConfig,name).CopyFrom(getattr(original,name))
                        result.append({"group":group,"fields":section["fields"],
                                       "state":"error","error":type(exc).__name__})
                        self.db.log("Falha ao gravar grupo "+group+" em fonte "+str(source_id),
                                    "error",source_id)
                        return {"success":False,"state":"partial_or_failed","steps":result,
                                "note":"Verifique manualmente os grupos aplicados. Releia o rádio."}
            self.db.log("Solicitada gravação dos grupos: "+",".join(x["group"] for x in changed),
                        source_id=source_id)
            return {"success":True,"state":"write_requested","steps":result,
                    "note":"Todos os comandos foram solicitados; não comprova ACK ou gravação persistente. Reconecte e releia."}

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
        buffered=[]; receipt_lock=threading.RLock(); persisted=[False]
        def onAckNak(packet):
            with self._lock:
                if self._interfaces.get(id) is not iface:return
            with receipt_lock:
                if persisted[0]:self.message_receipts.observe(id,packet)
                else:buffered.append(packet)
        data=iface.sendText(text,destinationId=recipient,wantAck=True,channelIndex=channel,onResponse=onAckNak)
        packet_id=str(data.get("id") if isinstance(data,dict) else getattr(data,"id",""))
        info=getattr(iface,"myInfo",None)
        local_num=number(info.get("my_node_num",info.get("myNodeNum")) if isinstance(info,dict)
                         else getattr(info,"my_node_num",None)) or number(getattr(getattr(iface,"localNode",None),"nodeNum",None))
        pktkey="tx:"+str(id)+":"+packet_id+":"+str(now_ms())
        with self._lock:
            state=self._states.get(id)
            if state is not None:
                state["tx_seq"]+=1
                state["last_tx_ms"]=now_ms()
        self.db.add_message({"source_id":id,"packet_key":pktkey,"packet_id":packet_id,"timestamp_ms":now_ms(),
           "from_node":local_num,"to_node":number(recipient),"channel":channel,"direction":"tx","text":text,"state":"accepted_by_radio"})
        with receipt_lock:
            persisted[0]=True
            for reply in buffered:self.message_receipts.observe(id,reply)
            buffered.clear()
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