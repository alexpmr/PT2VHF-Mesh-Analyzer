"""Opt-in, rate-limited RF enrichment of incomplete Meshtastic node records.

The scheduler never infers missing attributes, retransmits to MQTT, or claims
ACK/transmission is a remote response. One request may be outstanding at a time.
"""
from __future__ import annotations

import json
import threading
import time

KINDS = ("nodeinfo", "position", "telemetry", "traceroute", "neighbors", "ping")
DEFAULTS = {
    "enabled": False,
    "types": {"nodeinfo": True, "position": True, "telemetry": True,
              "traceroute": False, "neighbors": False, "ping": False},
    "evaluate_minutes": 15,
    "max_per_hour": 6,
    "min_gap_seconds": 60,
    "recent_hours": 72,
    "ages_hours": {"nodeinfo": 720, "position": 168,
                   "telemetry": 24, "traceroute": 336},
}
PORT_KIND = {"NODEINFO_APP": "nodeinfo", "POSITION_APP": "position",
             "TELEMETRY_APP": "telemetry", "TRACEROUTE_APP": "traceroute"}
THROTTLE_STATES = ("awaiting_reply",)


class NodeEnrichment:
    def __init__(self, db, sources):
        self.db = db
        self.sources = sources
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread = None
        self._last_error = ""
        self._last_run_ms = 0
        with db._lock, db._db:
            db._db.execute("""CREATE TABLE IF NOT EXISTS auto_node_queries (
                source_id INTEGER NOT NULL, node_num INTEGER NOT NULL,
                kind TEXT NOT NULL, request_id TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT 'never',
                sent_ms INTEGER NOT NULL DEFAULT 0,
                due_ms INTEGER NOT NULL DEFAULT 0,
                attempts INTEGER NOT NULL DEFAULT 0,
                last_reply_ms INTEGER NOT NULL DEFAULT 0,
                error TEXT NOT NULL DEFAULT '',
                PRIMARY KEY(source_id,node_num,kind)
            )""")
            db._db.execute("""CREATE TABLE IF NOT EXISTS auto_query_transmissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL, node_num INTEGER NOT NULL,
                kind TEXT NOT NULL, sent_ms INTEGER NOT NULL
            )""")
            db._db.execute("""CREATE INDEX IF NOT EXISTS idx_auto_query_transmissions_time
                              ON auto_query_transmissions(sent_ms)""")
            db._db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
                           ("node_enrichment", json.dumps(DEFAULTS)))

    def config(self):
        with self.db._lock:
            r = self.db._db.execute(
                "SELECT value FROM settings WHERE key='node_enrichment'").fetchone()
        try:
            stored = json.loads(r[0]) if r else {}
        except (TypeError, ValueError):
            stored = {}
        if not isinstance(stored, dict):
            stored = {}
        result = {**DEFAULTS, **{k: stored[k] for k in DEFAULTS if k in stored}}
        result["types"] = {k: bool((stored.get("types") or {}).get(k, DEFAULTS["types"][k]))
                           for k in KINDS}
        result["ages_hours"] = {k: int((stored.get("ages_hours") or {}).get(k, v))
                               for k, v in DEFAULTS["ages_hours"].items()}
        return result

    def save(self, patch):
        if not isinstance(patch, dict):
            raise ValueError("Configuração inválida")
        allowed = {"enabled", "types", "evaluate_minutes", "max_per_hour",
                   "min_gap_seconds", "recent_hours", "ages_hours"}
        if set(patch) - allowed:
            raise ValueError("Parâmetro desconhecido da automação")
        config = self.config()
        if "enabled" in patch:
            if type(patch["enabled"]) is not bool:
                raise ValueError("Ativação inválida")
            config["enabled"] = patch["enabled"]
        if "types" in patch:
            types = patch["types"]
            if not isinstance(types, dict) or set(types) - set(KINDS):
                raise ValueError("Tipos de consulta inválidos")
            for k, v in types.items():
                if type(v) is not bool:
                    raise ValueError("Seleção inválida: " + k)
                config["types"][k] = v
        for name, lo, hi in (("evaluate_minutes", 1, 1440),
                             ("max_per_hour", 1, 24),
                             ("min_gap_seconds", 30, 3600),
                             ("recent_hours", 1, 720)):
            if name in patch:
                value = patch[name]
                if type(value) is not int or not lo <= value <= hi:
                    raise ValueError("Valor inválido: " + name)
                config[name] = value
        if "ages_hours" in patch:
            values = patch["ages_hours"]
            if not isinstance(values, dict) or set(values) - set(DEFAULTS["ages_hours"]):
                raise ValueError("Prazos de atualização inválidos")
            for k, v in values.items():
                if type(v) is not int or not 1 <= v <= 8760:
                    raise ValueError("Prazo inválido: " + k)
                config["ages_hours"][k] = v
        with self.db._lock, self.db._db:
            self.db._db.execute("UPDATE settings SET value=? WHERE key='node_enrichment'",
                                (json.dumps(config),))
        self._wake.set()
        return config

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="meshtastic-node-enrichment")
        self._thread.start()

    def close(self):
        self._stop.set()
        self._wake.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)

    def _loop(self):
        while not self._stop.is_set():
            try:
                if self.config()["enabled"]:
                    self.tick()
            except Exception as exc:
                self._last_error = type(exc).__name__ + ": " + str(exc)[:130]
                self.db.log("Automação RF: erro " + type(exc).__name__, "warning")
            minutes = self.config()["evaluate_minutes"]
            self._wake.wait(max(30, minutes * 60))
            self._wake.clear()

    def _connection(self):
        snapshot = self.sources.snapshot()
        ready = []
        for src in self.db.sources():
            if src.get("kind") == "mqtt" or not src.get("enabled"):
                continue
            state = snapshot.get(str(src["id"]), {})
            if state.get("status") != "connected" or not state.get("tx_capable"):
                continue
            caps = self.sources.queries.capabilities(src["id"])
            if caps.get("ready"):
                ready.append((src["id"], caps.get("supported", []), state.get("local_node_num")))
        if len(ready) != 1:
            return None, ("Nenhum rádio TX disponível" if not ready else
                          "Mais de um rádio ativo: mantenha somente uma conexão")
        return ready[0], ""

    def _attempts(self, source_id):
        if source_id is None:
            return {}
        with self.db._lock:
            rows = self.db._db.execute(
                "SELECT * FROM auto_node_queries WHERE source_id=?", (source_id,)
            ).fetchall()
        return {(r["node_num"], r["kind"]): dict(r) for r in rows}

    def _observed(self, source_id, now, max_age):
        # RX provenance is required: old NodeDB cache alone is not RF reachability.
        return self.db._rows("""SELECT n.*,ns.source_id,ns.observed AS radio_observed,
                    ns.last_seen_ms AS source_last_seen
          FROM nodes n JOIN node_sources ns ON ns.node_num=n.node_num
          WHERE ns.source_id=? AND ns.observed=1 AND ns.last_seen_ms>=?
          ORDER BY ns.last_seen_ms DESC LIMIT 15000""",
          (source_id,now-max_age,))

    def _freshness(self, now, max_age):
        # Single bounded scan of the recent packet index for passive updates.
        rows = self.db._rows("""SELECT from_node,port,MAX(timestamp_ms) AS last_ms
          FROM packets WHERE timestamp_ms >= ? AND from_node IS NOT NULL
            AND port IN ('NODEINFO_APP','POSITION_APP','TELEMETRY_APP','TRACEROUTE_APP')
          GROUP BY from_node,port""", (now-max_age,))
        return {(r["from_node"], PORT_KIND[r["port"]]): r["last_ms"]
                for r in rows if r["port"] in PORT_KIND}

    def _candidates(self, source_id, supported, own, config, now):
        observed = self._observed(source_id, now, config["recent_hours"]*3600000)
        attempts = self._attempts(source_id)
        freshness = self._freshness(now, 365*86400000)
        result = []
        for node in observed:
            num = node["node_num"]
            if num == own or not 0 < num < 0xffffffff:
                continue
            # Give brand-new nodes time to announce metadata spontaneously.
            if now - int(node["first_seen_ms"] or now) < 180000:
                continue
            for kind in ("nodeinfo", "position", "telemetry", "traceroute"):
                if kind not in supported or not config["types"].get(kind):
                    continue
                if kind == "nodeinfo":
                    present = bool(node["long_name"] and node["short_name"] and node["hw_model"])
                elif kind == "position":
                    present = node["latitude"] is not None and node["longitude"] is not None
                elif kind == "telemetry":
                    present = node["battery"] is not None or node["voltage"] is not None
                else:
                    present = True  # Traceroute is explicitly opt-in; no fabricated route.
                seen = int(freshness.get((num, kind)) or 0)
                if kind == "position":
                    seen = max(seen, int(node["position_ms"] or 0))
                ttl = config["ages_hours"][kind]*3600000
                incomplete = not present
                if present and kind != "traceroute" and seen and now-seen < ttl:
                    continue  # Fresh broadcasts already satisfy the target.
                if kind == "traceroute" and seen and now-seen < ttl:
                    continue
                previous = attempts.get((num, kind))
                if previous and int(previous["due_ms"]) > now:
                    continue
                result.append({"node": num, "kind": kind,
                               "name": node["long_name"] or node["short_name"] or node["node_id"],
                               "reason": "Informação ausente" if incomplete else
                                         ("Data sem confirmação recente" if not seen else
                                          "Atualização vencida"),
                               "last_seen_ms": node["source_last_seen"],
                               "previous": previous})
        # Missing info first, then newest observed node, with oldest attempts fairly recycled.
        result.sort(key=lambda c: (0 if c["reason"] == "Informação ausente" else 1,
                                   int(c["previous"]["sent_ms"]) if c["previous"] else 0,
                                   -int(c["last_seen_ms"])))
        return result

    def _record(self, source_id, node, kind, reqid, state, now, due, attempts, error=""):
        with self.db._lock, self.db._db:
            self.db._db.execute("""INSERT INTO auto_node_queries
              (source_id,node_num,kind,request_id,state,sent_ms,due_ms,attempts,error)
              VALUES(?,?,?,?,?,?,?,?,?)
              ON CONFLICT(source_id,node_num,kind) DO UPDATE SET
              request_id=excluded.request_id,state=excluded.state,
              sent_ms=excluded.sent_ms,due_ms=excluded.due_ms,
              attempts=excluded.attempts,error=excluded.error""",
              (source_id,node,kind,reqid,state,now,due,attempts,error[:150]))
            if state == "awaiting_reply":
                self.db._db.execute("""INSERT INTO auto_query_transmissions
                  (source_id,node_num,kind,sent_ms) VALUES(?,?,?,?)""",
                  (source_id,node,kind,now))

    def _reconcile(self, now):
        active = self.db._rows(
            "SELECT * FROM auto_node_queries WHERE state='awaiting_reply'")
        if not active:
            return False
        live = {r["request_id"]: r for r in self.sources.queries.status()}
        for row in active:
            q = live.get(row["request_id"])
            state = q.get("state") if q else None
            if state in ("replied", "timeout", "disconnected", "error"):
                ok = state == "replied"
                attempts = 0 if ok else min(9, row["attempts"]+1)
                delay = 6*3600000 if ok else min(86400000, 900000*(2**min(attempts, 6)))
                with self.db._lock, self.db._db:
                    self.db._db.execute("""UPDATE auto_node_queries SET
                      state=?,attempts=?,due_ms=?,last_reply_ms=CASE WHEN ? THEN ? ELSE last_reply_ms END,
                      error=? WHERE source_id=? AND node_num=? AND kind=?""",
                      (state,attempts,now+delay,int(ok),now,
                       str(q.get("error") or "")[:150] if q else "",
                       row["source_id"],row["node_num"],row["kind"]))
            elif now-row["sent_ms"] >= 90000:
                attempts = min(9, row["attempts"]+1)
                with self.db._lock, self.db._db:
                    self.db._db.execute("""UPDATE auto_node_queries
                      SET state='timeout',attempts=?,due_ms=?,error='Sem resposta RF'
                      WHERE source_id=? AND node_num=? AND kind=?""",
                      (attempts,now+min(86400000,900000*(2**min(attempts,6))),
                       row["source_id"],row["node_num"],row["kind"]))
        return bool(self.db._rows("SELECT 1 FROM auto_node_queries WHERE state='awaiting_reply' LIMIT 1"))

    def overview(self):
        config = self.config()
        chosen, why = self._connection()
        now = int(time.time()*1000)
        if chosen:
            source_id, supported, own = chosen
            candidates = self._candidates(source_id, supported, own, config, now)
        else:
            source_id, supported, candidates = None, [], []
        recent = self.db._rows("""SELECT kind,state,COUNT(*) AS total
                        FROM auto_node_queries GROUP BY kind,state""")
        return {"success": True, "config": config, "source_id": source_id,
                "supported": supported, "reason": why, "queue": [
                    {k: v for k, v in c.items() if k != "previous"}
                    for c in candidates[:30]],
                "pending_count": len(candidates), "totals": recent,
                "last_run_ms": self._last_run_ms, "last_error": self._last_error}

    def tick(self, dry_run=False):
        with self._lock:
            cfg = self.config()
            now = int(time.time()*1000)
            self._last_run_ms = now
            if not cfg["enabled"] and not dry_run:
                return {"sent": False, "reason": "Automação desativada"}
            chosen, reason = self._connection()
            if chosen is None:
                return {"sent": False, "reason": reason}
            source_id, supported, own = chosen
            if not dry_run and self._reconcile(now):
                return {"sent": False, "reason": "Aguardando resposta RF anterior"}
            candidates = self._candidates(source_id, supported, own, cfg, now)
            if dry_run:
                return {"sent": False, "reason": "Simulação sem TX",
                        "queue": [{k: v for k,v in c.items() if k != "previous"}
                                  for c in candidates[:30]],
                        "pending_count": len(candidates)}
            if not candidates:
                return {"sent": False, "reason": "Nenhum dado elegível pendente"}
            with self.db._lock:
                recent = self.db._db.execute(
                    "SELECT COUNT(*),MAX(sent_ms) FROM auto_query_transmissions WHERE sent_ms>=?",
                    (now-3600000,)).fetchone()
            if recent[0] >= cfg["max_per_hour"]:
                return {"sent": False, "reason": "Limite de consultas por hora"}
            if recent[1] and now-recent[1] < cfg["min_gap_seconds"]*1000:
                return {"sent": False, "reason": "Intervalo mínimo de RF"}
            c = candidates[0]
            previous = c["previous"]
            try:
                req = self.sources.queries.start(source_id, c["node"], c["kind"])
            except (ValueError, RuntimeError) as exc:
                # Local contention or transient device state: short cooldown.
                self._record(source_id,c["node"],c["kind"],"", "error",now,
                             now+120000, previous["attempts"] if previous else 0,
                             type(exc).__name__+": "+str(exc))
                return {"sent": False, "reason": str(exc)[:150]}
            self._record(source_id,c["node"],c["kind"],req["request_id"],
                         "awaiting_reply",now,now+90000,
                         previous["attempts"] if previous else 0)
            return {"sent": True, "source_id": source_id, "node": c["node"],
                    "kind": c["kind"], "state": "awaiting_reply"}
