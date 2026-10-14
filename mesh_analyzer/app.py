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
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__
from .database import Database, profile_dir
from .transports import SourceManager, available_serial_ports

LOG = logging.getLogger("pt2vhf.mesh")


def build_handler(db:Database, sources:SourceManager, csrf:str, doc:str):
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

        def do_GET(self):
            path=urllib.parse.urlsplit(self.path).path
            try:
                if path in ("/","/mapa","/nos","/trafego","/mensagens","/estatisticas","/automacoes","/configuracoes","/ajuda"):
                    content=doc.replace("__CSRF_TOKEN__",html.escape(csrf,quote=True)).encode("utf-8")
                    self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8")
                    self.send_header("X-Frame-Options","DENY")
                    self.send_header("Content-Security-Policy","frame-ancestors 'none'")
                    self.send_header("Cache-Control","no-cache")
                    self.send_header("Content-Length",str(len(content)));self.end_headers();self.wfile.write(content)
                elif path == "/health":self._json({"success":True,"version":__version__,"database":"ok"})
                elif path == "/api/state":self._json({"success":True,"version":__version__,"sources":db.sources(),"connections":sources.snapshot(),"counts":db.stats(),"retention":db.retention()})
                elif path == "/api/nodes":self._json({"success":True,"data":db.node_rows()})
                elif path == "/api/packets":self._json({"success":True,"data":db.packet_rows()})
                elif path == "/api/messages":self._json({"success":True,"data":db.message_rows()})
                elif path == "/api/links":self._json({"success":True,"data":db.link_rows()})
                elif path == "/api/events":self._json({"success":True,"data":db.event_rows()})
                elif path == "/api/ports":self._json({"success":True,"data":available_serial_ports()})
                elif path == "/api/retention":self._json({"success":True,"data":db.retention()})
                elif path == "/api/stats":self._json({"success":True,"counts":db.stats(),"connections":sources.snapshot()})
                else:self._error("Rota não encontrada",404)
            except Exception as exc:
                LOG.exception("Erro GET %s",path)
                self._error(exc,500)

        def do_POST(self):
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
                if path == "/api/sources/save":
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
                elif path == "/api/sources/delete":
                    source_id=int(payload["id"])
                    sources.disconnect(source_id)
                    db.delete_source(source_id)
                    self._json({"success":True})
                elif path == "/api/retention":
                    result=db.set_retention(payload)
                    self._json({"success":True,"retention":result})
                elif path == "/api/retention/cleanup":
                    self._json({"success":True,"removed":db.cleanup()})
                elif path == "/api/messages/send":
                    result=sources.send_text(payload.get("source_id"),payload.get("to_node"),payload.get("text"),payload.get("channel",0))
                    self._json(result,201)
                else:self._error("Operação não encontrada",404)
            except (ValueError,KeyError,TypeError) as exc:
                self._error(exc,400)
            except Exception as exc:
                LOG.exception("Falha no POST %s",path)
                self._error("Falha interna: "+type(exc).__name__,500)
    return Handler


def run(host="127.0.0.1",port=8789,launch_browser=True,database=None):
    data=profile_dir()
    db=Database(database or (data/"mesh-analyzer.sqlite3"))
    drivers=SourceManager(db)
    try:
        drivers.start()
        csrf=secrets.token_urlsafe(32)
        resource=Path(__file__).with_name("ui.html")
        doc=resource.read_text(encoding="utf-8")
        server=ThreadingHTTPServer((host,int(port)),build_handler(db,drivers,csrf,doc))
        server.daemon_threads=True
        server.allow_reuse_address=True
        address="http://127.0.0.1:"+str(server.server_address[1])
        print("PT2VHF Mesh Analyzer v"+__version__+" — "+address,flush=True)
        db.log("Aplicação iniciada v"+__version__)
        def janitor():
            while not done.wait(3600):
                try:db.cleanup()
                except Exception:LOG.exception("Falha no job de retenção")
        done=threading.Event()
        worker=threading.Thread(target=janitor,name="retention-cleaner",daemon=True)
        worker.start()
        if launch_browser:
            threading.Timer(0.7,lambda:webbrowser.open(address)).start()
        try:server.serve_forever(poll_interval=.5)
        except KeyboardInterrupt:pass
        finally:
            done.set();server.server_close()
        return 0
    finally:
        drivers.close()
        db.close()


def main(argv=None):
    parser=argparse.ArgumentParser(description="PT2VHF Mesh Analyzer v0.1.0")
    parser.add_argument("--host",default="127.0.0.1",help="Interface de escuta (padrão: apenas localhost)")
    parser.add_argument("--port",type=int,default=8789)
    parser.add_argument("--no-browser",action="store_true")
    parser.add_argument("--data-dir",default=None)
    opts=parser.parse_args(argv)
    if opts.host not in ("127.0.0.1","localhost","::1"):
        parser.error("Por segurança, a v0.1.0 aceita apenas localhost; publicação LAN virá com autenticação própria.")
    if opts.data_dir:os.environ["PT2VHF_MESH_DATA"]=opts.data_dir
    logging.basicConfig(level=logging.WARNING,format="%(levelname)s: %(message)s")
    return run(opts.host,opts.port,not opts.no_browser)

if __name__=="__main__":raise SystemExit(main())