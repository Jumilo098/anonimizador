"""Capa 2: IDENTIFICADORES INDIRECTOS.

Edad exacta, fechas, ocupacion, cargo, institucion, aseguradora, localidad.
Ninguno identifica por si solo; combinados si (ver contextual.py).
"""
from __future__ import annotations

import re

from ...models import Capa, Categoria, Confianza, Hallazgo
from ...resources import lexicos as LX
from ...util.texto import patron_sin_tildes, plegar

DETECTOR = "indirectos"

# ---------------------------------------------------------------------------
# Edad
# ---------------------------------------------------------------------------
RE_EDAD = re.compile(
    r"(?<![\d.,])(?P<num>\d{1,3})\s*(?P<uni>anos|años|a\.?\s*de\s*edad)(?![a-z])",
    re.IGNORECASE,
)
RE_EDAD_ETIQUETA = re.compile(
    r"\bedad\s*[:=]\s*(?P<num>\d{1,3})(?:\s*(?:anos|años))?", re.IGNORECASE
)
# contextos que convierten "N anos" en dato clinico (duracion), no en edad
_ANTES_DURACION = re.compile(
    r"(hace|desde\s+hace|durante|hace\s+ya|ultimos|últimos|previos|evoluci[oó]n\s+de|"
    r"seguimiento\s+de|tratamiento\s+de|diagnosticad[oa]\s+hace)\s*$",
    re.IGNORECASE,
)
_DESPUES_DURACION = re.compile(
    r"^\s*(de\s+evoluci[oó]n|de\s+diagn[oó]stico|atr[aá]s|antes|previos|"
    r"de\s+seguimiento|de\s+tratamiento)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Fechas
# ---------------------------------------------------------------------------
_MESES_RE = "|".join(LX.MESES)
RE_FECHAS = [
    re.compile(r"\b(?P<d>\d{1,2})[/\-.](?P<m>\d{1,2})[/\-.](?P<a>\d{2,4})\b"),
    re.compile(r"\b(?P<a>\d{4})[/\-.](?P<m>\d{1,2})[/\-.](?P<d>\d{1,2})\b"),
    re.compile(
        r"\b(?P<d>\d{1,2})\s+de\s+(?P<mes>" + _MESES_RE + r")\s+(?:de[l]?\s+)?(?P<a>\d{4})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?P<mes>" + _MESES_RE + r")\s+(?:de[l]?\s+)?(?P<a>\d{4})\b", re.IGNORECASE
    ),
]
RE_FECHA_NACIMIENTO = re.compile(
    r"\b(?:fecha\s+de\s+nacimiento|f\.?\s*nac\.?|nacid[oa]\s+el|nacimiento)\s*[:=-]?\s*"
    r"(?P<val>[^\n\t|;]{4,30})",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Ocupacion, institucion, aseguradora, lugar
# ---------------------------------------------------------------------------
_OCUP_RE = "|".join(
    re.escape(o) for o in sorted(LX.OCUPACION_A_SECTOR, key=len, reverse=True)
)
RE_OCUPACION = re.compile(r"(?<![a-z])(" + _OCUP_RE + r")(?![a-z])")
RE_OCUPACION_ETIQUETA = re.compile(
    r"\b(?:ocupaci[oó]n|profesi[oó]n|oficio|cargo|labora\s+como|trabaja\s+como|"
    r"empleo)\s*[:=]?\s*(?P<val>[^\n\t|;.]{3,50})",
    re.IGNORECASE,
)

# Los prefijos se convierten en patrones tolerantes a tildes y mayusculas:
# en los documentos reales aparece "CENTRO CLINICO", "Centro Clínico", etc.
_INST_RE = "|".join(
    patron_sin_tildes(p)
    for p in sorted(LX.PREFIJOS_INSTITUCION, key=len, reverse=True)
)
RE_INSTITUCION = re.compile(
    # [ \t] simple y no \s+: el nombre de una institucion no cruza saltos de
    # linea NI dos espacios seguidos (en un PDF eso es el salto a otra columna,
    # y por ahi se colaba la etiqueta del campo siguiente: "EPS   Correo:").
    r"(?<![a-zA-Z])(?P<pref>(?i:" + _INST_RE + r"))\.?[ \t]"
    r"(?P<nombre>(?:(?i:de|del|la|las|los|san|santa|santo)[ \t])?"
    r"(?:[A-ZÁ-Ú][\wÁ-ÿ]*|[A-ZÁ-Ú]{3,})"
    r"(?:[ \t](?:(?i:de|del|la|las|los|y)[ \t])?(?:[A-ZÁ-Ú][\wÁ-ÿ]*|[A-ZÁ-Ú]{3,})){0,3})",
)

# Etiquetas de campo: si el "nombre" capturado es una de estas, no es el
# nombre de la institucion, es el campo siguiente del formulario.
ETIQUETAS_DE_CAMPO = {
    "correo", "email", "telefono", "tel", "celular", "fecha", "hora", "orden",
    "documento", "cedula", "historia", "paciente", "edad", "sexo", "ocupacion",
    "direccion", "municipio", "ciudad", "sede", "asegurador", "aseguradora",
    "poliza", "afiliado", "resultado", "referencia", "observaciones", "nombre",
    "apellidos", "servicio", "medico", "profesional", "registro", "firma",
}

_ASEG_RE = "|".join(re.escape(a) for a in sorted(LX.ASEGURADORAS, key=len, reverse=True))
RE_ASEGURADORA = re.compile(
    r"(?<![a-z])(?:eps|ips|arl|aseguradora|seguro)?\s*(" + _ASEG_RE + r")(?![a-z])"
)

_CIUD_RE = "|".join(
    re.escape(c) for c in sorted(set(LX.CIUDAD_A_REGION) | LX.DEPARTAMENTOS,
                                 key=len, reverse=True)
)
RE_CIUDAD = re.compile(r"(?<![a-z])(" + _CIUD_RE + r")(?![a-z])")


def _mk(unidad, tipo, texto, ini, fin, conf, nota="", categoria=Categoria.INDIRECTO):
    return Hallazgo(
        uid_unidad=unidad.uid,
        categoria=categoria,
        tipo=tipo,
        texto=texto[ini:fin],
        inicio=ini,
        fin=fin,
        capa=unidad.capa if isinstance(unidad.capa, Capa) else Capa.CONTENIDO,
        confianza=conf,
        detector=DETECTOR,
        nota=nota,
        ruta=unidad.ruta,
    )


def detectar(unidad, spans_clinicos=None) -> list:
    texto = unidad.texto or ""
    pl = plegar(texto)
    out = []

    # --- edad -------------------------------------------------------------
    for m in RE_EDAD.finditer(texto):
        antes = texto[max(0, m.start() - 32): m.start()]
        despues = texto[m.end(): m.end() + 24]
        if _ANTES_DURACION.search(antes) or _DESPUES_DURACION.search(despues):
            continue  # es una duracion clinica: NO se toca
        edad = int(m.group("num"))
        if edad > 120:
            continue
        out.append(_mk(unidad, "edad", texto, m.start(), m.end(), Confianza.ALTA))
    for m in RE_EDAD_ETIQUETA.finditer(texto):
        if not any(h.inicio <= m.start("num") < h.fin for h in out):
            out.append(_mk(unidad, "edad", texto, m.start("num"), m.end(),
                           Confianza.ALTA, "campo edad"))

    # --- fechas -----------------------------------------------------------
    ocupados = []
    for m in RE_FECHA_NACIMIENTO.finditer(texto):
        ini, fin = m.start("val"), m.end("val")
        out.append(_mk(unidad, "fecha_nacimiento", texto, ini, fin, Confianza.ALTA,
                       "fecha de nacimiento (cuasi-identificador fuerte)"))
        ocupados.append((ini, fin))
    for patron in RE_FECHAS:
        for m in patron.finditer(texto):
            if any(m.start() < f and i < m.end() for i, f in ocupados):
                continue
            ocupados.append((m.start(), m.end()))
            out.append(_mk(unidad, "fecha", texto, m.start(), m.end(), Confianza.ALTA))

    # --- ocupacion --------------------------------------------------------
    for m in RE_OCUPACION_ETIQUETA.finditer(texto):
        val = m.group("val").strip()
        out.append(_mk(unidad, "ocupacion", texto, m.start("val"),
                       m.start("val") + len(val), Confianza.ALTA, "campo ocupacion"))
    for m in RE_OCUPACION.finditer(pl):
        if any(h.inicio < m.end() and m.start() < h.fin for h in out):
            continue
        # OJO: en texto libre estas palabras suelen ser ADJETIVOS, no la
        # ocupacion del paciente ("consulta MEDICA", "Red MEDICA", "junta
        # MEDICA"). Sustituirlas por el sector destroza el documento, asi que
        # solo se marcan: la decision es humana.
        out.append(_mk(unidad, "posible_ocupacion", texto, m.start(), m.end(),
                       Confianza.BAJA,
                       "termino de ocupacion en texto libre: puede ser un "
                       "adjetivo y no la ocupacion de una persona"))

    # --- institucion ------------------------------------------------------
    for m in RE_INSTITUCION.finditer(texto):
        primera = plegar(m.group("nombre")).split()[0] if m.group("nombre") else ""
        if primera.strip(":.,") in ETIQUETAS_DE_CAMPO:
            continue   # es la etiqueta del campo siguiente, no el nombre
        out.append(_mk(unidad, "institucion", texto, m.start(), m.end(),
                       Confianza.ALTA))

    # --- aseguradora ------------------------------------------------------
    for m in RE_ASEGURADORA.finditer(pl):
        if any(h.inicio < m.end() and m.start() < h.fin for h in out):
            continue
        out.append(_mk(unidad, "aseguradora", texto, m.start(1), m.end(1),
                       Confianza.MEDIA))

    # --- localidad --------------------------------------------------------
    for m in RE_CIUDAD.finditer(pl):
        if any(h.inicio < m.end() and m.start() < h.fin for h in out):
            continue
        out.append(_mk(unidad, "localidad", texto, m.start(1), m.end(1),
                       Confianza.MEDIA))
    return out
