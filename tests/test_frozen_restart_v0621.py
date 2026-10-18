"""Windows end-to-end: old frozen app -> real PowerShell runner -> fresh onefile app.

Uses a tiny frozen health-service fixture in place of the GUI/radio application.
It deliberately inherits the old PyInstaller environment, with the SAME exe path.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from mesh_analyzer.updater import RUNNER_PS

FIXTURE = r'''
import http.server, json, os, subprocess, sys, time
from pathlib import Path
if len(sys.argv)>1 and sys.argv[1]=='parent':
    plan=Path(sys.argv[2]); data=json.loads(plan.read_text())
    data['parent_pid']=os.getpid()
    data['old_mei']=sys._MEIPASS
    plan.write_text(json.dumps(data))
    subprocess.Popen(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
        '-File',str(plan.parent/'runner.ps1'),'-Plan',str(plan)],
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,close_fds=True)
    sys.exit(0)
if len(sys.argv)>1 and sys.argv[1]=='launcher':
    # Simulate a onefile/bootstrap launcher exiting normally, while the
    # actual WebView/API successor continues starting in a separate process.
    fresh=dict(os.environ)
    fresh['PYINSTALLER_RESET_ENVIRONMENT']='1'
    subprocess.Popen([sys.executable,'server'],env=fresh,
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),close_fds=True)
    sys.exit(0)
root=Path(os.environ['MESH_FIXTURE_ROOT'])
if len(sys.argv)>1 and sys.argv[1]=='server':
    time.sleep(1.5)

(root/'child.json').write_text(json.dumps({'mei':sys._MEIPASS,'exists':Path(sys._MEIPASS).is_dir()}))
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # Make the exit=0 regression deterministic. A fast new instance can
        # become healthy while the initial PyInstaller bootloader is still
        # cleaning its _MEI folder. Deliberately withhold readiness until the
        # runner has observed and logged that initial launcher exit.
        try:
            runner_log=(root/'update.log').read_text(encoding='utf-8-sig')
        except OSError:
            runner_log=''
        if 'Initial launcher exited with code 0' not in runner_log:
            self.send_response(503)
            self.end_headers()
            return
        body=json.dumps({'version':'0.6.21','success':True,'ui_ready':True,
                         'update_nonce':os.environ.get('PT2VHF_UPDATE_NONCE','')}).encode()
        self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def log_message(self,*args):pass
http.server.HTTPServer(('127.0.0.1',int(os.environ['MESH_FIXTURE_PORT'])),Handler).serve_forever()
'''

@unittest.skipUnless(os.name=='nt','Real frozen restart requires Windows')
class FrozenRestartTests(unittest.TestCase):
    def test_portable_replacement_and_restart_survive_old_mei_cleanup(self):
        with tempfile.TemporaryDirectory(prefix='mesh restart ') as folder:
            root=Path(folder); src=root/'fixture.py'; src.write_text(FIXTURE)
            build=subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile',
                '--name','MeshRestartFixture','--distpath',str(root/'dist'),
                '--workpath',str(root/'build'),'--specpath',str(root),str(src)],
                capture_output=True,text=True,timeout=180)
            self.assertEqual(build.returncode,0,build.stderr[-3000:])
            target=root/'dist'/'MeshRestartFixture.exe'
            candidate=root/'candidate.exe'; candidate.write_bytes(target.read_bytes())
            (root/'runner.ps1').write_text(RUNNER_PS,encoding='utf-8')
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
            plan=root/'plan.json'; notice=root/'notice.json'
            plan.write_text(json.dumps({'version':'0.6.21','mode':'portable','notes':'fixture',
                'executable':str(target),'candidate':str(candidate),'previous':str(root/'previous.exe'),
                'log':str(root/'update.log'),'notice':str(notice),'runner_ready':str(root/'ready.json'),
                'run_nonce':'fixture-nonce','launch_nonce':'fixture-ready-nonce',
                'restart_arguments':'launcher',
                'health_url':f'http://127.0.0.1:{port}/health'}))
            env={**os.environ,'MESH_FIXTURE_ROOT':str(root),'MESH_FIXTURE_PORT':str(port)}
            child_pid=None
            try:
                old=subprocess.Popen([str(target),'parent',str(plan)],env=env)
                old.wait(timeout=30)
                deadline=time.monotonic()+50
                while time.monotonic()<deadline and not notice.exists():time.sleep(.2)
                # unittest evaluates the failure-message argument even on success.
                # PowerShell may still hold update.log open with exclusive sharing,
                # so never read it unless the notice is actually missing.
                if not notice.exists():
                    try:
                        details=(root/'update.log').read_text(encoding='utf-8',errors='replace')
                    except OSError as exc:
                        details=f'update.log unavailable: {exc}'
                    self.fail('Updater did not write completion notice: '+details)
                result=json.loads(notice.read_text(encoding='utf-8-sig'))
                self.assertEqual(result['status'],'installed',result)
                # The initial launcher has already exited code 0 before the
                # successor's delayed /health becomes ready.
                for attempt in range(15):
                    try:
                        update_log=(root/'update.log').read_text(encoding='utf-8-sig')
                        break
                    except OSError:
                        time.sleep(.2)
                else:
                    self.fail('Could not read the update runner log after completion')
                self.assertIn('Initial launcher exited with code 0',update_log)
                self.assertIn('Updated version confirmed via /health',update_log)
                data=json.loads((root/'child.json').read_text())
                self.assertTrue(data['exists'])
                self.assertNotEqual(data['mei'],json.loads(plan.read_text())['old_mei'])
                self.assertTrue(Path(data['mei']).exists())
            finally:
                # Restrict cleanup to the disposable fixture's exact executable.
                command="Get-Process -Name MeshRestartFixture -ErrorAction SilentlyContinue | Where-Object {$_.Path -eq $env:MESH_FIXTURE_EXE} | Stop-Process -Force"
                subprocess.run(['powershell.exe','-NoProfile','-Command',command],
                    env={**os.environ,'MESH_FIXTURE_EXE':str(target)},capture_output=True,timeout=15)
                time.sleep(.5)
