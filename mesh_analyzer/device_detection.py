"""Detecção de rádios Meshtastic novos e cadastro em um clique (#149, #151).

- DeviceWatcher acompanha em segundo plano portas USB/Serial, anúncios mDNS
  e (periodicamente) BLE próximos, e avisa sobre rádios ainda não cadastrados.
- AutoAdd varre USB, Wi-Fi e BLE sob demanda e cadastra todos os rádios
  Meshtastic verificados que ainda não estão configurados.

Nenhuma etapa transmite RF. Uma conexão só é cadastrada depois que o
handshake Meshtastic confirma o rádio (nome e Node ID lidos do dispositivo);
portas já usadas por uma conexão cadastrada nunca são abertas.
"""
from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import logging
import threading
import time

from .database import now_ms

LOG = logging.getLogger(__name__)

# Serviço GATT Meshtastic: identifica o rádio sem depender do nome anunciado.
MESHTASTIC_BLE_SERVICE = "6ba1b218-15a8-461f-9fa8-5dcae273eafd"
# Sinal mínimo para o aviso em segundo plano: rádios de vizinhos ao alcance
# do Bluetooth não devem gerar avisos; o rádio do usuário fica perto do PC.
BLE_NEAR_RSSI = -70
PROBE_TIMEOUT_S = 20
USB_POLL_S = 3
BLE_POLL_S = 45


def device_key(kind, address):
    return str(kind) + ":" + str(address).strip().lower()


def usb_serial_ports():
    """Portas seriais com VID USB: placas Meshtastic são sempre USB.

    Portas sem VID (COM1 da placa-mãe, "serial sobre Bluetooth" do Windows)
    ficam de fora: abri-las pode travar ou não é um rádio.
    """
    from serial.tools import list_ports
    result = []
    for port in list_ports.comports():
        device = str(getattr(port, "device", "") or "")
        if not device or getattr(port, "vid", None) is None:
            continue
        result.append({"kind": "serial", "address": device,
                       "name": str(getattr(port, "description", "") or device)[:90],
                       "config": {"port": device}})
    return result


def scan_ble(timeout=5.0, near_only=False):
    async def run():
        from bleak import BleakScanner
        found = await BleakScanner.discover(timeout=timeout, return_adv=True)
        items = []
        for device, adv in found.values():
            uuids = {str(u).lower() for u in (getattr(adv, "service_uuids", None) or [])}
            name = str(getattr(adv, "local_name", None) or device.name or "")
            if MESHTASTIC_BLE_SERVICE not in uuids and "meshtastic" not in name.casefold():
                continue
            rssi = getattr(adv, "rssi", None)
            if near_only and (rssi is None or rssi < BLE_NEAR_RSSI):
                continue
            items.append({"kind": "ble", "address": str(device.address),
                          "name": (name or "Bluetooth LE")[:90], "rssi": rssi,
                          "config": {"address": str(device.address)}})
        return items
    return asyncio.run(run())


def scan_mdns(seconds=4.0):
    from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
    results = []

    class Listener(ServiceListener):
        def add_service(self, zc, type_, name):
            results.extend(_mdns_items(zc, type_, name))

        def update_service(self, *args):
            pass

        def remove_service(self, *args):
            pass

    zc = Zeroconf()
    try:
        browser = ServiceBrowser(zc, ["_meshtastic._tcp.local."], Listener())
        time.sleep(seconds)
        browser.cancel()
    finally:
        zc.close()
    return results


def _mdns_items(zc, type_, name):
    items = []
    try:
        info = zc.get_service_info(type_, name, timeout=1500)
    except Exception:
        return items
    for raw in (info.addresses if info else []):
        if len(raw) != 4:
            continue
        host = str(ipaddress.IPv4Address(raw))
        if not ipaddress.ip_address(host).is_private:
            continue
        items.append({"kind": "tcp", "address": host,
                      "name": name.split("._meshtastic")[0][:90] or host,
                      "config": {"host": host, "port": info.port or 4403}})
    return items


