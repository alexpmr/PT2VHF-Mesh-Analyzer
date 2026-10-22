"""Pareamento Bluetooth LE com PIN digitado no aplicativo (#164).

Rádios Meshtastic com segurança BLE pedem um PIN de 6 dígitos (mostrado na
tela do rádio; 123456 nos modelos sem tela). Sem isso a conexão BLE fica
esperando o diálogo do sistema, às vezes escondido atrás da janela do app.

- Windows: pareamento personalizado do WinRT (DeviceInformationCustomPairing),
  respondendo ao pedido de PIN com o código informado no app.
- Linux: bluetoothctl com agente de teclado, enviando o PIN quando pedido.
- macOS: o próprio sistema mostra o diálogo de pareamento ao conectar.
"""
from __future__ import annotations

import asyncio
import re
import subprocess
import sys
import threading
import time

PIN_RE = re.compile(r"^\d{4,8}$")
ADDRESS_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


def validate(address: str, pin: str) -> tuple[str, str]:
    pin = str(pin or "").strip()
    if not PIN_RE.fullmatch(pin):
        raise ValueError("PIN: 4 a 8 dígitos (o rádio mostra 6 na tela; 123456 se não tiver tela)")
    return str(address or "").strip(), pin


def pair(address: str, pin: str, timeout: float = 40.0, platform: str | None = None) -> dict:
    """Pareia o endereço com o PIN. Devolve {"ok", "status", "error"}."""
    address, pin = validate(address, pin)
    platform = platform or sys.platform
    try:
        if platform == "win32":
            return asyncio.run(asyncio.wait_for(_pair_windows(address, pin), timeout))
        if platform.startswith("linux"):
            return _pair_linux(address, pin, timeout)
        return {"ok": True, "status": "system_dialog",
                "error": "No macOS o próprio sistema pede o PIN ao conectar; digite-o no diálogo do macOS."}
    except asyncio.TimeoutError:
        return {"ok": False, "status": "timeout", "error": "O rádio não respondeu ao pareamento a tempo"}
    except Exception as exc:
        return {"ok": False, "status": "error", "error": (str(exc) or type(exc).__name__)[:200]}


async def _pair_windows(address: str, pin: str) -> dict:
    from winrt.windows.devices.bluetooth import BluetoothLEDevice
    from winrt.windows.devices.enumeration import DevicePairingKinds, DevicePairingResultStatus
    if not ADDRESS_RE.fullmatch(address):
        raise ValueError("Endereço Bluetooth inválido")
    device = await BluetoothLEDevice.from_bluetooth_address_async(int(address.replace(":", ""), 16))
    if device is None:
        raise RuntimeError("Rádio Bluetooth não encontrado; aproxime-o do computador")
    info = device.device_information
    if info.pairing.is_paired:
        return {"ok": True, "status": "already_paired", "error": ""}
    custom = info.pairing.custom

    def on_request(sender, args):
        if args.pairing_kind == DevicePairingKinds.PROVIDE_PIN:
            args.accept_with_pin(pin)
        else:
            args.accept()

    token = custom.add_pairing_requested(on_request)
    try:
        kinds = DevicePairingKinds.PROVIDE_PIN | DevicePairingKinds.CONFIRM_ONLY | DevicePairingKinds.CONFIRM_PIN_MATCH
        result = await custom.pair_async(kinds)
    finally:
        custom.remove_pairing_requested(token)
    if result.status in (DevicePairingResultStatus.PAIRED, DevicePairingResultStatus.ALREADY_PAIRED):
        return {"ok": True, "status": "paired", "error": ""}
    return {"ok": False, "status": "failed",
            "error": "Pareamento recusado (%s). Confira o PIN na tela do rádio." % getattr(result.status, "name", result.status)}


def _pair_linux(address: str, pin: str, timeout: float, command=("bluetoothctl",)) -> dict:
    """Conversa com o bluetoothctl: agente de teclado, pareia e entrega o PIN."""
    if not ADDRESS_RE.fullmatch(address):
        raise ValueError("Endereço Bluetooth inválido")
    proc = subprocess.Popen(list(command), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    lines, done = [], threading.Event()

    def reader():
        for line in proc.stdout:
            lines.append(line)
        done.set()

    threading.Thread(target=reader, daemon=True).start()

    def send(text):
        proc.stdin.write(text + "\n")
        proc.stdin.flush()

    try:
        for cmd in ("agent KeyboardOnly", "default-agent", "pair " + address):
            send(cmd)
            time.sleep(0.3)
        sent_pin, end = False, time.monotonic() + timeout
        while time.monotonic() < end and not done.is_set():
            text = "".join(lines)
            if not sent_pin and re.search(r"(Enter passkey|Enter PIN|Passkey)", text, re.I):
                send(pin)
                sent_pin = True
            if re.search(r"Pairing successful|AlreadyExists|already paired", text, re.I):
                send("trust " + address)
                return {"ok": True, "status": "paired", "error": ""}
            if re.search(r"Failed to pair|AuthenticationFailed|AuthenticationCanceled|not available", text, re.I):
                return {"ok": False, "status": "failed", "error": "Pareamento recusado. Confira o PIN na tela do rádio."}
            time.sleep(0.2)
        return {"ok": False, "status": "timeout", "error": "O rádio não respondeu ao pareamento a tempo"}
    finally:
        try:
            send("quit")
        except Exception:
            pass
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
