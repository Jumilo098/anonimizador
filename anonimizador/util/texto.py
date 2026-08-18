"""Utilidades de texto que PRESERVAN LAS POSICIONES.

Es critico: todos los detectores devuelven (inicio, fin) sobre el texto
original. Cualquier normalizacion debe conservar la longitud, si no las
transformaciones se aplicarian en el lugar equivocado.
"""
from __future__ import annotations

import re

# Mapa 1 a 1 (no cambia la longitud de la cadena)
_ACENTOS = str.maketrans(
    "áàäâãéèëêíìïîóòöôõúùüûñçÁÀÄÂÃÉÈËÊÍÌÏÎÓÒÖÔÕÚÙÜÛÑÇ",
    "aaaaaeeeeiiiiooooouuuuncAAAAAEEEEIIIIOOOOOUUUUNC",
)


def plegar(texto: str) -> str:
    """minusculas + sin acentos, MISMA LONGITUD que la entrada."""
    return (texto or "").translate(_ACENTOS).lower()


def solapan(a: tuple, b: tuple) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def alguno_solapa(span: tuple, spans) -> bool:
    return any(solapan(span, s[:2]) for s in spans)


def fusionar_spans(spans):
    """Une intervalos solapados. Recibe iterables (ini, fin, ...)."""
    ordenados = sorted((s[0], s[1]) for s in spans)
    salida = []
    for ini, fin in ordenados:
        if salida and ini <= salida[-1][1]:
            salida[-1] = (salida[-1][0], max(salida[-1][1], fin))
        else:
            salida.append((ini, fin))
    return salida


_EQUIVALENTES = {
    "a": "aáàäâãAÁÀÄÂÃ", "e": "eéèëêEÉÈËÊ", "i": "iíìïîIÍÌÏÎ",
    "o": "oóòöôõOÓÒÖÔÕ", "u": "uúùüûUÚÙÜÛ", "n": "nñNÑ", "c": "cçCÇ",
}


def patron_sin_tildes(frase: str) -> str:
    """'centro clinico' -> patron que casa 'CENTRO CLÍNICO' y 'Centro Clinico'.

    Los lexicos se escriben sin tildes para poder leerlos y mantenerlos, pero
    los documentos reales vienen acentuados y en mayusculas.
    """
    salida = []
    for ch in frase:
        base = ch.lower()
        if base in _EQUIVALENTES:
            salida.append("[" + _EQUIVALENTES[base] + "]")
        elif base.isalpha():
            salida.append("[" + base + base.upper() + "]")
        elif base == " ":
            salida.append(r"[ \t]+")
        else:
            salida.append(re.escape(ch))
    return "".join(salida)


_PALABRA = re.compile(r"[A-Za-zÁ-ÿ][A-Za-zÁ-ÿ'-]*", re.UNICODE)


def palabras(texto: str):
    """Devuelve [(palabra, inicio, fin)] respetando posiciones originales."""
    return [(m.group(0), m.start(), m.end()) for m in _PALABRA.finditer(texto or "")]


def recortar(texto: str, maximo: int = 120) -> str:
    t = " ".join((texto or "").split())
    return t if len(t) <= maximo else t[: maximo - 1] + "…"


def contexto(texto: str, inicio: int, fin: int, ventana: int = 28) -> str:
    ini = max(0, inicio - ventana)
    end = min(len(texto), fin + ventana)
    return recortar(texto[ini:end], 90)


def aplicar_reemplazos(texto: str, reemplazos):
    """Aplica [(ini, fin, nuevo)] de derecha a izquierda. Sin solapes."""
    ordenados = sorted(reemplazos, key=lambda r: r[0], reverse=True)
    salida = texto
    ultimo_inicio = len(texto) + 1
    for ini, fin, nuevo in ordenados:
        if fin > ultimo_inicio:
            # solape: se ignora el reemplazo mas a la izquierda por seguridad
            continue
        salida = salida[:ini] + nuevo + salida[fin:]
        ultimo_inicio = ini
    return salida
