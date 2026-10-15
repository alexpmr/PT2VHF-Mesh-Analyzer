"""SQLite application state and retention. No MeshMonitor dependency."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

SOURCE_TYPES = {"serial", "tcp", "ble", "mqtt"}
RETAIN_KEYS = ("nodes", "packets", "messages", "positions", "traces", "links", "events", "waypoints")
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
            CREATE TABLE IF NOT EXISTS waypoints (
                source_id INTEGER NOT NULL,
                waypoint_id INTEGER NOT NULL,
                from_node INTEGER,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                icon INTEGER NOT NULL DEFAULT 0,
                expires_ms INTEGER NOT NULL DEFAULT 0,
                first_seen_ms INTEGER NOT NULL,
                last_seen_ms INTEGER NOT NULL,
                PRIMARY KEY(source_id, waypoint_id)
            );
            CREATE INDEX IF NOT EXISTS idx_waypoints_time ON waypoints(last_seen_ms DESC);
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
            CREATE TABLE IF NOT EXISTS node_sources (
                source_id INTEGER NOT NULL,
                node_num INTEGER NOT NULL,
                first_seen_ms INTEGER NOT NULL DEFAULT 0,
                last_seen_ms INTEGER NOT NULL DEFAULT 0,
                observed INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(source_id,node_num)
            );
            CREATE INDEX IF NOT EXISTS idx_node_sources_node ON node_sources(node_num);
            CREATE TABLE IF NOT EXISTS topology_processed (
                source_packet_key TEXT PRIMARY KEY
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
            CREATE TABLE IF NOT EXISTS communications (
                source_id INTEGER NOT NULL,
                from_node INTEGER NOT NULL,
                to_node INTEGER NOT NULL,
                transport TEXT NOT NULL CHECK(transport IN ('radio','mqtt')),
                first_seen_ms INTEGER NOT NULL,
                last_seen_ms INTEGER NOT NULL,
                observations INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY(source_id,from_node,to_node,transport)
            );
            CREATE INDEX IF NOT EXISTS idx_communications_last ON communications(last_seen_ms DESC);
            CREATE TABLE IF NOT EXISTS communication_processed (
                source_packet_key TEXT PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_ms INTEGER NOT NULL,
                source_id INTEGER,
                level TEXT NOT NULL,
                description TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rf_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                node_num INTEGER NOT NULL,
                timestamp_ms INTEGER NOT NULL,
                rx_good INTEGER,
                rx_bad INTEGER,
                channel_util REAL,
                air_util REAL,
                voltage REAL,
                battery INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_rf_samples_time
              ON rf_samples(source_id,node_num,timestamp_ms);
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)
            columns = {row[1] for row in self._db.execute("PRAGMA table_info(nodes)")}
            if "voltage" not in columns:
                self._db.execute("ALTER TABLE nodes ADD COLUMN voltage REAL")
            if "friendly_name" not in columns:
                self._db.execute("ALTER TABLE nodes ADD COLUMN friendly_name TEXT NOT NULL DEFAULT ''")
            self._db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('retention',?)", (json.dumps(DEFAULT_RETENTION),))
            # Run heavy archival provenance import once, not on every startup.
            migrated=self._db.execute("SELECT 1 FROM settings WHERE key='migrated_node_sources_v1'").fetchone()
            if migrated is None:
                self._db.execute("""INSERT OR IGNORE INTO node_sources(source_id,node_num,first_seen_ms,last_seen_ms,observed)
                  SELECT last_source_id,node_num,first_seen_ms,last_seen_ms,0
                  FROM nodes WHERE last_source_id IS NOT NULL""")
                self._db.execute("""INSERT INTO node_sources(source_id,node_num,first_seen_ms,last_seen_ms,observed)
                  SELECT source_id,from_node,MIN(timestamp_ms),MAX(timestamp_ms),1 FROM packets
                  WHERE from_node IS NOT NULL AND from_node>0 AND from_node<4294967295
                  GROUP BY source_id,from_node
                  ON CONFLICT(source_id,node_num) DO UPDATE SET
                    first_seen_ms=MIN(first_seen_ms,excluded.first_seen_ms),
                    last_seen_ms=MAX(last_seen_ms,excluded.last_seen_ms),
                    observed=MAX(observed,excluded.observed)""")
                self._db.execute("INSERT INTO settings(key,value) VALUES('migrated_node_sources_v1','true')")

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

    def add_rf_sample(self, source_id, node_num, timestamp_ms, **fields):
        if node_num is None:
            return
        allowed = ("rx_good", "rx_bad", "channel_util", "air_util", "voltage", "battery")
        values = [fields.get(key) for key in allowed]
        if all(v is None for v in values):
            return
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO rf_samples(source_id,node_num,timestamp_ms," +
                ",".join(allowed) + ") VALUES(" + ",".join("?" for _ in range(3+len(allowed))) + ")",
                [int(source_id), int(node_num), int(timestamp_ms)] + values)

    def delete_source(self, source_id):
        # Maintain historical packet source_id for auditability; no ON DELETE CASCADE.
        with self._lock,self._db:
            self._db.execute("DELETE FROM sources WHERE id=?", (int(source_id),))

    SYSTEM_DEFAULTS = {"open_browser_on_start": False, "allow_lan_access": False,
                       "update_minutes": 15}

    def ui_preferences(self):
        """Validated persisted map presentation options, independent of browser."""
        with self._lock:
            row=self._db.execute("SELECT value FROM settings WHERE key='ui_preferences'").fetchone()
        try:
            value=json.loads(row[0]) if row else {}
            return value if isinstance(value,dict) else {}
        except (TypeError,ValueError):
            return {}

    def save_ui_preferences(self,options):
        if not isinstance(options,dict):raise ValueError("Preferências inválidas")
        allowed={
            "mapWindow","mapMinObservations","mapBrightness","mapTerrainMaxSetting",
            "mapRfColor","mapRfWidth","mapInternetColor","mapInternetWidth",
            "mapShowLinksSetting","mapShowNodesSetting","mapShowWaypointsSetting","mapHeatmap","mapShowNamesSetting",
            "mapIdentifiedOnly","mapAutoZoom","soundEnabled","soundTheme","soundVolume",
            "soundDensity","soundMinInterval","soundMaxVoices","soundRouting","soundMessages",
            "soundAlerts","soundStereo","mapAnimateNodes","mapHighlightSource","mapHighlightRelay",
            "mapPulseSeconds","mapAnimationSpeed","mapType","mapRadar","mapRadarOpacity",
            "mapHillshade","mapTerrain","terrainCut","terrainMax","terrainOpacity"}
        if set(options)-allowed:raise ValueError("Opção de mapa desconhecida")
        if len(json.dumps(options))>12000:raise ValueError("Preferências excedem o limite")
        for k,v in options.items():
            if isinstance(v,(dict,list)) or v is None:raise ValueError("Valor inválido em "+k)
            if isinstance(v,str) and len(v)>100:raise ValueError("Valor muito longo em "+k)
        if "mapWindow" in options and options["mapWindow"] not in ("all","1h","12h","24h","7d","30d"):
            raise ValueError("Período do mapa inválido")
        if "mapType" in options and options["mapType"] not in ("osm","topo","satellite","light","dark"):
            raise ValueError("Tipo de mapa inválido")
        for name,low,high in (("mapMinObservations",1,99999),("mapBrightness",20,150),
             ("mapTerrainMaxSetting",100,9000),("mapRfWidth",1,12),
             ("mapInternetWidth",1,12),("soundVolume",0,100),
             ("soundMinInterval",40,1000),("soundMaxVoices",1,12),
             ("terrainCut",0,9000),("terrainMax",100,9000),("terrainOpacity",20,100),
             ("mapRadarOpacity",10,100)):
            if name in options:
                try:num=float(options[name])
                except (TypeError,ValueError):raise ValueError("Número inválido em "+name)
                if not low<=num<=high:raise ValueError("Fora do intervalo em "+name)
        import re
        for color in ("mapRfColor","mapInternetColor"):
            if color in options and not re.fullmatch(r"#[0-9a-fA-F]{6}",str(options[color])):
                raise ValueError("Cor inválida: "+color)
        merged=self.ui_preferences()
        merged.update(options)
        with self._lock,self._db:
            self._db.execute("INSERT INTO settings(key,value) VALUES('ui_preferences',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                             (json.dumps(merged,ensure_ascii=False),))
        return merged

    def system_settings(self):
        """Global per-profile preferences shared across desktop and local web UI."""
        with self._lock:
            row = self._db.execute("SELECT value FROM settings WHERE key='system'").fetchone()
        try:
            stored = json.loads(row[0]) if row else {}
            if not isinstance(stored, dict): stored = {}
        except (TypeError, ValueError):
            stored = {}
        data = dict(self.SYSTEM_DEFAULTS)
        data.update({k: stored[k] for k in data if k in stored})
        data["open_browser_on_start"] = data["open_browser_on_start"] is True
        # LAN access is not implemented without authenticated sessions.
        data["allow_lan_access"] = False
        n = data["update_minutes"]
        data["update_minutes"] = n if type(n) is int and 5 <= n <= 1440 else 15
        return data

    def set_system_settings(self, changes):
        if not isinstance(changes, dict) or not changes:
            raise ValueError("Informe preferências de Sistema")
        allowed = set(self.SYSTEM_DEFAULTS)
        if set(changes)-allowed:
            raise ValueError("Preferência desconhecida")
        if "allow_lan_access" in changes and changes["allow_lan_access"] is True:
            raise ValueError("Acesso LAN bloqueado até a implementação de autenticação segura")
        if "open_browser_on_start" in changes and type(changes["open_browser_on_start"]) is not bool:
            raise ValueError("Opção do navegador deve ser sim ou não")
        if "update_minutes" in changes and (type(changes["update_minutes"]) is not int or not 5 <= changes["update_minutes"] <= 1440):
            raise ValueError("Intervalo de atualização: 5 a 1440 minutos")
        updated = self.system_settings()
        updated.update(changes)
        updated["allow_lan_access"] = False
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO settings(key,value) VALUES('system',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (json.dumps(updated),))
        return updated

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
                   "positions":"timestamp_ms", "traces":"timestamp_ms", "links":"last_seen_ms", "events":"timestamp_ms",
                   "rf_samples":"timestamp_ms","waypoints":"last_seen_ms"}
        with self._lock,self._db:
            for table,col in columns.items():
                if days["packets" if table == "rf_samples" else table] == 0:
                    removed[table] = 0
                else:
                    cutoff = now_ms() - days["packets" if table == "rf_samples" else table] * 86400000
                    cur = self._db.execute(f"DELETE FROM {table} WHERE {col} < ?",(cutoff,))
                    removed[table] = cur.rowcount
        return removed

    def upsert_node(self, num, source_id, timestamp_ms=None, observed=False, **kwargs):
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
            fields = {k: v for k,v in kwargs.items() if k in {"long_name","short_name","latitude","longitude","altitude","hw_model","role","battery","snr","voltage"} and v is not None and v != ""}
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
            self._db.execute("""INSERT INTO node_sources(source_id,node_num,first_seen_ms,last_seen_ms,observed)
                VALUES(?,?,?,?,?) ON CONFLICT(source_id,node_num) DO UPDATE SET
                first_seen_ms=MIN(first_seen_ms,excluded.first_seen_ms),
                last_seen_ms=MAX(last_seen_ms,excluded.last_seen_ms),
                observed=MAX(observed,excluded.observed)""",
                (int(source_id),num,ts,ts,int(bool(observed))))

    def set_node_friendly_name(self, node_num, friendly_name):
        """Persistent local nickname: never changes the Meshtastic Node ID."""
        num = int(node_num)
        if not 0 < num < 0xffffffff:
            raise ValueError("Identificador de nó inválido")
        name = str(friendly_name).strip()
        if len(name) > 80 or any(ord(c) < 32 for c in name):
            raise ValueError("Nome amigável inválido (máximo 80 caracteres)")
        with self._lock, self._db:
            row = self._db.execute("SELECT node_num FROM nodes WHERE node_num=?", (num,)).fetchone()
            if row is None:
                raise ValueError("Nó não cadastrado")
            self._db.execute("UPDATE nodes SET friendly_name=? WHERE node_num=?", (name, num))
        return {"node_num": num, "friendly_name": name}

    def health(self, check=False):
        """Read-only SQLite diagnostics. Integrity PRAGMAs run only by request."""
        tables = ("sources","nodes","node_sources","packets","messages","positions","waypoints","communications",
                  "traces","links","topology_processed","events","rf_samples")
        with self._lock:
            counts = {name: int(self._db.execute(
                "SELECT COUNT(*) FROM "+name).fetchone()[0]) for name in tables}
            pages = int(self._db.execute("PRAGMA page_count").fetchone()[0])
            page_size = int(self._db.execute("PRAGMA page_size").fetchone()[0])
            free_pages = int(self._db.execute("PRAGMA freelist_count").fetchone()[0])
            journal = str(self._db.execute("PRAGMA journal_mode").fetchone()[0])
            integrity = None
            foreign_keys = None
            if check:
                integrity = [row[0] for row in self._db.execute("PRAGMA quick_check").fetchall()][:20]
                foreign_keys = len(self._db.execute("PRAGMA foreign_key_check").fetchall())
        files = {}
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(self.path)+suffix)
            try: files["db" if not suffix else suffix[1:]] = candidate.stat().st_size
            except OSError: files["db" if not suffix else suffix[1:]] = 0
        backup_dir = self.path.parent / "backups"
        snapshots = sorted(backup_dir.glob("mesh-analyzer-*.sqlite3"),reverse=True) if backup_dir.exists() else []
        try: free_disk = shutil.disk_usage(self.path.parent).free
        except OSError: free_disk = None
        return {"counts":counts, "files_bytes":files,
                "total_bytes":sum(files.values()),"free_disk_bytes":free_disk,
                "page_count":pages,"page_size":page_size,"free_pages":free_pages,
                "journal":journal,"integrity":integrity,"foreign_key_violations":foreign_keys,
                "last_backup":snapshots[0].name if snapshots else None,
                "retention":self.retention()}

    def backup(self):
        """Online SQLite backup uses sqlite3 backup API; never raw-copies a live WAL DB."""
        folder = self.path.parent / "backups"
        folder.mkdir(mode=0o700,parents=True,exist_ok=True)
        name = "mesh-analyzer-" + time.strftime("%Y%m%d-%H%M%S",time.localtime()) + "-" + str(now_ms()%1000).zfill(3) + ".sqlite3"
        dest = folder / name
        tmp = folder / (name+".part")
        target = None
        try:
            with self._lock:
                target = sqlite3.connect(str(tmp))
                self._db.backup(target,pages=128,sleep=0.1)
                target.close()
                target = None
            validation = sqlite3.connect(str(tmp))
            try:
                if validation.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise RuntimeError("Backup inconsistente")
            finally:
                validation.close()
            os.replace(tmp,dest)
            return {"file":name,"bytes":dest.stat().st_size}
        finally:
            if target is not None: target.close()
            tmp.unlink(missing_ok=True)

    def node_rows(self, limit=5000):
        rows=self._rows("SELECT * FROM nodes ORDER BY last_seen_ms DESC LIMIT ?",(min(int(limit),15000),))
        for r in rows: r["aliases"]=json.loads(r["aliases"] or "[]")
        return rows

    def node_source_rows(self):
        return self._rows("SELECT * FROM node_sources ORDER BY source_id,node_num")

    def topology_processed(self, key):
        with self._lock:
            return self._db.execute("SELECT 1 FROM topology_processed WHERE source_packet_key=?",(key,)).fetchone() is not None

    def record_communication(self, key, source_id, timestamp_ms, from_node, to_node, via_mqtt=False):
        """Capture *logical* unicast traffic, not a claim of a direct RF hop.

        Idempotent across live ingestion and archival reconstruction. Broadcast
        and incomplete addresses are deliberately not promoted into line segments.
        """
        with self._lock,self._db:
            inserted=self._db.execute(
                "INSERT OR IGNORE INTO communication_processed(source_packet_key) VALUES(?)",
                (str(key),)).rowcount
            if not inserted:return False
            try:
                a,b=int(from_node),int(to_node)
            except (TypeError,ValueError):
                return False
            if not (0<a<0xffffffff and 0<b<0xffffffff) or a==b:return False
            ts=int(timestamp_ms)
            transport="mqtt" if via_mqtt else "radio"
            self._db.execute("""INSERT INTO communications(
              source_id,from_node,to_node,transport,first_seen_ms,last_seen_ms,observations)
              VALUES(?,?,?,?,?,?,1)
              ON CONFLICT(source_id,from_node,to_node,transport) DO UPDATE SET
              first_seen_ms=MIN(first_seen_ms,excluded.first_seen_ms),
              last_seen_ms=MAX(last_seen_ms,excluded.last_seen_ms),
              observations=observations+1""",(int(source_id),a,b,transport,ts,ts))
            # Address in packet is *not* proof that the destination was heard.
            return True

    def communication_rows(self, limit=10000):
        return self._rows("""SELECT * FROM communications
               ORDER BY last_seen_ms DESC LIMIT ?""",(min(int(limit),20000),))

    def reprocess_archived_communications(self, limit=1000):
        """Replay a small, ordered batch from raw packets, safe against live RX.

        Progress is stored in communication_processed; reruns never double-count.
        A caller may loop asynchronously until remaining becomes zero.
        """
        rows=self._rows("""SELECT p.source_packet_key,p.source_id,p.timestamp_ms,
                  p.from_node,p.to_node,p.via_mqtt
                  FROM packets AS p LEFT JOIN communication_processed AS c
                    ON c.source_packet_key=p.source_packet_key
                  WHERE c.source_packet_key IS NULL ORDER BY p.id LIMIT ?""",
                  (max(1,min(int(limit),5000)),))
        recorded=0
        for row in rows:
            if self.record_communication(row["source_packet_key"],row["source_id"],
                row["timestamp_ms"],row["from_node"],row["to_node"],row["via_mqtt"]):
                recorded+=1
        return {"processed":len(rows),"communications":recorded,"remaining":len(rows)>=limit}

    def record_topology(self, key, source_id, timestamp_ms, edges, trace=None, historical=False):
        """Atomically store once per original packet; never invent direct RF status."""
        with self._lock,self._db:
            found=self._db.execute("SELECT 1 FROM topology_processed WHERE source_packet_key=?",(str(key),)).fetchone()
            if found:return False
            if trace:
                self._db.execute("INSERT INTO traces(source_id,timestamp_ms,origin,destination,route_json) VALUES(?,?,?,?,?)",
                    (source_id,timestamp_ms,trace["from"],trace["to"],json.dumps(trace)))
            for a,b,quality in list(dict.fromkeys(edges)):
                if not 0<a<b<0xffffffff:continue
                # A traceroute/neighbor reference is a source-specific mention;
                # it is NOT a reception by this node or evidence of being online.
                for num in (a,b):
                    self._db.execute("""INSERT OR IGNORE INTO nodes(node_num,node_id,
                          first_seen_ms,last_seen_ms,last_source_id)
                          VALUES(?,?,?,?,?)""",
                          (num,f"!{num:08x}",0,0,source_id))
                    self._db.execute("""INSERT INTO node_sources(
                          source_id,node_num,first_seen_ms,last_seen_ms,observed)
                          VALUES(?,?,?,?,1)
                          ON CONFLICT(source_id,node_num) DO UPDATE SET
                          last_seen_ms=MAX(last_seen_ms,excluded.last_seen_ms),
                          observed=MAX(observed,excluded.observed)""",
                          (source_id,num,timestamp_ms,timestamp_ms))
                if historical:
                    # Earlier versions already stored some decoded edges; avoid
                    # inflating their observation count when backfilling packets.
                    present=self._db.execute("SELECT 1 FROM links WHERE source_id=? AND a=? AND b=? AND quality=?",
                                        (source_id,a,b,quality)).fetchone()
                    if present:continue
                self._db.execute("""INSERT INTO links(source_id,a,b,quality,first_seen_ms,last_seen_ms,observations)
                    VALUES(?,?,?,?,?,?,1) ON CONFLICT(source_id,a,b,quality) DO UPDATE SET
                    last_seen_ms=MAX(last_seen_ms,excluded.last_seen_ms),
                    first_seen_ms=MIN(first_seen_ms,excluded.first_seen_ms),
                    observations=links.observations+1""",
                    (source_id,a,b,quality,timestamp_ms,timestamp_ms))
            self._db.execute("INSERT INTO topology_processed(source_packet_key) VALUES(?)",(str(key),))
        return True

    def reprocess_archived_topology(self, parser, limit=10000):
        """One-time migration for packets recorded before topology parsing existed."""
        rows=self._rows("""SELECT source_packet_key,source_id,timestamp_ms,raw_json,from_node,to_node,port
          FROM packets WHERE port IN ('TRACEROUTE_APP','NEIGHBORINFO_APP','70','71')
          AND source_packet_key NOT IN (SELECT source_packet_key FROM topology_processed)
          ORDER BY timestamp_ms DESC LIMIT ?""",(int(limit),))
        processed=0;linked=0
        for p in rows:
            try:
                packet=json.loads(p["raw_json"] or "{}")
                if not isinstance(packet,dict):continue
                # Correct old mislabeled numeric port 67 only when packet metadata
                # explicitly says traceroute; it is TELEMETRY in the protocol.
                kind,edges=parser(packet)
                if kind is None:continue
                self.record_topology(p["source_packet_key"],p["source_id"],
                            p["timestamp_ms"],edges or [],historical=True)
                processed+=1;linked+=len(edges or [])
            except (ValueError,TypeError,sqlite3.Error):continue
        return {"processed":processed,"candidate_edges":linked}

    def topology_diagnostics(self,source_id=None):
        args=() if source_id is None else (int(source_id),)
        where="" if source_id is None else " WHERE source_id=?"
        edges=self._rows("SELECT * FROM links"+where+" ORDER BY last_seen_ms DESC LIMIT 20000",args)
        coords={n["node_num"]:n for n in self._rows("SELECT node_num,latitude,longitude,position_ms FROM nodes")}
        visible=missing=0
        for edge in edges:
            a=coords.get(edge["a"]);b=coords.get(edge["b"])
            if a and b and all(n["latitude"] is not None and n["longitude"] is not None for n in (a,b)):
                visible+=1
            else:missing+=1
        return {"stored":len(edges),"drawable":visible,"missing_positions":missing,
                "note":"Relações de rota/neighbor não são prova de RF direto."}

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

    def upsert_waypoint(self, source_id, waypoint_id, from_node, ts, latitude, longitude,
                        name="", description="", icon=0, expires_ms=0):
        """One latest known waypoint per observing source, with historical provenance."""
        source_id, waypoint_id = int(source_id), int(waypoint_id)
        if not (0 < waypoint_id < 2**32): raise ValueError("Waypoint ID inválido")
        lat, lon = float(latitude), float(longitude)
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Coordenadas inválidas do waypoint")
        if abs(lat)<0.000001 and abs(lon)<0.000001:
            raise ValueError("Waypoint em 0,0 sem posição confiável")
        ts = int(ts)
        icon = int(icon or 0)
        if not 0 <= icon <= 0x10ffff: icon = 0
        with self._lock, self._db:
            self._db.execute("""
               INSERT INTO waypoints(source_id,waypoint_id,from_node,latitude,longitude,
                  name,description,icon,expires_ms,first_seen_ms,last_seen_ms)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(source_id,waypoint_id) DO UPDATE SET
                 from_node=excluded.from_node,latitude=excluded.latitude,
                 longitude=excluded.longitude,name=excluded.name,
                 description=excluded.description,icon=excluded.icon,
                 expires_ms=excluded.expires_ms,last_seen_ms=excluded.last_seen_ms
               WHERE excluded.last_seen_ms >= waypoints.last_seen_ms
            """,(source_id,waypoint_id,from_node,lat,lon,str(name)[:30],
                 str(description)[:100],icon,int(expires_ms or 0),ts,ts))

    def waypoint_rows(self, limit=5000):
        """Only active waypoints; expired records remain until normal retention cleanup."""
        return self._rows("""SELECT * FROM waypoints
           WHERE expires_ms=0 OR expires_ms>?
           ORDER BY last_seen_ms DESC LIMIT ?""",
           (now_ms(),min(int(limit),15000)))

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
            return {k:count(k) for k in ("nodes","packets","messages","positions","traces","links","events","sources","waypoints","communications")}