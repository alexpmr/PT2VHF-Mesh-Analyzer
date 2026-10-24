"""MeshCore, etapa 2 (#190): contatos, caminhos, colisões de prefixo e coleta periódica (#188).

O driver (`meshcore_driver`) avisa contatos, dados do rádio e resultados de
consultas; aqui eles ficam guardados por fonte para a aba MeshCore, o mapa e
as automações. Nada aqui transmite sozinho, exceto `MeshCoreAutomation`, que
respeita um orçamento por hora e recua quando o nó não responde.
"""
from __future__ import annotations

import json
import logging
import threading
import time

from .database import now_ms

LOG = logging.getLogger(__name__)
TYPES = {1: "Companion", 2: "Repetidor", 3: "Room server", 4: "Sensor"}
RELAYS = (2, 3)
RESULT_KINDS = ("status", "telemetry", "neighbours", "trace")
KEEP_RESULTS = 300
AUTO_DEFAULTS = {"enabled": False, "max_per_hour": 6, "min_gap_seconds": 120, "targets": []}
AUTO_KINDS = ("telemetry", "status")
BACKOFF_MAX_MIN = 12 * 60


def _key_num(key):
    try:
        return int(str(key)[:8], 16) or None
    except (TypeError, ValueError):
        return None


def _hops(path, hash_size):
    path, step = str(path or ""), max(1, int(hash_size)) * 2
    return [path[i:i + step] for i in range(0, len(path) - step + 1, step)]


