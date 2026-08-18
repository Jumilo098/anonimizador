#!/usr/bin/env bash
# ANONIMIZADOR - arranque de la interfaz local
set -e
cd "$(dirname "$0")"

PYEXE="python3"
[ -x "./.venv/bin/python" ] && PYEXE="./.venv/bin/python"

echo "Abriendo ANONIMIZADOR en su navegador (todo local). Para cerrar: Ctrl+C"
"$PYEXE" -m streamlit run app.py --server.address=127.0.0.1 --browser.gatherUsageStats=false
