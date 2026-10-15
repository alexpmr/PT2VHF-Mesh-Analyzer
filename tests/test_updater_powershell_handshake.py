"""Exercise the actual external updater handshake on Windows, not just PS syntax."""
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from mesh_analyzer.updater import RUNNER_PS


@unittest.skipUnless(os.name == "nt", "Windows PowerShell integration")
class WindowsRunnerHandshakeTests(unittest.TestCase):
    def test_hidden_powershell_writes_authenticated_ready_marker(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            script = root/"apply_update.ps1"
            script.write_text(RUNNER_PS, encoding="utf-8")
            plan = root/"plan.json"
            marker = root/"ready.json"
            log = root/"update.log"
            # A nonexistent parent is harmless: the runner must write readiness
            # before checking the old process and before any installer execution.
            p = {"log":str(log),"run_nonce":"integration-nonce",
                 "mode":"test-invalid","version":"0.0.0","notes":"",
                 "notice":str(root/"notice.json"),"runner_ready":str(marker),
                 "parent_pid":99999999,"executable":str(root/"old.exe"),
                 "health_url":"http://127.0.0.1:1/health"}
            plan.write_text(json.dumps(p),encoding="utf-8")
            flags=getattr(subprocess,"CREATE_NO_WINDOW",0)
            with (root/"output.log").open("ab",buffering=0) as out:
                proc=subprocess.Popen(
                    ["powershell.exe","-NoLogo","-NoProfile","-NonInteractive",
                     "-ExecutionPolicy","Bypass","-File",str(script),"-Plan",str(plan)],
                    cwd=d,stdin=subprocess.DEVNULL,stdout=out,
                    stderr=subprocess.STDOUT,creationflags=flags,close_fds=True)
                deadline=time.monotonic()+15
                try:
                    while time.monotonic()<deadline and not marker.exists() and proc.poll() is None:
                        time.sleep(.1)
                    self.assertTrue(marker.exists(),
                        "Runner did not acknowledge start; output: "+
                        (root/"output.log").read_text(errors="replace")[-1500:])
                    m=json.loads(marker.read_text(encoding="utf-8-sig"))
                    self.assertEqual(m["status"],"ready")
                    self.assertEqual(m["nonce"],"integration-nonce")
                finally:
                    try:proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=5)


if __name__=="__main__":
    unittest.main()
