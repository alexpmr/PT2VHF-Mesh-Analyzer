"""Regression of environment isolation and actual shipped onefile runtime."""
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.request
from mesh_analyzer import __version__
from mesh_analyzer.updater import RUNNER_PS, UpdateManager, restart_environment

class RuntimeTests(unittest.TestCase):
    def test_environment_is_independent_without_mutating_parent(self):
        env={'_PYI_APPLICATION_HOME_DIR':'missing-mei','_PYI_ARCHIVE_FILE':'app.exe',
             '_PYI_PARENT_PROCESS_LEVEL':'1','_MEIPASS2':'old-mei',
             'Path':'normal-path','LOCALAPPDATA':'profile','PT2VHF_MESH_DATA':'custom'}
        clean=restart_environment(env)
        self.assertFalse(any(k.startswith('_PYI_') or k=='_MEIPASS2' for k in clean))
        self.assertEqual(clean['PYINSTALLER_RESET_ENVIRONMENT'],'1')
        self.assertEqual(clean['PT2VHF_MESH_DATA'],'custom')
        self.assertIn('_PYI_ARCHIVE_FILE',env)

    def test_verified_plan_keeps_profile_port_and_attempt_identity(self):
        import hashlib, io, zipfile
        from unittest.mock import patch
        from mesh_analyzer.updater import release_assets
        archive=io.BytesIO()
        with zipfile.ZipFile(archive,'w') as z:z.writestr('PT2VHF-Mesh-Analyzer.exe',b'verified-package')
        package=archive.getvalue();name=release_assets(__version__)['portable']
        expected_sha=hashlib.sha256(package).hexdigest()
        class Response(io.BytesIO):
            @property
            def headers(self):return {'Content-Length':str(len(self.getvalue()))}
        class Monitor:
            _result={"notes":"test","assets":[{
                "name":name,
                "url":"https://www.pt2vhf.com/downloads/mesh-analyzer/"+name,
                "sha256":expected_sha,"size":len(package),
                "counterKey":"win-portable-x64"}]}
        with tempfile.TemporaryDirectory(prefix='custom profile ') as d:
            manager=UpdateManager(d,Monitor(),executable=Path(d)/'versioned.exe')
            manager.health_url='http://127.0.0.1:32145/health'
            manager.restart_arguments=['--data-dir',d,'--port','32145']
            def fetch(request,**kwargs):
                return Response(package)
            with patch('urllib.request.urlopen',side_effect=fetch):manager._download(__version__,'portable',name)
            self.assertEqual(manager.status()['phase'],'verified',manager.status())
            plan=json.loads(Path(manager._plan[1]).read_text())
            self.assertEqual(plan['health_url'],manager.health_url)
            self.assertEqual(plan['restart_arguments'],subprocess.list2cmdline(manager.restart_arguments))
            self.assertEqual(len(plan['launch_nonce']),32)
            self.assertEqual(Path(plan['candidate']).read_bytes(),b'verified-package')

    def test_previous_failure_is_distinguished_from_current_version(self):
        class Monitor:
            def status(self):return {'current':__version__}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'update_complete.json'
            path.write_text(json.dumps({'status':'failed','version':'0.6.26','error':'health timeout'}))
            manager=UpdateManager(d,Monitor(),executable=Path(d)/'app.exe')
            info=manager.notice()['notice']
            self.assertTrue(info['historical'])
            self.assertEqual(info['current_version'],__version__)
            self.assertEqual(info['status'],'failed')
            self.assertTrue(path.exists()) # keep evidence until user dismisses

@unittest.skipUnless(os.name=='nt' and os.environ.get('MESH_PACKAGED_EXE'), 'Post-build Windows packaged EXE')
class PackagedPortableTests(unittest.TestCase):
    def test_real_versioned_portable_replacement_and_health(self):
        with tempfile.TemporaryDirectory(prefix='mesh portable upgrade ') as folder:
            root=Path(folder); profile=root/'perfil com espaços';profile.mkdir()
            target=root/'MeshPortable-v0.6.28.exe'
            shutil.copyfile(os.environ['MESH_PACKAGED_EXE'],target)
            candidate=root/'candidate.exe';shutil.copyfile(target,candidate)
            from mesh_analyzer.database import Database
            db=Database(profile/'mesh-analyzer.sqlite3')
            db.upsert_node(123,123456,long_name='Preservar este nó');db.close()
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            url=f'http://127.0.0.1:{port}'
            script=root/'runner.ps1';script.write_text(RUNNER_PS,encoding='utf8')
            plan=root/'plan.json';notice=root/'notice.json';nonce='packaged-runtime-nonce'
            plan.write_text(json.dumps({'parent_pid':99999999,'executable':str(target),
                'mode':'portable','candidate':str(candidate),'previous':str(root/'previous.exe'),
                'version':__version__,'notes':'CI runtime test','log':str(root/'update.log'),
                'notice':str(notice),'runner_ready':str(root/'ready.json'),'run_nonce':'ready-nonce',
                'launch_nonce':nonce,'health_url':url+'/health',
                'restart_arguments':subprocess.list2cmdline(['--headless','--no-browser','--data-dir',str(profile),'--port',str(port)])}))
            # Reproduce a stale frozen runtime, without relying on a living _MEI.
            env={**os.environ,'_PYI_ARCHIVE_FILE':str(target),
                 '_PYI_APPLICATION_HOME_DIR':str(root/'removed_MEI'),
                 '_PYI_PARENT_PROCESS_LEVEL':'1','_MEIPASS2':str(root/'removed_MEI')}
            proc=subprocess.Popen(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
                '-File',str(script),'-Plan',str(plan)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                deadline=time.monotonic()+100
                while time.monotonic()<deadline:
                    try:
                        with urllib.request.urlopen(url+'/health',timeout=2) as r:health=json.load(r)
                        break
                    except Exception:time.sleep(.3)
                else:self.fail('Packaged EXE failed to start: '+(root/'update.log').read_text(encoding='utf-8-sig'))
                self.assertEqual(health['version'],__version__)
                self.assertEqual(health['update_nonce'],nonce)
                self.assertFalse(health['ui_ready'])
                self.assertFalse(notice.exists(),'Success must wait for UI readiness')
                with urllib.request.urlopen(url+'/',timeout=5) as r:html=r.read().decode()
                csrf=re.search(r'name="pt2vhf-csrf" content="([^"]+)"',html).group(1)
                request=urllib.request.Request(url+'/api/window/ready',data=b'{}',headers={
                    'Content-Type':'application/json','X-PT2VHF-CSRF':csrf})
                with urllib.request.urlopen(request,timeout=5) as r:self.assertTrue(json.load(r)['success'])
                self.assertEqual(proc.wait(timeout=20),0)
                result=json.loads(notice.read_text(encoding='utf-8-sig'))
                self.assertEqual(result['status'],'installed',result)
                with urllib.request.urlopen(url+'/api/nodes',timeout=5) as r:nodes=json.load(r)['data']
                self.assertTrue(any(n['long_name']=='Preservar este nó' for n in nodes))
                self.assertEqual(target.read_bytes(),candidate.read_bytes())
                self.assertTrue((root/'previous.exe').exists())
            finally:
                subprocess.run(['powershell.exe','-NoProfile','-Command',
                    'Get-Process -ErrorAction SilentlyContinue | Where-Object {$_.Path -eq $env:MESH_TEST_TARGET} | Stop-Process -Force'],
                    env={**os.environ,'MESH_TEST_TARGET':str(target)},capture_output=True,timeout=15)
                if proc.poll() is None:proc.kill();proc.wait(timeout=5)
                time.sleep(1)
