"""Alertas da malha (#165).

Regras avaliadas a cada minuto: favorito calado, bateria baixa, canal
congestionado, mensagem privada e menção. Cada condição gera no máximo um
alerta ativo por chave; ele só se repete depois de resolvido. Entrega no
aplicativo e, opcionalmente, por Telegram e e-mail (SMTP).
"""
from __future__ import annotations

import json
import logging
import smtplib
import ssl
import threading
import time
import urllib.parse
import urllib.request
from email.message import EmailMessage

from .database import now_ms

LOG = logging.getLogger(__name__)
REPEATER_ROLES = {"ROUTER", "REPEATER", "ROUTER_LATE", "ROUTER_CLIENT"}
SECRET = "********"
DEFAULTS = {
    "enabled": True,
    "silent_favorite_hours": 6,
    "battery_below": 20,
    "channel_util_above": 30,
    "direct_messages": True,
    "mentions": True,
    "telegram": {"enabled": False, "token": "", "chat_id": ""},
    "email": {"enabled": False, "host": "", "port": 587, "security": "starttls",
              "user": "", "password": "", "sender": "", "to": ""},
}


class AlertCenter:
    def __init__(self, db, sources, sender=None, interval=60):
        self.db = db
        self.sources = sources
        self.interval = interval
        self._send = sender or self._deliver
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.RLock()
        with db._lock, db._db:
            db._db.execute("""CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL, kind TEXT NOT NULL,
                title TEXT NOT NULL, text TEXT NOT NULL,
                created_ms INTEGER NOT NULL, resolved_ms INTEGER NOT NULL DEFAULT 0,
                read INTEGER NOT NULL DEFAULT 0, delivery TEXT NOT NULL DEFAULT ''
            )""")
            db._db.execute("CREATE INDEX IF NOT EXISTS idx_alerts_open ON alerts(key,resolved_ms)")

    # --- configuração -------------------------------------------------------
    def config(self, public=False):
        stored = self.db._setting("alerts", {}) or {}
        cfg = json.loads(json.dumps(DEFAULTS))
        for key, value in stored.items():
            if key in ("telegram", "email") and isinstance(value, dict):
                cfg[key].update({k: v for k, v in value.items() if k in cfg[key]})
            elif key in cfg:
                cfg[key] = value
        if public:
            for group, field in (("telegram", "token"), ("email", "password")):
                cfg[group]["has_" + field] = bool(cfg[group][field])
                cfg[group][field] = SECRET if cfg[group][field] else ""
        return cfg

    def save(self, patch):
        if not isinstance(patch, dict):
            raise ValueError("Configuração de alertas inválida")
        cfg = self.config()
        for key in ("enabled", "direct_messages", "mentions"):
            if key in patch:
                if type(patch[key]) is not bool:
                    raise ValueError("Valor inválido: " + key)
                cfg[key] = patch[key]
        for key, lo, hi in (("silent_favorite_hours", 0, 720), ("battery_below", 0, 100),
                            ("channel_util_above", 0, 100)):
            if key in patch:
                if type(patch[key]) is not int or not lo <= patch[key] <= hi:
                    raise ValueError("Valor inválido: " + key)
                cfg[key] = patch[key]
        for group in ("telegram", "email"):
            update = patch.get(group)
            if update is None:
                continue
            if not isinstance(update, dict) or set(update) - set(cfg[group]):
                raise ValueError("Configuração inválida: " + group)
            for k, v in update.items():
                if v == SECRET:
                    continue  # segredo mantido
                cfg[group][k] = v
        if cfg["email"]["security"] not in ("starttls", "ssl", "none"):
            raise ValueError("Segurança do e-mail: starttls, ssl ou none")
        cfg["email"]["port"] = int(cfg["email"]["port"] or 587)
        self.db._set_setting("alerts", cfg)
        return self.config(public=True)

    # --- ciclo ----------------------------------------------------------------
    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, name="mesh-alerts", daemon=True)
            self._thread.start()

    def close(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.wait(self.interval):
            try:
                self.evaluate()
            except Exception:
                LOG.exception("Falha ao avaliar alertas")

    def _own_nodes(self):
        own = set()
        for state in self.sources.snapshot().values():
            if state.get("local_node_num"):
                own.add(int(state["local_node_num"]))
        for src in self.db.sources(public=False):
            if src["config"].get("node_num"):
                own.add(int(src["config"]["node_num"]))
        return own

    def _name(self, num, row=None):
        row = row or (self.db._rows("SELECT long_name,short_name,node_id FROM nodes WHERE node_num=?", (int(num),)) or [{}])[0]
        return row.get("long_name") or row.get("short_name") or row.get("node_id") or "!%08x" % int(num)

    def evaluate(self, now=None):
        """Avalia todas as regras; devolve os alertas novos."""
        cfg = self.config()
        if not cfg["enabled"]:
            return []
        now = now or now_ms()
        active = {}  # chave -> (tipo, título, texto)
        own = self._own_nodes()
        if cfg["silent_favorite_hours"]:
            limit = now - cfg["silent_favorite_hours"] * 3600000
            for num, fav in self.db.app_favorites().items():
                if not fav["is_favorite"] or num in own:
                    continue
                row = self.db._rows("SELECT * FROM nodes WHERE node_num=?", (num,))
                if not row or not row[0]["last_seen_ms"]:
                    continue
                seen = int(row[0]["last_seen_ms"])
                if seen < limit and seen > now - 30 * 86400000:
                    hours = (now - seen) // 3600000
                    active["silent:%d" % num] = ("silent", "Favorito calado: " + self._name(num, row[0]),
                                                 "%s não é ouvido há %d h." % (self._name(num, row[0]), hours))
        if cfg["battery_below"]:
            favorites = {n for n, f in self.db.app_favorites().items() if f["is_favorite"]}
            rows = self.db._rows("""SELECT * FROM nodes WHERE battery IS NOT NULL AND battery>0 AND battery<=100
                                    AND battery<? AND last_seen_ms>=?""", (cfg["battery_below"], now - 86400000))
            for row in rows:
                if (row["role"] or "") in REPEATER_ROLES or row["node_num"] in favorites:
                    active["battery:%d" % row["node_num"]] = ("battery", "Bateria baixa: " + self._name(row["node_num"], row),
                        "%s está com %d%% de bateria." % (self._name(row["node_num"], row), row["battery"]))
        if cfg["channel_util_above"] and own:
            marks = ",".join("?" * len(own))
            row = self.db._rows("SELECT channel_util FROM rf_samples WHERE node_num IN (" + marks + ") "
                                "AND timestamp_ms>=? AND channel_util IS NOT NULL ORDER BY timestamp_ms DESC LIMIT 1",
                                tuple(own) + (now - 1800000,))
            if row and float(row[0]["channel_util"]) > cfg["channel_util_above"]:
                active["channel"] = ("channel", "Canal congestionado",
                                     "Utilização do canal em %.0f%% (limite %d%%)." % (float(row[0]["channel_util"]), cfg["channel_util_above"]))
        created = self._sync(active, now)
        created += self._messages(cfg, own, now)
        for alert in created:
            self._dispatch(alert, cfg)
        return created

    def _sync(self, active, now):
        """Cria alertas novos e resolve os que deixaram de valer (sem repetir)."""
        created = []
        with self.db._lock, self.db._db:
            open_rows = {r["key"]: r["id"] for r in self.db._db.execute(
                "SELECT id,key FROM alerts WHERE resolved_ms=0 AND kind IN ('silent','battery','channel')")}
            for key, alert_id in open_rows.items():
                if key not in active:
                    self.db._db.execute("UPDATE alerts SET resolved_ms=? WHERE id=?", (now, alert_id))
            for key, (kind, title, text) in active.items():
                if key in open_rows:
                    continue
                cur = self.db._db.execute("INSERT INTO alerts(key,kind,title,text,created_ms) VALUES(?,?,?,?,?)",
                                          (key, kind, title, text, now))
                created.append({"id": cur.lastrowid, "key": key, "kind": kind, "title": title, "text": text, "created_ms": now})
        return created

    def _messages(self, cfg, own, now):
        """Mensagens privadas e menções novas desde a última avaliação."""
        last = self.db._setting("alerts_last_message_id")
        newest = self.db._rows("SELECT MAX(id) AS id FROM messages")[0]["id"] or 0
        if last is None:
            self.db._set_setting("alerts_last_message_id", newest)  # não alerta o histórico antigo
            return []
        rows = self.db._rows("SELECT * FROM messages WHERE id>? AND direction='rx' ORDER BY id", (int(last),))
        self.db._set_setting("alerts_last_message_id", newest)
        names = set()
        for num in own:
            row = self.db._rows("SELECT long_name,short_name FROM nodes WHERE node_num=?", (num,))
            if row:
                names |= {n.casefold() for n in (row[0]["long_name"], row[0]["short_name"]) if n and len(n) >= 2}
        created = []
        with self.db._lock, self.db._db:
            for m in rows:
                sender = self._name(m["from_node"]) if m["from_node"] is not None else "?"
                direct = m["to_node"] is not None and m["to_node"] in own
                mention = not direct and any(n in str(m["text"]).casefold() for n in names)
                if direct and cfg["direct_messages"]:
                    kind, title = "dm", "Mensagem privada de " + sender
                elif mention and cfg["mentions"]:
                    kind, title = "mention", "Menção de " + sender
                else:
                    continue
                text = str(m["text"])[:300]
                cur = self.db._db.execute("INSERT INTO alerts(key,kind,title,text,created_ms,resolved_ms) VALUES(?,?,?,?,?,?)",
                                          ("msg:%d" % m["id"], kind, title, text, now, now))
                created.append({"id": cur.lastrowid, "kind": kind, "title": title, "text": text, "created_ms": now})
        return created

    # --- entrega ---------------------------------------------------------------
    def _dispatch(self, alert, cfg):
        channels = []
        if cfg["telegram"]["enabled"] and cfg["telegram"]["token"] and cfg["telegram"]["chat_id"]:
            channels.append("telegram")
        if cfg["email"]["enabled"] and cfg["email"]["host"] and cfg["email"]["to"]:
            channels.append("email")
        if not channels:
            return
        def work():
            done = []
            for channel in channels:
                try:
                    self._send(channel, alert, cfg)
                    done.append(channel)
                except Exception as exc:
                    done.append(channel + ":erro")
                    self.db.log("Alerta não entregue por " + channel + ": " + type(exc).__name__, "warning")
            if alert.get("id"):
                with self.db._lock, self.db._db:
                    self.db._db.execute("UPDATE alerts SET delivery=? WHERE id=?", (",".join(done), alert["id"]))
        threading.Thread(target=work, name="alert-delivery", daemon=True).start()

    @staticmethod
    def _deliver(channel, alert, cfg):
        text = "PT2VHF Mesh Analyzer — " + alert["title"] + "\n" + alert["text"]
        if channel == "telegram":
            tg = cfg["telegram"]
            data = urllib.parse.urlencode({"chat_id": tg["chat_id"], "text": text}).encode()
            url = "https://api.telegram.org/bot" + urllib.parse.quote(str(tg["token"]), safe=":") + "/sendMessage"
            with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=15) as resp:
                if resp.status != 200:
                    raise RuntimeError("Telegram HTTP %d" % resp.status)
        elif channel == "email":
            em = cfg["email"]
            msg = EmailMessage()
            msg["Subject"] = "[Mesh Analyzer] " + alert["title"]
            msg["From"] = em["sender"] or em["user"]
            msg["To"] = em["to"]
            msg.set_content(text)
            context = ssl.create_default_context()
            if em["security"] == "ssl":
                server = smtplib.SMTP_SSL(em["host"], int(em["port"]), timeout=20, context=context)
            else:
                server = smtplib.SMTP(em["host"], int(em["port"]), timeout=20)
            with server:
                if em["security"] == "starttls":
                    server.starttls(context=context)
                if em["user"]:
                    server.login(em["user"], em["password"])
                server.send_message(msg)

    def test(self, channel):
        cfg = self.config()
        if channel not in ("telegram", "email"):
            raise ValueError("Canal de teste inválido")
        try:
            self._send(channel, {"title": "Teste de alerta",
                                 "text": "Se você recebeu esta mensagem, a entrega está funcionando."}, cfg)
        except Exception as exc:
            raise RuntimeError((type(exc).__name__ + ": " + str(exc))[:200]) from exc
        return {"success": True}

    # --- consulta ----------------------------------------------------------------
    def list(self, limit=100):
        rows = self.db._rows("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (min(int(limit), 500),))
        unread = self.db._rows("SELECT COUNT(*) AS n FROM alerts WHERE read=0")[0]["n"]
        return {"alerts": rows, "unread": unread}

    def mark_read(self):
        with self.db._lock, self.db._db:
            self.db._db.execute("UPDATE alerts SET read=1 WHERE read=0")
        return {"success": True}
