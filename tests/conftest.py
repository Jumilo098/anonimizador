"""Aisla las pruebas: no deben ensuciar reports/ ni .trabajo/ del proyecto.

conftest.py se importa antes que los modulos de prueba, asi que aqui se pueden
fijar las variables de entorno que anonimizador.config lee al importarse.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

_BASE = Path(tempfile.mkdtemp(prefix="anonimizador_tests_"))
os.environ.setdefault("ANONIMIZADOR_REPORTS", str(_BASE / "reports"))
os.environ.setdefault("ANONIMIZADOR_WORKSPACE", str(_BASE / "trabajo"))
os.environ["ANONIMIZADOR_REPORTS"] = str(_BASE / "reports")
os.environ["ANONIMIZADOR_WORKSPACE"] = str(_BASE / "trabajo")
