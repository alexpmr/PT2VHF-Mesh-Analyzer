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
        if field.type == field.TYPE_MESSAGE or getattr(field, 'is_repeated', False):
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
        "full_revision": hashlib.sha256(config.SerializeToString()).hexdigest(),
        "editable_sections": editable_fields(config),
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

# Non-sensitive scalar fields on firmware-provided localConfig groups are editable.
# Channels, security and moduleConfig remain visible in sanitized, read-only form.
READ_ONLY_GROUPS = {"security"}
# Wi-Fi PSK is supported by Meshtastic network config but must never
# be returned to the browser; it may only be replaced explicitly.
WRITE_ONLY_FIELDS = {("network", "wifi_psk")}


def editable_fields(config):
    groups = {}
    for section in config.DESCRIPTOR.fields:
        if section.type != section.TYPE_MESSAGE or section.name in READ_ONLY_GROUPS:
            continue
        sub = getattr(config, section.name)
        fields = []
        for field in sub.DESCRIPTOR.fields:
            name=field.name
            is_secret = (section.name, name) in WRITE_ONLY_FIELDS
            if any(word in name.lower() for word in SENSITIVE) and not is_secret:
                continue
            if getattr(field,"is_repeated",False) or field.type in (field.TYPE_MESSAGE,field.TYPE_BYTES):
                continue
            if is_secret and field.type != field.TYPE_STRING:
                continue
            # Never echo the existing Wi-Fi password to UI, even from local cache.
            value = "" if is_secret else getattr(sub,name)
            desc={"name":name,"label":"Senha Wi-Fi (substituir)" if is_secret else name.replace("_"," ").title()}
            if is_secret:
                desc.update(type="secret", value="", configured=bool(getattr(sub,name)))
                fields.append(desc)
                continue
            if field.type == field.TYPE_ENUM:
                desc.update(type="enum",options=[v.name for v in field.enum_type.values],
                            value=field.enum_type.values_by_number[int(value)].name)
            elif field.type == field.TYPE_BOOL:
                desc.update(type="bool",value=bool(value))
            elif field.type in (field.TYPE_INT32,field.TYPE_UINT32,field.TYPE_INT64,field.TYPE_UINT64):
                desc.update(type="int",value=int(value))
                if section.name=="lora" and name in LORA_FIELDS and LORA_FIELDS[name]:
                    desc["min"],desc["max"]=LORA_FIELDS[name]
            elif field.type in (field.TYPE_FLOAT,field.TYPE_DOUBLE):
                desc.update(type="float",value=float(value))
            elif field.type == field.TYPE_STRING:
                desc.update(type="string",value=str(value),max=128)
            else:continue
            fields.append(desc)
        if fields:groups[section.name]=fields
    return groups


def prepare_all(local_node, expected_revision, edits):
    """Validate a multi-group edit before writing any command to the device."""
    config=local_node.localConfig
    if hashlib.sha256(config.SerializeToString()).hexdigest()!=expected_revision:
        raise ValueError("Configuração mudou; releia o rádio antes de gravar")
    if not isinstance(edits,dict) or not edits or len(edits)>18:
        raise ValueError("Nenhuma alteração de dispositivo enviada")
    supported=editable_fields(config)
    original=config.__class__();original.CopyFrom(config)
    changed=[]
    try:
        for group,fields in edits.items():
            if group not in supported or not isinstance(fields,dict) or len(fields)>150:
                raise ValueError("Grupo não suportado para alteração: "+str(group))
            known={f["name"]:f for f in supported[group]}
            proto_fields={f.name:f for f in getattr(config,group).DESCRIPTOR.fields}
            group_changes=[]
            for key,value in fields.items():
                if key not in known:raise ValueError("Campo indisponível: "+str(group)+"."+str(key))
                row=known[key];field=proto_fields[key]
                if row["type"]=="bool":
                    if type(value) is not bool:raise ValueError("Booleano inválido em "+key)
                elif row["type"]=="enum":
                    if not isinstance(value,str) or value not in field.enum_type.values_by_name:
                        raise ValueError("Enum inválido em "+key)
                    value=field.enum_type.values_by_name[value].number
                elif row["type"]=="int":
                    if type(value) is not int:raise ValueError("Inteiro inválido em "+key)
                    mn=0 if field.type in (field.TYPE_UINT32,field.TYPE_UINT64) else -(2**31 if field.type==field.TYPE_INT32 else 2**63)
                    mx=(2**32-1 if field.type==field.TYPE_UINT32 else
                        2**64-1 if field.type==field.TYPE_UINT64 else
                        2**31-1 if field.type==field.TYPE_INT32 else 2**63-1)
                    if "min" in row:mn=max(mn,row["min"])
                    if "max" in row:mx=min(mx,row["max"])
                    if not mn<=value<=mx:raise ValueError("Valor fora dos limites: "+key)
                elif row["type"]=="float":
                    if type(value) not in (int,float) or not -1e8<float(value)<1e8:
                        raise ValueError("Número inválido: "+key)
                elif row["type"]=="string":
                    if not isinstance(value,str) or len(value.encode("utf-8"))>128:
                        raise ValueError("Texto inválido: "+key)
                elif row["type"]=="secret":
                    if (group,key) not in WRITE_ONLY_FIELDS or not isinstance(value,str):
                        raise ValueError("Credencial não autorizada: "+str(key))
                    if not (8 <= len(value.encode("utf-8")) <= 63 or
                            (len(value)==64 and all(c in "0123456789abcdefABCDEF" for c in value))):
                        raise ValueError("Senha Wi-Fi deve ter 8 a 63 bytes ou 64 dígitos hexadecimais")
                if getattr(getattr(config,group),key)!=value:
                    setattr(getattr(config,group),key,value)
                    group_changes.append(key)
            if group_changes:changed.append({"group":group,"fields":group_changes})
        if not changed:raise ValueError("Nenhuma alteração detectada")
        return original,changed
    except Exception:
        config.CopyFrom(original)
        raise

