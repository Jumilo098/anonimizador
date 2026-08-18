@echo off
REM ================================================================
REM  ANONIMIZADOR - instalador para Windows
REM  Crea un entorno aislado e instala las dependencias. Todo local.
REM ================================================================
setlocal
cd /d "%~dp0"

echo.
echo  ANONIMIZADOR - instalacion
echo  ---------------------------------------------------------------
echo.

where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)

%PY% --version >nul 2>nul
if errorlevel 1 (
  echo  [ERROR] No se encontro Python.
  echo  Instalelo desde https://www.python.org/downloads/ y marque
  echo  la casilla "Add Python to PATH". Luego vuelva a ejecutar este archivo.
  pause
  exit /b 1
)

echo  Creando entorno virtual en .venv ...
%PY% -m venv .venv
if errorlevel 1 (
  echo  [ERROR] No se pudo crear el entorno virtual.
  pause
  exit /b 1
)

echo  Instalando dependencias (puede tardar unos minutos)...
call .venv\Scripts\python.exe -m pip install --upgrade pip
call .venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo  [ERROR] Fallo la instalacion de dependencias.
  pause
  exit /b 1
)

echo  Generando los casos sinteticos de demostracion...
call .venv\Scripts\python.exe -m anonimizador.casos_sinteticos

echo.
echo  LISTO. Ahora ejecute:  iniciar.bat
echo.
pause
