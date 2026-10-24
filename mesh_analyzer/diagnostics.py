"""#198: diagnóstico para suporte em .zip (Configurações → fim da aba).

Junta o que ajuda a investigar um problema sem levar dados pessoais: versões,
conexões (sem senhas, PIN, chaves ou credenciais), Bluetooth (adaptador, rádios
vistos, pareamento, últimas tentativas), portas USB, eventos, configurações e
números do banco. Não inclui texto de mensagens nem posições dos nós.

O log detalhado de Bluetooth (#191) fica ligado por alguns minutos: bleak,
meshtastic e o próprio app passam a registrar em DEBUG num buffer em memória,
que entra no .zip.
"""
from __future__ import annotations

import io
import json
import logging
import platform
import re
import sys
import threading
import time
import zipfile
from collections import deque
from datetime import datetime
from pathlib import Path

LOG = logging.getLogger(__name__)
SECRET = re.compile(r"(pass|senha|token|secret|psk|^pin$|_pin|pin_|key|credential)", re.I)
VERBOSE_LOGGERS = ("bleak", "meshtastic", "mesh_analyzer", "meshcore")
FILE_RE = re.compile(r"^PT2VHF-Diagnostico-\d{8}-\d{6}\.zip$")
MAX_RECORDS = 8000


class RingLog(logging.Handler):
    """Últimas linhas de log do app, em memória (entram no diagnóstico)."""

    def __init__(self, size=MAX_RECORDS):
        super().__init__(logging.DEBUG)
        self.records = deque(maxlen=size)
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        self.verbose_until = 0.0
        self._timer = None
        self._lock = threading.Lock()

    def emit(self, record):
        try:
            self.records.append(self.format(record)[:2000])
        except Exception:
            pass

    def install(self):
        root = logging.getLogger()
        if self not in root.handlers:
            for handler in root.handlers:
                if handler.level == logging.NOTSET:
                    handler.setLevel(logging.WARNING)   # o console continua só com avisos
            root.addHandler(self)
        for name in VERBOSE_LOGGERS:
            logger = logging.getLogger(name)
            if logger.level == logging.NOTSET or logger.level > logging.INFO:
                logger.setLevel(logging.INFO)
        return self

    def verbose(self, minutes=10):
        """Liga o log detalhado (DEBUG) por alguns minutos."""
        minutes = max(1, min(int(minutes), 60))
        with self._lock:
            self.verbose_until = time.time() + minutes * 60
            for name in VERBOSE_LOGGERS:
                logging.getLogger(name).setLevel(logging.DEBUG)
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(minutes * 60, self._quiet)
            self._timer.daemon = True
            self._timer.start()
        LOG.info("Log detalhado ligado por %d min (diagnóstico #198)", minutes)
        return self.status()

    def _quiet(self):
        with self._lock:
            self.verbose_until = 0.0
            for name in VERBOSE_LOGGERS:
                logging.getLogger(name).setLevel(logging.INFO)

    def status(self):
        left = max(0, int(self.verbose_until - time.time()))
        return {"verbose": left > 0, "seconds_left": left, "lines": len(self.records)}


RING = RingLog()


