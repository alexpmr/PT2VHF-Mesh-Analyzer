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
"""
from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager

FIND_TIMEOUT_S = 10.0
CONNECT_TIMEOUT_S = 20.0
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

    def __init__(self, failures, elapsed=None):
        self.failures = failures
        self.elapsed = list(elapsed or [])
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
        super().__init__(message)


def connect_client(address, on_disconnect, attempts=ATTEMPTS, sleep=time.sleep, bleak=None):
    """Procura e conecta o rádio; devolve o BLEClient pronto ou levanta LinkError."""
    from meshtastic.ble_interface import BLEClient, FROMRADIO_UUID
    if bleak is None:
        from bleak import BleakScanner
    else:
        BleakScanner = bleak
    failures, elapsed = [], []
    log = logging.getLogger(__name__)
    for attempt in range(attempts):
        client, stage, started = None, "find", time.monotonic()
        try:
            with BLEClient() as finder:
                device = finder.async_await(BleakScanner.find_device_by_address(address, timeout=FIND_TIMEOUT_S))
            if device is None:
                raise LookupError("not found")
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
            return client
        except Exception as exc:
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
    raise LinkError(failures, elapsed)


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
