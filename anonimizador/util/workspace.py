"""Directorio de trabajo aislado. El ORIGINAL NUNCA SE TOCA (bloque 2-N)."""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..config import REPORTS_DIR, WORKSPACE_DIR
from .hashing import sha256_archivo
from .safety import sanear_nombre


@dataclass
class Ejecucion:
    ejecucion_id: str
    dir_trabajo: Path
    dir_reporte: Path
    copia: Path
    nombre_original: str
    hash_original: str
    tam_original: int

    def ruta_salida(self, sufijo: str) -> Path:
        raiz = Path(self.copia.name).stem
        return self.dir_reporte / (raiz + "_DESIDENTIFICADO" + sufijo)


def _marca_tiempo() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]


def crear_ejecucion(origen, nombre_original=None) -> Ejecucion:
    """Copia el original a un area aislada y devuelve el contexto de ejecucion.

    Regla absoluta: a partir de aqui solo se trabaja sobre la copia.
    """
    origen = Path(origen)
    nombre = sanear_nombre(nombre_original or origen.name)
    eid = _marca_tiempo() + "_" + Path(nombre).stem[:24]
    dir_trabajo = WORKSPACE_DIR / eid
    dir_reporte = REPORTS_DIR / eid
    dir_trabajo.mkdir(parents=True, exist_ok=True)
    dir_reporte.mkdir(parents=True, exist_ok=True)

    hash_original = sha256_archivo(origen)
    tam = origen.stat().st_size
    copia = dir_trabajo / nombre
    shutil.copy2(origen, copia)
    return Ejecucion(
        ejecucion_id=eid,
        dir_trabajo=dir_trabajo,
        dir_reporte=dir_reporte,
        copia=copia,
        nombre_original=nombre,
        hash_original=hash_original,
        tam_original=tam,
    )


def verificar_original_intacto(origen, hash_esperado: str) -> bool:
    return sha256_archivo(origen) == hash_esperado


def listar_trabajo() -> list:
    salida = []
    for base in (WORKSPACE_DIR, REPORTS_DIR):
        if not base.exists():
            continue
        for d in sorted(base.iterdir()):
            if d.is_dir():
                bytes_ = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
                salida.append({"tipo": base.name, "ruta": str(d), "bytes": bytes_})
    return salida


def eliminar_archivos_de_trabajo(incluir_reportes: bool = False) -> dict:
    """Boton ELIMINAR ARCHIVOS DE TRABAJO (bloque 19)."""
    borrados = {"trabajo": 0, "reportes": 0}
    if WORKSPACE_DIR.exists():
        for d in list(WORKSPACE_DIR.iterdir()):
            shutil.rmtree(d, ignore_errors=True)
            borrados["trabajo"] += 1
    if incluir_reportes and REPORTS_DIR.exists():
        for d in list(REPORTS_DIR.iterdir()):
            shutil.rmtree(d, ignore_errors=True)
            borrados["reportes"] += 1
    return borrados


def guardar_json(ruta: Path, datos) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return ruta
