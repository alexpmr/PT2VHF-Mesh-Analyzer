$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } else { 'python' }
if ($python -eq 'py') {
    & py -3.12 -m pip install -r requirements-build.txt
    & py -3.12 branding/build_icons.py
    & py -3.12 -m unittest discover -s tests -v
    & py -3.12 -m PyInstaller --noconfirm --clean --onefile --windowed --name PT2VHF-Mesh-Analyzer --icon branding/mesh-analyzer.ico --add-data 'branding/mesh_analyzer_logo.png.b64;branding' --add-data 'branding/mesh-analyzer.ico;branding' --add-data 'mesh_analyzer/ui.html;mesh_analyzer' --collect-submodules meshtastic --collect-submodules bleak --collect-submodules paho --collect-submodules pubsub --collect-all webview --hidden-import serial.tools.list_ports launch.py
} else {
    & python -m pip install -r requirements-build.txt
    & python branding/build_icons.py
    & python -m unittest discover -s tests -v
    & python -m PyInstaller --noconfirm --clean --onefile --windowed --name PT2VHF-Mesh-Analyzer --icon branding/mesh-analyzer.ico --add-data 'branding/mesh_analyzer_logo.png.b64;branding' --add-data 'branding/mesh-analyzer.ico;branding' --add-data 'mesh_analyzer/ui.html;mesh_analyzer' --collect-submodules meshtastic --collect-submodules bleak --collect-submodules paho --collect-submodules pubsub --collect-all webview --hidden-import serial.tools.list_ports launch.py
}
if ($LASTEXITCODE -ne 0) {throw 'Falha ao gerar o executável Windows'}
Write-Host 'Executável em dist\PT2VHF-Mesh-Analyzer.exe'