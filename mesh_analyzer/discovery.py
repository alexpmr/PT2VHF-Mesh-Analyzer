"""Opt-in, time-bounded discovery of radio connection candidates.

Enumerating a COM port, BLE advert or mDNS service is not evidence that a
Meshtastic protocol handshake succeeded. Never connect automatically.
"""
from __future__ import annotations
import asyncio
import ipaddress
import threading
import time

class DeviceDiscovery:
    def __init__(self):
        self._lock=threading.RLock()
        self._state={"running":False,"items":[],"errors":[],"completed_ms":0}
        self._thread=None

    def snapshot(self):
        with self._lock:
            return {"running":self._state["running"],
                    "items":[dict(x) for x in self._state["items"]],
                    "errors":list(self._state["errors"]),
                    "completed_ms":self._state["completed_ms"]}

    def start(self):
        with self._lock:
            if self._state["running"]:
                return self.snapshot()
            self._state={"running":True,"items":[],"errors":[],"completed_ms":0}
            self._thread=threading.Thread(target=self._scan,
                                         daemon=True,name="mesh-device-discovery")
            self._thread.start()
            return self.snapshot()

    def _scan(self):
        items=[];errors=[]
        try:
            from serial.tools import list_ports
            for port in list_ports.comports():
                name=str(getattr(port,"device","") or "")
                if not name:continue
                items.append({"kind":"serial","name":str(getattr(port,"description","") or name)[:90],
                              "address":name,"config":{"port":name},
                              "verified":False,"method":"USB/Serial enumerado"})
        except Exception as exc:
            errors.append("USB/Serial: "+type(exc).__name__)
        async def scan_ble():
            from bleak import BleakScanner
            devices=await BleakScanner.discover(timeout=5,return_adv=False)
            return [{"kind":"ble","name":str(d.name or "Bluetooth LE")[:90],
                     "address":str(d.address),"config":{"address":str(d.address)},
                     "verified":False,"method":"Anúncio BLE detectado"}
                    for d in devices if d.address and
                    ("meshtastic" in str(d.name or "").casefold() or
                     "mesh" in str(d.name or "").casefold())]
        try:
            # Run from our own daemon thread; never block the HTTP UI.
            items.extend(asyncio.run(scan_ble()))
        except Exception as exc:
            errors.append("BLE: "+type(exc).__name__)
        try:
            # Passive mDNS browse only. Never sweep an IP subnet.
            from zeroconf import Zeroconf, ServiceBrowser, ServiceListener
            zc=Zeroconf()
            results=[]
            class Listener(ServiceListener):
                def add_service(self, zeroconf, type_, name):
                    try:
                        info=zeroconf.get_service_info(type_,name,timeout=350)
                        if info:
                            for raw in info.addresses:
                                if len(raw)!=4:continue
                                host=str(ipaddress.IPv4Address(raw))
                                if not ipaddress.ip_address(host).is_private:continue
                                results.append({"kind":"tcp","name":name[:90],
                                    "address":host,"config":{"host":host,"port":info.port or 4403},
                                    "verified":False,"method":"mDNS anunciado"})
                    except Exception:pass
                def update_service(self,*args):pass
                def remove_service(self,*args):pass
            try:
                browser=ServiceBrowser(zc,["_meshtastic._tcp.local."],Listener())
                time.sleep(4)
                browser.cancel()
            finally:zc.close()
            items.extend(results)
        except ImportError:
            errors.append("mDNS indisponível: instale zeroconf")
        except Exception as exc:
            errors.append("mDNS: "+type(exc).__name__)
        unique={}
        for item in items:
            unique.setdefault((item["kind"],item["address"]),item)
        with self._lock:
            self._state={"running":False,"items":list(unique.values()),
                         "errors":errors,"completed_ms":int(time.time()*1000)}
