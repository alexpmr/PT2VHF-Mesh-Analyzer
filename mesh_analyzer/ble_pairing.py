"""Pareamento Bluetooth LE com PIN digitado no aplicativo (#164).

Rádios Meshtastic com segurança BLE pedem um PIN de 6 dígitos (mostrado na
tela do rádio; 123456 nos modelos sem tela). Sem isso a conexão BLE fica
esperando o diálogo do sistema, às vezes escondido atrás da janela do app.

- Windows: pareamento personalizado do WinRT (DeviceInformationCustomPairing),
  respondendo ao pedido de PIN com o código informado no app.
- Linux: bluetoothctl com agente de teclado, enviando o PIN quando pedido.
- macOS: o próprio sistema mostra o diálogo de pareamento ao conectar.

Rádios sem PIN definido (modo "NO_PIN") pareiam sem código: `pair(endereço)`
sem PIN pareia direto e devolve status "pin_required" quando o rádio pede um.
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


PIN_REQUIRED = {"ok": False, "status": "pin_required",
                "error": "Este rádio pede PIN: digite o código mostrado na tela dele (123456 se ele não tiver tela)."}


def pair(address: str, pin: str | None = None, timeout: float = 40.0, platform: str | None = None) -> dict:
    """Pareia o endereço; sem PIN, pareia rádios que não exigem código.
    Devolve {"ok", "status", "error"}; status "pin_required" quando o rádio pede PIN."""
    if pin is None:
        address = str(address or "").strip()
    else:
        address, pin = validate(address, pin)
    platform = platform or sys.platform
    try:
        if platform == "win32":
            return asyncio.run(asyncio.wait_for(_pair_windows(address, pin), timeout))
        if platform.startswith("linux"):
            return _pair_linux(address, pin, timeout)
        return {"ok": True, "status": "system_dialog",
                "error": "" if pin is None else "No macOS o próprio sistema pede o PIN ao conectar; digite-o no diálogo do macOS."}
    except asyncio.TimeoutError:
        return {"ok": False, "status": "timeout", "error": "O rádio não respondeu ao pareamento a tempo"}
    except Exception as exc:
        return {"ok": False, "status": "error", "error": (str(exc) or type(exc).__name__)[:200]}


async def _pair_windows(address: str, pin: str) -> dict:
    from winrt.windows.devices.bluetooth import BluetoothLEDevice
    if not ADDRESS_RE.fullmatch(address):
        raise ValueError("Endereço Bluetooth inválido")
    device = await BluetoothLEDevice.from_bluetooth_address_async(int(address.replace(":", ""), 16))
    if device is None:
        raise RuntimeError("Rádio Bluetooth não encontrado; aproxime-o do computador")
    try:
        return await _pair_device(device, pin)
    finally:
        # #191: solta o rádio na hora; o objeto aberto atrapalhava a conexão logo em seguida.
        try:
            device.close()
        except Exception:
            pass


async def _pair_device(device, pin):
    from winrt.windows.devices.enumeration import DevicePairingKinds, DevicePairingResultStatus
    info = device.device_information
    if info.pairing.is_paired:
        return {"ok": True, "status": "already_paired", "error": ""}
    custom = info.pairing.custom
    asked_pin = []

    def on_request(sender, args):
        if args.pairing_kind == DevicePairingKinds.PROVIDE_PIN:
            if pin is None:
                asked_pin.append(True)   # sem resposta: o Windows cancela e o app pede o PIN
                return
            args.accept_with_pin(pin)
        else:
            args.accept()                # "Just Works" / confirmação: rádio sem PIN definido

    token = custom.add_pairing_requested(on_request)
    try:
        kinds = DevicePairingKinds.PROVIDE_PIN | DevicePairingKinds.CONFIRM_ONLY | DevicePairingKinds.CONFIRM_PIN_MATCH
        result = await custom.pair_async(kinds)
    finally:
        custom.remove_pairing_requested(token)
    if result.status in (DevicePairingResultStatus.PAIRED, DevicePairingResultStatus.ALREADY_PAIRED):
        return {"ok": True, "status": "paired", "error": ""}
    if asked_pin:
        return dict(PIN_REQUIRED)
    return {"ok": False, "status": "failed",
            "error": "Pareamento recusado (%s). Confira o PIN na tela do rádio." % getattr(result.status, "name", result.status)}


def is_paired(address: str, platform: str | None = None) -> bool | None:
    """#191: o sistema já tem este rádio pareado? None quando não dá para saber."""
    platform = platform or sys.platform
    try:
        if not ADDRESS_RE.fullmatch(str(address or "")):
            return None
        if platform == "win32":
            return asyncio.run(asyncio.wait_for(_windows_paired(address), 15))
        if platform.startswith("linux"):
            out = subprocess.run(["bluetoothctl", "info", address], capture_output=True, text=True, timeout=10).stdout
            return bool(re.search(r"Paired:\s*yes", out))
    except Exception:
        return None
    return None


