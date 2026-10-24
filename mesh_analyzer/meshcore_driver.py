"""#185: rádios MeshCore (firmware Companion) por USB/Serial, Bluetooth LE e Wi-Fi/TCP.

O `MeshCoreInterface` se apresenta ao `SourceManager` como uma interface
Meshtastic: converte os eventos do MeshCore em pacotes no mesmo formato que o
`PacketIngestor` já entende (NODEINFO, POSITION, TEXT_MESSAGE, ROUTING) e
expõe `myInfo`, `localNode`, `nodesByNum`, `sendText()` e `close()`. Assim mapa,
nós, tráfego, mensagens, estatísticas e alertas funcionam sem reescrita.

Identidade: o MeshCore identifica nós pela chave pública (32 bytes); o número
do nó no app é formado pelos 4 primeiros bytes da chave. Remetentes de canal
que não são contatos recebem um número derivado do nome.
"""
from __future__ import annotations

import asyncio
import random
import hashlib
import threading
import time
from types import SimpleNamespace

# Tipos de anúncio do MeshCore → papel equivalente no app (ícones e filtros).
ADV_TYPES = {1: ("Companion", "CLIENT"), 2: ("Repetidor", "REPEATER"), 3: ("Room server", "ROUTER"), 4: ("Sensor", "SENSOR")}
BROADCAST = 0xFFFFFFFF


def node_num(public_key: str):
    """Número de nó (32 bits) a partir da chave pública ou do prefixo em hex."""
    try:
        num = int(str(public_key)[:8], 16)
    except (TypeError, ValueError):
        return None
    return num if num not in (0, BROADCAST) else None


def name_num(name: str) -> int:
    """Número estável para remetentes de canal que não são contatos (só o nome é conhecido)."""
    num = int.from_bytes(hashlib.blake2s(("meshcore:" + name).encode("utf-8"), digest_size=4).digest(), "big")
    return num if num not in (0, BROADCAST) else 1


def short_name(name: str) -> str:
    letters = [c for c in str(name or "") if not c.isspace()]
    return "".join(letters[:4]) or "MC"


def _payload(event):
    return getattr(event, "payload", event) or {}


def _type_name(event):
    t = getattr(event, "type", None)
    return getattr(t, "name", str(t or ""))


