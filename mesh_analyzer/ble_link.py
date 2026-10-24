"""#191: conexão Bluetooth com rádios Meshtastic mais tolerante (sobretudo no Windows).

A `BLEInterface` da biblioteca Meshtastic procura o rádio duas vezes (ela mesma e o
bleak, porque conecta pelo endereço em texto), dá 10 s para abrir a sessão GATT e
ler os serviços, não tenta de novo e ainda faz uma varredura de 5 s logo depois de
conectar. Rádios que conectam bem no celular falhavam no Windows com
`TimeoutError` ou "Could not get GATT services: Unreachable".

Aqui a conexão: procura o rádio uma vez e conecta pelo dispositivo encontrado,
com prazo maior; tenta de novo sem o cache de serviços do Windows; confirma que
dá para ler os dados (o que revela rádio que exige pareamento) e devolve o erro
com a etapa em português. Enquanto isso, as varreduras Bluetooth do app esperam.

v0.6.53: no Windows, abre antes uma sessão GATT com MaintainConnection e espera ela
ficar ativa, como o Chrome (Web Bluetooth) faz. O bleak pede os serviços antes de
existir ligação; com alguns adaptadores/drivers (ex.: Realtek 4.2 USB) o Windows
responde "Unreachable" em ~12 ms, enquanto o cliente web conectava no mesmo PC.
"""
from __future__ import annotations

import asyncio
import logging
import sys
import threading
import time
from contextlib import contextmanager

FIND_TIMEOUT_S = 10.0
CONNECT_TIMEOUT_S = 20.0
SESSION_TIMEOUT_S = 20.0
ATTEMPTS = 2
RETRY_PAUSE_S = 2.0
STAGES = {"find": "procurar o rádio", "connect": "abrir a conexão",
          "access": "ler os dados do rádio"}
AUTH_HINTS = ("insufficient authentication", "insufficient encryption", "access denied",
              "authentication", "not paired", "0x05", "0x0f")

_lock = threading.Lock()
_active = 0


@contextmanager
def activity():
    """Marca uma conexão Bluetooth em andamento (as varreduras do app esperam)."""
    global _active
    with _lock:
        _active += 1
    try:
        yield
    finally:
        with _lock:
            _active -= 1


def busy():
    with _lock:
        return _active > 0


def needs_pairing(exc):
    return any(h in (str(exc) or "").lower() for h in AUTH_HINTS)


def describe(exc):
    """Erro do bleak/WinRT em português curto."""
    text = str(exc) or type(exc).__name__
    low = text.lower()
    if isinstance(exc, TimeoutError) or low in ("timeouterror", "timeout"):
        return "tempo esgotado"
    if "unreachable" in low:
        return "o Windows não alcançou o rádio (Unreachable)"
    if needs_pairing(exc):
        return "o rádio exige pareamento"
    if "not found" in low or "não encontrado" in low:
        return "rádio não encontrado"
    return text[:120]


class LinkError(Exception):
    """Falha de conexão com a etapa, o motivo e se o rádio pede pareamento."""

    def __init__(self, failures, elapsed=None, session_note=""):
        self.failures = failures
        self.elapsed = list(elapsed or [])
        self.session_note = session_note
        stage, exc = failures[-1]
        self.stage = stage
        self.auth = any(needs_pairing(e) for _, e in failures)
        tries = len(failures)
        message = "Bluetooth: falhou ao %s — %s" % (STAGES.get(stage, stage), describe(exc))
        if stage == "connect" and isinstance(exc, TimeoutError):
            message += " (%d s)" % CONNECT_TIMEOUT_S
        if tries > 1:
            message += "; %d tentativas" % tries
        connect = [ms for (st, _), ms in zip(failures, self.elapsed) if st == "connect"]
        if connect and max(connect) < 1500 and not isinstance(exc, TimeoutError):
            # Falha em milissegundos: o Windows recusou sem tentar falar com o rádio (#191).
            message += " — recusado pelo Windows em %d ms, sem chegar a falar com o rádio" % max(connect)
        if session_note:
            message += "; " + session_note
        super().__init__(message)


class _Session:
    """Sessão GATT do Windows mantida aberta enquanto o bleak conecta."""

    def __init__(self, device, session):
        self.device, self.session = device, session

    def close(self):
        for obj in (self.session, self.device):
            try:
                obj.close()
            except Exception:
                pass