class MeshCoreData:
    def __init__(self, db):
        self.db = db
        with db._lock, db._db:
            db._db.executescript("""
            CREATE TABLE IF NOT EXISTS meshcore_contacts (
                source_id INTEGER NOT NULL, node_num INTEGER NOT NULL,
                public_key TEXT NOT NULL, name TEXT NOT NULL DEFAULT '',
                type INTEGER NOT NULL DEFAULT 0, out_path TEXT NOT NULL DEFAULT '',
                out_path_len INTEGER NOT NULL DEFAULT -1, hash_mode INTEGER NOT NULL DEFAULT 0,
                last_advert INTEGER NOT NULL DEFAULT 0, latitude REAL, longitude REAL,
                updated_ms INTEGER NOT NULL, PRIMARY KEY(source_id,node_num));
            CREATE TABLE IF NOT EXISTS meshcore_path_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, source_id INTEGER NOT NULL,
                node_num INTEGER NOT NULL, old_path TEXT NOT NULL, old_len INTEGER NOT NULL,
                new_path TEXT NOT NULL, new_len INTEGER NOT NULL, timestamp_ms INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS meshcore_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT, source_id INTEGER NOT NULL,
                node_num INTEGER NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL,
                timestamp_ms INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_meshcore_results ON meshcore_results(source_id,node_num,kind,timestamp_ms);
            """)

    # --- eventos do driver ---------------------------------------------------------
    def observe(self, source_id, kind, data):
        sid = int(source_id)
        if kind in ("self", "device"):
            clean = {k: v for k, v in dict(data or {}).items() if isinstance(v, (str, int, float, bool)) or v is None}
            self.db._set_setting("meshcore_%s:%d" % (kind, sid), clean)
        elif kind == "contact":
            self._contact(sid, data or {})
        elif kind == "removed":
            with self.db._lock, self.db._db:
                self.db._db.execute("DELETE FROM meshcore_contacts WHERE source_id=? AND node_num=?",
                                    (sid, int(data["node_num"])))
        elif kind in RESULT_KINDS:
            self.add_result(sid, int(data.get("node_num") or 0), kind, data)

    def _contact(self, sid, c):
        num = _key_num(c.get("public_key"))
        if not num:
            return
        path, plen = str(c.get("out_path") or ""), int(c.get("out_path_len") if c.get("out_path_len") is not None else -1)
        lat, lon = c.get("adv_lat"), c.get("adv_lon")
        if not lat and not lon:
            lat = lon = None
        now = now_ms()
        with self.db._lock, self.db._db:
            old = self.db._db.execute("SELECT out_path,out_path_len FROM meshcore_contacts WHERE source_id=? AND node_num=?",
                                      (sid, num)).fetchone()
            self.db._db.execute("""INSERT INTO meshcore_contacts(source_id,node_num,public_key,name,type,out_path,
                out_path_len,hash_mode,last_advert,latitude,longitude,updated_ms) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(source_id,node_num) DO UPDATE SET public_key=excluded.public_key,name=excluded.name,
                type=excluded.type,out_path=excluded.out_path,out_path_len=excluded.out_path_len,
                hash_mode=excluded.hash_mode,last_advert=MAX(last_advert,excluded.last_advert),
                latitude=excluded.latitude,longitude=excluded.longitude,updated_ms=excluded.updated_ms""",
                (sid, num, str(c.get("public_key")), str(c.get("adv_name") or "")[:64], int(c.get("type") or 0),
                 path, plen, max(0, int(c.get("out_path_hash_mode") or 0)), int(c.get("last_advert") or 0), lat, lon, now))
            # Só conta como mudança quando havia um caminho conhecido e ele mudou de fato.
            if old and (old["out_path"], old["out_path_len"]) != (path, plen) and old["out_path_len"] >= 0:
                self.db._db.execute("""INSERT INTO meshcore_path_changes(source_id,node_num,old_path,old_len,new_path,
                    new_len,timestamp_ms) VALUES(?,?,?,?,?,?,?)""", (sid, num, old["out_path"], old["out_path_len"], path, plen, now))
                self.db._db.execute("""DELETE FROM meshcore_path_changes WHERE id IN (SELECT id FROM meshcore_path_changes
                    WHERE source_id=? ORDER BY id DESC LIMIT -1 OFFSET 1000)""", (sid,))

    def add_result(self, sid, num, kind, data):
        with self.db._lock, self.db._db:
            self.db._db.execute("INSERT INTO meshcore_results(source_id,node_num,kind,data,timestamp_ms) VALUES(?,?,?,?,?)",
                                (sid, num, kind, json.dumps(data, default=str)[:20000], now_ms()))
            self.db._db.execute("""DELETE FROM meshcore_results WHERE id IN (SELECT id FROM meshcore_results
                WHERE source_id=? AND node_num=? AND kind=? ORDER BY id DESC LIMIT -1 OFFSET ?)""", (sid, num, kind, KEEP_RESULTS))

    # --- consultas -----------------------------------------------------------------
    def contacts(self, sid):
        return self.db._rows("SELECT * FROM meshcore_contacts WHERE source_id=? ORDER BY name COLLATE NOCASE", (int(sid),))

    def results(self, sid, node_num=None, kind=None, limit=50):
        q, args = "SELECT * FROM meshcore_results WHERE source_id=?", [int(sid)]
        if node_num:
            q += " AND node_num=?"; args.append(int(node_num))
        if kind:
            q += " AND kind=?"; args.append(str(kind))
        rows = self.db._rows(q + " ORDER BY id DESC LIMIT ?", (*args, int(limit)))
        for r in rows:
            try:
                r["data"] = json.loads(r["data"])
            except ValueError:
                r["data"] = {}
        return rows

    def path_changes(self, sid, limit=50):
        return self.db._rows("""SELECT p.*,c.name FROM meshcore_path_changes p LEFT JOIN meshcore_contacts c
            ON c.source_id=p.source_id AND c.node_num=p.node_num WHERE p.source_id=? ORDER BY p.id DESC LIMIT ?""",
                             (int(sid), int(limit)))

    def hash_size(self, sid):
        device = self.db._setting("meshcore_device:%d" % int(sid), {}) or {}
        return max(0, int(device.get("path_hash_mode") or 0)) + 1

    def collisions(self, sid, contacts=None):
        """Repetidores/room servers que dividem o mesmo prefixo de caminho (1 byte e o tamanho do rádio).

        Num caminho MeshCore cada salto é só o começo da chave; dois repetidores com o mesmo
        começo ficam indistinguíveis e podem confundir rotas.
        """
        contacts = self.contacts(sid) if contacts is None else contacts
        own = self.db._setting("meshcore_self:%d" % int(sid), {}) or {}
        relays = [c for c in contacts if c["type"] in RELAYS]
        if own.get("public_key"):
            relays.append({"node_num": _key_num(own["public_key"]), "public_key": own["public_key"],
                           "name": own.get("name") or "Este rádio", "type": 1, "own": True})
        out = []
        for size in sorted({1, self.hash_size(sid)}):
            groups = {}
            for c in relays:
                groups.setdefault(str(c["public_key"])[:size * 2].lower(), []).append(c)
            for prefix, members in sorted(groups.items()):
                if len(members) > 1:
                    out.append({"prefix": prefix, "bytes": size, "members": [
                        {"node_num": m["node_num"], "name": m["name"], "type": TYPES.get(m["type"], "Nó"),
                         "own": bool(m.get("own"))} for m in members]})
        return out

    def paths(self, sid, contacts=None):
        """Caminho de saída de cada contato, com os repetidores resolvidos quando o prefixo é único."""
        contacts = self.contacts(sid) if contacts is None else contacts
        relays = [c for c in contacts if c["type"] in RELAYS]
        out = []
        for c in contacts:
            hs = c["hash_mode"] + 1
            hops = []
            for h in _hops(c["out_path"], hs) if c["out_path_len"] > 0 else []:
                found = [r for r in relays if str(r["public_key"]).lower().startswith(h.lower())]
                one = found[0] if len(found) == 1 else None
                hops.append({"hash": h, "candidates": len(found), "node_num": one and one["node_num"],
                             "name": one and one["name"], "latitude": one and one["latitude"],
                             "longitude": one and one["longitude"]})
            out.append({"node_num": c["node_num"], "name": c["name"], "type": TYPES.get(c["type"], "Nó"),
                        "mode": "flood" if c["out_path_len"] < 0 else "direct" if c["out_path_len"] == 0 else "routed",
                        "hops": hops, "latitude": c["latitude"], "longitude": c["longitude"]})
        return out

    def overview(self, sid, stale_days=30):
        sid = int(sid)
        contacts = self.contacts(sid)
        device = self.db._setting("meshcore_device:%d" % sid, {}) or {}
        own = self.db._setting("meshcore_self:%d" % sid, {}) or {}
        cut = time.time() - stale_days * 86400
        stale = [{"node_num": c["node_num"], "name": c["name"], "type": TYPES.get(c["type"], "Nó"),
                  "last_advert": c["last_advert"]} for c in contacts if c["last_advert"] and c["last_advert"] < cut]
        by_type = {}
        for c in contacts:
            label = TYPES.get(c["type"], "Nó")
            by_type[label] = by_type.get(label, 0) + 1
        limit = int(device.get("max_contacts") or 0)
        return {"source_id": sid, "self": {k: own.get(k) for k in ("name", "public_key", "radio_freq", "radio_bw",
                                                                   "radio_sf", "radio_cr", "tx_power", "manual_add_contacts")},
                "device": device, "contacts": len(contacts), "by_type": by_type,
                "occupancy": {"used": len(contacts), "max": limit,
                              "percent": round(100 * len(contacts) / limit) if limit else None},
                "hash_size": self.hash_size(sid), "collisions": self.collisions(sid, contacts),
                "paths": self.paths(sid, contacts), "path_changes": self.path_changes(sid, 30),
                "stale": sorted(stale, key=lambda s: s["last_advert"]), "stale_days": stale_days}


