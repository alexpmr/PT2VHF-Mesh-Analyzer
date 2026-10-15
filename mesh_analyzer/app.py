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
                "interval_minutes":minutes,"error":self._error}

    def _loop(self):
        while not self._stop.is_set():
            delay=max(0,(self._at+self.db.system_settings()["update_minutes"]*60)-time.time()) if self._at else 1
            self._wake.wait(delay)
            self._wake.clear()
            if self._stop.is_set():break
            due=not self._at or time.time()-self._at>=self.db.system_settings()["update_minutes"]*60
            if due:self.check(force=True)


def build_handler(db:Database, sources:SourceManager, csrf:str, doc:str, updates=None, updater=None, shutdown=None, ready_event=None, automation=None):
    class Handler(BaseHTTPRequestHandler):
        server_version="PT2VHF-Mesh-Analyzer/" + __version__
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
                elif path == "/health":self._json({"success":True,"version":__version__,"database":"ok","ui_ready":bool(ready_event and ready_event.is_set())})
                elif path == "/api/state":self._json({"success":True,"version":__version__,"sources":db.sources(),"connections":sources.snapshot(),"counts":db.stats(),"retention":db.retention(),"system":db.system_settings()})
                elif path == "/api/nodes":self._json({"success":True,"data":db.node_rows()})
                elif path == "/api/nodes/hops":self._json({"success":True,"data":db.node_hop_rows()})
                elif path == "/api/nodes/sources":
                    self._json({"success":True,"data":db.node_source_rows()})
                elif path == "/api/topology/diagnostics":
                    query=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                    source=query.get("source_id",[None])[0]
                    self._json({"success":True,"data":db.topology_diagnostics(source)})
                elif path == "/api/packets":self._json({"success":True,"data":db.packet_rows()})
                elif path == "/api/messages":self._json({"success":True,"data":db.message_rows()})
                elif path == "/api/links":self._json({"success":True,"data":db.link_rows()})
                elif path == "/api/communications":
                    self._json({"success":True,"data":db.communication_rows()})
                elif path == "/api/waypoints":self._json({"success":True,"data":db.waypoint_rows()})
                elif path == "/api/events":self._json({"success":True,"data":db.event_rows()})
                elif path == "/api/ports":self._json({"success":True,"data":available_serial_ports()})
                elif path == "/api/db/health":
                    check=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("check",["0"])[0]=="1"
                    self._json({"success":True,"data":db.health(check=check)})
                elif path == "/api/queries":
                    query=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                    self._json({"success":True,"data":sources.queries.status(query.get("node",[None])[0])})
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
                elif path == "/api/db/backup":
                    self._json({"success":True,"backup":db.backup()})
                elif path == "/api/nodes/friendly":
                    self._json({"success":True,"node":db.set_node_friendly_name(
                        payload.get("node_num"),payload.get("friendly_name",""))})
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
            except (ValueError,KeyError,TypeError) as exc:
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
    db=Database(database or (data/"mesh-analyzer.sqlite3"))
    drivers=SourceManager(db)
    updates=ReleaseMonitor(db)
    from .updater import UpdateManager
    updater=UpdateManager(data,updates)
    from .automations import NodeEnrichment
    automation=NodeEnrichment(db,drivers)
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
        server=ThreadingHTTPServer((host,int(port)),
                                  build_handler(db,drivers,csrf,doc,updates,updater,request_shutdown,ui_ready_event,automation))
        server.daemon_threads=True
        address="http://127.0.0.1:"+str(server.server_address[1])
        LOG.info("PT2VHF Mesh Analyzer v%s — %s",__version__,address)
        db.log("Aplicação iniciada v"+__version__)
        def janitor():
            while not done.wait(3600):
                try:db.cleanup()
                except Exception:LOG.exception("Falha no job de retenção")
        threading.Thread(target=janitor,name="retention-cleaner",daemon=True).start()
        updates.start()
        server_thread=threading.Thread(target=server.serve_forever,
             kwargs={"poll_interval":0.3},name="mesh-http",daemon=True)
        server_thread.start()
        automation.start()
        open_browser=(db.system_settings()["open_browser_on_start"]
                     if launch_browser is None else launch_browser)
        if open_browser:
            webbrowser.open(address)
        if desktop:
            try:
                from .desktop import open_desktop_window
                open_desktop_window(address, data)
            except Exception as exc:
                LOG.exception("Não foi possível iniciar a janela desktop")
                # Windowed PyInstaller EXEs have no console. Show a visible
                # diagnosis rather than silently redirecting to a browser.
                if sys.platform == "win32":
                    try:
                        import ctypes
                        ctypes.windll.user32.MessageBoxW(
                            None, str(exc)[:600],
                            "PT2VHF Mesh Analyzer — Falha na interface", 0x10)
                    except Exception:pass
                raise
        else:
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
            automation.close()
            if server:
                server.shutdown()
                server.server_close()
            drivers.close()
            db.close()


def main(argv=None):
    parser=argparse.ArgumentParser(description="PT2VHF Mesh Analyzer v"+__version__)
    parser.add_argument("--host",default="127.0.0.1",
                        help="Interface local; escuta externa não disponível")
    parser.add_argument("--port",type=int,default=8789)
    parser.add_argument("--browser",action="store_true",help="Abrir navegador externo adicional")
    parser.add_argument("--no-browser",action="store_true",help="Não abrir navegador externo")
    parser.add_argument("--headless",action="store_true",
                        help="Executar sem janela desktop (automação/testes)")
    parser.add_argument("--data-dir",default=None)
    opts=parser.parse_args(argv)
    if opts.host not in ("127.0.0.1","localhost","::1"):
        parser.error("Acesso LAN permanece bloqueado até existir autenticação.")
    if opts.browser and opts.no_browser:
        parser.error("Escolha apenas --browser ou --no-browser")
    if opts.data_dir:os.environ["PT2VHF_MESH_DATA"]=opts.data_dir
    logging.basicConfig(level=logging.WARNING,format="%(levelname)s: %(message)s")
    opening=True if opts.browser else False if opts.no_browser else None
    return run(opts.host,opts.port,opening,desktop=not opts.headless)

if __name__=="__main__":raise SystemExit(main())