def open_interface(candidate, timeout=PROBE_TIMEOUT_S):
    kind, conf = candidate["kind"], candidate["config"]
    if kind == "serial":
        from meshtastic.serial_interface import SerialInterface
        return SerialInterface(devPath=conf["port"], timeout=timeout)
    if kind == "tcp":
        from meshtastic.tcp_interface import TCPInterface
        return TCPInterface(hostname=conf["host"], portNumber=int(conf.get("port") or 4403), timeout=timeout)
    if kind == "ble":
        from meshtastic.ble_interface import BLEInterface
        return BLEInterface(address=conf["address"], timeout=timeout)
    raise ValueError("Tipo de conexão desconhecido")


def probe(candidate, opener=open_interface):
    """Handshake Meshtastic: confirma o rádio e lê nome e Node ID, sem TX RF."""
    iface = None
    try:
        iface = opener(candidate)
        info = iface.getMyNodeInfo() if callable(getattr(iface, "getMyNodeInfo", None)) else None
        info = info if isinstance(info, dict) else {}
        user = info.get("user") if isinstance(info.get("user"), dict) else {}
        num = info.get("num") or getattr(getattr(iface, "localNode", None), "nodeNum", None)
        if not num:
            return {"ok": False, "error": "Sem resposta do protocolo Meshtastic"}
        return {"ok": True, "node_num": int(num),
                "long_name": str(user.get("longName") or "").strip()[:72],
                "short_name": str(user.get("shortName") or "").strip()[:8]}
    except Exception as exc:
        text = str(exc) or type(exc).__name__
        return {"ok": False, "error": text[:160]}
    finally:
        if iface is not None:
            try:
                iface.close()
            except Exception:
                pass


class Registry:
    """Conexões já cadastradas, para não oferecer nem duplicar o mesmo rádio."""

    def __init__(self, db, sources):
        self.db = db
        self.sources = sources

    def snapshot(self):
        keys, nodes = set(), set()
        for src in self.db.sources(public=False):
            conf = src["config"]
            if src["kind"] == "serial" and conf.get("port"):
                keys.add(device_key("serial", conf["port"]))
            elif src["kind"] == "tcp" and conf.get("host"):
                keys.add(device_key("tcp", conf["host"]))
            elif src["kind"] == "ble" and conf.get("address"):
                keys.add(device_key("ble", conf["address"]))
            if conf.get("node_num"):
                nodes.add(int(conf["node_num"]))
        for state in self.sources.snapshot().values():
            if state.get("local_node_num"):
                nodes.add(int(state["local_node_num"]))
        return keys, nodes

    def configured(self, candidate):
        keys, _ = self.snapshot()
        return device_key(candidate["kind"], candidate["address"]) in keys

    def add(self, candidate, info):
        """Cadastra com o nome lido do rádio e conexão automática marcada."""
        _, nodes = self.snapshot()
        if self.configured(candidate) or info["node_num"] in nodes:
            raise LookupError("Rádio já configurado")
        config = dict(candidate["config"])
        config["node_num"] = info["node_num"]
        kinds = {"serial": "USB", "tcp": "Wi-Fi", "ble": "BLE"}
        name = info.get("long_name") or info.get("short_name") or candidate["name"]
        name = (name + " " + kinds[candidate["kind"]])[:72]
        source = self.db.upsert_source({"name": name, "kind": candidate["kind"],
                                        "config": config, "enabled": True})
        self.sources.connect(source["id"])
        return source


