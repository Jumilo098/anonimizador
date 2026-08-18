"""Deteccion y PROTECCION de la informacion clinica.

Este modulo no busca identificadores: busca lo que NO se puede tocar.
Es la mitad silenciosa de la camisa de fuerza: cualquier transformacion que
solape un "span protegido" queda BLOQUEADA y se manda a revision humana.
"""
from __future__ import annotations

import re

from ...models import ValorClinico
from ...resources import lexicos as LX
from ...util.hashing import normalizar
from ...util.texto import contexto, plegar

# ---------------------------------------------------------------------------
# Construccion de expresiones a partir de los lexicos
# ---------------------------------------------------------------------------
_UNIDADES_RE = "|".join(
    re.escape(u) for u in sorted(LX.UNIDADES, key=len, reverse=True)
)
NUM = r"\d+(?:[.,]\d+)?"

RE_NUM_UNIDAD = re.compile(
    r"(?P<num>" + NUM + r")\s*(?P<uni>" + _UNIDADES_RE + r")(?![A-Za-z0-9/])",
    re.IGNORECASE,
)

# 120/80 mmHg, 3.2 x 2.1 cm, 45 %
RE_RAZON = re.compile(r"\b(?P<a>\d{2,3})\s*/\s*(?P<b>\d{2,3})\s*(?:mmhg)?\b", re.I)
RE_MEDIDA = re.compile(
    r"\b(?P<a>" + NUM + r")\s*[x×]\s*(?P<b>" + NUM
    + r")(?:\s*[x×]\s*(?P<c>" + NUM + r"))?\s*(?P<uni>mm|cm|m)\b",
    re.I,
)
RE_RANGO_REF = re.compile(
    r"\(?\s*(?P<a>" + NUM + r")\s*(?:-|a|–)\s*(?P<b>" + NUM + r")\s*\)?",
)

_ANALITOS_RE = "|".join(
    re.escape(a) for a in sorted(LX.ANALITOS | LX.VITALES, key=len, reverse=True)
)
RE_ANALITO_VALOR = re.compile(
    r"(?<![a-z0-9])(?P<analito>" + _ANALITOS_RE + r")(?![a-z0-9])"
    r"\s*[:=]?\s*(?P<num>" + NUM + r")",
    re.IGNORECASE,
)

RE_DOSIS = re.compile(
    r"\b(?P<num>" + NUM + r")\s*(?P<uni>mg|g|mcg|ug|ml|ui|comprimidos?|tabletas?|"
    r"capsulas?|gotas?)\b(?P<pauta>\s*(?:cada|c/)\s*\d{1,2}\s*(?:h|horas|dias|d))?",
    re.IGNORECASE,
)

RE_PORCENTAJE = re.compile(r"\b(?P<num>" + NUM + r")\s*%")

# Terminos clinicos como palabra completa
_TERMINOS_RE = "|".join(
    re.escape(t) for t in sorted(LX.TERMINOS_CLINICOS, key=len, reverse=True)
)
RE_TERMINO = re.compile(r"(?<![a-z0-9])(" + _TERMINOS_RE + r")(?![a-z0-9])")

_NEG_RE = "|".join(re.escape(t) for t in sorted(LX.NEGACIONES, key=len, reverse=True))
RE_NEGACION = re.compile(r"(?<![a-z])(" + _NEG_RE + r")(?![a-z])")


# ---------------------------------------------------------------------------
# Spans protegidos
# ---------------------------------------------------------------------------
def spans_protegidos(texto: str):
    """Intervalos (ini, fin, motivo) que NINGUNA transformacion puede tocar."""
    if not texto:
        return []
    pl = plegar(texto)
    spans = []

    def add(m, motivo):
        spans.append((m.start(), m.end(), motivo))

    for m in RE_NUM_UNIDAD.finditer(pl):
        add(m, "valor con unidad")
    for m in RE_MEDIDA.finditer(pl):
        add(m, "medida")
    for m in RE_DOSIS.finditer(pl):
        add(m, "dosis")
    for m in RE_PORCENTAJE.finditer(pl):
        add(m, "porcentaje")
    for m in RE_ANALITO_VALOR.finditer(pl):
        add(m, "analito con valor")
    for m in RE_TERMINO.finditer(pl):
        add(m, "termino clinico")
    for m in RE_RAZON.finditer(pl):
        # 120/80 solo se protege si hay contexto de signo vital cerca
        ini = max(0, m.start() - 30)
        if re.search(r"\b(ta|pa|tension|presion|arterial)\b", pl[ini:m.start()]):
            add(m, "signo vital")
    return spans


