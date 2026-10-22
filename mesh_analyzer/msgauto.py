"""Mensagens agendadas (#172) e respostas automáticas a comandos (#173).

Tudo passa pelo rádio ativo e por um orçamento único de envios por hora,
separado das consultas RF automáticas. Respostas só para mensagens recebidas
há pouco (nunca para o histórico reenviado pelo rádio ao conectar), nunca para
o próprio rádio e com pausa por remetente.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import unicodedata
import urllib.request
from datetime import datetime, timedelta

from .database import now_ms

LOG = logging.getLogger(__name__)
DEFAULTS = {"enabled": True, "max_per_hour": 10}
MAX_MESSAGE_BYTES = 220
FRESH_MS = 120000
KINDS = ("once", "daily", "interval")
MATCHES = ("exact", "starts", "contains")
SCOPES = ("dm", "channel", "both")


def _fold(text):
    return "".join(c for c in unicodedata.normalize("NFD", str(text or "").casefold().strip())
                   if unicodedata.category(c) != "Mn")


class MessageAutomation:
    def __init__(self, db, sources, interval=5, weather=None):
        self.db = db
        self.sources = sources
        self.interval = interval
        self._weather = weather or self._fetch_weather
        self._weather_cache = (0, "")
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.RLock()
        with db._lock, db._db:
            db._db.executescript("""
            CREATE TABLE IF NOT EXISTS scheduled_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, enabled INTEGER NOT NULL DEFAULT 1,
                name TEXT NOT NULL DEFAULT '', text TEXT NOT NULL,
                target INTEGER, channel INTEGER NOT NULL DEFAULT 0,
                kind TEXT NOT NULL, at_ms INTEGER NOT NULL DEFAULT 0,
                time_hhmm TEXT NOT NULL DEFAULT '', weekdays INTEGER NOT NULL DEFAULT 127,
                interval_min INTEGER NOT NULL DEFAULT 0,
                next_ms INTEGER NOT NULL DEFAULT 0, last_sent_ms INTEGER NOT NULL DEFAULT 0,
                last_error TEXT NOT NULL DEFAULT '', created_ms INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS auto_replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT, enabled INTEGER NOT NULL DEFAULT 1,
                trigger TEXT NOT NULL, match TEXT NOT NULL DEFAULT 'exact',
                response TEXT NOT NULL, scope TEXT NOT NULL DEFAULT 'both',
                cooldown_s INTEGER NOT NULL DEFAULT 300, created_ms INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS msgauto_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp_ms INTEGER NOT NULL,
                kind TEXT NOT NULL, ref_id INTEGER NOT NULL, target INTEGER,
                sender INTEGER, text TEXT NOT NULL, status TEXT NOT NULL, error TEXT NOT NULL DEFAULT '');
            CREATE INDEX IF NOT EXISTS idx_msgauto_log_time ON msgauto_log(timestamp_ms);
            """)

    # --- configuração ---------------------------------------------------------
    def config(self):
        cfg = dict(DEFAULTS)
        stored = self.db._setting("msgauto", {}) or {}
        cfg.update({k: stored[k] for k in DEFAULTS if k in stored})
        return cfg

    def save_config(self, patch):
        cfg = self.config()
        if "enabled" in patch:
            if type(patch["enabled"]) is not bool:
                raise ValueError("Ativação inválida")
            cfg["enabled"] = patch["enabled"]
        if "max_per_hour" in patch:
            if type(patch["max_per_hour"]) is not int or not 1 <= patch["max_per_hour"] <= 60:
                raise ValueError("Limite por hora: 1 a 60")
            cfg["max_per_hour"] = patch["max_per_hour"]
        self.db._set_setting("msgauto", cfg)
        return cfg

    def overview(self):
        return {"config": self.config(),
                "schedules": self.db._rows("SELECT * FROM scheduled_messages ORDER BY id"),
                "replies": self.db._rows("SELECT * FROM auto_replies ORDER BY id"),
                "log": self.db._rows("SELECT * FROM msgauto_log ORDER BY id DESC LIMIT 50"),
                "sent_last_hour": self._sent_last_hour(now_ms())}

    @staticmethod
    def _text(value, field="Texto"):
        text = str(value or "").strip()
        if not text:
            raise ValueError(field + " vazio")
        if len(text.encode("utf-8")) > MAX_MESSAGE_BYTES:
            raise ValueError(field + " acima de 220 bytes")
        return text

    # --- agendamentos -----------------------------------------------------------
    def save_schedule(self, data, now=None):
        now = now or now_ms()
        kind = data.get("kind")
        if kind not in KINDS:
            raise ValueError("Tipo de agendamento: once, daily ou interval")
        text = self._text(data.get("text"))
        target = data.get("target")
        target = None if target in (None, "", "^all") else int(target)
        channel = int(data.get("channel") or 0)
        if not 0 <= channel <= 7:
            raise ValueError("Canal inválido")
        row = {"enabled": 1 if data.get("enabled", True) else 0, "name": str(data.get("name") or "")[:60],
               "text": text, "target": target, "channel": channel, "kind": kind,
               "at_ms": 0, "time_hhmm": "", "weekdays": 127, "interval_min": 0}
        if kind == "once":
            row["at_ms"] = int(data.get("at_ms") or 0)
            if row["at_ms"] <= now:
                raise ValueError("Escolha uma data e hora no futuro")
        elif kind == "daily":
            hhmm = str(data.get("time_hhmm") or "")
            try:
                datetime.strptime(hhmm, "%H:%M")
            except ValueError:
                raise ValueError("Horário no formato HH:MM") from None
            row["time_hhmm"] = hhmm
            row["weekdays"] = int(data.get("weekdays", 127)) & 127 or 127
        else:
            row["interval_min"] = int(data.get("interval_min") or 0)
            if not 15 <= row["interval_min"] <= 10080:
                raise ValueError("Intervalo: 15 minutos a 7 dias")
        row["next_ms"] = self._next_time(row, now)
        sid = int(data.get("id") or 0)
        fields = list(row)
        with self.db._lock, self.db._db:
            if sid:
                self.db._db.execute("UPDATE scheduled_messages SET " + ",".join(f + "=?" for f in fields) + ",last_error='' WHERE id=?",
                                    [row[f] for f in fields] + [sid])
            else:
                sid = self.db._db.execute("INSERT INTO scheduled_messages(" + ",".join(fields) + ",created_ms) VALUES(" +
                                          ",".join("?" * len(fields)) + ",?)", [row[f] for f in fields] + [now]).lastrowid
        return self.db._rows("SELECT * FROM scheduled_messages WHERE id=?", (sid,))[0]

    def delete_schedule(self, sid):
        with self.db._lock, self.db._db:
            self.db._db.execute("DELETE FROM scheduled_messages WHERE id=?", (int(sid),))
        return {"success": True}

    @staticmethod
    def _next_time(row, now):
        if row["kind"] == "once":
            return row["at_ms"] if row["at_ms"] > now else 0
        if row["kind"] == "interval":
            base = max(now, int(row.get("last_sent_ms") or 0))
            return base + row["interval_min"] * 60000
        hour, minute = (int(x) for x in row["time_hhmm"].split(":"))
        current = datetime.fromtimestamp(now / 1000)
        for day in range(0, 8):
            candidate = (current + timedelta(days=day)).replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate.timestamp() * 1000 > now and row["weekdays"] & (1 << candidate.weekday()):
                return int(candidate.timestamp() * 1000)
        return 0

    # --- respostas automáticas --------------------------------------------------
    def save_reply(self, data, now=None):
        trigger = self._text(data.get("trigger"), "Comando")[:60]
        response = self._text(data.get("response"), "Resposta")
        match = data.get("match", "exact")
        scope = data.get("scope", "both")
        if match not in MATCHES or scope not in SCOPES:
            raise ValueError("Tipo de comparação ou alcance inválido")
        cooldown = int(data.get("cooldown_s", 300))
        if not 30 <= cooldown <= 86400:
            raise ValueError("Pausa por remetente: 30 s a 24 h")
        row = {"enabled": 1 if data.get("enabled", True) else 0, "trigger": trigger, "match": match,
               "response": response, "scope": scope, "cooldown_s": cooldown}
        rid = int(data.get("id") or 0)
        with self.db._lock, self.db._db:
            if rid:
                self.db._db.execute("UPDATE auto_replies SET " + ",".join(f + "=?" for f in row) + " WHERE id=?", list(row.values()) + [rid])
            else:
                rid = self.db._db.execute("INSERT INTO auto_replies(" + ",".join(row) + ",created_ms) VALUES(" +
                                          ",".join("?" * len(row)) + ",?)", list(row.values()) + [now or now_ms()]).lastrowid
        return self.db._rows("SELECT * FROM auto_replies WHERE id=?", (rid,))[0]

    def delete_reply(self, rid):
        with self.db._lock, self.db._db:
            self.db._db.execute("DELETE FROM auto_replies WHERE id=?", (int(rid),))
        return {"success": True}

    @staticmethod
    def matches(rule, text):
        message, trigger = _fold(text), _fold(rule["trigger"])
        if rule["match"] == "exact":
            return message == trigger
        if rule["match"] == "starts":
            return message == trigger or message.startswith(trigger + " ")
        return trigger in message

    def render(self, template, message=None, now=None):
        """Variáveis: {nome} {curto} {id} {snr} {rssi} {saltos} {hora} {data} {canal} {texto} {clima}."""
        now = now or now_ms()
        moment = datetime.fromtimestamp(now / 1000)
        values = {"hora": moment.strftime("%H:%M"), "data": moment.strftime("%d/%m/%Y"),
                  "nome": "", "curto": "", "id": "", "snr": "?", "rssi": "?", "saltos": "?", "canal": "0", "texto": ""}
        if message:
            num = message.get("from_node")
            node = (self.db._rows("SELECT * FROM nodes WHERE node_num=?", (num,)) or [{}])[0] if num is not None else {}
            values.update(nome=node.get("long_name") or node.get("short_name") or "", curto=node.get("short_name") or "",
                          id=node.get("node_id") or ("!%08x" % num if num is not None else ""),
                          canal=str(message.get("channel") or 0), texto=str(message.get("text") or "")[:80])
            values["nome"] = values["nome"] or values["id"]
            pkt = self.db._rows("SELECT rx_snr,rx_rssi,hop_start,hop_limit FROM packets WHERE source_packet_key=?",
                                (message.get("packet_key"),))
            if pkt:
                p = pkt[0]
                if p["rx_snr"] is not None:
                    values["snr"] = "%.1f dB" % float(p["rx_snr"])
                if p["rx_rssi"] is not None:
                    values["rssi"] = "%d dBm" % int(p["rx_rssi"])
                if p["hop_start"] is not None and p["hop_limit"] is not None:
                    values["saltos"] = str(int(p["hop_start"]) - int(p["hop_limit"]))
        if "{clima}" in template:
            values["clima"] = self._weather_text()
        out = template
        for key, value in values.items():
            out = out.replace("{" + key + "}", str(value))
        encoded = out.encode("utf-8")[:MAX_MESSAGE_BYTES]
        return encoded.decode("utf-8", "ignore")

    def _weather_text(self):
        at, text = self._weather_cache
        if text and time.time() - at < 600:
            return text
        try:
            text = self._weather()
        except Exception:
            text = "clima indisponível"
        self._weather_cache = (time.time(), text)
        return text

    def _fetch_weather(self):
        """Tempo atual na posição do rádio ativo (Open-Meteo, sem chave)."""
        active = self.sources.active_radio()
        own = (self.sources.snapshot().get(str(active), {}) or {}).get("local_node_num") if active else None
        row = (self.db._rows("SELECT latitude,longitude FROM nodes WHERE node_num=?", (own,)) or [{}])[0] if own else {}
        if row.get("latitude") is None:
            return "clima indisponível (rádio sem posição)"
        url = ("https://api.open-meteo.com/v1/forecast?latitude=%.4f&longitude=%.4f"
               "&current=temperature_2m,relative_humidity_2m,wind_speed_10m" % (row["latitude"], row["longitude"]))
        with urllib.request.urlopen(url, timeout=10) as resp:
            cur = json.loads(resp.read())["current"]
        return "%.0f°C, umidade %d%%, vento %.0f km/h" % (cur["temperature_2m"], cur["relative_humidity_2m"], cur["wind_speed_10m"])

    # --- envio ---------------------------------------------------------------------
    def _sent_last_hour(self, now):
        return self.db._rows("SELECT COUNT(*) AS n FROM msgauto_log WHERE status='sent' AND timestamp_ms>=?",
                             (now - 3600000,))[0]["n"]

    def _log(self, kind, ref, target, sender, text, status, error=""):
        with self.db._lock, self.db._db:
            self.db._db.execute("""INSERT INTO msgauto_log(timestamp_ms,kind,ref_id,target,sender,text,status,error)
              VALUES(?,?,?,?,?,?,?,?)""", (now_ms(), kind, ref, target, sender, text[:240], status, str(error)[:160]))

    def _send(self, kind, ref, target, channel, text, sender=None):
        now = now_ms()
        if self._sent_last_hour(now) >= self.config()["max_per_hour"]:
            self._log(kind, ref, target, sender, text, "skipped", "Limite de envios por hora")
            return False
        radio = self.sources.active_radio()
        if radio is None:
            self._log(kind, ref, target, sender, text, "skipped", "Nenhum rádio conectado")
            return False
        try:
            self.sources.send_text(radio, target, text, channel)
        except Exception as exc:
            self._log(kind, ref, target, sender, text, "error", str(exc))
            return False
        self._log(kind, ref, target, sender, text, "sent")
        return True

    def run_schedules(self, now=None):
        now = now or now_ms()
        sent = 0
        for row in self.db._rows("SELECT * FROM scheduled_messages WHERE enabled=1 AND next_ms>0 AND next_ms<=?", (now,)):
            ok = self._send("schedule", row["id"], row["target"], row["channel"], self.render(row["text"], None, now))
            sent += ok
            row["last_sent_ms"] = now if ok else row["last_sent_ms"]
            following = self._next_time(row, now) if row["kind"] != "once" else 0
            with self.db._lock, self.db._db:
                self.db._db.execute("UPDATE scheduled_messages SET next_ms=?,last_sent_ms=?,last_error=?,enabled=? WHERE id=?",
                                    (following, row["last_sent_ms"], "" if ok else "Não enviado; veja o registro",
                                     0 if row["kind"] == "once" else row["enabled"], row["id"]))
        return sent

    def _own_nodes(self):
        own = {int(s["local_node_num"]) for s in self.sources.snapshot().values() if s.get("local_node_num")}
        own |= {int(s["config"]["node_num"]) for s in self.db.sources(public=False) if s["config"].get("node_num")}
        return own

    def run_replies(self, now=None):
        now = now or now_ms()
        last = self.db._setting("msgauto_last_message_id")
        newest = self.db._rows("SELECT MAX(id) AS id FROM messages")[0]["id"] or 0
        self.db._set_setting("msgauto_last_message_id", newest)
        if last is None:
            return 0
        rules = self.db._rows("SELECT * FROM auto_replies WHERE enabled=1 ORDER BY id")
        if not rules:
            return 0
        own = self._own_nodes()
        sent = 0
        for m in self.db._rows("SELECT * FROM messages WHERE id>? AND direction='rx' ORDER BY id", (int(last),)):
            if m["from_node"] in own or now - int(m["timestamp_ms"]) > FRESH_MS:
                continue  # nunca responde a si mesmo nem a histórico reenviado
            direct = m["to_node"] is not None and m["to_node"] != 0xffffffff
            for rule in rules:
                if rule["scope"] == "dm" and not direct or rule["scope"] == "channel" and direct:
                    continue
                if not self.matches(rule, m["text"]):
                    continue
                recent = self.db._rows("""SELECT 1 FROM msgauto_log WHERE kind='reply' AND ref_id=? AND sender=?
                    AND status='sent' AND timestamp_ms>=? LIMIT 1""", (rule["id"], m["from_node"], now - rule["cooldown_s"] * 1000))
                if recent:
                    self._log("reply", rule["id"], None, m["from_node"], rule["response"], "skipped", "Pausa por remetente")
                    break
                target = m["from_node"] if direct else None
                sent += self._send("reply", rule["id"], target, m["channel"] or 0, self.render(rule["response"], m, now), m["from_node"])
                break
        return sent

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, name="message-automation", daemon=True)
            self._thread.start()

    def close(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.wait(self.interval):
            if not self.config()["enabled"]:
                continue
            try:
                self.run_replies()
                self.run_schedules()
            except Exception:
                LOG.exception("Falha nas mensagens automáticas")
