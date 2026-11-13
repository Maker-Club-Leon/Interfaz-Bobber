@echo off
rem Arranque en Windows: crea el entorno la primera vez e inicia la app.
rem Opciones:  run.bat --selftest | --calibrar | --manual | --ventana | --descargar-modelos
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Creando entorno virtual con Python 3.12...
  py -3.12 -m venv .venv >nul 2>&1
  if not exist ".venv\Scripts\python.exe" (
    python -c "import sys; sys.exit(sys.version_info[:2] != (3, 12) or sys.maxsize < 2**32)" >nul 2>&1
    if not errorlevel 1 python -m venv .venv
  )
  if not exist ".venv\Scripts\python.exe" (
    echo No se encontro Python 3.12 de 64 bits. Instalalo desde python.org y vuelve a ejecutar run.bat.
    pause & exit /b 1
  )
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Fallo la instalacion de dependencias. Revisa el README, seccion Solucion de problemas.
    pause & exit /b 1
  )
)
".venv\Scripts\python.exe" -m mascota %*
if errorlevel 1 pause