class DeviceWatcher:
    """#149: avisa quando um rádio novo aparece (USB plugado, mDNS ou BLE próximo)."""

    def __init__(self, db, sources, prober=probe, usb=usb_serial_ports, ble=scan_ble):
        self.db = db
        self.sources = sources
        self.registry = Registry(db, sources)
        self._probe = prober
        self._usb = usb
        self._ble = ble
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._notices = {}
        self._snoozed = set()
        self._busy = set()
        self._usb_seen = None
        self._thread = None
        self._zc = None

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, name="device-watcher", daemon=True)
            self._thread.start()

    def close(self):
        self._stop.set()
        if self._zc is not None:
            try:
                self._zc.close()
            except Exception:
                pass

    def busy(self, key, value=True):
        with self._lock:
            (self._busy.add if value else self._busy.discard)(key)

    def wait_idle(self, key, seconds=PROBE_TIMEOUT_S + 5):
        """Aguarda o monitor terminar de verificar a mesma porta (uma porta, um dono)."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            with self._lock:
                if key not in self._busy:
                    return True
            time.sleep(0.2)
        return False

    def notices(self):
        with self._lock:
            return [dict(n) for n in self._notices.values()]

    def _enabled(self, kind):
        return self.db.system_settings()["device_autodetect"].get(kind, True)

    def _offer(self, candidate, info=None):
        key = device_key(candidate["kind"], candidate["address"])
        with self._lock:
            if key in self._notices or key in self._snoozed or key in self._busy:
                return
        if key in self.db.ignored_devices() or self.registry.configured(candidate):
            return
        if info is not None:
            _, nodes = self.registry.snapshot()
            if info["node_num"] in nodes:
                return
        notice = {"id": hashlib.blake2s(key.encode(), digest_size=6).hexdigest(), "key": key,
                  "kind": candidate["kind"], "address": candidate["address"],
                  "name": (info or {}).get("long_name") or candidate["name"],
                  "verified": info is not None, "detected_ms": now_ms(),
                  "candidate": candidate}
        with self._lock:
            self._notices[key] = notice

    def _drop_missing(self, kind, present):
        with self._lock:
            for key in [k for k, n in self._notices.items() if n["kind"] == kind and k not in present]:
                self._notices.pop(key, None)
            # "Agora não" vale até o dispositivo sair e voltar.
            self._snoozed = {k for k in self._snoozed if not k.startswith(kind + ":") or k in present}

    def _check_usb(self):
        ports = {device_key("serial", p["address"]): p for p in self._usb()}
        previous, self._usb_seen = self._usb_seen, set(ports)
        self._drop_missing("serial", set(ports))
        if previous is None or not self._enabled("serial"):
            return  # Primeira leitura é a linha de base: aviso só ao plugar.
        for key in set(ports) - previous:
            candidate = ports[key]
            if self.registry.configured(candidate):
                continue
            # Placas ESP32 reiniciam ao abrir a porta; aguarda o boot.
            if self._stop.wait(2):
                return
            self.busy(key)
            try:
                info = self._probe(candidate)
            finally:
                self.busy(key, False)
            if info.get("ok"):
                self._offer(candidate, info)

    def _check_ble(self):
        if not self._enabled("ble"):
            return
        snapshot = self.sources.snapshot()
        for src in self.db.sources(public=False):
            # Varredura BLE durante conexão BLE ativa pode derrubá-la no Windows.
            if src["kind"] == "ble" and snapshot.get(str(src["id"]), {}).get("status") in ("connecting", "connected"):
                return
        try:
            found = self._ble(timeout=4.0, near_only=True)
        except Exception as exc:
            LOG.debug("Varredura BLE indisponível: %s", exc)
            return
        self._drop_missing("ble", {device_key("ble", d["address"]) for d in found})
        for candidate in found:
            self._offer(candidate)

    def _start_mdns(self):
        try:
            from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
        except ImportError:
            return
        watcher = self

        class Listener(ServiceListener):
            def add_service(self, zc, type_, name):
                if watcher._enabled("tcp"):
                    for item in _mdns_items(zc, type_, name):
                        watcher._offer(item)

            def update_service(self, *args):
                pass

            def remove_service(self, *args):
                pass

        try:
            self._zc = Zeroconf()
            ServiceBrowser(self._zc, ["_meshtastic._tcp.local."], Listener())
        except Exception as exc:
            LOG.debug("mDNS indisponível: %s", exc)

    def _loop(self):
        self._start_mdns()
        next_ble = time.monotonic() + 10
        while not self._stop.is_set():
            try:
                self._check_usb()
            except Exception as exc:
                LOG.debug("Enumeração USB falhou: %s", exc)
            if time.monotonic() >= next_ble:
                self._check_ble()
                next_ble = time.monotonic() + BLE_POLL_S
            self._stop.wait(USB_POLL_S)

    def dismiss(self, notice_id, never=False):
        with self._lock:
            key = next((k for k, n in self._notices.items() if n["id"] == notice_id), None)
            if key is None:
                raise LookupError("Aviso não encontrado")
            self._notices.pop(key)
            if not never:
                self._snoozed.add(key)
        if never:
            self.db.ignore_device(key)
        return {"success": True}

    def accept(self, notice_id):
        """Um clique: verifica, cadastra com conexão automática e conecta."""
        with self._lock:
            notice = next((n for n in self._notices.values() if n["id"] == notice_id), None)
            if notice is None:
                raise LookupError("Aviso não encontrado ou já tratado")
            self._busy.add(notice["key"])
        try:
            info = self._probe(notice["candidate"])
            if not info.get("ok"):
                raise RuntimeError("Não é um rádio Meshtastic ou não respondeu: " + info["error"])
            try:
                source = self.registry.add(notice["candidate"], info)
            except LookupError:
                with self._lock:
                    self._notices.pop(notice["key"], None)
                raise
            with self._lock:
                self._notices.pop(notice["key"], None)
            active = self.sources.active_radio()
            return {"success": True, "source": source,
                    "other_active": active is not None and active != source["id"]}
        finally:
            self.busy(notice["key"], False)


class AutoAdd:
    """#151: varre USB, Wi-Fi e BLE e cadastra todos os rádios novos verificados."""

    def __init__(self, db, sources, watcher=None, prober=probe, usb=usb_serial_ports,
                 ble=scan_ble, mdns=scan_mdns):
        self.db = db
        self.registry = Registry(db, sources)
        self.watcher = watcher
        self._probe = prober
        self._usb = usb
        self._ble = ble
        self._mdns = mdns
        self._lock = threading.RLock()
        self._state = {"running": False, "phase": "idle", "results": [], "finished_ms": 0}

    def status(self):
        with self._lock:
            return {**self._state, "results": [dict(r) for r in self._state["results"]]}

    def start(self):
        with self._lock:
            if self._state["running"]:
                return self.status()
            self._state = {"running": True, "phase": "Procurando em USB, Wi-Fi e Bluetooth…",
                           "results": [], "finished_ms": 0}
        threading.Thread(target=self.run, name="auto-add-radios", daemon=True).start()
        return self.status()

    def _result(self, candidate, outcome, detail=""):
        with self._lock:
            self._state["results"].append({"kind": candidate["kind"], "address": candidate["address"],
                                           "name": candidate["name"], "outcome": outcome,
                                           "detail": detail})

    def run(self):
        with self._lock:
            self._state = {"running": True, "phase": "Procurando em USB, Wi-Fi e Bluetooth…",
                           "results": [], "finished_ms": 0}
        candidates, errors = [], []
        scans = (("USB", lambda: self._usb()), ("Wi-Fi", lambda: self._mdns(4.0)),
                 ("Bluetooth", lambda: self._ble(timeout=5.0, near_only=True)))
        for label, scan in scans:
            try:
                candidates.extend(scan())
            except Exception as exc:
                errors.append(label + ": " + (str(exc) or type(exc).__name__)[:80])
        unique = {}
        for c in candidates:
            unique.setdefault(device_key(c["kind"], c["address"]), c)
        pending = []
        for key, c in unique.items():
            if self.registry.configured(c):
                self._result(c, "configured", "Já configurado")
            else:
                pending.append((key, c))
        with self._lock:
            self._state["phase"] = "Verificando " + str(len(pending)) + " dispositivo(s)…"
        for key, c in pending:
            if self.watcher:
                self.watcher.wait_idle(key)
                if self.registry.configured(c):
                    self._result(c, "configured", "Adicionado pelo aviso de rádio detectado")
                    continue
                self.watcher.busy(key)
            try:
                info = self._probe(c)
                if not info.get("ok"):
                    self._result(c, "no_response", info.get("error", ""))
                    continue
                try:
                    source = self.registry.add(c, info)
                    self._result(c, "added", source["name"])
                except LookupError:
                    self._result(c, "configured", "Mesmo rádio já cadastrado por outra conexão")
            except Exception as exc:
                self._result(c, "error", str(exc)[:160])
            finally:
                if self.watcher:
                    self.watcher.busy(key, False)
        with self._lock:
            self._state.update(running=False, phase="done", errors=errors, finished_ms=now_ms())
