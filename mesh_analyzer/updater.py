"""Verified, opt-in Windows update staging and detached replacement.

No updater ever replaces an executable while its Python/Windows process is alive.
Only the application's fixed GitHub release assets are accepted.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile

OWNER = "alexpmr/PT2VHF-Mesh-Analyzer"
RELEASE_BASE = "https://github.com/" + OWNER + "/releases/download/"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
CHECKSUM_RE = re.compile(r"^([A-Fa-f0-9]{64})\s+\*?([A-Za-z0-9_.-]+)$")
MAX_SIZE = 100 * 1024 * 1024

# This runner executes *after the desktop and all sources have exited*. It
# has no ability to kill processes or elevate privilege.
RUNNER_PS = r"""
param([Parameter(Mandatory=$true)][string]$Plan)
$ErrorActionPreference = 'Stop'
$p = Get-Content -LiteralPath $Plan -Raw -Encoding UTF8 | ConvertFrom-Json
$log = [string]$p.log
function WriteLog([string]$line) {
    Add-Content -LiteralPath $log -Value ((Get-Date -Format 'o') + ' ' + $line) -Encoding UTF8
}
function WriteNotice([string]$status,[string]$detail) {
    $obj = @{ version = [string]$p.version; notes = [string]$p.notes;
              status = $status; error = $detail;
              updated_at = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() } | ConvertTo-Json -Compress
    $tmp = ([string]$p.notice + '.new')
    [IO.File]::WriteAllText($tmp, $obj, [Text.Encoding]::UTF8)
    Move-Item -LiteralPath $tmp -Destination ([string]$p.notice) -Force
}
$child = $null
try {
    # Detached runner readiness is acknowledged before app shutdown.
    $ready = @{ nonce = [string]$p.run_nonce; pid = $PID; status = 'ready' } |
        ConvertTo-Json -Compress
    [IO.File]::WriteAllText([string]$p.runner_ready, $ready, [Text.Encoding]::UTF8)
    WriteLog ('Detached updater ready PID=' + $PID + '; mode=' + [string]$p.mode)

    WriteLog 'Waiting for Mesh Analyzer process and database handles to close'
    $timeout = [DateTime]::UtcNow.AddSeconds(90)
    while ([DateTime]::UtcNow -lt $timeout) {
        $running = Get-Process -Id ([int]$p.parent_pid) -ErrorAction SilentlyContinue
        if ($null -eq $running) { break }
        try {
            if ($running.Path -and ([IO.Path]::GetFullPath($running.Path) -ne
                 [IO.Path]::GetFullPath([string]$p.executable))) { break }
        } catch {}
        Start-Sleep -Milliseconds 450
    }
    $running = Get-Process -Id ([int]$p.parent_pid) -ErrorAction SilentlyContinue
    if ($running) {
        $same = $false
        try {
            $same = ([IO.Path]::GetFullPath($running.Path) -eq
                     [IO.Path]::GetFullPath([string]$p.executable))
        } catch { $same = $true }
        if ($same) { throw 'Original application still running after 90 seconds' }
    }
    if ([string]$p.mode -eq 'setup') {
        WriteLog 'Installing verified Windows Setup'
        $args = @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-')
        $proc = Start-Process -FilePath ([string]$p.package) -ArgumentList $args -Wait -PassThru
        if ($proc.ExitCode -ne 0) { throw ('Setup failed: exit code ' + $proc.ExitCode) }
    } elseif ([string]$p.mode -eq 'portable') {
        WriteLog 'Replacing portable executable'
        $target = [string]$p.executable
        $previous = [string]$p.previous
        $candidate = [string]$p.candidate
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { throw 'Missing verified portable executable' }
        Copy-Item -LiteralPath $target -Destination $previous -Force
        try {
            Copy-Item -LiteralPath $candidate -Destination ($target + '.new') -Force
            Move-Item -LiteralPath ($target + '.new') -Destination $target -Force
        } catch {
            Copy-Item -LiteralPath $previous -Destination $target -Force
            throw
        }
    } else { throw 'Invalid update mode' }
    $exe = [string]$p.executable
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
        throw ('Executable missing after installation: ' + $exe)
    }
    WriteLog 'Launching updated executable'
    WriteLog ('Launching path=' + $exe + '; cwd=' + [IO.Path]::GetDirectoryName($exe))
    $child = Start-Process -FilePath $exe -WorkingDirectory ([IO.Path]::GetDirectoryName($exe)) -PassThru
    WriteLog ('Launched PID=' + $child.Id)
    $healthy = $false
    $deadline = [DateTime]::UtcNow.AddSeconds(90)
    while ([DateTime]::UtcNow -lt $deadline) {
        Start-Sleep -Milliseconds 700
        $child.Refresh()
        if ($child.HasExited) { throw ('Updated application exited early: ' + $child.ExitCode) }
        try {
            $response = Invoke-RestMethod -Uri ([string]$p.health_url) -TimeoutSec 2 -ErrorAction Stop
            if ($response.version -eq [string]$p.version -and $response.success -eq $true -and $response.ui_ready -eq $true) {
                $healthy = $true
                break
            }
        } catch {
            # The HTTP service may not have started yet.
        }
    }
    if (-not $healthy) { throw 'Updated application did not confirm its version via /health' }
    # Never report success before the new process actually launches and reports readiness.
    WriteNotice 'installed' ''
    WriteLog 'Updated version confirmed via /health and running'
    exit 0
} catch {
    $reason = $_.Exception.Message
    WriteLog ('FAILED: ' + $reason)
    if ([string]$p.mode -eq 'portable' -and
        (Test-Path -LiteralPath ([string]$p.previous) -PathType Leaf)) {
        try {
            if ($null -eq $child -or $child.HasExited) {
                Copy-Item -LiteralPath ([string]$p.previous) -Destination ([string]$p.executable) -Force
                WriteLog 'Restored previous portable executable after failed restart'
            }
        } catch { WriteLog ('Rollback failed: ' + $_.Exception.Message) }
    }
    try { WriteNotice 'failed' $reason } catch { WriteLog ('Cannot save update failure: ' + $_.Exception.Message) }
    # The original GUI is already closed: make the failure recoverable and visible.
    try {
        Add-Type -AssemblyName System.Windows.Forms
        $answer = [System.Windows.Forms.MessageBox]::Show(
          ('PT2VHF Mesh Analyzer nao reiniciou automaticamente.' + [Environment]::NewLine +
           $reason + [Environment]::NewLine + [Environment]::NewLine +
           'Abrir a pasta com o log de atualizacao?'),
          'PT2VHF Mesh Analyzer - Atualizacao falhou',
          [System.Windows.Forms.MessageBoxButtons]::YesNo,
          [System.Windows.Forms.MessageBoxIcon]::Error)
        if ($answer -eq [System.Windows.Forms.DialogResult]::Yes) {
            Start-Process -FilePath 'explorer.exe' -ArgumentList ('/select,' + [string]$p.log)
        }
    } catch { WriteLog ('Recovery dialog unavailable: ' + $_.Exception.Message) }
    exit 1
}
"""


def release_assets(tag):
    if not VERSION_RE.fullmatch(str(tag)):
        raise ValueError("Versão remota inválida")
    stem = "PT2VHF-Mesh-Analyzer-v" + tag
    return {
        "setup": f"{stem}-Setup-Win11-x64.exe",
        "portable": f"{stem}-Portable-Win11-x64.zip",
    }


def parse_checksums(document, filename):
    lines = document.splitlines()
    for line in lines:
        found = CHECKSUM_RE.fullmatch(line.strip())
        if found and found.group(2) == filename:
            return found.group(1).lower()
    raise ValueError("SHA256 do pacote não consta do arquivo oficial")


def deployment_mode(executable=None):
    exe = Path(executable or sys.executable).resolve()
    if not getattr(sys, "frozen", False) and executable is None:
        raise RuntimeError("Atualização interna disponível somente no aplicativo Windows empacotado")
    if os.name != "nt" and executable is None:
        raise RuntimeError("Atualização direta disponível apenas no Windows")
    standard = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / \
        "Programs" / "PT2VHF Mesh Analyzer" / "PT2VHF-Mesh-Analyzer.exe"
    # Inno Setup may remember a user-selected installation directory.
    # Treat a folder with an actual Inno uninstaller as Setup even if the
    # install path differs from DefaultDirName.
    installed=(exe.parent/"unins000.exe").is_file() and (exe.parent/"unins000.dat").is_file()
    return "setup" if exe == standard.resolve() or installed else "portable"


def approved_asset_url(url, version, name):
    expected = RELEASE_BASE + "v" + version + "/" + name
    if url != expected:
        raise ValueError("Endereço do pacote não corresponde à release oficial")
    return url


def stream_verified(url, dest, expected_sha, max_size=MAX_SIZE, report=None, cancelled=None):
    if not isinstance(expected_sha,str) or not re.fullmatch(r"[a-f0-9]{64}",expected_sha):
        raise ValueError("SHA256 esperado inválido")
    partial = Path(str(dest) + ".part")
    h = hashlib.sha256()
    count = 0
    try:
        req = urllib.request.Request(url,headers={"User-Agent":"PT2VHF-Mesh-Analyzer-updater"})
        with urllib.request.urlopen(req,timeout=22) as resp, partial.open("wb") as out:
            total = int(resp.headers.get("Content-Length",0))
            if total > max_size:raise ValueError("Pacote excede o tamanho seguro")
            while True:
                if cancelled and cancelled.is_set():raise RuntimeError("Download cancelado")
                chunk = resp.read(131072)
                if not chunk:break
                if cancelled and cancelled.is_set():raise RuntimeError("Download cancelado")
                count += len(chunk)
                if count > max_size:raise ValueError("Pacote excede o tamanho seguro")
                h.update(chunk)
                out.write(chunk)
                if report:report(count,total)
        if h.hexdigest() != expected_sha:
            raise ValueError("SHA256 divergente: atualização cancelada")
        os.replace(partial,dest)
        return count
    finally:
        partial.unlink(missing_ok=True)


class UpdateManager:
    """Single download and explicit install confirmation, shared between clients."""
    def __init__(self,profile,monitor,executable=None):
        self.profile=Path(profile)
        self.monitor=monitor
        self.executable=Path(executable or sys.executable).resolve()
        self._lock=threading.RLock()
        self._phase="idle"
        self._error=None
        self._size=0
        self._received=0
        self._version=None
        self._mode=None
        self._plan=None
        self._busy=None
        self._cancel=threading.Event()

    def status(self):
        with self._lock:
            return {"success":True,"phase":self._phase,"error":self._error,
                    "received":self._received,"total":self._size,
                    "version":self._version,"mode":self._mode}

    def notice(self):
        path=self.profile/"update_complete.json"
        try:
            obj=json.loads(path.read_text(encoding="utf-8-sig"))
            if obj.get("status") == "failed" or (obj.get("version") == self.monitor.status()["current"] and obj.get("status") == "installed"):
                return {"success":True,"notice":obj}
        except (OSError,TypeError,ValueError):pass
        return {"success":True,"notice":None}

    def dismiss(self):
        path=self.profile/"update_complete.json"
        try:
            obj=json.loads(path.read_text(encoding="utf-8-sig"))
            if obj.get("status") == "failed" or obj.get("version") == self.monitor.status()["current"]:
                path.unlink(missing_ok=True)
        except (OSError,TypeError,ValueError):pass
        return {"success":True}

    def start(self,version):
        status=self.monitor.status()
        if status.get("error") or not status.get("available") or status.get("latest")!=version:
            raise ValueError("Verifique novamente a atualização disponível")
        mode=deployment_mode()
        names=release_assets(version)
        filename=names[mode]
        assets=self.monitor._result.get("assets",[]) if self.monitor._result else []
        matches=[a for a in assets if a.get("name")==filename]
        if len(matches)!=1:raise ValueError("Pacote adequado ausente da release")
        approved_asset_url(matches[0].get("url"),version,filename)
        with self._lock:
            if self._phase in ("downloading","verified","installing"):
                raise ValueError("Já existe uma atualização em andamento")
            self._cancel.clear()
            self._phase="downloading"
            self._error=None
            self._version=version
            self._mode=mode
            self._size=0
            self._received=0
        self._busy=threading.Thread(target=self._download,
                                    args=(version,mode,filename),daemon=True,
                                    name="verified-update-download")
        self._busy.start()
        return self.status()

    def _download(self,version,mode,filename):
        try:
            folder=self.profile/"updates"/("v"+version)
            folder.mkdir(parents=True,exist_ok=True)
            doc_url=RELEASE_BASE+"v"+version+"/SHA256SUMS.txt"
            req=urllib.request.Request(doc_url,headers={"User-Agent":"PT2VHF-Mesh-Analyzer-updater"})
            with urllib.request.urlopen(req,timeout=12) as resp:
                sums=resp.read(60000).decode("ascii")
            expected=parse_checksums(sums,filename)
            package=folder/filename
            def report(n,total):
                with self._lock:self._received=n;self._size=total
            stream_verified(RELEASE_BASE+"v"+version+"/"+filename,package,expected,report=report,cancelled=self._cancel)
            candidate=None
            if mode=="portable":
                candidate=folder/"candidate.exe"
                with zipfile.ZipFile(package) as z:
                    names=z.namelist()
                    if names != ["PT2VHF-Mesh-Analyzer.exe"]:
                        raise ValueError("Portable ZIP tem conteúdo inesperado")
                    info=z.getinfo(names[0])
                    if info.file_size>MAX_SIZE:raise ValueError("EXE extraído excede limite")
                    with z.open(names[0]) as src, candidate.open("wb") as dst:
                        copied=0
                        while True:
                            block=src.read(131072)
                            if not block:break
                            copied+=len(block)
                            if copied>MAX_SIZE:raise ValueError("EXE extraído excede limite")
                            dst.write(block)
            plan={"parent_pid":os.getpid(),"executable":str(self.executable),
                  "package":str(package),"candidate":str(candidate or ""),
                  "previous":str(folder/"previous.exe"),"mode":mode,
                  "version":version,"notes":(self.monitor._result or {}).get("notes","")[:3000],
                  "notice":str(self.profile/"update_complete.json"),
                  "log":str(self.profile/"update.log"),
                  "health_url":"http://127.0.0.1:8789/health",
                  "runner_ready":str(folder/"runner_ready.json"),
                  "run_nonce":secrets.token_hex(8)}
            planfile=folder/"plan.json"
            planfile.write_text(json.dumps(plan,ensure_ascii=False),encoding="utf-8")
            script=folder/"apply_update.ps1"
            script.write_text(RUNNER_PS,encoding="utf-8")
            with self._lock:
                self._plan=(str(script),str(planfile))
                self._phase="verified"
        except Exception as exc:
            with self._lock:
                self._phase="cancelled" if self._cancel.is_set() else "error"
                self._error=None if self._cancel.is_set() else str(exc)[:240]

    def cancel(self):
        with self._lock:
            if self._phase!="downloading":
                raise ValueError("Só é possível cancelar durante o download")
            self._cancel.set()
            return self.status()

    def launch(self):
        with self._lock:
            if self._phase!="verified" or self._plan is None:
                raise ValueError("Download não foi verificado ou não está pronto")
            script,plan=self._plan
            if os.name!="nt":raise RuntimeError("Instalação interna requer Windows")
            expected=json.loads(Path(plan).read_text(encoding="utf-8"))
            marker=Path(expected["runner_ready"])
            marker.unlink(missing_ok=True)
            creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)|getattr(subprocess,"DETACHED_PROCESS",0)
            proc=subprocess.Popen(
                ["powershell.exe","-NoProfile","-NonInteractive",
                 "-ExecutionPolicy","Bypass","-WindowStyle","Hidden",
                 "-File",script,"-Plan",plan],
                cwd=str(self.profile),stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                creationflags=creationflags,close_fds=True)
            # Do not close original application until the detached updater is alive.
            acknowledged=False
            deadline=time.monotonic()+12
            while time.monotonic()<deadline:
                if marker.exists():
                    try:
                        ready=json.loads(marker.read_text(encoding="utf-8-sig"))
                        if ready.get("status")=="ready" and ready.get("nonce")==expected["run_nonce"]:
                            acknowledged=True
                            break
                    except (OSError,ValueError,TypeError):pass
                if proc.poll() is not None:break
                time.sleep(.15)
            if not acknowledged:
                if proc.poll() is None:
                    try:proc.terminate()
                    except OSError:pass
                raise RuntimeError(
                  "Atualizador externo não confirmou inicialização. "
                  "O Mesh Analyzer permanecerá aberto. Consulte update.log.")

            self._phase="installing"
            return self.status()
