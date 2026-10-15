param(
    [Parameter(Mandatory = $true)]
    [string]$TargetExe
)
$ErrorActionPreference = 'Stop'
$profile = Join-Path $env:LOCALAPPDATA 'PT2VHF-Mesh-Analyzer'
$log = Join-Path $profile 'installer-close.log'
New-Item -ItemType Directory -Path $profile -Force | Out-Null
function Log([string]$message) {
    Add-Content -LiteralPath $log -Encoding UTF8 -Value (
        (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss') + ' ' + $message)
}
try {
    $target = [IO.Path]::GetFullPath($TargetExe)
    $userSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    Log ('Installer process cleanup starting, target=' + $target)
    $found = @()
    foreach ($item in @(Get-CimInstance Win32_Process -Filter "Name='PT2VHF-Mesh-Analyzer.exe'")) {
        if (-not $item.ExecutablePath) { continue }
        $candidate = [IO.Path]::GetFullPath([string]$item.ExecutablePath)
        if (-not [string]::Equals($candidate, $target,
                [StringComparison]::OrdinalIgnoreCase)) { continue }
        $owner = Invoke-CimMethod -InputObject $item -MethodName GetOwnerSid
        if ([int]$owner.ReturnValue -ne 0 -or [string]$owner.Sid -ne $userSid) {
            Log ('Refusing process PID=' + $item.ProcessId + ': different or unknown user')
            throw 'Process owner could not be verified for exact target'
        }
        $found += [int]$item.ProcessId
    }
    if (-not $found.Count) {
        Log 'No running copy of the same executable. Continue installation.'
        exit 0
    }
    foreach ($id in $found) {
        $process = Get-Process -Id $id -ErrorAction SilentlyContinue
        if (-not $process) { continue }
        if ($process.MainWindowHandle -ne [IntPtr]::Zero) {
            Log ('Requesting graceful close PID=' + $id)
            [void]$process.CloseMainWindow()
        }
    }
    $deadline = [DateTime]::UtcNow.AddSeconds(15)
    do {
        $remaining = @($found | Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue })
        if (-not $remaining.Count) { break }
        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $deadline)

    # The PyInstaller one-file bootloader sometimes leaves a headless child
    # alive even after the WebView2 window disappears.
    foreach ($id in $remaining) {
        $still = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $id)
        if (-not $still) { continue }
        $path = [IO.Path]::GetFullPath([string]$still.ExecutablePath)
        $owner = Invoke-CimMethod -InputObject $still -MethodName GetOwnerSid
        if (-not [string]::Equals($path, $target,
                [StringComparison]::OrdinalIgnoreCase) -or
            [string]$owner.Sid -ne $userSid) {
            Log ('Refusing PID=' + $id + ': identity/path changed after grace period')
            throw 'Process identity changed during installer cleanup'
        }
        Log ('Terminating own remaining Mesh Analyzer PID=' + $id)
        Stop-Process -Id $id -Force -ErrorAction Stop
    }
    # Windows can retain terminating onefile parent/child processes longer than
    # 750 ms. Verify only PIDs still pointing to the *same* target executable.
    $waitUntil = [DateTime]::UtcNow.AddSeconds(10)
    do {
        $alive = @()
        foreach ($oldPid in $found) {
            $current = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $oldPid) -ErrorAction SilentlyContinue
            if (-not $current -or -not $current.ExecutablePath) { continue }
            $currentPath = [IO.Path]::GetFullPath([string]$current.ExecutablePath)
            if ([string]::Equals($currentPath, $target,
                    [StringComparison]::OrdinalIgnoreCase)) {
                $alive += [int]$oldPid
            } else {
                Log ('PID ' + $oldPid + ' is no longer the target executable')
            }
        }
        if (-not $alive.Count) { break }
        Start-Sleep -Milliseconds 350
    } while ([DateTime]::UtcNow -lt $waitUntil)
    if ($alive.Count) {
        Log ('ERROR: still running after close: ' + ($alive -join ','))
        exit 3
    }
    Log ('All target processes exited; installer may proceed')
    exit 0
} catch {
    Log ('ERROR: ' + $_.Exception.Message)
    exit 2
}