class MeshCoreAutomation:
    """#188: telemetria/status periódicos de contatos MeshCore escolhidos, com orçamento e recuo."""

    def __init__(self, db, sources, interval=30):
        self.db = db
        self.sources = sources
        self.interval = interval
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.Lock()
        self.last = {"ms": 0, "reason": ""}

    def config(self):
        stored = self.db._setting("meshcore_automation", {}) or {}
        cfg = {**AUTO_DEFAULTS, **{k: stored[k] for k in AUTO_DEFAULTS if k in stored}}
        cfg["targets"] = [t for t in cfg["targets"] if isinstance(t, dict)]
        return cfg

    def save(self, patch):
        if not isinstance(patch, dict) or set(patch) - set(AUTO_DEFAULTS):
            raise ValueError("Configuração inválida")
        cfg = self.config()
        if "enabled" in patch:
            if type(patch["enabled"]) is not bool:
                raise ValueError("Ativação inválida")
            cfg["enabled"] = patch["enabled"]
        for name, lo, hi in (("max_per_hour", 1, 30), ("min_gap_seconds", 30, 3600)):
            if name in patch:
                if type(patch[name]) is not int or not lo <= patch[name] <= hi:
                    raise ValueError("Valor inválido: " + name)
                cfg[name] = patch[name]
        if "targets" in patch:
            if not isinstance(patch["targets"], list) or len(patch["targets"]) > 30:
                raise ValueError("Lista de contatos inválida (até 30)")
            old = {(t["node_num"], t["kind"]): t for t in cfg["targets"]}
            targets = []
            for t in patch["targets"]:
                try:
                    num, kind, minutes = int(t["node_num"]), str(t.get("kind") or "telemetry"), int(t.get("interval_minutes") or 60)
                except (TypeError, ValueError, KeyError):
                    raise ValueError("Contato inválido") from None
                if kind not in AUTO_KINDS or not 15 <= minutes <= 10080 or not 0 < num < 0xFFFFFFFF:
                    raise ValueError("Contato, tipo ou intervalo inválido (15 min a 7 dias)")
                prev = old.get((num, kind), {})
                targets.append({"node_num": num, "kind": kind, "interval_minutes": minutes,
                                "next_ms": int(prev.get("next_ms") or 0), "failures": int(prev.get("failures") or 0),
                                "last_ok_ms": int(prev.get("last_ok_ms") or 0), "last_error": str(prev.get("last_error") or "")})
            cfg["targets"] = targets
        self.db._set_setting("meshcore_automation", cfg)
        return cfg

    @staticmethod
    def _passwords(db):
        return db._setting("meshcore_passwords", {}) or {}

    def set_password(self, node_num, password):
        """Senha de convidado/admin do repetidor, guardada só neste computador."""
        pw = self._passwords(self.db)
        if password:
            if len(str(password)) > 15:
                raise ValueError("Senha MeshCore: até 15 caracteres")
            pw[str(int(node_num))] = str(password)
        else:
            pw.pop(str(int(node_num)), None)
        self.db._set_setting("meshcore_passwords", pw)
        return sorted(int(k) for k in pw)

    def overview(self):
        return {"config": self.config(), "last": self.last, "with_password": sorted(int(k) for k in self._passwords(self.db))}

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, name="meshcore-automation", daemon=True)
            self._thread.start()

    def close(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.wait(self.interval):
            try:
                self.tick()
            except Exception:
                LOG.exception("Falha na coleta periódica MeshCore")

    def tick(self, now=None):
        with self._lock:
            now = now or now_ms()
            cfg = self.config()
            self.last["ms"] = now
            if not cfg["enabled"]:
                return self._done("Coleta MeshCore desativada")
            sid, iface = self.sources.meshcore_interface()
            if iface is None:
                return self._done("Nenhum rádio MeshCore conectado")
            sent = [t for t in self.db._setting("meshcore_automation_sent", []) or [] if t > now - 3600000]
            if len(sent) >= cfg["max_per_hour"]:
                return self._done("Limite de consultas MeshCore por hora")
            if sent and now - max(sent) < cfg["min_gap_seconds"] * 1000:
                return self._done("Intervalo mínimo entre consultas")
            due = sorted((t for t in cfg["targets"] if t["next_ms"] <= now), key=lambda t: t["next_ms"])
            if not due:
                return self._done("Nada pendente")
            target = due[0]
            sent.append(now)
            self.db._set_setting("meshcore_automation_sent", sent)
            try:
                password = self._passwords(self.db).get(str(target["node_num"]))
                if password is not None:
                    iface.login(target["node_num"], password)
                getattr(iface, target["kind"])(target["node_num"])
                target.update(failures=0, last_ok_ms=now, last_error="", next_ms=now + target["interval_minutes"] * 60000)
                reason = "ok"
            except Exception as exc:
                target["failures"] += 1
                # Recuo exponencial a partir de 15 min (nunca antes do intervalo escolhido), até 12 h.
                wait = min(max(target["interval_minutes"], 15 * 2 ** (target["failures"] - 1)), BACKOFF_MAX_MIN)
                target.update(last_error=str(exc)[:160], next_ms=now + wait * 60000)
                reason = str(exc)[:160]
            stored = self.config()
            for t in stored["targets"]:
                if (t["node_num"], t["kind"]) == (target["node_num"], target["kind"]):
                    t.update({k: target[k] for k in ("failures", "last_ok_ms", "last_error", "next_ms")})
            self.db._set_setting("meshcore_automation", stored)
            return self._done(reason, node_num=target["node_num"], kind=target["kind"], sent=True)

    def _done(self, reason, **extra):
        self.last.update(reason=reason)
        return {"reason": reason, "sent": False, **extra}
