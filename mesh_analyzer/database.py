"""SQLite application state and retention. No MeshMonitor dependency."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

SOURCE_TYPES = {"serial", "tcp", "ble", "mqtt"}
RETAIN_KEYS = ("nodes", "packets", "messages", "positions", "traces", "links", "events")
DEFAULT_RETENTION = {key: 0 for key in RETAIN_KEYS}  # 0: never delete


def now_ms() -> int:
    return int(time.time() * 1000)


def profile_dir() -> Path:
    root = os.environ.get("PT2VHF_MESH_DATA")
    if root:
        return Path(root).expanduser().resolve()
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "PT2VHF-Mesh-Analyzer"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "PT2VHF-Mesh-Analyzer"


class Database:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(self.path), check_same_thread=False, timeout=15)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.execute("PRAGMA busy_timeout=5000")
        with self._lock, self._db:
            self._db.executescript("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                kind TEXT NOT NULL CHECK(kind IN ('serial','tcp','ble','mqtt')),
                config TEXT NOT NULL DEFAULT '{}',
                enabled INTEGER NOT NULL DEFAULT 1,
                created_ms INTEGER NOT NULL,
                updated_ms INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS nodes (
                node_num INTEGER PRIMARY KEY,
                node_id TEXT NOT NULL,
                long_name TEXT NOT NULL DEFAULT '',
                short_name TEXT NOT NULL DEFAULT '',
                aliases TEXT NOT NULL DEFAULT '[]',
                latitude REAL,
                longitude REAL,
                altitude REAL,
                position_ms INTEGER,
                first_seen_ms INTEGER NOT NULL,
                last_seen_ms INTEGER NOT NULL,
                last_source_id INTEGER,
                hw_model TEXT DEFAULT '',
                role TEXT DEFAULT '',
                battery INTEGER,
                snr REAL
            );
            CREATE TABLE IF NOT EXISTS packets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                packet_id TEXT NOT NULL,
                source_packet_key TEXT NOT NULL UNIQUE,
                timestamp_ms INTEGER NOT NULL,
                from_node INTEGER,
                to_node INTEGER,
                port TEXT,
                channel INTEGER,
                rx_snr REAL,
                rx_rssi REAL,
                hop_start INTEGER,
                hop_limit INTEGER,
                via_mqtt INTEGER NOT NULL DEFAULT 0,
                encrypted INTEGER NOT NULL DEFAULT 0,
                text_preview TEXT,
                raw_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_packets_time ON packets(timestamp_ms DESC);
            CREATE INDEX IF NOT EXISTS idx_packets_from ON packets(from_node);
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                packet_key TEXT NOT NULL UNIQUE,
                packet_id TEXT,
                timestamp_ms INTEGER NOT NULL,
                from_node INTEGER,
                to_node INTEGER,
                channel INTEGER NOT NULL DEFAULT 0,
                direction TEXT NOT NULL,
                text TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'received'
            );
            CREATE INDEX IF NOT EXISTS idx_messages_time ON messages(timestamp_ms DESC);
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_num INTEGER NOT NULL,
                source_id INTEGER NOT NULL,
                timestamp_ms INTEGER NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                altitude REAL
            );
            CREATE INDEX IF NOT EXISTS idx_positions_time ON positions(timestamp_ms DESC);
            CREATE TABLE IF NOT EXISTS traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                timestamp_ms INTEGER NOT NULL,
                origin INTEGER,
                destination INTEGER,
                route_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS links (
                source_id INTEGER NOT NULL,
                a INTEGER NOT NULL,
                b INTEGER NOT NULL,
                quality TEXT NOT NULL,
                first_seen_ms INTEGER NOT NULL,
                last_seen_ms INTEGER NOT NULL,
                observations INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY(source_id,a,b,quality)
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_ms INTEGER NOT NULL,
                source_id INTEGER,
                level TEXT NOT NULL,
                description TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)
            self._db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('retention',?)", (json.dumps(DEFAULT_RETENTION),))

    def close(self):
        with self._lock:
            self._db.close()

    def _rows(self, query, args=()):
        with self._lock:
            return [dict(row) for row in self._db.execute(query, args).fetchall()]

    def log(self, text: str, level: str = "info", source_id: int | None = None):
        # Never store secrets, config objects, credentials or packet payloads in operational logs.
        with self._lock, self._db:
            self._db.execute("INSERT INTO events(timestamp_ms,source_id,level,description) VALUES(?,?,?,?)", (now_ms(), source_id, level, str(text)[:360]))

    @staticmethod
    def _public_source(row: dict) -> dict:
        result = dict(row)
        config = json.loads(result.pop("config") or "{}")
        result["config"] = {k: ("********" if "password" in k or "secret" in k or "token" in k else v) for k, v in config.items()}
        result["has_password"] = bool(config.get("password"))
        result["enabled"] = bool(result["enabled"])
        return result

    def sources(self, public=True):
        result = self._rows("SELECT * FROM sources ORDER BY id")
        if public:
            return [self._public_source(r) for r in result]
        for r in result:
            r["config"] = json.loads(r["config"] or "{}")
        return result

    def source(self, source_id, public=False):
        with self._lock:
            row = self._db.execute("SELECT * FROM sources WHERE id=?", (int(source_id),)).fetchone()
        if not row:
            return None
        obj = dict(row)
        if public:
            return self._public_source(obj)
        obj["config"] = json.loads(obj["config"] or "{}")
        return obj

    def upsert_source(self, payload: dict):
        if not isinstance(payload, dict):
            raise ValueError("Dados inválidos")
        source_id = int(payload.get("id") or 0)
        existing = self.source(source_id) if source_id else None
        if source_id and existing is None:
            raise ValueError("Fonte não encontrada")
        kind = str(payload.get("kind") or (existing or {}).get("kind") or "").lower().strip()
        name = str(payload.get("name") or (existing or {}).get("name") or "").strip()[:72]
        if kind not in SOURCE_TYPES or not name:
            raise ValueError("Informe nome e tipo de fonte válidos")
        if "enabled" in payload:
            enabled = bool(payload["enabled"])
        else:
            enabled = bool(existing["enabled"]) if existing else True
        config = dict((existing or {}).get("config") or {})
        update = payload.get("config") or {}
        if not isinstance(update, dict):
            raise ValueError("Configuração inválida")
        allowed = {"serial": {"port", "baudrate"}, "tcp": {"host", "port"},
                   "ble": {"address"}, "mqtt": {"host", "port", "topic", "username", "password", "tls"}}[kind]
        config = {k: v for k, v in config.items() if k in allowed} if existing and existing["kind"] == kind else {}
        for key, value in update.items():
            if key not in allowed:
                continue
            if key == "password" and value == "********":
                continue
            config[key] = value
        if kind == "serial" and not str(config.get("port") or "").strip():
            raise ValueError("Informe a porta COM/serial")
        if kind == "tcp":
            if not str(config.get("host") or "").strip():
                raise ValueError("Informe o IP ou hostname")
            port = int(config.get("port") or 4403)
            if not 1 <= port <= 65535: raise ValueError("Porta inválida")
            config["port"] = port
        if kind == "ble" and not str(config.get("address") or "").strip():
            raise ValueError("Informe o endereço/identificador Bluetooth LE")
        if kind == "mqtt":
            if not str(config.get("host") or "").strip(): raise ValueError("Informe o host MQTT")
            if not str(config.get("topic") or "").strip(): raise ValueError("Informe tópico MQTT")
            config["port"] = int(config.get("port") or (8883 if config.get("tls") else 1883))
            if not 1 <= config["port"] <= 65535: raise ValueError("Porta MQTT inválida")
            config["tls"] = bool(config.get("tls"))
        with self._lock, self._db:
            now = now_ms()
            if existing:
                self._db.execute("UPDATE sources SET name=?,kind=?,config=?,enabled=?,updated_ms=? WHERE id=?",
                                 (name,kind,json.dumps(config),int(enabled),now,source_id))
            else:
                source_id = self._db.execute("INSERT INTO sources(name,kind,config,enabled,created_ms,updated_ms) VALUES(?,?,?,?,?,?)",
                                             (name,kind,json.dumps(config),int(enabled),now,now)).lastrowid
        return self.source(source_id,public=True)

    def delete_source(self, source_id):
        # Maintain historical packet source_id for auditability; no ON DELETE CASCADE.
        with self._lock,self._db:
            self._db.execute("DELETE FROM sources WHERE id=?", (int(source_id),))

    def retention(self):
        with self._lock:
            row = self._db.execute("SELECT value FROM settings WHERE key='retention'").fetchone()
        try:
            value = json.loads(row[0]) if row else {}
            return {k: int(value.get(k, 0)) for k in RETAIN_KEYS}
        except Exception:
            return dict(DEFAULT_RETENTION)

    def set_retention(self, payload):
        if not isinstance(payload,dict): raise ValueError("Retenções inválidas")
        updated = self.retention()
        for k,v in payload.items():
            if k not in RETAIN_KEYS: raise ValueError("Categoria de retenção desconhecida: " + k)
            v = int(v)
            if v < 0 or v > 36500: raise ValueError("Prazo inválido")
            updated[k] = v
        with self._lock,self._db:
            self._db.execute("INSERT INTO settings(key,value) VALUES('retention',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (json.dumps(updated),))
        return updated

    def cleanup(self):
        removed = {}
        days = self.retention()
        columns = {"nodes":"last_seen_ms", "packets":"timestamp_ms", "messages":"timestamp_ms",
                   "positions":"timestamp_ms", "traces":"timestamp_ms", "links":"last_seen_ms", "events":"timestamp_ms"}
        with self._lock,self._db:
            for table,col in columns.items():
                if days[table] == 0:
                    removed[table] = 0
                else:
                    cutoff = now_ms() - days[table] * 86400000
                    cur = self._db.execute(f"DELETE FROM {table} WHERE {col} < ?",(cutoff,))
                    removed[table] = cur.rowcount
        return removed

    def upsert_node(self, num, source_id, timestamp_ms=None, **kwargs):
        try:
            num = int(num)
            if num <= 0 or num >= 0xffffffff: return
        except (ValueError,TypeError):
            return
        ts = int(now_ms() if timestamp_ms is None else timestamp_ms)
        node_id=f"!{num & 0xffffffff:08x}"
        with self._lock,self._db:
            old = self._db.execute("SELECT * FROM nodes WHERE node_num=?",(num,)).fetchone()
            if old is None:
                self._db.execute("INSERT INTO nodes(node_num,node_id,first_seen_ms,last_seen_ms,last_source_id) VALUES(?,?,?,?,?)",
                                 (num,node_id,ts,ts,source_id))
                old = self._db.execute("SELECT * FROM nodes WHERE node_num=?",(num,)).fetchone()
            fields = {k: v for k,v in kwargs.items() if k in {"long_name","short_name","latitude","longitude","altitude","hw_model","role","battery","snr"} and v is not None and v != ""}
            aliases = json.loads(old["aliases"] or "[]")
            for name in (old["long_name"],old["short_name"],fields.get("long_name"),fields.get("short_name")):
                if isinstance(name,str) and name.strip() and name not in aliases and not name.startswith("!"):
                    aliases.append(name[:80])
            if aliases: fields["aliases"] = json.dumps(aliases[-48:],ensure_ascii=False)
            lat=fields.get("latitude")
            lon=fields.get("longitude")
            if lat is not None or lon is not None:
                if lat is None or lon is None or not (-90<=float(lat)<=90 and -180<=float(lon)<=180) or (abs(float(lat))<0.01 and abs(float(lon))<0.01):
                    fields.pop("latitude",None);fields.pop("longitude",None)
                elif ts >= int(old["position_ms"] or 0):
                    fields["position_ms"] = ts
                else:
                    fields.pop("latitude",None);fields.pop("longitude",None)
            fields["last_seen_ms"] = max(ts,int(old["last_seen_ms"] or 0))
            fields["last_source_id"] = source_id
            cols=list(fields)
            args=list(fields.values())+[num]
            self._db.execute("UPDATE nodes SET "+",".join(k+"=?" for k in cols)+" WHERE node_num=?",args)

    def node_rows(self, limit=5000):
        rows=self._rows("SELECT * FROM nodes ORDER BY last_seen_ms DESC LIMIT ?",(min(int(limit),15000),))
        for r in rows: r["aliases"]=json.loads(r["aliases"] or "[]")
        return rows

    def add_packet(self, item:dict):
        fields=["source_id","packet_id","source_packet_key","timestamp_ms","from_node","to_node", "port","channel","rx_snr","rx_rssi","hop_start","hop_limit","via_mqtt","encrypted","text_preview","raw_json"]
        with self._lock,self._db:
            try:
                values = dict(item)
                values.setdefault("via_mqtt",0)
                values.setdefault("encrypted",0)
                self._db.execute("INSERT INTO packets("+",".join(fields)+") VALUES("+",".join("?" for _ in fields)+")",
                                 [values.get(k) for k in fields])
                return True
            except sqlite3.IntegrityError as exc:
                if "UNIQUE constraint failed" in str(exc):return False
                raise

    def add_message(self, item:dict):
        fields=["source_id","packet_key","packet_id","timestamp_ms","from_node","to_node","channel","direction","text","state"]
        with self._lock,self._db:
            try:
                self._db.execute("INSERT INTO messages("+",".join(fields)+") VALUES("+",".join("?" for _ in fields)+")",
                                 [item.get(k) for k in fields])
                return self._db.execute("SELECT last_insert_rowid()").fetchone()[0]
            except sqlite3.IntegrityError: return None

    def add_position(self,num,source_id,ts,lat,lon,alt=None):
        with self._lock,self._db:
            self._db.execute("INSERT INTO positions(node_num,source_id,timestamp_ms,latitude,longitude,altitude) VALUES(?,?,?,?,?,?)",(num,source_id,ts,lat,lon,alt))

    def add_trace(self,source_id,ts,origin,dest,route):
        with self._lock,self._db:
            self._db.execute("INSERT INTO traces(source_id,timestamp_ms,origin,destination,route_json) VALUES(?,?,?,?,?)",(source_id,ts,origin,dest,json.dumps(route)))

    def add_link(self,source_id,a,b,ts,quality):
        a,b=sorted((int(a),int(b)))
        if a==b:return
        with self._lock,self._db:
            self._db.execute("""INSERT INTO links(source_id,a,b,quality,first_seen_ms,last_seen_ms,observations)
              VALUES(?,?,?,?,?,?,1) ON CONFLICT(source_id,a,b,quality) DO UPDATE SET
              last_seen_ms=MAX(last_seen_ms,excluded.last_seen_ms),observations=observations+1""",(source_id,a,b,quality,ts,ts))

    def packet_rows(self,limit=300):
        return self._rows("SELECT id,source_id,packet_id,timestamp_ms,from_node,to_node,port,channel,rx_snr,rx_rssi,hop_start,hop_limit,via_mqtt,encrypted,text_preview FROM packets ORDER BY timestamp_ms DESC,id DESC LIMIT ?",(min(int(limit),3000),))

    def message_rows(self,limit=300):
        return self._rows("SELECT * FROM messages ORDER BY timestamp_ms DESC,id DESC LIMIT ?",(min(int(limit),3000),))

    def link_rows(self):
        return self._rows("SELECT * FROM links ORDER BY last_seen_ms DESC LIMIT 20000")

    def event_rows(self,limit=80):
        return self._rows("SELECT * FROM events ORDER BY timestamp_ms DESC LIMIT ?",(min(int(limit),500),))

    def stats(self):
        with self._lock:
            def count(table):return int(self._db.execute("SELECT COUNT(*) FROM "+table).fetchone()[0])
            return {k:count(k) for k in ("nodes","packets","messages","positions","traces","links","events","sources")}