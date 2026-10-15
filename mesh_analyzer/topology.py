"""Evidence-conservative Meshtastic topology parsing.

Ports and protobufs follow Meshtastic's public protocol:
Telemetry=67, Traceroute=70, NeighborInfo=71.
Received packets do not imply a direct RF hop to the originator.
"""
from __future__ import annotations

import base64


def number(value):
    if value is None or isinstance(value,bool):return None
    try:
        if isinstance(value,str) and value.startswith("!"):
            value=int(value[1:],16)
        n=int(value)
        return n if 0<n<0xffffffff else None
    except (ValueError,TypeError,OverflowError):return None


def _raw_payload(decoded):
    value=decoded.get("payload")
    if isinstance(value,(bytes,bytearray)):return bytes(value)
    if isinstance(value,dict) and isinstance(value.get("base64"),str):
        try:return base64.b64decode(value["base64"],validate=True)
        except (ValueError,base64.binascii.Error):return None
    return None


def decoded_traceroute(decoded):
    """Read route/routeBack from predecoded dictionaries or RouteDiscovery bytes."""
    obj=decoded.get("traceroute") or decoded.get("routeDiscovery") or decoded
    if isinstance(obj,dict):
        def candidates(key,alt):
            v=obj.get(key)
            if v is None:v=obj.get(alt)
            if isinstance(v,dict):v=v.get("route") or v.get("routeNodes")
            return v if isinstance(v,(list,tuple)) else None
        towards=candidates("route","routeNodes")
        back=candidates("routeBack","route_back")
        if towards is not None or back is not None:
            return {"route":towards or [],"route_back":back or []}
    payload=_raw_payload(decoded)
    if payload is None:return None
    try:
        from meshtastic.protobuf import mesh_pb2
        route=mesh_pb2.RouteDiscovery()
        route.ParseFromString(payload)
        return {"route":list(route.route),"route_back":list(route.route_back)}
    except Exception:
        return None


def traceroute_segments(packet, decoded):
    """Port Traffic Analyzer's ordered leg decomposition for raw Meshtastic RF.

    Traffic Analyzer receives requester-first, normalized MeshMonitor API
    traceroutes. Here the raw answer is sent FROM remote TO requester.
    Never bridge invalid/unknown hops or infer direct RF from an empty route.
    """
    found = decoded_traceroute(decoded)
    if found is None:
        return None
    requester = number(packet.get("to", packet.get("toId")))
    remote = number(packet.get("from", packet.get("fromId")))
    if requester is None or remote is None:
        return []
    out = []
    for label, raw_route in (("route", found.get("route") or []),
                             ("route_back", found.get("route_back") or [])):
        # Unlike Traffic Analyzer's oriented API, the raw packet's empty
        # arrays are ambiguous; with no intermediate IDs, do not create links.
        if not raw_route:
            continue
        # Invalid placeholder positions must remain gaps, not be discarded
        # and connected around (e.g. A, invalid, B).
        values = [number(x) for x in raw_route]
        chain = ([requester] + values + [remote] if label == "route"
                 else [remote] + values + [requester])
        for a, b in zip(chain, chain[1:]):
            if a is None or b is None or a == b:
                continue
            out.append((min(a, b), max(a, b),
                        "observed_route_unverified_rf"))
    return list(dict.fromkeys(out))


def neighbor_segments(packet,decoded):
    """Read neighbors advertised by the sender; unverified by local receiver."""
    raw=decoded.get("neighborinfo") or decoded.get("neighborInfo") or decoded
    if not isinstance(raw,dict):return []
    data=raw.get("neighbors")
    if data is None:
        payload=_raw_payload(decoded)
        if payload is not None:
            try:
                from meshtastic.protobuf import mesh_pb2
                msg=mesh_pb2.NeighborInfo();msg.ParseFromString(payload)
                data=[{"nodeId":n.node_id} for n in msg.neighbors]
            except Exception:return []
    if not isinstance(data,(list,tuple)):return []
    sender=number(packet.get("from",packet.get("fromId")))
    if sender is None:return []
    edges=[]
    for info in data[:150]:
        if isinstance(info,dict):
            node=number(info.get("nodeId",info.get("node_id")))
        else:node=number(info)
        if node and node!=sender:
            edges.append((min(sender,node),max(sender,node),"neighbor_reported_unverified_rf"))
    return list(dict.fromkeys(edges))


def extract_topology(packet):
    decoded=packet.get("decoded") if isinstance(packet.get("decoded"),dict) else {}
    raw=decoded.get("portnum")
    port=str(raw).upper()
    try:code=int(raw)
    except (ValueError,TypeError):code=None
    if port=="TRACEROUTE_APP" or code==70:
        return "traceroute",traceroute_segments(packet,decoded)
    if port=="NEIGHBORINFO_APP" or code==71:
        return "neighbor",neighbor_segments(packet,decoded)
    return None,None