def clean(value):
    """Remove campos com cara de segredo (senha, PIN, chave, token…), em qualquer nível."""
    if isinstance(value, dict):
        return {k: ("***" if SECRET.search(str(k)) and v not in (None, "", False) else clean(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, bytes):
        return "<%d bytes>" % len(value)
    return value


def _versions():
    out = {"app": None, "python": sys.version.split()[0], "sistema": platform.platform(),
           "maquina": platform.machine(), "empacotado": bool(getattr(sys, "frozen", False))}
    try:
        from . import __version__
        out["app"] = __version__
    except Exception:
        pass
    from importlib import metadata
    for package in ("meshtastic", "bleak", "meshcore", "winrt-runtime", "pywebview", "paho-mqtt", "pyserial"):
        try:
            out[package] = metadata.version(package)
        except Exception:
            out[package] = None
    return out


def _usb():
    try:
        from serial.tools import list_ports
        return [{"porta": p.device, "descricao": p.description, "fabricante": p.manufacturer,
                 "vid": "%04X" % p.vid if p.vid else None, "pid": "%04X" % p.pid if p.pid else None,
                 "hwid": p.hwid} for p in list_ports.comports()]
    except Exception as exc:
        return {"erro": str(exc)[:200]}


def _bluetooth(watcher, autoadd, scan=True):
    data = {}
    try:
        from .ble_pairing import adapter_info, is_paired
        data["adaptador"] = adapter_info()
    except Exception as exc:
        data["adaptador"] = {"erro": str(exc)[:200]}
        is_paired = None
    if scan:
        try:
            from .device_detection import scan_ble
            seen = scan_ble(timeout=5.0)
            for item in seen:
                item.pop("config", None)
                if is_paired:
                    item["pareado_no_sistema"] = is_paired(item["address"])
            data["radios_vistos"] = seen
        except Exception as exc:
            data["radios_vistos"] = {"erro": str(exc)[:200]}
    if autoadd is not None:
        data["adicionar_automaticamente"] = clean(autoadd.status())
    if watcher is not None:
        try:
            data["avisos_de_radio"] = clean([{k: v for k, v in n.items() if k != "candidate"} for n in watcher.notices()])
        except Exception as exc:
            data["avisos_de_radio"] = {"erro": str(exc)[:200]}
    return data


def _config(db, automation=None, msgauto=None, alerts=None):
    out = {}
    for name, read in (("sistema", lambda: db.system_settings()), ("retencao", lambda: db.retention()),
                       ("automacao_meshtastic", lambda: automation.config() if automation else None),
                       ("mensagens_automaticas", lambda: msgauto.config() if msgauto else None),
                       ("alertas", lambda: alerts.config(public=True) if alerts else None),
                       ("meshcore", lambda: db._setting("meshcore_automation", None))):
        try:
            out[name] = clean(read())
        except Exception as exc:
            out[name] = {"erro": str(exc)[:200]}
    return out


def _events(db, days=7):
    since = int((time.time() - days * 86400) * 1000)
    rows = db._rows("SELECT timestamp_ms,source_id,level,description FROM events WHERE timestamp_ms>=? "
                    "ORDER BY timestamp_ms LIMIT 20000", (since,))
    return "\n".join("%s [%s] fonte=%s %s" % (datetime.fromtimestamp(r["timestamp_ms"] / 1000).strftime("%Y-%m-%d %H:%M:%S"),
                                             r["level"], r["source_id"], r["description"]) for r in rows)


def build(db, sources=None, watcher=None, autoadd=None, automation=None, msgauto=None, alerts=None, scan=True):
    """Monta o .zip em memória e devolve os bytes."""
    versions = _versions()
    connections = []
    snapshot = {}
    try:
        snapshot = sources.snapshot() if sources is not None else {}
    except Exception:
        pass
    for src in db.sources(public=False):
        connections.append({"id": src["id"], "nome": src["name"], "tipo": src["kind"], "ativa": bool(src["enabled"]),
                            "config": clean(src.get("config") or {}), "estado": clean(snapshot.get(str(src["id"]), {}))})
    files = {
        "resumo.txt": "PT2VHF Mesh Analyzer — diagnóstico para suporte\nGerado em %s\n\n%s\n\n"
                      "Não inclui texto de mensagens, posições dos nós, senhas, PIN, chaves ou credenciais.\n"
                      % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                         "\n".join("%s: %s" % (k, v) for k, v in versions.items())),
        "conexoes.json": connections,
        "bluetooth.json": _bluetooth(watcher, autoadd, scan=scan),
        "usb.json": _usb(),
        "configuracao.json": _config(db, automation, msgauto, alerts),
        "banco.json": {"contagens": db.stats(), "saude": clean(db.health())},
        "eventos.txt": _events(db),
        "log.txt": "\n".join(RING.records) or "(sem linhas de log nesta execução)",
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False, indent=2, default=str)
            zf.writestr(name, content)
    return buf.getvalue()


def diagnostics_dir(profile: Path) -> Path:
    path = Path(profile) / "diagnostics"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save(profile: Path, data: bytes, keep=5) -> Path:
    folder = diagnostics_dir(profile)
    path = folder / datetime.now().strftime("PT2VHF-Diagnostico-%Y%m%d-%H%M%S.zip")
    path.write_bytes(data)
    for old in sorted(folder.glob("PT2VHF-Diagnostico-*.zip"))[:-keep]:
        try:
            old.unlink()
        except OSError:
            pass
    return path


def diagnostic_file(profile: Path, name: str) -> Path:
    if not FILE_RE.fullmatch(str(name)):
        raise ValueError("Nome de diagnóstico inválido")
    path = diagnostics_dir(profile) / name
    if not path.is_file():
        raise LookupError("Diagnóstico não encontrado")
    return path
