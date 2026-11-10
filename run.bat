@echo off
rem Arranque en Windows: crea el entorno la primera vez e inicia la app.
rem Opciones:  run.bat --selftest | --calibrar | --manual | --ventana | --descargar-modelos
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Creando entorno virtual...
  py -3.12 -m venv .venv >nul 2>&1
  if errorlevel 1 py -3.11 -m venv .venv >nul 2>&1
  if errorlevel 1 python -m venv .venv
  if not exist ".venv\Scripts\python.exe" (
    echo No se pudo crear el entorno. Instala Python 3.11 o 3.12 de 64 bits desde python.org
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
