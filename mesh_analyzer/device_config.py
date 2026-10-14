"""Local Meshtastic device configuration: guarded LoRa editing and redacted snapshots.

Only a connected native transport may configure its own local node.
A successful writeConfig call is not proof of persistent read-back/ACK.
"""
from __future__ import annotations

import hashlib
import json

SENSITIVE = ("psk", "password", "passphrase", "secret", "private_key", "public_key",
             "token", "pin", "admin_key", "key")
LORA_FIELDS = {
    "region": None, "modem_preset": None, "hop_limit": (1, 7),
    "tx_power": (0, 30), "tx_enabled": None,
    "use_preset": None, "frequency_slot": (0, 104),
}


def redact(value):
    """Remove credentials and keying material from device snapshots."""
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if any(p in str(k).lower() for p in SENSITIVE)
                    else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def _to_dict(message):
    from google.protobuf.json_format import MessageToDict
    return MessageToDict(message, preserving_proto_field_name=True,
                         always_print_fields_with_no_presence=False)


def lora_descriptor_fields(config):
    """Render only protobuf fields known to this connected firmware/library."""
    data = []
    for field in config.DESCRIPTOR.fields:
        name = field.name
        if name not in LORA_FIELDS:
            continue
        if field.type == field.TYPE_MESSAGE or field.label == field.LABEL_REPEATED:
            continue
        current = getattr(config, name)
        row = {"name": name, "label": name.replace("_", " ").title()}
        if field.type == field.TYPE_ENUM:
            options = [v.name for v in field.enum_type.values]
            row.update(type="enum", options=options,
                       value=field.enum_type.values_by_number[int(current)].name)
        elif field.type == field.TYPE_BOOL:
            row.update(type="bool", value=bool(current))
        elif field.type in (field.TYPE_INT32, field.TYPE_UINT32, field.TYPE_INT64,
                            field.TYPE_UINT64):
            row.update(type="int", value=int(current))
            bounds = LORA_FIELDS[name]
            if bounds:
                row.update(min=bounds[0], max=bounds[1])
        else:
            continue
        data.append(row)
    return data


def read_device(local_node, metadata=None):
    if not local_node or getattr(local_node, "localConfig", None) is None:
        raise ValueError("Configuração local não disponível; aguarde sincronização do rádio")
    config = local_node.localConfig
    lora = getattr(config, "lora", None)
    if lora is None:
        raise ValueError("Dispositivo não apresentou configuração LoRa")
    raw = lora.SerializeToString()
    sections = redact(_to_dict(config))
    modules = getattr(local_node, "moduleConfig", None)
    if modules is not None:
        sections["modules"] = redact(_to_dict(modules))
    # Do not export channel secrets in status/backup snapshots.
    channels = getattr(local_node, "channels", None) or []
    sections["channels"] = [redact(_to_dict(c)) for c in channels]
    return {
        "revision": hashlib.sha256(raw).hexdigest(),
        "fields": lora_descriptor_fields(lora),
        "sections": sections,
        "firmware": str(getattr(metadata, "firmware_version", "") or "")[:64],
        "note": "Valores lidos do cache local sincronizado pelo Meshtastic Python. "
                "Gravação requer confirmação e pode reiniciar/desconectar o rádio.",
    }


def prepare_lora(local_node, expected_revision, changes):
    """Validate requested edits and mutate the local protobuf; caller performs writeConfig."""
    if not isinstance(changes, dict) or not 1 <= len(changes) <= len(LORA_FIELDS):
        raise ValueError("Envie um ou mais campos LoRa permitidos")
    if not isinstance(expected_revision, str) or len(expected_revision) != 64:
        raise ValueError("Releia a configuração antes de gravar")
    lora = local_node.localConfig.lora
    revision = hashlib.sha256(lora.SerializeToString()).hexdigest()
    if revision != expected_revision:
        raise ValueError("Configuração alterada desde a leitura; recarregue antes de salvar")
    fields = {f.name: f for f in lora.DESCRIPTOR.fields}
    original = lora.__class__()
    original.CopyFrom(lora)
    effective = []
    try:
        for name, value in changes.items():
            if name not in LORA_FIELDS or name not in fields:
                raise ValueError("Parâmetro LoRa não suportado: " + str(name))
            field = fields[name]
            if field.type == field.TYPE_ENUM:
                if not isinstance(value, str) or value not in field.enum_type.values_by_name:
                    raise ValueError("Valor de enum inválido para " + name)
                parsed = field.enum_type.values_by_name[value].number
            elif field.type == field.TYPE_BOOL:
                if type(value) is not bool:
                    raise ValueError("Booleano inválido para " + name)
                parsed = value
            elif field.type in (field.TYPE_INT32, field.TYPE_UINT32,
                                field.TYPE_INT64, field.TYPE_UINT64):
                if type(value) is not int:
                    raise ValueError("Inteiro inválido para " + name)
                bounds = LORA_FIELDS[name]
                if bounds is None or not bounds[0] <= value <= bounds[1]:
                    raise ValueError("Valor fora dos limites para " + name)
                parsed = value
            else:
                raise ValueError("Tipo de campo não suportado: " + name)
            if getattr(lora, name) != parsed:
                setattr(lora, name, parsed)
                effective.append(name)
        if not effective:
            raise ValueError("Nenhuma configuração foi alterada")
        return original, effective
    except Exception:
        lora.CopyFrom(original)
        raise