def protegido(texto: str, inicio: int, fin: int, spans=None) -> str:
    """Devuelve el motivo si el rango pisa informacion clinica; '' si es libre."""
    for ini, f, motivo in (spans if spans is not None else spans_protegidos(texto)):
        if inicio < f and ini < fin:
            return motivo
    return ""


# ---------------------------------------------------------------------------
# Extraccion de valores clinicos comparables (bloque 14)
# ---------------------------------------------------------------------------
def _norm_num(s: str) -> str:
    s = (s or "").replace(",", ".").strip()
    try:
        f = float(s)
    except ValueError:
        return s
    return ("%.6f" % f).rstrip("0").rstrip(".")


def extraer_valores(texto: str) -> list:
    """Convierte el texto en una lista de unidades clinicas comparables."""
    if not texto:
        return []
    pl = plegar(texto)
    vals: list[ValorClinico] = []

    def add(clase, m, normalizado):
        vals.append(
            ValorClinico(
                clase=clase,
                texto=texto[m.start():m.end()],
                normalizado=normalizado,
                contexto=contexto(texto, m.start(), m.end()),
            )
        )

    for m in RE_NUM_UNIDAD.finditer(pl):
        add("numero_unidad", m, _norm_num(m.group("num")) + " " + m.group("uni").lower())
    for m in RE_MEDIDA.finditer(pl):
        partes = [_norm_num(m.group("a")), _norm_num(m.group("b"))]
        if m.group("c"):
            partes.append(_norm_num(m.group("c")))
        add("medida", m, "x".join(partes) + " " + m.group("uni").lower())
    for m in RE_PORCENTAJE.finditer(pl):
        add("porcentaje", m, _norm_num(m.group("num")) + " %")
    for m in RE_DOSIS.finditer(pl):
        pauta = " ".join((m.group("pauta") or "").split())
        add(
            "dosis",
            m,
            _norm_num(m.group("num")) + " " + m.group("uni").lower() + (" " + pauta if pauta else ""),
        )
    for m in RE_ANALITO_VALOR.finditer(pl):
        add(
            "analito_valor",
            m,
            normalizar(m.group("analito")) + "=" + _norm_num(m.group("num")),
        )
    for m in RE_RAZON.finditer(pl):
        ini = max(0, m.start() - 30)
        if re.search(r"\b(ta|pa|tension|presion|arterial)\b", pl[ini:m.start()]):
            add("signo_vital", m, m.group("a") + "/" + m.group("b"))
    for m in RE_TERMINO.finditer(pl):
        termino = m.group(1)
        if termino in LX.ANATOMIA:
            clase = "anatomia"
        elif termino in LX.LATERALIDAD:
            clase = "lateralidad"
        elif termino in LX.MEDICAMENTOS:
            clase = "medicamento"
        elif termino in LX.PROCEDIMIENTOS:
            clase = "procedimiento"
        elif termino in LX.DIAGNOSTICOS:
            clase = "diagnostico"
        elif termino in LX.CERTEZA:
            clase = "certeza"
        else:
            clase = "termino_clinico"
        add(clase, m, termino)
    for m in RE_NEGACION.finditer(pl):
        add("negacion", m, m.group(1))
    return vals


def resumen_valores(valores) -> dict:
    """Cuenta por clase, para el informe humano."""
    salida: dict[str, int] = {}
    for v in valores:
        salida[v.clase] = salida.get(v.clase, 0) + 1
    return dict(sorted(salida.items()))
