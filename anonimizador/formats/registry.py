"""Registro de manejadores. Arquitectura extensible: anadir un formato es
crear un manejador y registrarlo aqui."""
from __future__ import annotations

from .docx_handler import ManejadorDocx
from .image_handler import ManejadorImagen
from .pdf_handler import ManejadorPdf
from .text_handler import ManejadorTexto
from .xlsx_handler import ManejadorXlsx

MANEJADORES = [
    ManejadorTexto(),
    ManejadorDocx(),
    ManejadorPdf(),
    ManejadorImagen(),
    ManejadorXlsx(),
]


def manejador_para(extension: str):
    ext = (extension or "").lower()
    for m in MANEJADORES:
        if ext in m.extensiones:
            return m
    return None


def extensiones_soportadas():
    salida = []
    for m in MANEJADORES:
        salida.extend(m.extensiones)
    return sorted(set(salida))
