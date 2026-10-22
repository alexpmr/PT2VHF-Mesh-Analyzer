"""Análises da malha a partir do banco local.

- node_timeline (#168): séries de bateria, tensão, SNR, utilização do canal e presença.
- repeaters (#169): disponibilidade e estado dos ROUTER/REPEATER.
- coverage (#167): grade de SNR/RSSI das recepções diretas com posição conhecida.
- routes (#170): rotas de traceroute e nós intermediários mais usados (gargalos).
- terrain_profile (#171): perfil de elevação entre dois nós com zona de Fresnel.

Somente dados observados: nenhuma rota, posição ou medida é inventada.
"""
from __future__ import annotations

import json
import math
import urllib.request

from .database import now_ms
from .topology import extract_topology

REPEATER_ROLES = ("ROUTER", "REPEATER", "ROUTER_LATE", "ROUTER_CLIENT")
TRACEROUTE_PORTS = ("TRACEROUTE_APP", "70")


def _bucket_ms(hours):
    """~50–60 pontos por gráfico: 30 min (24 h), 3 h (7 d), 12 h (30 d)."""
    return 1800000 if hours <= 24 else 10800000 if hours <= 168 else 43200000


def _average(rows, field, bucket):
    acc = {}
    for r in rows:
        if r[field] is None:
            continue
        key = int(r["timestamp_ms"]) // bucket * bucket
        total, count = acc.get(key, (0.0, 0))
        acc[key] = (total + float(r[field]), count + 1)
    return [[k, round(t / c, 2)] for k, (t, c) in sorted(acc.items())]


