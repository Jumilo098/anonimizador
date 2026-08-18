"""Controles de seguridad de entrada (bloque 29).

No se ejecuta nada del documento: ni macros, ni scripts, ni URLs.
No se confia en la extension: se valida la firma binaria real.
"""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

from ..config import ALLOWED_EXTENSIONS, MAGIC_SIGNATURES, MAX_FILE_BYTES


class ArchivoRechazado(Exception):
    """El archivo no supera los controles de seguridad."""


_SEGURO = re.compile(r"[^A-Za-z0-9._-]+")


def sanear_nombre(nombre: str, maximo: int = 90) -> str:
    """Nombre de archivo seguro: sin rutas, sin unicode raro, sin espacios."""
    base = os.path.basename(str(nombre or "documento"))
    base = base.replace("\\", "/").split("/")[-1]
    base = unicodedata.normalize("NFKD", base)
    base = "".join(c for c in base if not unicodedata.combining(c))
    base = _SEGURO.sub("_", base).strip("._") or "documento"
    raiz, punto, ext = base.rpartition(".")
    if not punto:
        raiz, ext = base, ""
    raiz = raiz[:maximo] or "documento"
    ext = ext.lower()[:8]
    if ext:
        return raiz + "." + ext
    return raiz


def extension_de(nombre: str) -> str:
    return Path(str(nombre)).suffix.lower()


def detectar_formato(ruta, nombre_original=None) -> str:
    """Devuelve la extension validada contra la firma binaria del archivo.

    Lanza ArchivoRechazado si la extension no esta permitida o si el contenido
    no corresponde con lo que el nombre promete.
    """
    ruta = Path(ruta)
    nombre = nombre_original or ruta.name
    ext = extension_de(nombre)
    if ext not in ALLOWED_EXTENSIONS:
        permitidas = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ArchivoRechazado(
            "Extension no soportada en V1: " + (ext or "(sin extension)")
            + ". Permitidas: " + permitidas
        )
    if not ruta.exists():
        raise ArchivoRechazado("No existe el archivo: " + str(ruta))
    tam = ruta.stat().st_size
    if tam == 0:
        raise ArchivoRechazado("El archivo esta vacio.")
    if tam > MAX_FILE_BYTES:
        raise ArchivoRechazado(
            "El archivo pesa %.1f MB y el limite de seguridad es %.0f MB."
            % (tam / 1e6, MAX_FILE_BYTES / 1e6)
        )
    firmas = MAGIC_SIGNATURES.get(ext)
    if firmas:
        with open(ruta, "rb") as fh:
            cabecera = fh.read(16)
        if not any(cabecera.startswith(f) for f in firmas):
            raise ArchivoRechazado(
                "El contenido no corresponde a un archivo " + ext
                + ". Se rechaza por seguridad (posible extension falsificada)."
            )
    if ext in {".txt", ".md"}:
        with open(ruta, "rb") as fh:
            muestra = fh.read(4096)
        if b"\x00" in muestra:
            raise ArchivoRechazado("El .txt contiene bytes nulos: no es texto plano.")
    return ext


def leer_texto(ruta, limite=None) -> str:
    """Lectura tolerante de texto plano, sin ejecutar nada."""
    datos = Path(ruta).read_bytes()
    if limite:
        datos = datos[:limite]
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return datos.decode(enc)
        except UnicodeDecodeError:
            continue
    return datos.decode("utf-8", "replace")
