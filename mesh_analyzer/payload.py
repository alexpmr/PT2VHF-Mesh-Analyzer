"""Conteúdo legível dos pacotes (aba Tráfego, v0.6.62).

O pacote decodificado já é guardado em `packets.raw_json`; aqui ele vira um resumo curto
para a tabela e uma lista de campos para o painel de detalhes, conforme o tipo
(telemetria, posição, NodeInfo, roteamento, traceroute, vizinhos e texto).
"""
from __future__ import annotations

import json


def _get(d, *names, default=None):
    for name in names:
        if isinstance(d, dict) and name in d and d[name] is not None:
            return d[name]
    return default


def _num(v, decimals=1):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    text = ("%.*f" % (decimals, f)).rstrip("0").rstrip(".") if decimals else "%d" % round(f)
    return text.replace(".", ",")


def _node(v):
    try:
        n = int(v)
    except (TypeError, ValueError):
        return str(v)
    return "!%08x" % (n & 0xFFFFFFFF)


def _decoded(raw):
    try:
        packet = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except ValueError:
        return {}
    return packet.get("decoded") or {} if isinstance(packet, dict) else {}


def _telemetry(t):
    fields, summary = [], []
    dev = _get(t, "deviceMetrics", "device_metrics") or {}
    env = _get(t, "environmentMetrics", "environment_metrics") or {}
    power = _get(t, "powerMetrics", "power_metrics") or {}
    local = _get(t, "localStats", "local_stats") or {}
    battery = _get(dev, "batteryLevel", "battery_level")
    if battery is not None:
        label = "externa (USB/fonte)" if int(battery) > 100 else _num(battery, 0) + "%"
        fields.append(("Bateria", label))
        summary.append("🔋 " + ("EXT" if int(battery) > 100 else _num(battery, 0) + "%"))
    for key, label, unit, short in (("voltage", "Tensão", " V", True), ("channelUtilization", "Utilização do canal", "%", True),
                                    ("airUtilTx", "Airtime TX", "%", False), ("uptimeSeconds", "Ligado há", "", False)):
        v = _get(dev, key, key[0].lower() + "".join("_" + c.lower() if c.isupper() else c for c in key[1:]))
        if v is None:
            continue
        if key == "uptimeSeconds":
            text = "%d h %02d min" % (int(v) // 3600, int(v) % 3600 // 60)
        else:
            text = _num(v, 2 if key == "voltage" else 1) + unit
        fields.append((label, text))
        if short:
            summary.append(("canal " if key == "channelUtilization" else "") + text)
    for key, label, unit in (("temperature", "Temperatura", " °C"), ("relativeHumidity", "Umidade", "%"),
                             ("barometricPressure", "Pressão", " hPa"), ("gasResistance", "Gás", " MΩ"),
                             ("iaq", "IAQ", ""), ("lux", "Luz", " lx"), ("windSpeed", "Vento", " m/s")):
        v = _get(env, key)
        if v is not None:
            fields.append((label, _num(v, 1) + unit))
            if key in ("temperature", "relativeHumidity", "barometricPressure"):
                summary.append(_num(v, 1) + unit)
    for key, label in (("ch1Voltage", "Canal 1 (V)"), ("ch1Current", "Canal 1 (mA)"), ("ch2Voltage", "Canal 2 (V)")):
        v = _get(power, key)
        if v is not None:
            fields.append((label, _num(v, 2)))
    for key, label in (("numPacketsTx", "Pacotes TX"), ("numPacketsRx", "Pacotes RX"), ("numOnlineNodes", "Nós online"),
                       ("numTotalNodes", "Nós no NodeDB"), ("numPacketsRxBad", "Pacotes RX com erro")):
        v = _get(local, key)
        if v is not None:
            fields.append((label, _num(v, 0)))
    if local and not summary:
        online = _get(local, "numOnlineNodes")
        if online is not None:
            summary.append("%s nós online" % _num(online, 0))
    return summary, fields


def _position(p):
    lat = _get(p, "latitude")
    lon = _get(p, "longitude")
    if lat is None and _get(p, "latitudeI", "latitude_i") is not None:
        lat = _get(p, "latitudeI", "latitude_i") / 1e7
        lon = (_get(p, "longitudeI", "longitude_i") or 0) / 1e7
    fields, summary = [], []
    if lat is not None and lon is not None:
        coord = "%.5f, %.5f" % (float(lat), float(lon))
        fields.append(("Coordenadas", coord))
        summary.append("📍 " + coord)
    alt = _get(p, "altitude")
    if alt is not None:
        fields.append(("Altitude", _num(alt, 0) + " m"))
        summary.append(_num(alt, 0) + " m")
    sats = _get(p, "satsInView", "sats_in_view")
    if sats is not None:
        fields.append(("Satélites", _num(sats, 0)))
        summary.append("%s sat." % _num(sats, 0))
    for key, label in (("groundSpeed", "Velocidade (m/s)"), ("precisionBits", "Precisão (bits)"), ("PDOP", "PDOP")):
        v = _get(p, key)
        if v is not None:
            fields.append((label, _num(v, 1)))
    return summary, fields


def _user(u):
    fields = [(label, str(_get(u, *keys))) for label, keys in
              (("Nome longo", ("longName", "long_name")), ("Nome curto", ("shortName", "short_name")),
               ("Hardware", ("hwModel", "hw_model")), ("Papel", ("role",)), ("ID", ("id",)))
              if _get(u, *keys) is not None]
    name = _get(u, "longName", "long_name") or _get(u, "shortName", "short_name") or ""
    hw = _get(u, "hwModel", "hw_model")
    return ["👤 " + str(name)] + ([str(hw)] if hw else []), fields


def _route(r, title):
    fields, summary = [], []
    route = _get(r, "route") or []
    back = _get(r, "routeBack", "route_back") or []
    snr = _get(r, "snrTowards", "snr_towards") or []
    if route:
        hops = " → ".join(_node(n) for n in route)
        fields.append(("Rota (ida)", hops))
        summary.append("%d salto(s)" % len(route))
    if snr:
        # O firmware guarda o SNR de cada salto em quartos de dB (int8 = dB × 4).
        fields.append(("SNR por salto (dB)", " · ".join(_num(v / 4, 2) for v in snr)))
    if back:
        fields.append(("Rota (volta)", " → ".join(_node(n) for n in back)))
    if not route and not back:
        summary.append(title + " direto")
    return summary, fields


def describe(port, raw_json, text_preview=""):
    """(resumo curto, [(campo, valor), ...]) do conteúdo de um pacote."""
    d = _decoded(raw_json)
    port = str(port or "")
    try:
        if port == "TELEMETRY_APP":
            summary, fields = _telemetry(_get(d, "telemetry") or {})
        elif port == "POSITION_APP":
            summary, fields = _position(_get(d, "position") or {})
        elif port == "NODEINFO_APP":
            summary, fields = _user(_get(d, "user") or {})
        elif port == "TRACEROUTE_APP":
            summary, fields = _route(_get(d, "traceroute") or {}, "traceroute")
        elif port == "ROUTING_APP":
            routing = _get(d, "routing") or {}
            err = _get(routing, "errorReason", "error_reason")
            summary = ["✔ entregue (ACK)" if err in (None, "NONE", 0) else "✖ " + str(err)]
            fields = [("Resultado", summary[0])]
            if _get(routing, "routeReply", "route_reply"):
                s2, f2 = _route(_get(routing, "routeReply", "route_reply"), "rota")
                fields += f2
        elif port == "NEIGHBORINFO_APP":
            info = _get(d, "neighborinfo", "neighborInfo") or {}
            neigh = _get(info, "neighbors") or []
            summary = ["%d vizinho(s)" % len(neigh)]
            fields = [("Vizinhos", ", ".join("%s (SNR %s)" % (_node(_get(n, "nodeId", "node_id")), _num(_get(n, "snr"), 1))
                                             for n in neigh) or "—")]
        elif port in ("TEXT_MESSAGE_APP", "1"):
            text = text_preview or _get(d, "text") or ""
            summary, fields = (["💬 " + text[:60]] if text else []), [("Texto", text)] if text else []
        else:
            summary, fields = [], []
    except (TypeError, ValueError, AttributeError):
        summary, fields = [], []
    if not fields and d:
        keys = [k for k in d if k not in ("portnum", "payload", "bitfield", "raw")]
        if keys:
            fields = [("Campos", ", ".join(keys))]
    return " · ".join(x for x in summary if x)[:120], fields


def packet_detail(row):
    """Detalhe de um pacote: campos legíveis e o JSON completo (formatado)."""
    summary, fields = describe(row.get("port"), row.get("raw_json"), row.get("text_preview") or "")
    try:
        pretty = json.dumps(json.loads(row.get("raw_json") or "{}"), ensure_ascii=False, indent=2)
    except ValueError:
        pretty = row.get("raw_json") or ""
    return {"summary": summary, "fields": [{"label": k, "value": v} for k, v in fields], "json": pretty[:20000]}
