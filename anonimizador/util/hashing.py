"""Hashes y enmascarado. Nunca guardamos identificadores completos en los logs."""
from __future__ import annotations

import hashlib
import unicodedata
from pathlib import Path

SAL_LOCAL = b"anonimizador-local-v1"


def sha256_archivo(ruta, bloque: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for trozo in iter(lambda: fh.read(bloque), b""):
            h.update(trozo)
    return h.hexdigest()


def sha256_texto(texto: str) -> str:
    return hashlib.sha256((texto or "").encode("utf-8", "replace")).hexdigest()


def hash_hallazgo(texto: str) -> str:
    """Hash corto y salado de un identificador: rastreable sin exponerlo."""
    norm = normalizar(texto)
    return hashlib.sha256(SAL_LOCAL + norm.encode("utf-8")).hexdigest()[:16]


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.lower().split())


def enmascarar(texto: str, visibles: int = 2) -> str:
    """Juan Camilo -> Ju*********o. Nunca expone el valor completo."""
    if texto is None:
        return ""
    t = str(texto).strip()
    if not t:
        return ""
    if len(t) <= 2:
        return "*" * len(t)
    if len(t) <= visibles + 1:
        return t[0] + "*" * (len(t) - 1)
    return t[:visibles] + "*" * max(1, len(t) - visibles - 1) + t[-1]
