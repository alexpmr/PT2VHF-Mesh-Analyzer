"""Standalone local HTTP application for Windows 11 and future Linux/macOS."""
from __future__ import annotations

import argparse
import html
import json
import logging
import os
import secrets
import signal
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__
from .database import Database, profile_dir
from .analytics import calculate, parse_filters
from .transports import SourceManager, available_serial_ports

LOG = logging.getLogger("pt2vhf.mesh")
_UPDATE_CACHE = {"at": 0.0, "data": None}
_UPDATE_LOCK = threading.Lock()


def latest_release(force=False):
    """Bounded, cached request to the project's public GitHub Releases endpoint."""
    with _UPDATE_LOCK:
        if not force and _UPDATE_CACHE["data"] is not None and time.monotonic()-_UPDATE_CACHE["at"] < 300:
            return _UPDATE_CACHE["data"]
        request = urllib.request.Request(
            "https://api.github.com/repos/alexpmr/PT2VHF-Mesh-Analyzer/releases/latest",
            headers={"User-Agent": "PT2VHF-Mesh-Analyzer/"+__version__,
                     "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(request, timeout=6) as response:
            info = json.load(response)
        tag = str(info.get("tag_name") or "").removeprefix("v")
        if not tag or not all(x.isdigit() for x in tag.split(".")):
            raise ValueError("Release remota sem versão válida")
        current = tuple(int(x) for x in __version__.split("."))
        remote = tuple(int(x) for x in tag.split("."))
        data = {"success": True, "current": __version__, "latest": tag,
                "available": remote > current,
                "release_url": "https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/latest",
                "notes": str(info.get("body") or "")[:1800],
                "assets": [{"name":str(a.get("name") or ""),
                            "url":str(a.get("browser_download_url") or "")}
                           for a in info.get("assets", []) if a.get("name")]}
        _UPDATE_CACHE.update(at=time.monotonic(), data=data)
        return data



def in_container():
    """Modo container (#160): PT2VHF_CONTAINER=1, definido pela imagem oficial."""
    return os.environ.get("PT2VHF_CONTAINER")=="1"


class ReleaseMonitor:
    """Exactly one update timer per running application, not per browser tab."""
    def __init__(self, db):
        self.db=db
        self._lock=threading.Lock()
        self._wake=threading.Event()
        self._stop=threading.Event()
        self._at=0.0
        self._result=None
        self._error=None
        self._thread=None

    def start(self):
        if self._thread is not None:return
        self._thread=threading.Thread(target=self._loop,name="release-checker",daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._wake.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=2)

    def changed(self):
        self._wake.set()

    def check(self, force=False):
        if not self._lock.acquire(blocking=False):
            return self.status()
        try:
            try:
                result=latest_release(force=force)
                self._result=result
                self._error=None
            except Exception as exc:
                self._error=str(exc)[:200]
            self._at=time.time()
            return self.status()
        finally:
            self._lock.release()

    def status(self):
        minutes=self.db.system_settings()["update_minutes"]
        return {"success":True,"current":__version__,
                "latest":self._result.get("latest") if self._result else None,
                "available":self._result.get("available") if self._result else None,
                "release_url":self._result.get("release_url") if self._result else
                    "https://github.com/alexpmr/PT2VHF-Mesh-Analyzer/releases/latest",
                "notes":self._result.get("notes","") if self._result else "",
                "checked_at":self._at or None,
                "next_check":self._at+minutes*60 if self._at else None,
                "interval_minutes":minutes,"error":self._error,
                "direct_update":os.name=="nt" and not in_container(),
                "container":in_container()}

    def _loop(self):
        while not self._stop.is_set():
            delay=max(0,(self._at+self.db.system_settings()["update_minutes"]*60)-time.time()) if self._at else 1
            self._wake.wait(delay)
            self._wake.clear()
            if self._stop.is_set():break
            due=not self._at or time.time()-self._at>=self.db.system_settings()["update_minutes"]*60
            if due:self.check(force=True)


def view_source(path):
    """#189: ?source=<id> escolhido no topo; vazio = todas as conexões."""
    value=urllib.parse.parse_qs(urllib.parse.urlsplit(path).query).get("source",[""])[0]
    return int(value) if value.isdigit() else None


def radios_available(db, sources):
    """#152: BLE só é varrido quando há conexão BLE em espera para conferir."""
    active=sources.active_radio()
    need_ble=any(s["kind"]=="ble" and s["enabled"] and s["id"]!=active for s in db.sources(public=False))
    seen=[]
    if need_ble:
        try:
            from .device_detection import scan_ble
            seen=[d["address"] for d in scan_ble(timeout=4.0)]
        except Exception:
            LOG.debug("Varredura BLE indisponível para o seletor de rádio",exc_info=True)
    return sources.available_radios(ble_seen=seen)


def build_handler(db:Database, sources:SourceManager, csrf:str, doc:str, updates=None, updater=None, shutdown=None, ready_event=None, automation=None, discovery=None, watcher=None, autoadd=None, restart=None, alerts=None, msgauto=None):
    elevation_cache=[]
    def elevations():
        # #179/#180: elevações do terreno com cache no SQLite.
        if not elevation_cache:
            from .survey import Elevations
            elevation_cache.append(Elevations(db,cache_dir=profile_dir()/"terrain-tiles"))
        return elevation_cache[0]
    def own_nodes():
        own={int(s["local_node_num"]) for s in sources.snapshot().values() if s.get("local_node_num")}
        own|={int(s["config"]["node_num"]) for s in db.sources(public=False) if s["config"].get("node_num")}
        return own
    def meshcore_overview(source=None):
        sid,iface=sources.meshcore_interface(source)
        if sid is None and source:sid=int(source)
        if sid is None:
            known=[x["id"] for x in db.sources(public=False) if (x.get("config") or {}).get("protocol")=="meshcore"]
            sid=known[0] if known else None
        auto=getattr(sources,"meshcore_auto",None)
        result={"connected":iface is not None,"source_id":sid,
                "automation":auto.overview() if auto else None}
        if sid is not None:result.update(sources.meshcore.overview(sid))
        return result

    def meshcore_action(payload):
        """Operações MeshCore no rádio conectado (#190). Algumas esperam resposta da malha (até ~1 min)."""
        sid,iface=sources.meshcore_interface(payload.get("source_id"))
        if iface is None:raise ValueError("Conecte um rádio MeshCore para usar esta função")
        action=str(payload.get("action") or "")
        node=payload.get("node")
        node=int(node,0) if isinstance(node,str) else node
        simple={"reset_path":"reset_path","discover":"path_discovery","status":"status","telemetry":"telemetry",
                "neighbours":"neighbours","trace":"trace","remove":"remove_contact"}
        if action in simple:
            if not node:raise ValueError("Escolha o contato")
            result=getattr(iface,simple[action])(node)
            db.log("MeshCore: "+action+" para !%08x"%int(node),source_id=sid)
            return result
        if action=="login":
            auto=getattr(sources,"meshcore_auto",None)
            password=payload.get("password")
            if password is None and auto:password=auto._passwords(db).get(str(int(node)),"")
            result=iface.login(node,password or "")
            if payload.get("remember") and auto:auto.set_password(node,password or "")
            return result
        if action=="cli":return iface.cli(node,payload.get("command"))
        if action=="advert":return iface.send_advert(payload.get("flood") is True)
        if action=="autoadd":return iface.autoadd(payload.get("enabled") if "enabled" in payload else None)
        if action=="channels":return {"channels":iface.channels()}
        if action=="set_channel":return iface.set_channel(payload.get("index"),payload.get("name"))
        if action=="uri":return iface.contact_uri(node)
        if action=="stats":return iface.stats()
        raise ValueError("Operação MeshCore desconhecida")

    def survey_link(item):
        from . import survey
        node=lambda v:int(v,0) if isinstance(v,str) and v else (int(v) if isinstance(v,int) else None)
        observed=survey.observed_link(db,own_nodes(),node(item.get("node_a")),node(item.get("node_b")))
        return survey.link_analysis(elevations(),item.get("a"),item.get("b"),item.get("params") or {},observed)
    class Handler(BaseHTTPRequestHandler):
        server_version="PT2VHF-Mesh-Analyzer/" + __version__

        def _pdf(self,body,filename):
            self.send_response(200)
            self.send_header("Content-Type","application/pdf")
            self.send_header("Content-Disposition","attachment; filename="+filename)
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Length",str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self,fmt,*args):
            if not str(self.path).startswith("/api/"):
                LOG.info("HTTP %s", fmt % args)

        def _json(self,body,status=200):
            data=json.dumps(body,ensure_ascii=False,default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Length",str(len(data)))
            self.end_headers()
            try:self.wfile.write(data)
            except (ConnectionAbortedError,BrokenPipeError,ConnectionResetError):pass

        def _error(self,exc,status=400):
            return self._json({"success":False,"error":str(exc)[:240]},status)

        def _local_host(self):
            host=self.headers.get("Host","").split(":")[0].strip("[]").lower()
            return host in ("127.0.0.1","localhost","::1")

        def do_GET(self):
            if not self._local_host():return self._error("Host não autorizado",403)
            path=urllib.parse.urlsplit(self.path).path
            try:
                if path in ("/","/mapa","/nos","/trafego","/mensagens","/estatisticas","/automacoes","/configuracoes","/ajuda") or path.startswith("/estatisticas/") or path.startswith("/configuracoes/"):
                    content=doc.replace("__CSRF_TOKEN__",html.escape(csrf,quote=True)).encode("utf-8")
                    self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8")
                    self.send_header("X-Frame-Options","DENY")
                    self.send_header("Content-Security-Policy","frame-ancestors 'none'")
                    self.send_header("Cache-Control","no-cache")
                    self.send_header("Content-Length",str(len(content)));self.end_headers();self.wfile.write(content)
                elif path == "/health":self._json({"success":True,"version":__version__,"database":"ok","update_nonce":os.environ.get("PT2VHF_UPDATE_NONCE",""),"ui_ready":bool(ready_event and ready_event.is_set())})
                elif path == "/api/state":self._json({"success":True,"version":__version__,"sources":db.sources(),"connections":sources.snapshot(),"counts":db.stats(),"retention":db.retention(),"system":db.system_settings()})
                elif path == "/api/nodes":self._json({"success":True,"data":db.node_rows()})
                elif path == "/api/nodes/hops":self._json({"success":True,"data":db.node_hop_rows()})
                elif path == "/api/nodes/sources":
                    self._json({"success":True,"data":db.node_source_rows()})
                elif path == "/api/topology/diagnostics":
                    query=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                    source=query.get("source_id",[None])[0]
                    self._json({"success":True,"data":db.topology_diagnostics(source)})
                elif path == "/api/packets":
                    self._json({"success":True,"data":db.packet_rows(source_id=view_source(self.path))})
                elif path == "/api/messages":
                    sources.message_receipts.expire()
                    self._json({"success":True,"data":db.message_rows(source_id=view_source(self.path))})
                elif path == "/api/links":self._json({"success":True,"data":db.link_rows()})
                elif path == "/api/communications":
                    self._json({"success":True,"data":db.communication_rows()})
                elif path == "/api/waypoints":self._json({"success":True,"data":db.waypoint_rows()})
                elif path == "/api/events":self._json({"success":True,"data":db.event_rows()})
                elif path == "/api/ports":self._json({"success":True,"data":available_serial_ports()})
                elif path == "/api/radios/available":
                    self._json({"success":True,"data":radios_available(db,sources),
                                "switch":sources.switch_status()})
                elif path == "/api/radios/switch":self._json({"success":True,"data":sources.switch_status()})
                elif path == "/api/devices/detected":
                    notices=[{k:v for k,v in n.items() if k not in ("candidate","key")} for n in watcher.notices()] if watcher else []
                    self._json({"success":True,"data":notices})
                elif path.startswith("/api/insights/"):
                    from . import insights
                    q={k:v[0] for k,v in urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).items()}
                    hours=int(q.get("hours") or 24)
                    kind=path.rsplit("/",1)[1]
                    if kind=="timeline":data=insights.node_timeline(db,int(q["node"],0),hours)
                    elif kind=="repeaters":data=insights.repeaters(db,hours)
                    elif kind=="coverage":data=insights.coverage(db,hours,float(q.get("cell") or 0.01))
                    elif kind=="routes":data=insights.routes(db,hours)
                    elif kind=="terrain":
                        pos={}
                        for key in ("a","b"):
                            row=db._rows("SELECT latitude,longitude FROM nodes WHERE node_num=?",(int(q[key],0),))
                            if not row or row[0]["latitude"] is None:raise ValueError("Os dois nós precisam ter posição conhecida")
                            pos[key]=(row[0]["latitude"],row[0]["longitude"])
                        data=insights.terrain_profile(pos["a"],pos["b"],float(q.get("freq") or 915),
                            float(q.get("ha") or 2),float(q.get("hb") or 2),elevations=elevations().get)
                    else:raise LookupError("Análise desconhecida")
                    self._json({"success":True,"data":data})
                elif path == "/api/channels":
                    self._json({"success":True,**sources.channel_list()})
                elif path == "/api/meshcore":
                    query=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                    self._json({"success":True,**meshcore_overview(query.get("source",[None])[0])})
                elif path == "/api/meshcore/results":
                    query={k:v[0] for k,v in urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).items()}
                    sid,_=sources.meshcore_interface()
                    sid=int(query.get("source") or sid or 0)
                    self._json({"success":True,"data":sources.meshcore.results(sid,int(query.get("node") or 0,0) or None,
                        query.get("kind") or None,min(200,int(query.get("limit") or 50)))})
                elif path == "/api/msgauto":
                    if not msgauto:raise ValueError("Mensagens automáticas indisponíveis")
                    self._json({"success":True,**msgauto.overview()})
                elif path == "/api/alerts":
                    self._json({"success":True,**alerts.list()} if alerts else {"success":True,"alerts":[],"unread":0})
                elif path == "/api/alerts/config":
                    if not alerts:raise ValueError("Alertas indisponíveis")
                    self._json({"success":True,"config":alerts.config(public=True)})
                elif path == "/api/messages/search":
                    query=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                    node=query.get("node",[""])[0]
                    days=query.get("days",[""])[0]
                    self._json({"success":True,"data":db.search_messages(query.get("q",[""])[0][:200],
                        int(node,0) if node else None,int(days) if days else None)})
                elif path == "/api/survey/defaults":
                    from . import survey
                    radio=survey.radio_defaults(sources)
                    presets=list(survey.PRESETS)+([radio["preset"]] if radio["preset"] not in survey.PRESETS else [])
                    self._json({"success":True,"radio":radio,"presets":presets,
                                "saved":survey.saved_surveys(db)})
                elif path == "/api/messages/context":
                    query=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                    self._json({"success":True,"data":db.message_context(int(query.get("id",["0"])[0]))})
                elif path == "/api/backup/status":
                    from .backup import last_restore, pending_restore
                    self._json({"success":True,"pending":pending_restore(profile_dir()),
                                "last":last_restore(profile_dir()),"container":in_container()})
                elif path == "/api/backup/download":
                    from .backup import backup_file
                    query=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                    file=backup_file(profile_dir(),query.get("file",[""])[0])
                    body=file.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type","application/zip")
                    self.send_header("Content-Disposition","attachment; filename="+file.name)
                    self.send_header("X-Content-Type-Options","nosniff")
                    self.send_header("Cache-Control","no-store")
                    self.send_header("Content-Length",str(len(body)))
                    self.end_headers();self.wfile.write(body)
                elif path == "/api/devices/autoadd":
                    self._json({"success":True,"data":autoadd.status() if autoadd else {"running":False,"phase":"idle","results":[]}})
                elif path == "/api/discovery":self._json({"success":True,"data":discovery.snapshot() if discovery else {"running":False,"items":[],"errors":["Serviço indisponível"]}})
                elif path == "/api/db/health":
                    check=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("check",["0"])[0]=="1"
                    self._json({"success":True,"data":db.health(check=check)})
                elif path == "/api/queries":
                    query=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                    self._json({"success":True,"data":sources.queries.status(query.get("node",[None])[0])})
                elif path == "/api/tasks":
                    from .task_status import snapshot
                    self._json(snapshot(db,sources,automation))
                elif path == "/api/automation":
                    self._json(automation.overview() if automation else
                               {"success":False,"error":"Automação não disponível"})
                elif path == "/api/activity":
                    self._json({"success":True,"sources":sources.snapshot()})
                elif path == "/api/device/config":
                    query=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                    source_id=int(query.get("source_id",[0])[0])
                    self._json({"success":True,"data":sources.radio_config(source_id)})
                elif path == "/api/update/latest":
                    self._json(updates.status() if updates else latest_release())
                elif path == "/api/update/progress":
                    self._json(updater.status() if updater else {"success":False,"error":"Atualizador indisponível"})
                elif path == "/api/update/notice":
                    self._json(updater.notice() if updater else {"success":True,"notice":None})
                elif path == "/api/system/settings":
                    self._json({"success":True,"settings":db.system_settings()})
                elif path == "/api/preferences/map":
                    self._json({"success":True,"settings":db.ui_preferences()})
                elif path == "/api/retention":self._json({"success":True,"data":db.retention()})
                elif path == "/api/stats":self._json({"success":True,"counts":db.stats(),"connections":sources.snapshot()})
                elif path == "/api/analytics":
                    query=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                    filters={k:v[0] for k,v in query.items()}
                    self._json(calculate(db,filters,sources.snapshot()))
                else:self._error("Rota não encontrada",404)
            except (ValueError,LookupError) as exc:
                self._error(exc,400)
            except Exception as exc:
                LOG.exception("Erro GET %s",path)
                self._error(exc,500)

        def do_POST(self):
            if not self._local_host():return self._error("Host não autorizado",403)
            path=urllib.parse.urlsplit(self.path).path
            try:
                if self.headers.get("X-PT2VHF-CSRF","") != csrf:
                    return self._error("Token de segurança inválido",403)
                origin=self.headers.get("Origin","")
                host=self.headers.get("Host","")
                if origin and urllib.parse.urlparse(origin).netloc!=host:
                    return self._error("Origem não autorizada",403)
                if path == "/api/backup/restore":
                    # #166: o .zip vem como corpo bruto (não cabe no limite de JSON).
                    if "application/zip" not in self.headers.get("Content-Type",""):
                        return self._error("Envie o arquivo .zip do backup",415)
                    from .backup import stage_restore
                    meta=stage_restore(profile_dir(),self.rfile,int(self.headers.get("Content-Length","0")))
                    return self._json({"success":True,"pending":meta})
                if "application/json" not in self.headers.get("Content-Type",""):
                    return self._error("Content-Type application/json necessário",415)
                size=int(self.headers.get("Content-Length","0"))
                if not 1<=size<=20000:return self._error("Corpo inválido",413)
                payload=json.loads(self.rfile.read(size).decode("utf-8"))
                if not isinstance(payload,dict):return self._error("JSON inválido")
                if path == "/api/window/ready":
                    if ready_event:ready_event.set()
                    self._json({"success":True})
                elif path == "/api/report/pdf":
                    from .reporting import generate
                    body=generate(db,payload,sources.snapshot())
                    self.send_response(200)
                    self.send_header("Content-Type","application/pdf")
                    self.send_header("Content-Disposition","attachment; filename=PT2VHF-Mesh-Analyzer-Relatorio.pdf")
                    self.send_header("X-Content-Type-Options","nosniff")
                    self.send_header("Cache-Control","no-store")
                    self.send_header("Content-Length",str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                elif path == "/api/sources/save":
                    existing_id=int(payload.get("id") or 0)
                    existing=db.source(existing_id) if existing_id else None
                    obj=db.upsert_source(payload)
                    if existing_id:sources.disconnect(existing_id)
                    if obj["enabled"]:sources.connect(obj["id"])
                    self._json({"success":True,"source":obj})
                elif path == "/api/sources/enable":
                    source_id=int(payload["id"])
                    src=db.source(source_id)
                    if not src:raise ValueError("Fonte não encontrada")
                    src["enabled"]=bool(payload.get("enabled"))
                    obj=db.upsert_source(src)
                    if obj["enabled"]:sources.connect(source_id)
                    else:sources.disconnect(source_id)
                    self._json({"success":True,"source":obj})
                elif path == "/api/radios/activate":
                    self._json({"success":True,"data":sources.activate(payload["id"])})
                elif path == "/api/devices/accept":
                    if not watcher:raise ValueError("Detecção automática indisponível")
                    self._json(watcher.accept(str(payload.get("id",""))))
                elif path == "/api/devices/pair":
                    if not watcher:raise ValueError("Detecção automática indisponível")
                    self._json(watcher.pair(str(payload.get("id","")),str(payload.get("pin",""))))
                elif path == "/api/devices/cancel":
                    if not watcher:raise ValueError("Detecção automática indisponível")
                    self._json(watcher.cancel(str(payload.get("id",""))))
                elif path == "/api/devices/undo":
                    if not watcher:raise ValueError("Detecção automática indisponível")
                    self._json(watcher.undo(str(payload.get("id",""))))
                elif path == "/api/devices/autoadd/cancel":
                    if not autoadd:raise ValueError("Adição automática indisponível")
                    self._json({"success":True,"data":autoadd.cancel()})
                elif path == "/api/devices/dismiss":
                    if not watcher:raise ValueError("Detecção automática indisponível")
                    self._json(watcher.dismiss(str(payload.get("id","")),payload.get("never") is True))
                elif path == "/api/devices/autoadd/start":
                    if not autoadd:raise ValueError("Adição automática indisponível")
                    self._json({"success":True,"data":autoadd.start(first_run=payload.get("first_run") is True)})
                elif path == "/api/discovery/start":
                    if not discovery:raise ValueError("Descoberta indisponível")
                    self._json({"success":True,"data":discovery.start()})
                elif path == "/api/sources/reconnect":
                    result=sources.restart(payload["id"])
                    self._json({"success":True,"data":result})
                elif path == "/api/sources/delete":
                    source_id=int(payload["id"])
                    sources.disconnect(source_id)
                    db.delete_source(source_id)
                    self._json({"success":True})
                elif path == "/api/retention":
                    result=db.set_retention(payload)
                    self._json({"success":True,"retention":result})
                elif path == "/api/alerts/config":
                    if not alerts:raise ValueError("Alertas indisponíveis")
                    self._json({"success":True,"config":alerts.save(payload)})
                elif path == "/api/channels/save":
                    active=sources.active_radio()
                    if active is None:raise ValueError("Conecte um rádio para editar os canais")
                    self._json(sources.set_channel(active,payload.get("index"),payload.get("name",""),
                        payload.get("enabled") is not False,payload.get("psk","keep"),payload.get("psk_value","")))
                elif path == "/api/msgauto/config":
                    self._json({"success":True,"config":msgauto.save_config(payload)})
                elif path == "/api/msgauto/schedule":
                    self._json({"success":True,"schedule":msgauto.save_schedule(payload)})
                elif path == "/api/msgauto/schedule/delete":
                    self._json(msgauto.delete_schedule(payload["id"]))
                elif path == "/api/msgauto/reply":
                    self._json({"success":True,"reply":msgauto.save_reply(payload)})
                elif path == "/api/msgauto/reply/delete":
                    self._json(msgauto.delete_reply(payload["id"]))
                elif path == "/api/survey/link":
                    self._json({"success":True,"data":survey_link(payload)})
                elif path == "/api/meshcore/action":
                    self._json({"success":True,"data":meshcore_action(payload)})
                elif path == "/api/meshcore/automation":
                    auto=getattr(sources,"meshcore_auto",None)
                    if not auto:raise ValueError("Coleta MeshCore indisponível")
                    if "password" in payload:
                        auto.set_password(payload.get("node_num"),payload.get("password"))
                    else:auto.save(payload)
                    self._json({"success":True,**auto.overview()})
                elif path == "/api/meshcore/automation/run":
                    auto=getattr(sources,"meshcore_auto",None)
                    if not auto:raise ValueError("Coleta MeshCore indisponível")
                    self._json({"success":True,"result":auto.tick()})
                elif path == "/api/survey/best":
                    from . import survey
                    self._json({"success":True,"data":survey.best_points(elevations(),payload.get("polygon"),
                        payload.get("reference"),payload.get("count") or 10)})
                elif path == "/api/survey/save":
                    from . import survey
                    self._json({"success":True,"item":survey.save_survey(db,payload),"saved":survey.saved_surveys(db)})
                elif path == "/api/survey/delete":
                    from . import survey
                    survey.delete_survey(db,payload.get("id"))
                    self._json({"success":True,"saved":survey.saved_surveys(db)})
                elif path == "/api/survey/pdf":
                    from . import survey, survey_pdf
                    name=str(payload.get("name") or "")[:60]
                    if payload.get("kind")=="link":
                        body=survey_pdf.link_pdf(survey_link(payload),name)
                        return self._pdf(body,"PT2VHF-Analise-de-Enlace.pdf")
                    result=survey.best_points(elevations(),payload.get("polygon"),payload.get("reference"),payload.get("count") or 10)
                    links=[]
                    for item in (payload.get("links") or [])[:20]:
                        links.append({"rank":item.get("rank"),"target":str(item.get("target") or "B")[:40],"link":survey_link(item)})
                    body=survey_pdf.survey_pdf(result,name,links,survey_pdf.nearby_nodes(db,result))
                    return self._pdf(body,"PT2VHF-Survey-Melhor-Ponto.pdf")
                elif path == "/api/msgauto/preview":
                    sample={"from_node":None,"channel":0,"text":str(payload.get("command",""))}
                    self._json({"success":True,"text":msgauto.render(str(payload.get("template",""))[:400],sample)})
                elif path == "/api/alerts/read":
                    if not alerts:raise ValueError("Alertas indisponíveis")
                    self._json(alerts.mark_read())
                elif path == "/api/alerts/test":
                    if not alerts:raise ValueError("Alertas indisponíveis")
                    self._json(alerts.test(str(payload.get("channel",""))))
                elif path == "/api/backup/export":
                    from .backup import export_backup
                    self._json({"success":True,"backup":export_backup(db,profile_dir())})
                elif path == "/api/backup/cancel":
                    from .backup import cancel_restore
                    cancel_restore(profile_dir());self._json({"success":True})
                elif path == "/api/backup/restart":
                    if not restart:raise ValueError("Reinício indisponível")
                    restart();self._json({"success":True})
                elif path == "/api/db/backup":
                    self._json({"success":True,"backup":db.backup()})
                elif path == "/api/nodes/delete":
                    self._json(sources.node_deletion.delete(payload.get("source_id"),
                        payload.get("node_num"), payload.get("confirmed")))
                elif path == "/api/nodes/friendly":
                    self._json({"success":True,"node":db.set_node_friendly_name(
                        payload.get("node_num"),payload.get("friendly_name",""))})
                elif path == "/api/nodes/favorite":
                    self._json(sources.set_app_favorite(payload.get("node_num"),payload.get("is_favorite")))
                elif path == "/api/favorites/sync":
                    active=sources.active_radio()
                    if active is None:raise ValueError("Conecte um rádio para sincronizar favoritos")
                    changed=sources.sync_favorites_from_radio(active,max_commands=20)
                    self._json({"success":True,"source_id":active,"imported":changed,
                                "state":sources.snapshot().get(str(active),{})})
                elif path == "/api/retention/cleanup":
                    self._json({"success":True,"removed":db.cleanup()})
                elif path == "/api/system/settings":
                    data=db.set_system_settings(payload)
                    if updates:updates.changed()
                    self._json({"success":True,"settings":data})
                elif path == "/api/preferences/map":
                    self._json({"success":True,"settings":db.save_ui_preferences(payload)})
                elif path == "/api/update/check":
                    self._json(updates.check(force=True) if updates else latest_release(force=True))
                elif path == "/api/update/prepare":
                    if not updater:raise ValueError("Atualização interna indisponível")
                    self._json(updater.start(str(payload.get("version") or "")))
                elif path == "/api/update/cancel":
                    if not updater:raise ValueError("Atualizador indisponível")
                    self._json(updater.cancel())
                elif path == "/api/update/install":
                    if not updater or not shutdown:raise ValueError("Atualização interna indisponível")
                    self._json(updater.launch())
                    # The external updater only proceeds once every handle closes.
                    threading.Timer(0.8,shutdown).start()
                elif path == "/api/update/ack":
                    self._json(updater.dismiss() if updater else {"success":True})
                elif path == "/api/device/apply":
                    result=sources.update_device(payload.get("source_id"),
                            payload.get("revision"),payload.get("changes"))
                    self._json(result)
                elif path == "/api/device/lora":
                    result=sources.update_lora(payload.get("source_id"),payload.get("revision"),
                                               payload.get("changes"))
                    self._json(result)
                elif path == "/api/queries/send":
                    result=sources.queries.start(payload.get("source_id"),payload.get("node"),payload.get("kind"),payload.get("channel",0))
                    self._json({"success":True,"data":result},201)
                elif path == "/api/automation/settings":
                    if not automation:raise ValueError("Automação indisponível")
                    self._json({"success":True,"config":automation.save(payload)})
                elif path == "/api/automation/run":
                    if not automation:raise ValueError("Automação indisponível")
                    self._json({"success":True,"result":automation.tick(
                        dry_run=payload.get("simulate") is True)})
                elif path == "/api/messages/send":
                    result=sources.send_text(payload.get("source_id"),payload.get("to_node"),payload.get("text"),payload.get("channel",0))
                    self._json(result,201)
                else:self._error("Operação não encontrada",404)
            except (ValueError,LookupError,TypeError) as exc:
                self._error(exc,400)
            except RuntimeError as exc:
                LOG.exception("Falha operacional no POST %s",path)
                self._error(str(exc)[:240] or "Falha operacional",500)
            except Exception as exc:
                LOG.exception("Falha no POST %s",path)
                self._error("Falha interna: "+type(exc).__name__,500)
    return Handler


def run(host="127.0.0.1", port=8789, launch_browser=None, database=None,
        desktop=True):
    """A private loopback backend serves the desktop WebView2 window."""
    data=profile_dir()
    from .backup import apply_pending_restore
    restored=apply_pending_restore(database or (data/"mesh-analyzer.sqlite3"))  # #166
    db=Database(database or (data/"mesh-analyzer.sqlite3"))
    if restored:db.log("Restauração de backup: "+restored.get("status",""),
                       "info" if restored.get("status")=="applied" else "error")
    db.recover_node_roles()
    drivers=SourceManager(db)
    updates=ReleaseMonitor(db)
    from .updater import UpdateManager
    updater=UpdateManager(data,updates)
    from .automations import NodeEnrichment
    automation=NodeEnrichment(db,drivers)
    from .discovery import DeviceDiscovery
    discovery=DeviceDiscovery()
    from .device_detection import AutoAdd, DeviceWatcher
    watcher=DeviceWatcher(db,drivers)
    autoadd=AutoAdd(db,drivers,watcher)
    from .alerts import AlertCenter
    alerts=AlertCenter(db,drivers)
    from .msgauto import MessageAutomation
    msgauto=MessageAutomation(db,drivers)
    from .meshcore_data import MeshCoreAutomation
    drivers.meshcore_auto=MeshCoreAutomation(db,drivers)
    server=None
    done=threading.Event()
    try:
        drivers.start()
        # Replay previously archived protobuf/JSON once in a bounded background
        # migration. The record key prevents the same packet from replaying twice.
        from .topology import extract_topology
        def topology_migration():
            try:
                info=db.reprocess_archived_topology(extract_topology)
                db.log("Reprocessamento histórico de topologia: "+
                       str(info["processed"])+" pacotes, "+
                       str(info["candidate_edges"])+" relações analisadas")
            except Exception:
                LOG.exception("Falha ao reprocessar topologia histórica")
        replay=threading.Thread(target=topology_migration,
                                name="topology-backfill",daemon=True)
        replay.start()
        def passive_migration():
            try:
                processed=observed=0
                while not done.is_set():
                    result=db.reprocess_archived_communications(limit=1200)
                    processed+=result["processed"]
                    observed+=result["communications"]
                    if not result["remaining"]:break
                    # Keep interactive reception responsive on large databases.
                    time.sleep(0.025)
                db.log("Comunicações passivas recuperadas do histórico: "+
                       str(processed)+" pacotes analisados; "+
                       str(observed)+" registros de fluxo.")
            except Exception:
                LOG.exception("Falha ao recuperar comunicações históricas")
        passive_replay=threading.Thread(target=passive_migration,
                      name="passive-traffic-backfill",daemon=True)
        passive_replay.start()
        csrf=secrets.token_urlsafe(32)
        doc=Path(__file__).with_name("ui.html").read_text(encoding="utf-8")
        # One image source shared by HTML logo and favicon, with no external
        # request. PyInstaller bundles the exact same image used to build its
        # icon resource and the Inno Setup executable/desktop shortcuts.
        import base64
        from .branding import brand_image_data_uri
        doc=doc.replace("__PT2VHF_MESH_LOGO__",brand_image_data_uri())
        ui_ready_event=threading.Event()
        shutdown_requested=threading.Event()
        shutdown_started=threading.Event()
        shutdown_complete=threading.Event()
        shutdown_mutex=threading.Lock()
        def request_shutdown():
            # Calling webview.destroy() from a Timer thread did not reliably
            # terminate the desktop loop. The coordinator below shuts down
            # every resource before ending this *specific* process.
            shutdown_requested.set()
        def clean_up_once():
            with shutdown_mutex:
                if shutdown_complete.is_set():return
                done.set()
                updates.stop()
                watcher.close()
                alerts.close()
                msgauto.close()
                drivers.meshcore_auto.close()
                automation.close()
                if server:
                    server.shutdown()
                    server.server_close()
                drivers.close()
                for t in list(drivers._threads.values()):
                    if t.is_alive() and t is not threading.current_thread():t.join(timeout=2)
                replay.join(timeout=4)
                passive_replay.join(timeout=4)
                db.close()
                shutdown_complete.set()
        def update_shutdown_coordinator():
            shutdown_requested.wait()
            shutdown_started.set()
            try:
                # Stop accepting new requests, close radio/SQLite *before*
                # the updater sees our PID exit. The windowed main thread can
                # remain in webview.start(), hence an explicit local self-exit
                # is required once all managed resources are closed.
                clean_up_once()
                LOG.warning("Update shutdown complete, exiting only Mesh Analyzer PID=%s",os.getpid())
                os._exit(0)
            except Exception:
                LOG.exception("Update shutdown incomplete; keeping current version running")
        threading.Thread(target=update_shutdown_coordinator,
                         name="update-clean-shutdown",daemon=True).start()
        def request_restart():
            """#166: reabre o app (aplicando a restauração pendente) e encerra este processo."""
            from .backup import restart_command
            from .updater import restart_environment
            env=restart_environment();env["PT2VHF_RESTARTED"]="1"
            command=restart_command()+updater.restart_arguments
            if in_container():
                # O container reinicia o processo (restart: unless-stopped).
                threading.Timer(0.5,request_shutdown).start();return
            import subprocess
            kwargs={"env":env,"cwd":os.getcwd()}
            if os.name=="nt":kwargs["creationflags"]=getattr(subprocess,"DETACHED_PROCESS",0)|getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0)
            else:kwargs["start_new_session"]=True
            subprocess.Popen(command,**kwargs)
            threading.Timer(0.5,request_shutdown).start()
        handler=build_handler(db,drivers,csrf,doc,updates,updater,request_shutdown,ui_ready_event,automation,discovery,watcher,autoadd,request_restart,alerts,msgauto)
        for attempt in range(60):
            try:
                server=ThreadingHTTPServer((host,int(port)),handler)
                break
            except OSError:
                # Reaberto pelo próprio app: espera a instância anterior liberar a porta.
                if not os.environ.get("PT2VHF_RESTARTED") or attempt==59:raise
                time.sleep(0.5)
        server.daemon_threads=True
        address="http://127.0.0.1:"+str(server.server_address[1])
        updater.health_url=address+"/health"
        updater.restart_arguments=['--data-dir',str(data),'--port',str(server.server_address[1]),'--no-browser']
        if not desktop:updater.restart_arguments.append('--headless')
        LOG.info("PT2VHF Mesh Analyzer v%s — %s",__version__,address)
        db.log("Aplicação iniciada v"+__version__)
        def janitor():
            while not done.wait(3600):
                try:db.cleanup()
                except Exception:LOG.exception("Falha no job de retenção")
        threading.Thread(target=janitor,name="retention-cleaner",daemon=True).start()
        updates.start()
        alerts.start()
        msgauto.start()
        drivers.meshcore_auto.start()
        # #149: monitoramento de rádios novos só com interface (não em testes headless).
        if desktop and not os.environ.get("PT2VHF_DISABLE_AUTODETECT"):
            watcher.start()
            # #162: sem nenhuma conexão, procura e conecta o rádio antes do aviso
            # "Configure sua primeira conexão" (USB primeiro).
            if not db.sources():
                autoadd.start(first_run=True)
        server_thread=threading.Thread(target=server.serve_forever,
             kwargs={"poll_interval":0.3},name="mesh-http",daemon=True)
        server_thread.start()
        automation.start()
        open_browser=(db.system_settings()["open_browser_on_start"]
                     if launch_browser is None else launch_browser)
        if open_browser:
            webbrowser.open(address)
        browser_mode=False
        if desktop:
            try:
                from .desktop import open_desktop_window
                open_desktop_window(address, data)
            except Exception as exc:
                LOG.exception("Não foi possível iniciar a janela desktop")
                if sys.platform.startswith("linux"):
                    # Linux packages do not bundle GTK/Qt: use the default
                    # browser and keep serving until the process is stopped.
                    LOG.warning("Abrindo %s no navegador padrão", address)
                    if not open_browser:webbrowser.open(address)
                    browser_mode=True
                # Windowed PyInstaller EXEs have no console. Show a visible
                # diagnosis rather than silently redirecting to a browser.
                if sys.platform == "win32":
                    try:
                        import ctypes
                        ctypes.windll.user32.MessageBoxW(
                            None, str(exc)[:600],
                            "PT2VHF Mesh Analyzer — Falha na interface", 0x10)
                    except Exception:pass
                if not browser_mode:raise
        if not desktop or browser_mode:
            # #160: "docker stop" envia SIGTERM; encerra fechando rádio e SQLite.
            def stop_requested(signum,frame):raise KeyboardInterrupt
            if threading.current_thread() is threading.main_thread():
                signal.signal(signal.SIGTERM,stop_requested)
            try:
                while server_thread.is_alive():
                    server_thread.join(timeout=0.5)
            except KeyboardInterrupt:
                pass
        return 0
    finally:
        # Normal close and update close share the same teardown. The
        # coordinator may already have completed it.
        if 'clean_up_once' in locals():
            clean_up_once()
        else:
            done.set()
            updates.stop()
            watcher.close()
            alerts.close()
            msgauto.close()
            drivers.meshcore_auto.close()
            automation.close()
            if server:
                server.shutdown()
                server.server_close()
            drivers.close()
            db.close()


def main(argv=None):
    parser=argparse.ArgumentParser(description="PT2VHF Mesh Analyzer v"+__version__)
    container=in_container()
    parser.add_argument("--host",default=os.environ.get("PT2VHF_HOST","127.0.0.1"),
                        help="Interface local; escuta externa não disponível")
    parser.add_argument("--port",type=int,default=int(os.environ.get("PT2VHF_PORT") or 8789))
    parser.add_argument("--browser",action="store_true",help="Abrir navegador externo adicional")
    parser.add_argument("--no-browser",action="store_true",help="Não abrir navegador externo")
    parser.add_argument("--headless",action="store_true",
                        help="Executar sem janela desktop (automação/testes)")
    parser.add_argument("--data-dir",default=None)
    opts=parser.parse_args(argv)
    # #160: no container o servidor escuta em 0.0.0.0 *dentro* do container
    # para o mapeamento de porta funcionar; a checagem de Host (só localhost)
    # e o token CSRF continuam valendo, então a rede local segue bloqueada.
    allowed=("127.0.0.1","localhost","::1")+(("0.0.0.0",) if container else ())
    if opts.host not in allowed:
        parser.error("Acesso LAN permanece bloqueado até existir autenticação.")
    if opts.browser and opts.no_browser:
        parser.error("Escolha apenas --browser ou --no-browser")
    if opts.data_dir:os.environ["PT2VHF_MESH_DATA"]=opts.data_dir
    logging.basicConfig(level=logging.WARNING,format="%(levelname)s: %(message)s")
    opening=True if opts.browser else False if opts.no_browser else None
    return run(opts.host,opts.port,opening,desktop=not opts.headless)

if __name__=="__main__":raise SystemExit(main())