def node_timeline(db, node, hours=24, now=None):
    now = now or now_ms()
    hours = max(1, min(int(hours), 24 * 90))
    since = now - hours * 3600000
    bucket = _bucket_ms(hours)
    node = int(node)
    samples = db._rows("""SELECT timestamp_ms,battery,voltage,channel_util,air_util FROM rf_samples
                          WHERE node_num=? AND timestamp_ms>=? ORDER BY timestamp_ms""", (node, since))
    packets = db._rows("""SELECT timestamp_ms,rx_snr,rx_rssi,via_mqtt FROM packets
                          WHERE from_node=? AND timestamp_ms>=? ORDER BY timestamp_ms""", (node, since))
    rf = [p for p in packets if not p["via_mqtt"]]
    heard = {}
    for p in packets:
        key = int(p["timestamp_ms"]) // bucket * bucket
        heard[key] = heard.get(key, 0) + 1
    buckets = list(range(since // bucket * bucket, now + 1, bucket))
    return {"node": node, "hours": hours, "bucket_ms": bucket, "since": since, "until": now,
            "battery": _average([s for s in samples if s["battery"] is None or s["battery"] <= 100], "battery", bucket),
            "voltage": _average(samples, "voltage", bucket),
            "channel_util": _average(samples, "channel_util", bucket),
            "air_util": _average(samples, "air_util", bucket),
            "snr": _average(rf, "rx_snr", bucket),
            "rssi": _average(rf, "rx_rssi", bucket),
            "heard": [[b, heard.get(b, 0)] for b in buckets],
            "packets": len(packets)}


def _intermediates(db, since):
    """Conta quantas rotas de traceroute passam por cada nó intermediário."""
    counts, routes = {}, []
    rows = db._rows("""SELECT timestamp_ms,source_id,from_node,to_node,raw_json FROM packets
                       WHERE port IN ('TRACEROUTE_APP','70') AND timestamp_ms>=? AND raw_json<>''
                       ORDER BY timestamp_ms DESC LIMIT 2000""", (since,))
    for r in rows:
        try:
            kind, edges = extract_topology(json.loads(r["raw_json"]))
        except (ValueError, TypeError):
            continue
        if kind != "traceroute" or not edges:
            continue
        ends = {r["from_node"], r["to_node"]}
        hops = sorted({n for a, b, _ in edges for n in (a, b)} - ends)
        for n in hops:
            counts[n] = counts.get(n, 0) + 1
        routes.append({"timestamp_ms": r["timestamp_ms"], "from": r["from_node"], "to": r["to_node"],
                       "edges": [[a, b, q] for a, b, q in edges], "intermediates": hops})
    return counts, routes


def routes(db, hours=24, now=None, limit=150):
    now = now or now_ms()
    counts, found = _intermediates(db, now - max(1, int(hours)) * 3600000)
    names = {r["node_num"]: r for r in db._rows("SELECT node_num,long_name,short_name,node_id,role FROM nodes")}
    ranking = sorted(counts.items(), key=lambda x: -x[1])[:30]
    total = len(found) or 1
    return {"routes": found[:limit], "total_routes": len(found),
            "bottlenecks": [{"node": n, "routes": c, "share": round(100 * c / total, 1),
                             "name": (names.get(n) or {}).get("long_name") or (names.get(n) or {}).get("short_name") or "!%08x" % n,
                             "role": (names.get(n) or {}).get("role") or ""} for n, c in ranking]}


def repeaters(db, hours=24, now=None):
    now = now or now_ms()
    hours = max(1, min(int(hours), 24 * 90))
    since = now - hours * 3600000
    marks = ",".join("?" * len(REPEATER_ROLES))
    nodes = db._rows("SELECT * FROM nodes WHERE role IN (" + marks + ")", REPEATER_ROLES)
    counts, _ = _intermediates(db, since)
    out = []
    for n in nodes:
        num = n["node_num"]
        start = max(since, int(n["first_seen_ms"] or since))
        total_hours = max(1, math.ceil((now - start) / 3600000))
        heard_hours = db._rows("""SELECT COUNT(DISTINCT timestamp_ms/3600000) AS h FROM packets
                                  WHERE from_node=? AND timestamp_ms>=?""", (num, start))[0]["h"]
        packets = db._rows("SELECT COUNT(*) AS c FROM packets WHERE from_node=? AND timestamp_ms>=?", (num, since))[0]["c"]
        sample = (db._rows("""SELECT battery,voltage,channel_util,air_util,timestamp_ms FROM rf_samples
                              WHERE node_num=? ORDER BY timestamp_ms DESC LIMIT 1""", (num,)) or [{}])[0]
        ping = (db._rows("""SELECT state,attempts,last_reply_ms FROM auto_node_queries WHERE node_num=? AND kind='ping'
                            ORDER BY sent_ms DESC LIMIT 1""", (num,)) or [{}])[0] if _has_table(db, "auto_node_queries") else {}
        out.append({"node": num, "name": n["long_name"] or n["short_name"] or n["node_id"], "role": n["role"],
                    "availability": round(100 * min(heard_hours, total_hours) / total_hours, 1),
                    "last_seen_ms": n["last_seen_ms"], "packets": packets,
                    "battery": sample.get("battery", n["battery"]), "voltage": sample.get("voltage", n["voltage"]),
                    "channel_util": sample.get("channel_util"), "air_util": sample.get("air_util"),
                    "route_hops": counts.get(num, 0), "presence": ping.get("state"),
                    "latitude": n["latitude"], "longitude": n["longitude"]})
    out.sort(key=lambda r: (r["availability"], -(r["last_seen_ms"] or 0)))
    return {"hours": hours, "repeaters": out}


def _has_table(db, name):
    return bool(db._rows("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)))


def coverage(db, hours=168, cell_deg=0.01, now=None):
    """Grade das recepções diretas (0 salto, sem MQTT) na posição do transmissor."""
    now = now or now_ms()
    since = now - max(1, int(hours)) * 3600000
    cell = max(0.002, min(float(cell_deg), 0.2))
    rows = db._rows("""SELECT p.from_node,p.rx_snr,p.rx_rssi,p.timestamp_ms,n.latitude,n.longitude FROM packets p
                       JOIN nodes n ON n.node_num=p.from_node
                       WHERE p.timestamp_ms>=? AND p.via_mqtt=0 AND p.direction='rx' AND p.rx_snr IS NOT NULL
                         AND p.hop_start IS NOT NULL AND p.hop_limit IS NOT NULL AND p.hop_start=p.hop_limit
                         AND n.latitude IS NOT NULL AND n.longitude IS NOT NULL""", (since,))
    cells = {}
    for r in rows:
        lat, lon = float(r["latitude"]), float(r["longitude"])
        if abs(lat) < 1e-6 and abs(lon) < 1e-6:
            continue
        key = (math.floor(lat / cell), math.floor(lon / cell))
        c = cells.setdefault(key, {"snr": 0.0, "rssi": 0.0, "rssi_n": 0, "count": 0, "best": -99.0, "nodes": set()})
        c["snr"] += float(r["rx_snr"]); c["count"] += 1; c["best"] = max(c["best"], float(r["rx_snr"]))
        if r["rx_rssi"] is not None:
            c["rssi"] += float(r["rx_rssi"]); c["rssi_n"] += 1
        c["nodes"].add(r["from_node"])
    return {"cell_deg": cell, "hours": int(hours), "samples": len(rows),
            "cells": [{"lat": (k[0]) * cell, "lon": (k[1]) * cell, "size": cell,
                       "snr": round(c["snr"] / c["count"], 1), "best_snr": round(c["best"], 1),
                       "rssi": round(c["rssi"] / c["rssi_n"]) if c["rssi_n"] else None,
                       "count": c["count"], "nodes": len(c["nodes"])} for k, c in cells.items()]}


# --- #171: perfil de terreno ------------------------------------------------------
EARTH_R = 6371000.0


def _haversine(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * EARTH_R * math.asin(math.sqrt(h))


def _fetch_elevations(points):
    lats = ",".join("%.5f" % p[0] for p in points)
    lons = ",".join("%.5f" % p[1] for p in points)
    url = "https://api.open-meteo.com/v1/elevation?latitude=" + lats + "&longitude=" + lons
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            values = [float(x) for x in json.loads(resp.read())["elevation"]]
    except Exception as exc:
        raise RuntimeError("Não foi possível consultar as elevações do terreno (Open-Meteo). "
                           "Verifique a conexão com a internet.") from exc
    if len(values) != len(points):
        raise RuntimeError("Resposta de elevação incompleta")
    return values


def terrain_profile(a, b, freq_mhz=915.0, height_a=2.0, height_b=2.0, samples=60, elevations=None):
    """Perfil entre a=(lat,lon) e b=(lat,lon): terreno, linha de visada e 1ª zona de Fresnel."""
    samples = max(10, min(int(samples), 100))
    dist = _haversine(a, b)
    if dist < 10:
        raise ValueError("Os dois nós estão na mesma posição")
    points = [(a[0] + (b[0] - a[0]) * i / (samples - 1), a[1] + (b[1] - a[1]) * i / (samples - 1)) for i in range(samples)]
    elev = elevations(points) if elevations else _fetch_elevations(points)
    wavelength = 299.792458 / float(freq_mhz)
    start, end = elev[0] + height_a, elev[-1] + height_b
    profile, worst = [], None
    for i, (p, ground) in enumerate(zip(points, elev)):
        d1 = dist * i / (samples - 1)
        d2 = dist - d1
        # Curvatura da Terra com k=4/3 (refração atmosférica padrão).
        bulge = d1 * d2 / (2 * EARTH_R * 4 / 3)
        los = start + (end - start) * d1 / dist
        fresnel = math.sqrt(wavelength * d1 * d2 / dist) if 0 < i < samples - 1 else 0.0
        effective = ground + bulge
        clearance = los - effective
        ratio = clearance / fresnel if fresnel else None
        profile.append({"distance_m": round(d1), "ground_m": round(ground, 1), "terrain_m": round(effective, 1),
                        "los_m": round(los, 1), "fresnel_m": round(fresnel, 1)})
        if ratio is not None and (worst is None or ratio < worst["ratio"]):
            worst = {"distance_m": round(d1), "clearance_m": round(clearance, 1), "ratio": round(ratio, 2)}
    if worst is None or worst["ratio"] >= 0.6:
        verdict = "Visada livre: pelo menos 60% da 1ª zona de Fresnel desobstruída."
    elif worst["clearance_m"] > 0:
        verdict = "Visada com obstrução parcial da zona de Fresnel: enlace possível, com perdas."
    else:
        verdict = "Sem visada direta: o terreno bloqueia a linha entre os nós."
    return {"distance_m": round(dist), "freq_mhz": freq_mhz, "profile": profile, "worst": worst, "verdict": verdict}