def unpair(address: str, platform: str | None = None) -> bool:
    """#191: remove o pareamento do sistema (o rádio continua cadastrado no app)."""
    platform = platform or sys.platform
    try:
        if not ADDRESS_RE.fullmatch(str(address or "")):
            return False
        if platform == "win32":
            return asyncio.run(asyncio.wait_for(_windows_unpair(address), 20))
        if platform.startswith("linux"):
            out = subprocess.run(["bluetoothctl", "remove", address], capture_output=True, text=True, timeout=15).stdout
            return bool(re.search(r"Device has been removed|not available", out))
    except Exception:
        return False
    return False


def adapter_info(platform: str | None = None) -> dict | None:
    """#191: adaptador Bluetooth do computador (nome, suporte a BLE e ao papel central)."""
    platform = platform or sys.platform
    try:
        if platform == "win32":
            return asyncio.run(asyncio.wait_for(_windows_adapter(), 10))
        if platform.startswith("linux"):
            out = subprocess.run(["bluetoothctl", "show"], capture_output=True, text=True, timeout=8).stdout
            name = re.search(r"Name:\s*(.+)", out)
            return {"present": bool(out.strip()), "name": name.group(1).strip() if name else "",
                    "powered": bool(re.search(r"Powered:\s*yes", out))}
    except Exception as exc:
        return {"present": None, "error": (str(exc) or type(exc).__name__)[:120]}
    return None


async def _windows_adapter():
    from winrt.windows.devices.bluetooth import BluetoothAdapter
    adapter = await BluetoothAdapter.get_default_async()
    if adapter is None:
        return {"present": False}
    info = {"present": True, "le": bool(adapter.is_low_energy_supported),
            "central": bool(adapter.is_central_role_supported)}
    try:
        from winrt.windows.devices.enumeration import DeviceInformation
        device = await DeviceInformation.create_from_id_async(adapter.device_id)
        info["name"] = str(device.name or "")
    except Exception:
        info["name"] = ""
    return info


async def _windows_device(address):
    from winrt.windows.devices.bluetooth import BluetoothLEDevice
    return await BluetoothLEDevice.from_bluetooth_address_async(int(address.replace(":", ""), 16))


async def _windows_paired(address):
    device = await _windows_device(address)
    if device is None:
        return None
    try:
        return bool(device.device_information.pairing.is_paired)
    finally:
        device.close()


async def _windows_unpair(address):
    from winrt.windows.devices.enumeration import DeviceUnpairingResultStatus
    device = await _windows_device(address)
    if device is None:
        return False
    try:
        result = await device.device_information.pairing.unpair_async()
        return result.status in (DeviceUnpairingResultStatus.UNPAIRED, DeviceUnpairingResultStatus.ALREADY_UNPAIRED)
    finally:
        device.close()


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
        for cmd in ("agent KeyboardDisplay", "default-agent", "pair " + address):
            send(cmd)
            time.sleep(0.3)
        sent_pin, sent, end = False, [], time.monotonic() + timeout
        while time.monotonic() < end and not done.is_set():
            text = "".join(lines)
            if not sent_pin and re.search(r"(Enter passkey|Enter PIN|Passkey)", text, re.I):
                if pin is None:
                    send("no")
                    return dict(PIN_REQUIRED)
                send(pin)
                sent_pin = True
            if re.search(r"Confirm passkey|Request confirmation|Authorize service", text, re.I) and "yes" not in sent:
                send("yes")          # rádio sem PIN: só confirmação
                sent.append("yes")
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