async def _windows_session(address, timeout):
    from winrt.windows.devices.bluetooth import BluetoothLEDevice
    from winrt.windows.devices.bluetooth.genericattributeprofile import GattSession, GattSessionStatus
    device = await BluetoothLEDevice.from_bluetooth_address_async(int(address.replace(":", ""), 16))
    if device is None:
        return None, False
    session = await GattSession.from_device_id_async(device.bluetooth_device_id)
    loop, active = asyncio.get_running_loop(), asyncio.Event()

    def changed(sender, args):
        if args.status == GattSessionStatus.ACTIVE:
            loop.call_soon_threadsafe(active.set)
    token = session.add_session_status_changed(changed)
    try:
        session.maintain_connection = True   # é isto que faz o Windows abrir a ligação
        if session.session_status == GattSessionStatus.ACTIVE:
            active.set()
        try:
            await asyncio.wait_for(active.wait(), timeout)
            ok = True
        except asyncio.TimeoutError:
            ok = False
    finally:
        session.remove_session_status_changed(token)
    return _Session(device, session), ok


def windows_prewarm(address, helper, timeout=SESSION_TIMEOUT_S):
    """Abre a sessão GATT e espera ela ficar ativa. Devolve (sessão, ativa?)."""
    return helper.async_await(_windows_session(address, timeout))


def connect_client(address, on_disconnect, attempts=ATTEMPTS, sleep=time.sleep, bleak=None, prewarm=None):
    """Procura e conecta o rádio; devolve o BLEClient pronto ou levanta LinkError."""
    from meshtastic.ble_interface import BLEClient, FROMRADIO_UUID
    if bleak is None:
        from bleak import BleakScanner
    else:
        BleakScanner = bleak
    if prewarm is None and sys.platform == "win32":
        prewarm = windows_prewarm
    elif prewarm is False:      # desligado explicitamente (testes)
        prewarm = None
    failures, elapsed, note = [], [], ""
    log = logging.getLogger(__name__)
    for attempt in range(attempts):
        client, stage, started, held = None, "find", time.monotonic(), None
        try:
            with BLEClient() as finder:
                device = finder.async_await(BleakScanner.find_device_by_address(address, timeout=FIND_TIMEOUT_S))
                if device is None:
                    raise LookupError("not found")
                if prewarm is not None:
                    began = time.monotonic()
                    try:
                        held, active = prewarm(address, finder)
                    except Exception as exc:
                        held, active = None, False
                        log.info("BLE %s: sessão do Windows não pôde ser aberta: %s", address, exc)
                    waited = int((time.monotonic() - began) * 1000)
                    log.info("BLE %s: sessão do Windows %s em %d ms", address, "ativa" if active else "não ativa", waited)
                    note = "" if active else "a sessão Bluetooth do Windows não ficou ativa em %d s" % SESSION_TIMEOUT_S
            stage = "connect"
            options = {"disconnected_callback": on_disconnect, "timeout": CONNECT_TIMEOUT_S}
            if attempt:
                # Segunda tentativa: serviços lidos do rádio, não do cache do Windows.
                options["winrt"] = {"use_cached_services": False}
            client = BLEClient(device, **options)
            started = time.monotonic()
            client.connect()
            stage = "access"
            client.read_gatt_char(FROMRADIO_UUID)
            if held is not None:
                held.close()   # a sessão do bleak já mantém a ligação
            return client
        except Exception as exc:
            if held is not None:
                held.close()
                held = None
            failures.append((stage, exc))
            elapsed.append(int((time.monotonic() - started) * 1000))
            log.info("BLE %s: tentativa %d falhou em %s após %d ms: %s", address, attempt + 1, stage,
                     elapsed[-1], str(exc) or type(exc).__name__)
            if client is not None:
                try:
                    client.disconnect()
                except Exception:
                    pass
                try:
                    client.close()
                except Exception:
                    pass
            if needs_pairing(exc) or attempt + 1 >= attempts:
                break
            sleep(RETRY_PAUSE_S)
    raise LinkError(failures, elapsed, note)


def meshtastic_interface(address, timeout=20):
    """`BLEInterface` com a conexão acima no lugar da original."""
    from meshtastic.ble_interface import BLEInterface

    class MeshtasticBLE(BLEInterface):
        def connect(self, address=None):
            self._link_ready = False

            def lost(_client):
                # Só derruba a interface depois de pronta (não nas tentativas que falharam).
                if self._link_ready:
                    self.close()
            try:
                client = connect_client(address, lost)
            except LinkError as exc:
                error = BLEInterface.BLEError(str(exc), "LINK")
                error.auth = exc.auth
                raise error from exc
            self._link_ready = True
            return client

    with activity():
        return MeshtasticBLE(address=address, timeout=timeout)
