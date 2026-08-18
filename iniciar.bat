@echo off
REM  ANONIMIZADOR - arranque (interfaz local en el navegador)
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set PYEXE=.venv\Scripts\python.exe
) else (
  echo  No se encontro el entorno .venv: se usara el Python del sistema.
  echo  Si falla algo, ejecute primero instalar.bat
  set PYEXE=python
)

echo.
echo  Abriendo ANONIMIZADOR en su navegador...
echo  Todo el procesamiento ocurre en este equipo. Para cerrar: Ctrl+C
echo.
%PYEXE% -m streamlit run app.py --server.address=127.0.0.1 --browser.gatherUsageStats=false
pause
