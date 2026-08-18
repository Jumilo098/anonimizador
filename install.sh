#!/usr/bin/env bash
# ANONIMIZADOR - instalacion en macOS / Linux
set -e
cd "$(dirname "$0")"

echo "ANONIMIZADOR - instalacion"
if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] No se encontro python3. Instalelo desde https://www.python.org/downloads/"
  exit 1
fi

python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m anonimizador.casos_sinteticos

echo
echo "LISTO. Ahora ejecute: ./start.sh"
