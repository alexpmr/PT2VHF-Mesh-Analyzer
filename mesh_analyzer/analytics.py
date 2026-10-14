"""Auditable Meshtastic analytics from the standalone SQLite database.

All measurements are observations from configured receivers, not a reconstruction
of the entire RF network. A route is not evidence of a direct physical link.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
import math
import time

PERIODS = {"1h": 3600, "6h": 21600, "24h": 86400, "7d": 604800,
           "30d": 2592000, "all": None}
BROADCAST = 0xFFFFFFFF


def parse_filters(params=None):
    params = params or {}
    period = str(params.get("period") or "24h")
    if period not in PERIODS:
        raise ValueError("Período inválido")
    result = {"period": period}
    for key in ("source", "node", "channel"):
        raw = params.get(key)
        if raw in (None, "", "all"):
            result[key] = None
        else:
            value = int(raw)
            if not 0 <= value <= 0xFFFFFFFF:
                raise ValueError("Filtro inválido: " + key)
            result[key] = value
    return result


def _where(filters, table="packets", only_origin=False):
    start = (int(time.time()) - PERIODS[filters["period"]]) * 1000 if PERIODS[filters["period"]] else None
    where, args = [], []
    if start is not None:
        where.append("timestamp_ms >= ?")
        args.append(start)
    if filters["source"] is not None:
        where.append("source_id = ?")
        args.append(filters["source"])
    if filters["node"] is not None:
        if only_origin:
            where.append("from_node = ?")
            args.append(filters["node"])
        else:
            where.append("(from_node = ? OR to_node = ?)")
            args.extend([filters["node"], filters["node"]])
    if filters["channel"] is not None and table in ("packets", "messages"):
        where.append("channel = ?")
        args.append(filters["channel"])
    return (" WHERE " + " AND ".join(where) if where else ""), tuple(args)


def _aggregate(db, sql, params=()):
    rows = db._rows(sql, params)
    return rows[0] if rows else {}


def calculate(db, params=None, connection_status=None):
    filters = parse_filters(params)
    clause, args = _where(filters)
    count = _aggregate(db, """SELECT
        COUNT(*) as observations,
        SUM(CASE WHEN via_mqtt=1 THEN 1 ELSE 0 END) as mqtt,
        SUM(CASE WHEN via_mqtt=0 THEN 1 ELSE 0 END) as receiver,
        COUNT(DISTINCT from_node) as originators,
        COUNT(DISTINCT source_id) as receivers,
        AVG(CASE WHEN via_mqtt=0 THEN rx_snr END) as mean_snr,
        AVG(CASE WHEN via_mqtt=0 THEN rx_rssi END) as mean_rssi,
        SUM(CASE WHEN port='TRACEROUTE_APP' THEN 1 ELSE 0 END) as traceroutes,
        SUM(CASE WHEN port='TELEMETRY_APP' THEN 1 ELSE 0 END) as telemetry
        FROM packets""" + clause, args)
    total_nodes = _aggregate(db, "SELECT COUNT(*) as n FROM nodes").get("n") or 0
    cutoff = (int(time.time()) - 7200) * 1000
    recent_nodes = _aggregate(db, "SELECT COUNT(*) as n FROM nodes WHERE last_seen_ms >= ?", (cutoff,)).get("n") or 0
    # A NodeDB import can contain cached timestamps. Count originators in observed
    # packets for the selected period separately from node-catalog activity.
    active = int(count.get("originators") or 0)
    msg_clause, msg_args = _where(filters, "messages")
    msg = _aggregate(db, "SELECT COUNT(*) as n FROM messages" + msg_clause, msg_args)
    types = db._rows("SELECT COALESCE(port,'UNKNOWN') as name, COUNT(*) as count FROM packets"
                     + clause + " GROUP BY COALESCE(port,'UNKNOWN') ORDER BY count DESC LIMIT 20", args)
    sources = db._rows("SELECT source_id as id, COUNT(*) as count,"
                       " AVG(CASE WHEN via_mqtt=0 THEN rx_snr END) as mean_snr"
                       " FROM packets" + clause + " GROUP BY source_id ORDER BY count DESC", args)
    origins = db._rows("SELECT from_node as id, COUNT(*) as count FROM packets" + clause
                       + " AND from_node IS NOT NULL GROUP BY from_node ORDER BY count DESC LIMIT 20"
                       if clause else "SELECT from_node as id, COUNT(*) as count FROM packets WHERE from_node IS NOT NULL GROUP BY from_node ORDER BY count DESC LIMIT 20", args)
    # Use SQL aggregation rather than truncating to a recent packet limit.
    hourly = db._rows("SELECT (timestamp_ms / 3600000) * 3600000 as timestamp_ms,"
                      " COUNT(*) as count, SUM(via_mqtt) as mqtt FROM packets" + clause
                      + " GROUP BY (timestamp_ms / 3600000) ORDER BY timestamp_ms DESC LIMIT 168", args)
    hourly.reverse()
    hops = db._rows("SELECT (hop_start-hop_limit) as hops, COUNT(*) as count FROM packets" +
                    (clause+" AND " if clause else " WHERE ") +
                    "hop_start IS NOT NULL AND hop_limit IS NOT NULL"
                    " AND hop_start >= hop_limit GROUP BY (hop_start-hop_limit) ORDER BY hops", args)
    # Keep relation counts aligned to the period/source/node filters. The
    # relationship table does not encode channel; do not invent that filter.
    link_where,link_args=[],[]
    if PERIODS[filters["period"]]:
        link_where.append("last_seen_ms >= ?")
        link_args.append((int(time.time())-PERIODS[filters["period"]])*1000)
    if filters["source"] is not None:
        link_where.append("source_id = ?")
        link_args.append(filters["source"])
    if filters["node"] is not None:
        link_where.append("(a = ? OR b = ?)")
        link_args.extend([filters["node"],filters["node"]])
    link_sql=" WHERE "+" AND ".join(link_where) if link_where else ""
    links=db._rows("SELECT quality, COUNT(*) as count, SUM(observations) as observations"
                   " FROM links"+link_sql+" GROUP BY quality ORDER BY observations DESC",tuple(link_args))
    # 'quality' can represent an observed traceroute without confirming RF.
    node_rows = db._rows("SELECT node_num, node_id, long_name, short_name, role, hw_model,"
                         " latitude, longitude, position_ms, first_seen_ms, last_seen_ms, battery, voltage, snr"
                         " FROM nodes ORDER BY last_seen_ms DESC LIMIT 5000")
    node_names = {n["node_num"]: n["long_name"] or n["short_name"] or n["node_id"] for n in node_rows}
    for p in origins:
        p["name"] = node_names.get(p["id"], f"!{p['id']:08x}" if p["id"] is not None else "—")
    for s in sources:
        meta = db.source(s["id"], public=True)
        s["name"] = meta["name"] if meta else f"Conexão histórica #{s['id']}"
        s["kind"] = meta["kind"] if meta else "unknown"
        s["connection"] = (connection_status or {}).get(str(s["id"]), {}).get("status", "não informado")
    message_by_channel=db._rows(
        "SELECT channel, COUNT(*) AS count FROM messages"+msg_clause+
        " GROUP BY channel ORDER BY count DESC",msg_args)
    message_by_direction=db._rows(
        "SELECT direction, COUNT(*) AS count FROM messages"+msg_clause+
        " GROUP BY direction ORDER BY count DESC",msg_args)
    message_originators=db._rows(
        "SELECT from_node as node_num,COUNT(*) as count FROM messages"+
        (msg_clause+" AND " if msg_clause else " WHERE ")+
        "from_node IS NOT NULL GROUP BY from_node ORDER BY count DESC LIMIT 30",msg_args)
    for row in message_originators:
        row["name"]=node_names.get(row["node_num"],f"!{row['node_num']:08x}")
    # Only positively classified RF-direct records are ranking candidates.
    # A route/neighbor/MQTT record must never be promoted to direct RF.
    confirmed_where=["quality='confirmed_direct_rf'"]+link_where
    confirmed_links=db._rows(
        "SELECT a,b,source_id,quality,observations,last_seen_ms FROM links WHERE "+
        " AND ".join(confirmed_where)+" ORDER BY last_seen_ms DESC LIMIT 500",
        tuple(link_args))
    coords={n["node_num"]:n for n in node_rows}
    direct_rank=[]
    for link in confirmed_links:
        a,b=coords.get(link["a"]),coords.get(link["b"])
        if not a or not b:continue
        if any(n["latitude"] is None or n["longitude"] is None or not n["position_ms"] for n in (a,b)):
            continue
        # Historical/mobile links cannot inherit coordinates far from their
        # RF observation. Position timestamps require close temporal agreement.
        if any(abs(n["position_ms"]-link["last_seen_ms"])>1800000 for n in (a,b)):
            continue
        lat1,lon1,lat2,lon2=map(math.radians,
             [a["latitude"],a["longitude"],b["latitude"],b["longitude"]])
        delta=2*6371.0088*math.asin(min(1,math.sqrt(
              math.sin((lat2-lat1)/2)**2+
              math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2)))
        direct_rank.append({"a":link["a"],"b":link["b"],"name_a":node_names[link["a"]],
                            "name_b":node_names[link["b"]],"distance_km":round(delta,3),
                            "observations":link["observations"],"snr":None,
                            "source_id":link["source_id"],"last_rf_ms":link["last_seen_ms"]})
    direct_rank.sort(key=lambda x:(-x["distance_km"],x["a"],x["b"]))
    direct_rank=direct_rank[:10]
    silent = [n for n in node_rows if n["last_seen_ms"] < cutoff and n["last_seen_ms"] > 0]
    low_battery = [n for n in node_rows if n["battery"] is not None and 0 <= n["battery"] < 20]
    alerts = ([{"severity": "atenção", "kind": "nó silencioso",
                "node": n["node_id"], "description": "Sem observação recente no inventário local"}
               for n in silent[:35]] +
              [{"severity": "crítico" if n["battery"] < 10 else "atenção",
                "kind": "bateria", "node": n["node_id"],
                "description": f"Bateria registrada: {n['battery']}%"}
               for n in low_battery[:35]])
    alerts.sort(key=lambda x: (0 if x["severity"] == "crítico" else 1, x["node"]))
    rx_samples = db._rows("SELECT source_id,node_num,timestamp_ms,rx_good,rx_bad,"
                          "channel_util,air_util,voltage,battery FROM rf_samples ORDER BY timestamp_ms DESC LIMIT 5000")
    rf_summary = []
    grouped = defaultdict(list)
    for item in rx_samples:
        grouped[(item["source_id"], item["node_num"])].append(item)
    for (source, node), samples in grouped.items():
        samples.sort(key=lambda x: x["timestamp_ms"])
        newest = samples[-1]
        rates = []
        for a,b in zip(samples,samples[1:]):
            if a["rx_good"] is None or a["rx_bad"] is None or b["rx_good"] is None or b["rx_bad"] is None:
                continue
            total = b["rx_good"] - a["rx_good"]
            bad = b["rx_bad"] - a["rx_bad"]
            # LocalStats num_packets_rx is received total, num_packets_rx_bad
            # is an invalid subset; neither is an explicit CRC counter.
            if total <= 0 or bad < 0 or bad > total:
                continue
            rates.append((total,bad))
        total_rx = sum(x for x,_ in rates)
        bad = sum(y for _,y in rates)
        rf_summary.append({"source":source, "node":node_names.get(node, f"!{node:08x}"),
                           "node_num":node,"samples":len(samples),
                           "last_seen_ms":newest["timestamp_ms"],
                           "channel_util": newest["channel_util"],
                           "air_util": newest["air_util"],
                           "voltage": newest["voltage"],
                           "battery": newest["battery"],
                           "rx_total_delta": total_rx if rates else None,
                           "rx_bad_delta": bad if rates else None,
                           "rx_invalid_percent": round(100*bad/total_rx,2) if total_rx else None,
                           "crc_error_percent": None,
                           "crc_note": "Contador específico de CRC não disponível; RX inválido ≠ erro de CRC."})
    return {
        "success": True, "generated_ms": int(time.time()*1000), "filters":filters,
        "scope": "Observações recebidas por conexões cadastradas; não representa todo o tráfego no ar.",
        "counts": {"nodes_known": total_nodes,"nodes_recent_catalog": recent_nodes,
                   "active_originators": active, "observations":int(count.get("observations") or 0),
                   "mqtt":int(count.get("mqtt") or 0),"receiver":int(count.get("receiver") or 0),
                   "messages":int(msg.get("n") or 0),
                   "rx_observations":int(count.get("observations") or 0),
                   "tx_observations":None,
                   "traceroutes":int(count.get("traceroutes") or 0),
                   "telemetry":int(count.get("telemetry") or 0),
                   "sources_observed":int(count.get("receivers") or 0),
                   "mean_snr":count.get("mean_snr"), "mean_rssi":count.get("mean_rssi"),
                   "relations_observed":sum(int(v["count"]) for v in links),
                   "confirmed_direct_rf":None,
                   "alerts":len(alerts), "critical":sum(a["severity"]=="crítico" for a in alerts)},
        "packet_types":types, "source_breakdown":sources, "top_originators":origins,
        "message_by_channel":message_by_channel,"message_by_direction":message_by_direction,
        "message_originators":message_originators,"direct_rf_rank":direct_rank,
        "hourly":hourly,"hops":hops,"link_types":links,"alerts":alerts,
        "nodes":node_rows,"rf_samples":rf_summary,
        "diagnosis": {
            "external_lora": "Não observável pelos dados atuais; receptor SDR/CAD dedicado necessário.",
            "noise_floor": "Não medido; RSSI de pacotes não equivale a piso de ruído.",
            "crc": "Indisponível: contadores específicos de CRC não são registrados.",
            "coexistence": "Sobreposição RF exige frequência central, BW/SF e medições por receptor.",
            "possible_causes": ["Enlace marginal / fading / obstrução",
                                "Colisões de transmissões simultâneas",
                                "Interferência de outras redes LoRa ou não-LoRa",
                                "Antena, cabo, conectores, alimentação e configuração"],
            "confidence":"Dados insuficientes para determinar a causa por RF",
        },
    }
