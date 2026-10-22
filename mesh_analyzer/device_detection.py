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
# #156: prazo total da verificação, incluindo pareamento BLE; ao estourar, a
# tentativa é abandonada com segurança em vez de prender a interface.
PROBE_DEADLINE_S = {"serial": 30, "tcp": 30, "ble": 45}
TIMEOUT_HINT = {
    "serial": "O rádio não respondeu a tempo pela USB. Confira se outro programa está usando a porta.",
    "tcp": "O rádio não respondeu a tempo pelo Wi-Fi. Confira se ele está ligado e na mesma rede.",
    "ble": "O rádio não respondeu a tempo pelo Bluetooth. Se ele pedir PIN, confira a janela de "
           "pareamento do Windows (PIN na tela do rádio; 123456 se ele não tiver tela).",
}
# #162: na primeira abertura a busca não pode segurar o usuário por muito tempo.
FIRST_RUN_DEADLINE_S = {"serial": 20, "tcp": 20, "ble": 25}
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


def bounded_probe(prober, candidate, cancel=None, deadline=None):
    """Executa a verificação com prazo rígido e cancelamento (#156).

    A thread da verificação continua sozinha se o SDK travar; `probe()` fecha a
    interface quando ela retornar, e o resultado tardio é descartado.
    """
    kind = candidate["kind"]
    deadline = deadline or PROBE_DEADLINE_S.get(kind, 30)
    box, done = {}, threading.Event()

    def run():
        try:
            box["result"] = prober(candidate)
        except Exception as exc:
            box["result"] = {"ok": False, "error": (str(exc) or type(exc).__name__)[:160]}
        finally:
            done.set()

    threading.Thread(target=run, name="probe-" + kind, daemon=True).start()
    end = time.monotonic() + deadline
    while not done.wait(0.2):
        if cancel is not None and cancel.is_set():
            return {"ok": False, "cancelled": True, "error": "Cancelado pelo usuário"}
        if time.monotonic() >= end:
            return {"ok": False, "timed_out": True, "error": TIMEOUT_HINT.get(kind, "Tempo esgotado")}
    return box["result"]


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

    def source_for(self, candidate):
        key = device_key(candidate["kind"], candidate["address"])
        for src in self.db.sources(public=False):
            conf = src["config"]
            address = conf.get("port") or conf.get("host") or conf.get("address")
            if src["kind"] == candidate["kind"] and address and device_key(src["kind"], address) == key:
                return src
        return None

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
    """#149/#155/#156: rádios novos (USB plugado, mDNS, BLE próximo).

    USB verificado pode ser adicionado e conectado sem clique, com prioridade
    sobre Wi-Fi/BLE; os demais geram aviso com verificação em segundo plano,
    prazo, fila Bluetooth e Cancelar.
    """

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
        self._ble_line = []
        self._deferred = []
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

    def wait_idle(self, key, seconds=max(PROBE_DEADLINE_S.values()) + 5):
        """Aguarda o monitor terminar de verificar a mesma porta (uma porta, um dono)."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            with self._lock:
                if key not in self._busy:
                    return True
            time.sleep(0.2)
        return False

    # Fila Bluetooth: o adaptador do Windows não aguenta conexões simultâneas.
    def enter_ble(self, token, cancel=None, on_wait=None):
        with self._lock:
            if token not in self._ble_line:
                self._ble_line.append(token)
        while True:
            with self._lock:
                position = self._ble_line.index(token) + 1
            if position == 1:
                return True
            if on_wait:
                on_wait(position, len(self._ble_line))
            if (cancel is not None and cancel.is_set()) or self._stop.wait(0.2):
                self.leave_ble(token)
                return False

    def leave_ble(self, token):
        with self._lock:
            if token in self._ble_line:
                self._ble_line.remove(token)

    def verify(self, candidate, token, cancel=None, on_wait=None, deadline=None):
        """Verificação com prazo, cancelamento e fila Bluetooth."""
        ble = candidate["kind"] == "ble"
        if ble and not self.enter_ble(token, cancel, on_wait):
            return {"ok": False, "cancelled": True, "error": "Cancelado pelo usuário"}
        try:
            return bounded_probe(self._probe, candidate, cancel, deadline)
        finally:
            if ble:
                self.leave_ble(token)

    def notices(self):
        with self._lock:
            result = []
            for n in self._notices.values():
                item = {k: v for k, v in n.items() if k not in ("cancel",)}
                if isinstance(n.get("job"), dict):
                    item["job"] = dict(n["job"])
                result.append(item)
            return result

    def _settings(self):
        return self.db.system_settings()

    def _enabled(self, kind):
        return self._settings()["device_autodetect"].get(kind, True)

    def _new_notice(self, key, candidate, name, **extra):
        notice = {"id": hashlib.blake2s(key.encode(), digest_size=6).hexdigest(), "key": key,
                  "type": "detected", "kind": candidate["kind"], "address": candidate["address"],
                  "name": name, "detected_ms": now_ms(), "candidate": candidate}
        notice.update(extra)
        with self._lock:
            self._notices[key] = notice
        return notice

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
        self._new_notice(key, candidate, (info or {}).get("long_name") or candidate["name"],
                         verified=info is not None)

    def _drop_missing(self, kind, present):
        with self._lock:
            for key in [k for k, n in self._notices.items()
                        if n["kind"] == kind and k not in present and n["type"] == "detected"
                        and not (n.get("job") or {}).get("phase") in ("queued", "pairing", "connecting", "registering")]:
                self._notices.pop(key, None)
            # "Agora não" vale até o dispositivo sair e voltar.
            self._snoozed = {k for k in self._snoozed if not k.startswith(kind + ":") or k in present}

    # --- #155: prioridade USB e adição automática --------------------------------
    def _radio_busy(self):
        try:
            return any(q.get("state") == "awaiting_reply" for q in self.sources.queries.status())
        except Exception:
            return False

    def _prefer_usb(self, source_id):
        """Rádio USB assume no lugar de Wi-Fi/BLE (troca segura de #152)."""
        if not self._settings()["usb_priority"]:
            return False
        active = self.sources.active_radio()
        if active is None or active == source_id:
            return False
        current = self.db.source(active)
        if not current or current["kind"] == "serial":
            return False
        if self._radio_busy():
            with self._lock:
                if source_id not in self._deferred:
                    self._deferred.append(source_id)
            return False
        try:
            self.sources.activate(source_id)
            return True
        except (ValueError, RuntimeError) as exc:
            LOG.warning("Prioridade USB não aplicada: %s", exc)
            return False

    def _run_deferred(self):
        with self._lock:
            pending, self._deferred = self._deferred, []
        for source_id in pending:
            if self.db.source(source_id):
                self._prefer_usb(source_id)

    def _auto_add(self, candidate, info):
        key = device_key(candidate["kind"], candidate["address"])
        if key in self.db.ignored_devices():
            return None
        previous = self.sources.active_radio()
        try:
            source = self.registry.add(candidate, info)
        except LookupError:
            return None
        switched = self._prefer_usb(source["id"])
        self._new_notice(key, candidate, source["name"], type="auto_added",
                         source_id=source["id"], previous_id=previous, switched=switched,
                         waiting=bool(previous) and not switched)
        self.db.log("Rádio adicionado automaticamente: " + source["name"], source_id=source["id"])
        return source

    def _check_usb(self):
        ports = {device_key("serial", p["address"]): p for p in self._usb()}
        previous, self._usb_seen = self._usb_seen, set(ports)
        self._drop_missing("serial", set(ports))
        if previous is None or not self._enabled("serial"):
            return  # Primeira leitura é a linha de base: aviso só ao plugar.
        for key in set(ports) - previous:
            candidate = ports[key]
            configured = self.registry.source_for(candidate)
            if configured:
                if configured["enabled"]:
                    self._prefer_usb(configured["id"])  # rádio já cadastrado replugado
                continue
            # Placas ESP32 reiniciam ao abrir a porta; aguarda o boot.
            if self._stop.wait(2):
                return
            self.busy(key)
            try:
                info = self.verify(candidate, key)
            finally:
                self.busy(key, False)
            if not info.get("ok"):
                continue
            if self._settings()["device_autoconnect"].get("serial"):
                self._auto_add(candidate, info)
            else:
                self._offer(candidate, info)

    def _check_ble(self):
        if not self._enabled("ble"):
            return
        snapshot = self.sources.snapshot()
        for src in self.db.sources(public=False):
            # Varredura BLE durante conexão BLE ativa pode derrubá-la no Windows.
            if src["kind"] == "ble" and snapshot.get(str(src["id"]), {}).get("status") in ("connecting", "connected"):
                return
        with self._lock:
            if self._ble_line:
                return  # verificação BLE em andamento
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
                self._run_deferred()
            except Exception as exc:
                LOG.debug("Enumeração USB falhou: %s", exc)
            if time.monotonic() >= next_ble:
                self._check_ble()
                next_ble = time.monotonic() + BLE_POLL_S
            self._stop.wait(USB_POLL_S)

    def _find(self, notice_id):
        with self._lock:
            for key, n in self._notices.items():
                if n["id"] == notice_id:
                    return key, n
        raise LookupError("Aviso não encontrado ou já tratado")

    def dismiss(self, notice_id, never=False):
        key, notice = self._find(notice_id)
        if (notice.get("job") or {}).get("phase") in ("queued", "pairing", "connecting", "registering"):
            self.cancel(notice_id)
        with self._lock:
            self._notices.pop(key, None)
            if notice["type"] == "detected" and not never and (notice.get("job") or {}).get("phase") != "done":
                self._snoozed.add(key)
        if never:
            self.db.ignore_device(key)
        return {"success": True}

    def cancel(self, notice_id):
        """#156: Cancelar libera o aviso na hora; nada é cadastrado."""
        key, notice = self._find(notice_id)
        with self._lock:
            event = notice.get("cancel")
            job = notice.get("job") or {}
            if job.get("phase") not in ("queued", "pairing", "connecting"):
                raise ValueError("Não há verificação em andamento para cancelar")
            if event:
                event.set()
            notice["job"] = {"phase": "cancelled", "detail": "Verificação cancelada"}
        return {"success": True}

    def accept(self, notice_id, wait=False):
        """Um clique: verifica em segundo plano, cadastra com conexão automática e conecta."""
        key, notice = self._find(notice_id)
        with self._lock:
            if (notice.get("job") or {}).get("phase") in ("queued", "pairing", "connecting", "registering"):
                return {"success": True, "job": dict(notice["job"])}
            cancel = threading.Event()
            notice["cancel"] = cancel
            notice["job"] = {"phase": "connecting", "started_ms": now_ms(), "detail": ""}
            self._busy.add(key)
        worker = threading.Thread(target=self._accept_job, args=(key, notice, cancel),
                                  name="accept-" + notice["kind"], daemon=True)
        worker.start()
        if wait:
            worker.join()
        with self._lock:
            return {"success": True, "job": dict(notice.get("job") or {})}

    def _job(self, notice, cancel, **values):
        with self._lock:
            if cancel.is_set() or notice.get("cancel") is not cancel:
                return False
            notice["job"] = {**(notice.get("job") or {}), **values}
            return True

    def _accept_job(self, key, notice, cancel):
        candidate = notice["candidate"]
        try:
            def waiting(position, total):
                self._job(notice, cancel, phase="queued", position=position, total=total)
            info = self.verify(candidate, "accept:" + key, cancel, waiting)
            if cancel.is_set():
                return
            if not info.get("ok"):
                # #164: rádio BLE que não respondeu pode estar esperando o PIN de pareamento.
                self._job(notice, cancel, phase="failed", error=info.get("error", "Sem resposta"),
                          timed_out=bool(info.get("timed_out")), needs_pin=candidate["kind"] == "ble")
                return
            if not self._job(notice, cancel, phase="registering"):
                return
            try:
                source = self.registry.add(candidate, info)
            except LookupError as exc:
                self._job(notice, cancel, phase="failed", error=str(exc))
                return
            active = self.sources.active_radio()
            switched = candidate["kind"] == "serial" and self._prefer_usb(source["id"])
            self._job(notice, cancel, phase="done", source={"id": source["id"], "name": source["name"]},
                      other_active=active is not None and active != source["id"] and not switched,
                      switched=switched)
        except Exception as exc:
            self._job(notice, cancel, phase="failed", error=(str(exc) or type(exc).__name__)[:160])
        finally:
            self.busy(key, False)

    def pair(self, notice_id, pin, pairer=None):
        """#164: pareia o rádio BLE com o PIN digitado e segue para verificar e conectar."""
        from . import ble_pairing
        key, notice = self._find(notice_id)
        if notice["kind"] != "ble":
            raise ValueError("O PIN só se aplica a rádios Bluetooth")
        ble_pairing.validate(notice["address"], pin)
        with self._lock:
            if (notice.get("job") or {}).get("phase") in ("queued", "pairing", "connecting", "registering"):
                raise ValueError("Já existe uma verificação em andamento para este rádio")
            cancel = threading.Event()
            notice["cancel"] = cancel
            notice["job"] = {"phase": "pairing", "started_ms": now_ms(), "detail": ""}
            self._busy.add(key)

        def work():
            try:
                result = (pairer or ble_pairing.pair)(notice["address"], pin)
                if cancel.is_set():
                    return
                if not result.get("ok"):
                    self._job(notice, cancel, phase="failed", error=result.get("error") or "Pareamento recusado",
                              needs_pin=True)
                    return
                self._job(notice, cancel, phase="connecting", detail=result.get("status", ""))
                self._accept_job(key, notice, cancel)
            finally:
                self.busy(key, False)

        threading.Thread(target=work, name="ble-pair", daemon=True).start()
        with self._lock:
            return {"success": True, "job": dict(notice["job"])}

    def undo(self, notice_id):
        """#155: Desfazer remove a conexão adicionada sozinha e não oferece mais o dispositivo."""
        key, notice = self._find(notice_id)
        source_id = notice.get("source_id") or ((notice.get("job") or {}).get("source") or {}).get("id")
        if not source_id:
            raise ValueError("Nada para desfazer neste aviso")
        self.sources.disconnect(source_id)
        self.db.delete_source(source_id)
        self.db.ignore_device(key)
        previous = notice.get("previous_id")
        if notice.get("switched") and previous and (self.db.source(previous) or {}).get("enabled"):
            try:
                self.sources.activate(previous)
            except (ValueError, RuntimeError):
                pass
        with self._lock:
            self._notices.pop(key, None)
        return {"success": True}


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
        self._cancel = threading.Event()
        self._state = {"running": False, "phase": "idle", "results": [], "finished_ms": 0,
                       "first_run": False, "added": []}

    def status(self):
        with self._lock:
            return {**self._state, "results": [dict(r) for r in self._state["results"]]}

    def start(self, first_run=False):
        with self._lock:
            if self._state["running"]:
                return self.status()
            self._cancel = threading.Event()
            self._state = self._initial(first_run)
        threading.Thread(target=self.run, args=(first_run,), name="auto-add-radios", daemon=True).start()
        return self.status()

    @staticmethod
    def _initial(first_run):
        return {"running": True, "first_run": first_run, "added": [], "results": [], "finished_ms": 0,
                "phase": "Procurando rádios Meshtastic na USB…" if first_run else
                         "Procurando em USB, Wi-Fi e Bluetooth…"}

    def cancel(self):
        self._cancel.set()
        return self.status()

    def _result(self, candidate, outcome, detail=""):
        with self._lock:
            self._state["results"].append({"kind": candidate["kind"], "address": candidate["address"],
                                           "name": candidate["name"], "outcome": outcome,
                                           "detail": detail})

    def _phase(self, text):
        with self._lock:
            self._state["phase"] = text

    def _verify(self, key, candidate, deadline=None):
        if self.watcher:
            return self.watcher.verify(candidate, "auto:" + key, self._cancel, deadline=deadline)
        return bounded_probe(self._probe, candidate, self._cancel, deadline)

    def _added(self, candidate, source, first_run):
        with self._lock:
            self._state["added"].append({"id": source["id"], "name": source["name"], "kind": candidate["kind"]})
        self._result(candidate, "added", source["name"])
        if first_run and self.watcher:
            # Mesmo cartão de "adicionado sozinho" do #155, com Desfazer.
            self.watcher._new_notice(device_key(candidate["kind"], candidate["address"]), candidate,
                                     source["name"], type="auto_added", source_id=source["id"],
                                     previous_id=None, switched=False, waiting=False, first_run=True)

    def _allowed(self, candidate, first_run):
        """Na primeira abertura respeita as preferências por tipo e os dispositivos "Nunca"."""
        if not first_run:
            return True
        key = device_key(candidate["kind"], candidate["address"])
        prefs = self.db.system_settings()["device_autodetect"]
        return prefs.get(candidate["kind"], True) and key not in self.db.ignored_devices()

    def _first_run_usb(self):
        """#162: todas as portas USB verificadas em paralelo; quem responder entra na hora."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        ports = []
        for c in self._usb():
            if not self._allowed(c, True):
                continue
            if self.registry.configured(c):
                self._result(c, "configured", "Já configurado")
            else:
                ports.append(c)
        if not ports:
            return 0
        self._phase("Verificando " + str(len(ports)) + " porta(s) USB…")
        added = 0
        with ThreadPoolExecutor(max_workers=min(8, len(ports))) as pool:
            jobs = {pool.submit(bounded_probe, self._probe, c, self._cancel, FIRST_RUN_DEADLINE_S["serial"]): c
                    for c in ports}
            for job in as_completed(jobs):
                c = jobs[job]
                info = job.result()
                if info.get("cancelled"):
                    self._result(c, "cancelled", "Cancelado")
                elif not info.get("ok"):
                    self._result(c, "no_response", info.get("error", ""))
                else:
                    try:
                        self._added(c, self.registry.add(c, info), True)
                        added += 1
                    except LookupError:
                        self._result(c, "configured", "Mesmo rádio já cadastrado por outra conexão")
        return added

    def run(self, first_run=False):
        with self._lock:
            self._state = self._initial(first_run)
        cancel = self._cancel
        candidates, errors = [], []
        scans = [("USB", lambda: self._usb()), ("Wi-Fi", lambda: self._mdns(4.0)),
                 ("Bluetooth", lambda: self._ble(timeout=5.0, near_only=True))]
        if first_run:
            try:
                if self._first_run_usb() or cancel.is_set():
                    return self._finish(errors)
            except Exception as exc:
                errors.append("USB: " + (str(exc) or type(exc).__name__)[:80])
            self._phase("Nenhum rádio na USB; procurando no Wi-Fi e no Bluetooth próximo…")
            scans = scans[1:]
        for label, scan in scans:
            if cancel.is_set():
                break
            try:
                candidates.extend(scan())
            except Exception as exc:
                errors.append(label + ": " + (str(exc) or type(exc).__name__)[:80])
        unique = {}
        for c in candidates:
            unique.setdefault(device_key(c["kind"], c["address"]), c)
        pending = []
        for key, c in unique.items():
            if not self._allowed(c, first_run):
                continue
            if self.registry.configured(c):
                self._result(c, "configured", "Já configurado")
            else:
                pending.append((key, c))
        for index, (key, c) in enumerate(pending, 1):
            if cancel.is_set():
                self._result(c, "cancelled", "Cancelado antes da verificação")
                continue
            self._phase("Verificando " + str(index) + " de " + str(len(pending)) + ": " + c["name"] + "…")
            if self.watcher:
                self.watcher.wait_idle(key)
                if self.registry.configured(c):
                    self._result(c, "configured", "Adicionado pelo aviso de rádio detectado")
                    continue
                self.watcher.busy(key)
            try:
                info = self._verify(key, c, FIRST_RUN_DEADLINE_S.get(c["kind"]) if first_run else None)
                if info.get("cancelled"):
                    self._result(c, "cancelled", "Cancelado")
                    continue
                if not info.get("ok"):
                    self._result(c, "no_response", info.get("error", ""))
                    continue
                try:
                    self._added(c, self.registry.add(c, info), first_run)
                except LookupError:
                    self._result(c, "configured", "Mesmo rádio já cadastrado por outra conexão")
            except Exception as exc:
                self._result(c, "error", str(exc)[:160])
            finally:
                if self.watcher:
                    self.watcher.busy(key, False)
        self._finish(errors)

    def _finish(self, errors):
        with self._lock:
            self._state.update(running=False, phase="cancelled" if self._cancel.is_set() else "done",
                               errors=errors, finished_ms=now_ms())
