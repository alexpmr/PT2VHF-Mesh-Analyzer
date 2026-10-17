@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
 echo Python nao encontrado. Instale Python 3.12 para Windows 10/11 x64.
 pause
 exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
 echo Criando ambiente virtual...
 py -3.12 -m venv ".venv" || goto :fail
)
echo Instalando/verificando bibliotecas Meshtastic...
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail
echo Abrindo PT2VHF Mesh Analyzer...
".venv\Scripts\python.exe" -m mesh_analyzer
goto :end
:fail
echo Nao foi possivel instalar/iniciar. Veja a mensagem acima.
pause
:end
endlocal
