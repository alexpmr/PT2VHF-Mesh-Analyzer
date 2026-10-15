"""Bounded, observable Meshtastic node requests. RF receipt is not a response."""
from __future__ import annotations

import threading
import time
import uuid

from .transports import number, port_name

PORTS = {"nodeinfo": 4, "position": 3, "telemetry": 67, "traceroute": 70}
RESPONSE_PORTS = {4: "nodeinfo", 3: "position", 67: "telemetry", 70: "traceroute"}


class NodeQueries:
    def __init__(self, manager):
        self.manager = manager
        self.lock = threading.RLock()
        self.pending = {}
        self.last_sent = {}

    def capabilities(self, source_id):
        try:
            source_id = int(source_id)
        except (ValueError, TypeError):
            return {"ready": False, "reason": "Selecione um rádio"}
        src = self.manager.db.source(source_id)
        with self.manager._lock:
            iface = self.manager._interfaces.get(source_id)
        if not src or src.get("kind") == "mqtt":
            return {"ready": False, "reason": "MQTT somente recepção"}
        if iface is None:
            return {"ready": False, "reason": "Rádio desconectado"}
        if not callable(getattr(iface, "sendData", None)):
            return {"ready": False, "reason": "SDK sem API sendData"}
        return {"ready": True, "supported": ["nodeinfo", "position", "telemetry"] +
                (["traceroute"] if callable(getattr(iface, "sendTraceRoute", None)) else []),
                "reason": ""}

    def start(self, source_id, target, kind, channel=0):
        source_id = int(source_id)
        target = number(target)
        kind = str(kind).lower().strip()
        if target is None or not 0 < target < 0xffffffff:
            raise ValueError("Destino unicast inválido")
        try:
            channel = int(channel)
        except (ValueError, TypeError):
            raise ValueError("Canal inválido") from None
        if not 0 <= channel <= 7:
            raise ValueError("Canal inválido")
        caps = self.capabilities(source_id)
        if not caps["ready"]:
            raise ValueError(caps["reason"])
        if kind not in caps["supported"]:
            raise ValueError("Consulta não suportada nesta interface: " + kind)
        with self.manager._lock:
            iface = self.manager._interfaces.get(source_id)
            local = getattr(iface, "myInfo", None)
            ifaces = getattr(iface, "nodesByNum", {}) or {}
            own = number(local.get("my_node_num") if isinstance(local, dict)
                         else getattr(local, "my_node_num", None))
            if own == target:
                raise ValueError("Destino é o próprio rádio")
        now = time.monotonic()
        key = (source_id, target, kind)
        with self.lock:
            for req in self.pending.values():
                if (req["source_id"], req["target"], req["kind"]) == key and req["state"] == "awaiting_reply":
                    raise ValueError("Já existe consulta deste tipo aguardando resposta")
            if now - self.last_sent.get(source_id, 0) < 3:
                raise ValueError("Aguarde 3 segundos entre consultas RF")
            rid = uuid.uuid4().hex
            row = {"request_id": rid, "source_id": source_id, "target": target,
                   "kind": kind, "state": "sending", "created_ms": int(time.time()*1000),
                   "deadline_ms": int(time.time()*1000)+45000, "packet_id": None,
                   "response": None, "error": None}
            self.pending[rid] = row
            self.last_sent[source_id] = now
        try:
            dest = "!%08x" % target
            # Use protocol-defined protobuf request payloads. The SDK's
            # sendTraceRoute requires hopLimit and can block for a timeout, so
            # send RouteDiscovery directly through sendData instead.
            from meshtastic.protobuf import portnums_pb2, mesh_pb2, telemetry_pb2
            if kind == "nodeinfo":
                payload = mesh_pb2.User()
            elif kind == "position":
                payload = mesh_pb2.Position()
            elif kind == "telemetry":
                payload = telemetry_pb2.Telemetry()
                payload.device_metrics.CopyFrom(telemetry_pb2.DeviceMetrics())
            elif kind == "traceroute":
                payload = mesh_pb2.RouteDiscovery()
            enum = portnums_pb2.PortNum.Value(port_name(PORTS[kind]))
            outgoing = iface.sendData(
                payload, destinationId=dest, portNum=enum,
                wantResponse=True, channelIndex=channel)
            packet_id = outgoing.get("id") if isinstance(outgoing, dict) else getattr(outgoing, "id", None)
            # Outbound requests are not delivered back through the RX callback.
            # Record separately with real local/destination IDs, never broadcast.
            local_num = own
            if local_num is None:
                with self.manager._lock:
                    info = getattr(iface, "myInfo", None)
                    local_num = number(info.get("my_node_num") or info.get("myNodeNum")) if isinstance(info, dict) else number(getattr(info, "my_node_num", None))
            if local_num is None:
                local_num = number(getattr(getattr(iface, "localNode", None), "nodeNum", None)
                                   or getattr(iface, "myNodeNum", None))
            if local_num is not None:
                stamp=int(time.time()*1000)
                self.manager.db.upsert_node(local_num,source_id,timestamp_ms=stamp)
            self.manager.db.add_packet({
                "source_id":source_id,
                "packet_id":str(packet_id or rid),
                "source_packet_key":f"tx:{source_id}:{rid}",
                "timestamp_ms":int(time.time()*1000),
                "from_node":local_num,"to_node":target,
                "port":port_name(PORTS[kind]),"channel":channel,
                "direction":"tx","via_mqtt":0,"encrypted":0,
                "text_preview":"Consulta RF solicitada: "+kind
            })
            with self.manager._lock:
                states=getattr(self.manager,"_states",None)
                current=states.get(source_id) if isinstance(states,dict) else None
                if current is not None:
                    current["tx_seq"]=current.get("tx_seq",0)+1
                    current["last_tx_ms"]=int(time.time()*1000)
            with self.lock:
                row["state"] = "awaiting_reply"
                row["packet_id"] = packet_id
            self.manager.db.log("Consulta RF %s enviada ao nó %s (%s)" % (kind, dest, rid[:10]),
                                source_id=source_id)
        except Exception as exc:
            with self.lock:
                row["state"] = "error"
                row["error"] = str(exc)[:160]
            raise ValueError("Falha na transmissão: "+str(exc)[:160]) from exc
        return dict(row)

    def observe(self, source_id, packet):
        if not isinstance(packet, dict):
            return
        decoded = packet.get("decoded") or {}
        if not isinstance(decoded, dict):
            return
        kind = RESPONSE_PORTS.get(number(decoded.get("portnum")) or
                next((p for p, name in ((4,"NODEINFO_APP"),(3,"POSITION_APP"),(67,"TELEMETRY_APP"),(70,"TRACEROUTE_APP"))
                      if name == str(decoded.get("portnum"))), -1))
        if not kind:
            return
        sender = number(packet.get("from") or packet.get("fromId"))
        if sender is None:
            return
        request_id = number(decoded.get("requestId") or decoded.get("request_id"))
        now = int(time.time()*1000)
        with self.lock:
            eligible = [r for r in self.pending.values()
                        if r["source_id"] == source_id and r["target"] == sender
                        and r["kind"] == kind and r["state"] == "awaiting_reply"]
            if not eligible:
                return
            # When request_id is echoed, enforce it. Otherwise attribute a single
            # matching reply conservatively and mark it as uncorrelated.
            candidates = [r for r in eligible if request_id and number(r["packet_id"]) == request_id]
            if request_id and not candidates:
                return
            if not candidates:
                # Packets without an echoed request ID may be periodic
                # broadcasts; do not present them as a confirmed reply.
                return
            row = candidates[0]
            row["state"] = "replied"
            row["received_ms"] = now
            row["correlation"] = "request_id" if candidates else "source_sender_port_time"
            row["response"] = {k: str(v)[:300] for k, v in decoded.items() if k != "payload"}
            if kind == "traceroute":
                # Keep the route evidence structured. A reply without route
                # arrays is NOT proof that the destination was heard directly.
                from .topology import decoded_traceroute
                parsed = decoded.get("traceroute") or decoded.get("routeDiscovery") or {}
                if not isinstance(parsed, dict):
                    parsed = {}
                evidence = decoded_traceroute(decoded) or {}
                # The SDK may expose nested dictionaries or only raw Protobuf.
                # RouteDiscovery's two ordered arrays are authoritative.
                parsed = {**parsed, **evidence}
                def ids(field, alternate):
                    raw = parsed.get(field, parsed.get(alternate, decoded.get(field, decoded.get(alternate, []))))
                    if isinstance(raw, (tuple, list)):
                        return [n for item in raw if (n := number(item)) is not None]
                    return []
                def metrics(field, alternate):
                    raw = parsed.get(field, parsed.get(alternate, decoded.get(field, decoded.get(alternate, []))))
                    if not isinstance(raw, (tuple, list)):
                        return []
                    return [float(item) for item in raw if isinstance(item, (int, float)) and not isinstance(item, bool)]
                row["route_detail"] = {
                    "route": ids("route", "routeTowards"),
                    "route_back": ids("routeBack", "route_back"),
                    "snr_towards_raw": metrics("snrTowards", "snr_towards"),
                    "snr_back_raw": metrics("snrBack", "snr_back"),
                    "has_intermediate_hops": bool(ids("route", "routeTowards") or ids("routeBack", "route_back")),
                    "status": "Rota com saltos informados" if ids("route", "routeTowards") or ids("routeBack", "route_back") else "Nenhum salto intermediário informado",
                }

    def status(self, target=None):
        now = int(time.time()*1000)
        target = number(target)
        with self.lock:
            for row in self.pending.values():
                if row["state"] == "awaiting_reply" and now > row["deadline_ms"]:
                    row["state"] = "timeout"
                if row["state"] == "awaiting_reply" and not self.capabilities(row["source_id"])["ready"]:
                    row["state"] = "disconnected"
            rows = [dict(r) for r in self.pending.values()
                    if target is None or r["target"] == target]
        return sorted(rows, key=lambda r: r["created_ms"], reverse=True)[:100]
