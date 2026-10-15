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
            if kind == "traceroute":
                outgoing = iface.sendTraceRoute(dest, channelIndex=channel)
            else:
                # A request is a real Meshtastic port request, not a text message.
                # Only firmware supporting the corresponding request will answer.
                from meshtastic.protobuf import portnums_pb2
                enum = portnums_pb2.PortNum.Value(port_name(PORTS[kind]))
                outgoing = iface.sendData(
                    b"", destinationId=dest, portNum=enum,
                    wantResponse=True, channelIndex=channel)
            packet_id = outgoing.get("id") if isinstance(outgoing, dict) else getattr(outgoing, "id", None)
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
            row = (candidates or eligible)[0]
            row["state"] = "replied"
            row["received_ms"] = now
            row["correlation"] = "request_id" if candidates else "source_sender_port_time"
            row["response"] = {k: str(v)[:300] for k, v in decoded.items() if k != "payload"}

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