class MeshCoreInterface:
    """Adaptador síncrono do cliente assíncrono `meshcore` para o SourceManager."""

    is_meshcore = True

    def __init__(self, kind, conf, on_packet, on_lost=None, timeout=20, factory=None, on_event=None, source_id=None):
        self.kind = kind
        self.source_id = source_id
        self._on_event = on_event  # (tipo, dados, interface): contatos, rádio e resultados (#190)
        self._contacts = {}        # node_num -> contato MeshCore completo
        self.device_info = {}
        self._cli_waiters = {}     # prefixo da chave -> futuros aguardando resposta de CLI
        self.conf = dict(conf or {})
        self._on_packet = on_packet
        self._on_lost = on_lost
        self.myInfo = {}
        self.localNode = SimpleNamespace(nodeNum=None, channels=[], localConfig=None)
        self.nodesByNum = {}
        self.metadata = None
        self.self_info = {}
        self._keys = {}            # node_num -> chave pública completa (hex)
        self._names = {}           # nome anunciado -> node_num
        self._pending_acks = {}    # código do ACK -> (callback, destino)
        self._closed = False
        self._mc = None
        self._factory = factory
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, name="meshcore-" + kind, daemon=True)
        self._thread.start()
        try:
            self._call(self._start(), timeout + 15)
        except BaseException:
            self.close()
            raise

    # --- infraestrutura ---------------------------------------------------------
    def _call(self, coro, timeout):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(timeout)
        except TimeoutError:
            future.cancel()
            raise RuntimeError("O rádio MeshCore não respondeu a tempo")

    async def _create(self):
        if self._factory:
            return await self._factory(self.kind, self.conf)
        from meshcore import MeshCore
        if self.kind == "serial":
            return await MeshCore.create_serial(self.conf["port"], int(self.conf.get("baudrate") or 115200))
        if self.kind == "tcp":
            return await MeshCore.create_tcp(self.conf["host"], int(self.conf.get("port") or 5000))
        if self.kind == "ble":
            pin = str(self.conf.get("pin") or "") or None
            return await MeshCore.create_ble(self.conf["address"], pin=pin)
        raise RuntimeError("Transporte desconhecido para MeshCore")

    async def _start(self):
        from meshcore import EventType
        mc = await self._create()
        if mc is None:
            raise RuntimeError("O rádio não respondeu como MeshCore Companion. Confira se o firmware é o Companion "
                               "(USB, Bluetooth ou Wi-Fi) e se nenhum outro programa está usando o rádio.")
        self._mc = mc
        info = dict(getattr(mc, "self_info", {}) or {})
        self._apply_self_info(info)
        try:
            result = await mc.commands.send_device_query()
            if _type_name(result) != "ERROR":
                self.device_info = dict(_payload(result) or {})
                self._notify("device", self.device_info)
        except Exception:
            pass
        handlers = {
            EventType.SELF_INFO: lambda e: self._apply_self_info(_payload(e)),
            EventType.NEW_CONTACT: lambda e: self._contact(_payload(e), heard=True),
            EventType.NEXT_CONTACT: lambda e: self._contact(_payload(e), heard=False),
            EventType.ADVERTISEMENT: self._advert_push,
            EventType.CONTACT_MSG_RECV: lambda e: self._direct_message(_payload(e)),
            EventType.CHANNEL_MSG_RECV: lambda e: self._channel_message(_payload(e)),
            EventType.ACK: lambda e: self._ack(_payload(e)),
            EventType.RX_LOG_DATA: lambda e: self._rx_log(_payload(e)),
            EventType.DISCONNECTED: lambda e: self._lost(),
        }
        for event_type, handler in handlers.items():
            mc.subscribe(event_type, self._wrap(handler))
        try:
            result = await mc.commands.get_contacts()
            contacts = _payload(result) if _type_name(result) != "ERROR" else {}
            for contact in (contacts or {}).values():
                self._contact(contact, heard=False)
        except Exception:
            pass
        try:
            await mc.start_auto_message_fetching()
        except Exception:
            pass

    def _wrap(self, handler):
        async def run(event):
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass
        return run

    def _emit(self, packet):
        if not self._closed and self._on_packet:
            self._on_packet(packet=packet, interface=self)

    def _lost(self):
        if not self._closed and self._on_lost:
            self._on_lost(interface=self)

    def _notify(self, kind, data):
        if self._on_event and not self._closed:
            try:
                self._on_event(kind, data, self)
            except Exception:
                pass

    # --- conversão de eventos -----------------------------------------------------
    def _apply_self_info(self, info):
        if not info:
            return
        self.self_info = dict(info)
        self._notify("self", self.self_info)
        num = node_num(info.get("public_key"))
        if num:
            self.myInfo = {"my_node_num": num}
            self.localNode.nodeNum = num
            self._keys[num] = info.get("public_key")
            name = str(info.get("name") or "").strip()
            user = {"longName": name, "shortName": short_name(name), "hwModel": "MeshCore Companion", "role": "CLIENT"}
            self.nodesByNum[num] = {"user": user, "lastHeard": int(time.time())}
            if info.get("adv_lat") or info.get("adv_lon"):
                self.nodesByNum[num]["position"] = {"latitude": info.get("adv_lat"), "longitude": info.get("adv_lon")}

    def _contact(self, c, heard):
        num = node_num(c.get("public_key"))
        if not num:
            return None
        self._keys[num] = c.get("public_key")
        self._contacts[num] = dict(c)
        self._notify("contact", dict(c, heard=bool(heard)))
        name = str(c.get("adv_name") or "").strip()
        if name:
            self._names[name] = num
        kind, role = ADV_TYPES.get(int(c.get("type") or 0), ("Nó", "CLIENT"))
        user = {"longName": name or ("MeshCore " + str(c.get("public_key"))[:8]), "shortName": short_name(name),
                "hwModel": "MeshCore " + kind, "role": role}
        entry = {"user": user}
        lat, lon = c.get("adv_lat"), c.get("adv_lon")
        if lat or lon:
            entry["position"] = {"latitude": lat, "longitude": lon}
        if c.get("last_advert"):
            entry["lastHeard"] = int(c["last_advert"])
        self.nodesByNum[num] = entry
        if heard:
            self._announce(num, user, lat, lon, c.get("last_advert"), c.get("out_path_len"))
        return num

    def _announce(self, num, user, lat, lon, when=None, path_len=None, snr=None, rssi=None):
        base = {"from": num, "to": BROADCAST, "rxTime": int(when or time.time())}
        if path_len is not None and int(path_len) >= 0:
            base.update(hopStart=int(path_len), hopLimit=0)
        if snr is not None:
            base["rxSnr"] = snr
        if rssi is not None:
            base["rxRssi"] = rssi
        self._emit({**base, "id": "mc-info-%08x-%d" % (num, base["rxTime"]),
                    "decoded": {"portnum": "NODEINFO_APP", "user": user}})
        if lat or lon:
            self._emit({**base, "id": "mc-pos-%08x-%d" % (num, base["rxTime"]),
                        "decoded": {"portnum": "POSITION_APP", "position": {"latitude": lat, "longitude": lon}}})

    async def _advert_push(self, event):
        key = _payload(event).get("public_key")
        num = node_num(key)
        if not num or self._mc is None:
            return
        try:
            result = await self._mc.commands.get_contact_by_key(bytes.fromhex(key))
            contact = _payload(result) if _type_name(result) != "ERROR" else None
        except Exception:
            contact = None
        if isinstance(contact, dict) and contact.get("public_key"):
            self._contact(contact, heard=True)

    def _direct_message(self, m):
        prefix = str(m.get("pubkey_prefix") or "")
        if int(m.get("txt_type") or 0) == 1:
            # Resposta de comando de CLI de um repetidor/room server: não é conversa.
            for key in list(self._cli_waiters):
                if prefix and key.startswith(prefix[:12]):
                    for fut in self._cli_waiters.pop(key):
                        if not fut.done():
                            fut.set_result(str(m.get("text") or ""))
            return
        sender = next((n for n, k in self._keys.items() if str(k).startswith(prefix)), None) if prefix else None
        sender = sender or node_num(prefix)
        ts = int(m.get("sender_timestamp") or time.time())
        packet = {"from": sender, "to": self.localNode.nodeNum, "channel": 0, "rxTime": ts,
                  "id": "mc-dm-%s-%d" % (prefix, ts), "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": str(m.get("text") or "")}}
        if m.get("SNR") is not None:
            packet["rxSnr"] = m.get("SNR")
        if isinstance(m.get("path_len"), int) and 0 <= m["path_len"] < 64:
            packet.update(hopStart=m["path_len"], hopLimit=0)
        self._emit(packet)

    def _channel_message(self, m):
        text = str(m.get("text") or "")
        name, body = (text.split(": ", 1) + [""])[:2] if ": " in text else ("", text)
        name = name.strip()
        sender = self._names.get(name) if name else None
        if sender is None and name:
            sender = name_num(name)
            if sender not in self.nodesByNum:
                user = {"longName": name, "shortName": short_name(name), "hwModel": "MeshCore (canal)", "role": "CLIENT"}
                self.nodesByNum[sender] = {"user": user}
                self._emit({"from": sender, "to": BROADCAST, "rxTime": int(time.time()), "id": "mc-chname-%08x" % sender,
                            "decoded": {"portnum": "NODEINFO_APP", "user": user}})
        ts = int(m.get("sender_timestamp") or time.time())
        packet = {"from": sender, "to": BROADCAST, "channel": int(m.get("channel_idx") or 0), "rxTime": ts,
                  "id": "mc-ch-%s-%d" % (m.get("txt_hash") or hashlib.blake2s(text.encode(), digest_size=4).hexdigest(), ts),
                  "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": body if name else text}}
        if m.get("SNR") is not None:
            packet["rxSnr"] = m.get("SNR")
        if isinstance(m.get("path_len"), int) and 0 <= m["path_len"] < 64:
            packet.update(hopStart=m["path_len"], hopLimit=0)
        self._emit(packet)

    def _rx_log(self, d):
        """Cada pacote ouvido pelo rádio vira uma linha de tráfego com SNR/RSSI e saltos."""
        kind = str(d.get("payload_typename") or "RAW")
        sender = None
        if kind == "ADVERT" and d.get("adv_key"):
            sender = node_num(d.get("adv_key"))
        path_len = d.get("path_len")
        packet = {"from": sender, "to": BROADCAST, "rxTime": int(d.get("recv_time") or time.time()),
                  "id": "mc-rx-" + str(d.get("pkt_hash") or hashlib.blake2s(str(d.get("raw_hex")).encode(), digest_size=6).hexdigest()),
                  "decoded": {"portnum": "MESHCORE_" + kind}}
        if d.get("snr") is not None:
            packet["rxSnr"] = d.get("snr")
        if d.get("rssi") is not None:
            packet["rxRssi"] = d.get("rssi")
        if isinstance(path_len, int) and 0 <= path_len < 64:
            packet.update(hopStart=path_len, hopLimit=0)
        self._emit(packet)

    def _ack(self, a):
        code = str(a.get("code") or "")
        pending = self._pending_acks.pop(code, None)
        if pending:
            callback, target, request = pending
            try:
                callback({"from": target, "to": self.localNode.nodeNum,
                          "decoded": {"portnum": "ROUTING_APP", "requestId": request, "routing": {"errorReason": "NONE"}}})
            except Exception:
                pass

    # --- API usada pelo SourceManager ----------------------------------------------
    def sendText(self, text, destinationId="^all", wantAck=True, channelIndex=0, onResponse=None):
        if self._mc is None:
            raise RuntimeError("Rádio MeshCore desconectado")
        if destinationId in (None, "", "^all", "broadcast"):
            result = self._call(self._mc.commands.send_chan_msg(int(channelIndex), str(text)), 15)
            if _type_name(result) == "ERROR":
                raise RuntimeError("O rádio MeshCore recusou a mensagem do canal")
            return {"id": int(time.time() * 1000) & 0x7FFFFFFF}
        target = int(str(destinationId).lstrip("!"), 16) if str(destinationId).startswith("!") else int(destinationId)
        key = self._keys.get(target)
        if not key:
            raise ValueError("Este nó MeshCore não está nos contatos do rádio; aguarde um anúncio dele")
        result = self._call(self._mc.commands.send_msg(key, str(text)), 15)
        if _type_name(result) == "ERROR":
            raise RuntimeError("O rádio MeshCore recusou a mensagem")
        raw = _payload(result).get("expected_ack") or ""
        code = raw.hex() if isinstance(raw, (bytes, bytearray)) else str(raw)
        request = int(code, 16) if code else int(time.time() * 1000) & 0x7FFFFFFF
        if onResponse and code:
            self._pending_acks[code] = (onResponse, target, request)
        return {"id": request}

    # --- operações MeshCore (#190) -----------------------------------------------------
    def contact(self, num):
        num = int(num)
        c = self._contacts.get(num)
        if not c:
            raise ValueError("Este nó não está nos contatos do rádio MeshCore")
        return c

    def resolve(self, prefix):
        """Nó dono de um prefixo de chave, quando só um contato combina (senão None)."""
        prefix = str(prefix or "").lower()
        if not prefix:
            return None
        found = [n for n, c in self._contacts.items() if str(c.get("public_key") or "").lower().startswith(prefix)]
        own = self.self_info.get("public_key")
        if own and str(own).lower().startswith(prefix):
            found.append(node_num(own))
        return found[0] if len(found) == 1 else None

    def _run(self, coro, timeout=45):
        if self._mc is None:
            raise RuntimeError("Rádio MeshCore desconectado")
        return self._call(coro, timeout)

    def send_advert(self, flood=False):
        result = self._run(self._mc.commands.send_advert(flood=bool(flood)), 15)
        if _type_name(result) == "ERROR":
            raise RuntimeError("O rádio recusou o envio do anúncio")
        return {"flood": bool(flood)}

    def reset_path(self, num):
        c = self.contact(num)
        result = self._run(self._mc.commands.reset_path(c["public_key"]), 15)
        if _type_name(result) == "ERROR":
            raise RuntimeError("O rádio recusou zerar o caminho")
        c.update(out_path="", out_path_len=-1)
        self._notify("contact", dict(c, heard=False))
        return {"ok": True}

    def path_discovery(self, num):
        c = self.contact(num)
        event = self._run(self._mc.commands.send_path_discovery_sync(c["public_key"]), 60)
        if event is None:
            raise RuntimeError("Sem resposta da descoberta de caminho")
        data = dict(_payload(event) or {})
        if data.get("out_path") is not None:
            hs = int(data.get("out_path_hash_len") or 1)
            c.update(out_path=data.get("out_path") or "", out_path_len=int(data.get("out_path_len") or 0),
                     out_path_hash_mode=max(0, hs - 1))
            self._notify("contact", dict(c, heard=False))
        return data

    def login(self, num, password=""):
        c = self.contact(num)
        event = self._run(self._mc.commands.send_login_sync(c["public_key"], str(password or "")), 60)
        if event is None or _type_name(event) != "LOGIN_SUCCESS":
            raise RuntimeError("Login recusado ou sem resposta (confira a senha e o alcance)")
        return dict(_payload(event) or {})

    def status(self, num):
        c = self.contact(num)
        data = self._run(self._mc.commands.req_status_sync(c), 60)
        if not data:
            raise RuntimeError("O nó não respondeu ao pedido de status (pode exigir login)")
        self._notify("status", {"node_num": int(num), **dict(data)})
        return dict(data)

    def telemetry(self, num):
        c = self.contact(num)
        data = self._run(self._mc.commands.req_telemetry_sync(c), 60)
        if data is None:
            raise RuntimeError("O nó não respondeu ao pedido de telemetria (pode exigir login ou estar com a telemetria desligada)")
        self._notify("telemetry", {"node_num": int(num), "lpp": list(data)})
        return {"lpp": list(data)}

    def neighbours(self, num):
        c = self.contact(num)
        data = self._run(self._mc.commands.req_neighbours_sync(c, pubkey_prefix_length=4), 60)
        if not data:
            raise RuntimeError("O repetidor não respondeu ao pedido de vizinhos (pode exigir login)")
        result = {"node_num": int(num), "neighbours": list(data.get("neighbours") or []),
                  "total": data.get("neighbours_count")}
        known = []
        for n in result["neighbours"]:
            other = self.resolve(n.get("pubkey"))
            n["node_num"] = other
            if other:
                known.append({"nodeId": other, "snr": n.get("snr")})
        if known:  # vizinhos informados pelo repetidor alimentam a topologia, como no NeighborInfo
            self._emit({"from": int(num), "to": BROADCAST, "rxTime": int(time.time()),
                        "id": "mc-nb-%08x-%d" % (int(num), int(time.time())),
                        "decoded": {"portnum": "NEIGHBORINFO_APP", "neighborinfo": {"neighbors": known}}})
        self._notify("neighbours", result)
        return result

    def cli(self, num, command, timeout=25):
        c = self.contact(num)
        command = str(command or "").strip()
        if not command or len(command.encode("utf-8")) > 160:
            raise ValueError("Comando vazio ou longo demais")

        async def run():
            fut = self._loop.create_future()
            self._cli_waiters.setdefault(c["public_key"], []).append(fut)
            result = await self._mc.commands.send_cmd(c, command)
            if _type_name(result) == "ERROR":
                raise RuntimeError("O rádio recusou o comando")
            try:
                return await asyncio.wait_for(fut, timeout)
            except asyncio.TimeoutError:
                raise RuntimeError("Sem resposta do comando (faça login como admin antes)") from None
        return {"reply": self._run(run(), timeout + 10)}

    def trace(self, num):
        """Traceroute pelos repetidores do caminho até o repetidor e de volta, com SNR por trecho."""
        c = self.contact(num)
        if int(c.get("type") or 0) not in (2, 3):
            raise ValueError("Traceroute MeshCore só passa por repetidores e room servers")
        hs = max(0, int(c.get("out_path_hash_mode") or 0)) + 1
        hops = split_path(c.get("out_path") or "", hs) if int(c.get("out_path_len") or 0) > 0 else []
        if hs not in (1, 2, 4):  # o trace aceita hashes de 1, 2 ou 4 bytes: reduz para 1 byte
            hs, hops = 1, [h[:2] for h in hops]
        target = str(c["public_key"])[:hs * 2]
        route = hops + [target] + list(reversed(hops))

        async def run():
            from meshcore import EventType
            tag = random.randint(1, 0xFFFFFFFF)
            sent = await self._mc.commands.send_trace(tag=tag, path=",".join(route))
            if _type_name(sent) == "ERROR":
                raise RuntimeError("O rádio recusou o traceroute")
            wait = max(10.0, float((_payload(sent) or {}).get("suggested_timeout") or 0) / 1000 * 2)
            event = await self._mc.dispatcher.wait_for_event(EventType.TRACE_DATA, attribute_filters={"tag": tag}, timeout=min(wait, 90))
            if event is None:
                raise RuntimeError("O traceroute não voltou a tempo")
            return dict(_payload(event) or {})
        data = self._run(run(), 120)
        result = {"node_num": int(num), "route": route, "path": data.get("path") or [], "hash_size": hs}
        for hop in result["path"]:
            if hop.get("hash"):
                hop["node_num"] = self.resolve(hop["hash"])
        nums = [self.resolve(h) for h in hops]
        own = getattr(self.localNode, "nodeNum", None)
        if own and all(nums) and data.get("path"):
            back = list(reversed(nums))
            self._emit({"from": int(num), "to": own, "rxTime": int(time.time()),
                        "id": "mc-tr-%08x-%d" % (int(num), int(time.time())),
                        "decoded": {"portnum": "TRACEROUTE_APP",
                                    "traceroute": {"route": nums, "routeBack": back}}})
        self._notify("trace", result)
        return result

    def remove_contact(self, num):
        c = self.contact(num)
        result = self._run(self._mc.commands.remove_contact(c["public_key"]), 15)
        if _type_name(result) == "ERROR":
            raise RuntimeError("O rádio recusou remover o contato")
        self._contacts.pop(int(num), None)
        self._notify("removed", {"node_num": int(num), "public_key": c["public_key"]})
        return {"ok": True}

    def autoadd(self, enabled=None):
        if enabled is not None:
            result = self._run(self._mc.commands.set_manual_add_contacts(not bool(enabled)), 15)
            if _type_name(result) == "ERROR":
                raise RuntimeError("O rádio recusou a alteração")
            self.self_info["manual_add_contacts"] = not bool(enabled)
        return {"auto_add": not bool(self.self_info.get("manual_add_contacts"))}

    def channels(self):
        out = []
        count = int(self.device_info.get("max_channels") or 8)
        for idx in range(min(count, 40)):
            try:
                event = self._run(self._mc.commands.get_channel(idx), 10)
            except RuntimeError:
                break
            if _type_name(event) == "ERROR":
                break
            data = _payload(event) or {}
            name = str(data.get("channel_name") or "")
            out.append({"index": idx, "name": name, "hash": data.get("channel_hash"),
                        "empty": not name and not any(bytes(data.get("channel_secret") or b""))})
        return out

    def set_channel(self, index, name):
        name = str(name or "").strip()
        if not name or len(name.encode("utf-8")) > 31:
            raise ValueError("Nome do canal: 1 a 31 caracteres (use #nome para canais públicos por hashtag)")
        result = self._run(self._mc.commands.set_channel(int(index), name), 15)
        if _type_name(result) == "ERROR":
            raise RuntimeError("O rádio recusou o canal")
        return {"index": int(index), "name": name}

    def contact_uri(self, num=None):
        key = self.contact(num)["public_key"] if num else None
        event = self._run(self._mc.commands.export_contact(key), 15)
        if _type_name(event) == "ERROR":
            raise RuntimeError("O rádio não exportou o contato")
        return {"uri": (_payload(event) or {}).get("uri", "")}

    def stats(self):
        out = {}
        for key, name in (("core", "get_stats_core"), ("radio", "get_stats_radio"), ("packets", "get_stats_packets")):
            try:
                event = self._run(getattr(self._mc.commands, name)(), 10)
                if _type_name(event) != "ERROR":
                    out[key] = dict(_payload(event) or {})
            except Exception:
                pass
        return out

    def close(self):
        if self._closed:
            return
        self._closed = True
        mc = self._mc
        if mc is not None and self._loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(mc.disconnect(), self._loop).result(8)
            except Exception:
                pass
        try:
            self._loop.call_soon_threadsafe(self._loop.stop)
        except RuntimeError:
            pass


def split_path(hexpath, hash_size):
    """Caminho MeshCore (hex) em trechos de `hash_size` bytes, do primeiro repetidor ao último."""
    hexpath, step = str(hexpath or ""), max(1, int(hash_size)) * 2
    return [hexpath[i:i + step] for i in range(0, len(hexpath) - step + 1, step)]


def probe_meshcore(candidate, timeout=20):
    """Verificação de rádio MeshCore para a detecção automática (sem TX)."""
    iface = None
    try:
        iface = MeshCoreInterface(candidate["kind"], candidate["config"], on_packet=None, timeout=timeout)
        num = iface.localNode.nodeNum
        if not num:
            return {"ok": False, "error": "Sem resposta do protocolo MeshCore"}
        name = str(iface.self_info.get("name") or "").strip()
        return {"ok": True, "node_num": int(num), "long_name": name[:72], "short_name": short_name(name),
                "protocol": "meshcore"}
    except Exception as exc:
        return {"ok": False, "error": (str(exc) or type(exc).__name__)[:160]}
    finally:
        if iface is not None:
            iface.close()
