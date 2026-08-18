"""Capa 1: IDENTIFICADORES DIRECTOS.

Todo determinista: expresiones regulares + etiquetas + lexicos.
Cada hallazgo lleva una confianza explicita; la politica decide que hacer
con las confianzas medias y bajas.
"""
from __future__ import annotations

import re

from ...models import Capa, Categoria, Confianza, Hallazgo
from ...resources import lexicos as LX
from ...util.texto import plegar

DETECTOR = "directos"

# ---------------------------------------------------------------------------
# Patrones simples
# ---------------------------------------------------------------------------
PATRONES = [
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), Confianza.ALTA),
    ("url", re.compile(r"\bhttps?://[^\s<>\"')]+", re.I), Confianza.ALTA),
    ("usuario_red", re.compile(r"(?<![\w@.])@[A-Za-z][A-Za-z0-9._]{2,30}\b"), Confianza.MEDIA),
    # Octetos 0-255: si no se acota, una cedula "1.094.556.231" se clasifica
    # como direccion IP y el informe miente sobre lo que encontro.
    (
        "ip",
        re.compile(r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}"
                   r"(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])"),
        Confianza.ALTA,
    ),
    (
        "documento_identidad",
        re.compile(
            r"\b(?:c\.?\s?c\.?|t\.?\s?i\.?|c\.?\s?e\.?|n\.?\s?i\.?t\.?|dni|nie|rut|curp|"
            r"pasaporte|cedula|c[ée]dula|identificaci[oó]n|documento)\s*"
            r"(?:(?:n[oº°]|nro|num(?:ero)?)\.?\s*)?[:#\-]?\s*"
            # admite identificadores alfanumericos tipo CC-DEMO-640317, no solo
            # numeros: en muchos sistemas el documento no es puramente numerico
            r"(?P<val>[A-Z0-9][A-Z0-9.\-]{3,20}\d)",
            re.I,
        ),
        Confianza.ALTA,
    ),
    (
        "historia_clinica",
        re.compile(
            r"\b(?:h\.?\s?c\.?|historia\s+cl[ií]nica|hist\.?\s*cl[ií]n\.?|nhc|mrn|"
            r"expediente|folio)\s*(?:(?:n[oº°]|nro|num(?:ero)?)\.?\s*)?[:#\-]?\s*"
            r"(?P<val>[A-Z0-9][A-Z0-9.\-]{3,20}\d)",
            re.I,
        ),
        Confianza.ALTA,
    ),
    (
        "numero_administrativo",
        re.compile(
            r"\b(?:orden|autorizaci[oó]n|factura|remisi[oó]n|solicitud|radicado|"
            r"p[oó]liza|afiliado|carn[eé]|contrato|episodio|ingreso|cama|habitaci[oó]n)\s*"
            r"(?:(?:n[oº°]|nro|num(?:ero)?)\.?\s*)?[:#\-]?\s*(?P<val>[A-Z]{0,4}-?[\d][\d.\-/]{2,16})",
            re.I,
        ),
        Confianza.ALTA,
    ),
    (
        "telefono_etiquetado",
        re.compile(
            r"\b(?:tel[eé]fono|tel|cel|celular|m[oó]vil|movil|whatsapp|contacto|fax)\s*"
            r"[:#-]?\s*(?P<val>\+?[\d][\d\s().\-]{6,18}\d)",
            re.I,
        ),
        Confianza.ALTA,
    ),
    (
        "telefono",
        re.compile(r"(?<![\d.,/-])(?:\+\d{1,3}[\s.-]?)?3\d{2}[\s.-]?\d{3}[\s.-]?\d{4}(?![\d.,/-])"),
        Confianza.MEDIA,
    ),
    (
        # Solo se dispara si tras la palabra viene un numero o '#': asi no se
        # come nombres propios que empiezan por "Cl..." o "Av...".
        "direccion",
        re.compile(
            r"\b(?:calle|carrera|cra|kr|avenida|avda|diagonal|transversal|"
            r"manzana|urbanizaci[oó]n|apartamento|apto|autopista|carretera|"
            r"km|kil[oó]metro)\.?\s*(?=[\d#])[\w#\-\s.º°]{1,45}?"
            # el corte tambien ocurre ante 2+ espacios (columnas de un PDF) y
            # al final de linea: sin re.M el `$` solo miraba el fin del texto
            r"(?=[,;\n]|\.\s|\s{2,}|$)",
            re.I | re.M,
        ),
        Confianza.MEDIA,
    ),
    (
        "codigo_postal",
        re.compile(r"\b(?:c[oó]digo\s+postal|cp|zip)\s*[:#-]?\s*(?P<val>\d{4,6})\b", re.I),
        Confianza.ALTA,
    ),
    (
        # Quien firma es una persona: el valor llega hasta el fin de linea.
        "firma_digital",
        re.compile(r"\b(?:firmado\s+(?:digitalmente\s+)?por|firma\s+electr[oó]nica|"
                   r"suscrito\s+por)\s*[:#-]?\s*(?P<val>[^\n;|]{2,60})", re.I),
        Confianza.ALTA,
    ),
    (
        # El registro profesional es un codigo: se corta en el primer espacio.
        "firma_digital",
        re.compile(r"\b(?:registro(?:\s+(?:m[eé]dico|profesional))?|r\.?\s?m\.?|"
                   r"m\.?\s?p\.?|matr[ií]cula\s+profesional|colegiado|"
                   r"tarjeta\s+profesional)\s*(?:n[oº°]\.?\s*)?[:#-]?\s*"
                   # el calificativo no es el valor: "Registro medico 12345"
                   r"(?!m[eé]dico\b|profesional\b)(?P<val>[A-Z0-9][\w.\-/]{2,40})",
                   re.I),
        Confianza.ALTA,
    ),
]

# ---------------------------------------------------------------------------
# Nombres por etiqueta
# ---------------------------------------------------------------------------
ETIQUETAS_NOMBRE = [
    "paciente", "nombre del paciente", "nombres y apellidos", "nombre completo",
    "nombres", "nombre", "apellidos", "apellido", "acompanante", "acompañante",
    "responsable", "acudiente", "madre", "padre", "conyuge", "cónyuge",
    "esposo", "esposa", "hijo", "hija", "hermano", "hermana", "familiar",
    "contacto de emergencia", "medico tratante", "médico tratante", "medico",
    "médico", "profesional", "elaborado por", "realizado por", "informado por",
    "revisado por", "solicitado por", "remitido por", "atendido por",
    "enfermera", "enfermero", "auxiliar", "firma", "titular", "beneficiario",
    "usuario", "autor",
]

_ETQ_RE = "|".join(re.escape(e) for e in sorted(ETIQUETAS_NOMBRE, key=len, reverse=True))
RE_ETIQUETA_NOMBRE = re.compile(
    r"(?<![a-z])(?P<etq>" + _ETQ_RE + r")\s*[:\-]\s*(?P<val>[^\n\t|;]{2,70})",
    re.IGNORECASE,
)

RE_TRATAMIENTO = re.compile(
    r"\b(?P<trat>(?i:dr|dra|doctor|doctora|sr|sra|srta|lic|prof|enf))\.?\s+"
    r"(?P<val>(?:[A-ZÁ-Ú][a-zá-ú]+(?:\s+(?:de|del|la|los)\s+)?\s*){1,4})",
)

# Secuencias de palabras capitalizadas (heuristica)
RE_CAPITALIZADAS = re.compile(
    r"\b[A-ZÁ-Ú][a-zá-ú]{2,}(?:\s+(?:de|del|la|las|los)\s+[A-ZÁ-Ú][a-zá-ú]{2,}"
    r"|\s+[A-ZÁ-Ú][a-zá-ú]{2,}){1,3}\b"
)

_CORTE_VALOR = re.compile(
    r"\s{2,}|\t|\||;|\(|\s-\s|,\s*(?=[A-ZÁ-Ú][a-zá-ú]+\s*:)"
)


def _limpiar_valor(val: str) -> str:
    """Corta el valor de una etiqueta antes de que empiece el siguiente campo."""
    corte = _CORTE_VALOR.search(val)
    if corte:
        val = val[: corte.start()]
    return val.rstrip(" .;,:-")


def _parece_clinico(fragmento: str) -> bool:
    """Freno de mano: si el valor del campo es informacion clinica, no se toca."""
    palabras = {plegar(re.sub(r"[^\wÁ-ÿ]", "", t))
                for t in re.split(r"\s+", fragmento or "") if t}
    return bool(palabras & LX.TERMINOS_CLINICOS)


def _parece_nombre(fragmento: str):
    """(es_nombre, confianza). Nunca marca como nombre un termino clinico."""
    tokens = [t for t in re.split(r"\s+", fragmento.strip()) if t]
    if not tokens or len(tokens) > 6:
        return False, Confianza.BAJA
    utiles = [t for t in tokens if plegar(t) not in LX.PARTICULAS_APELLIDO]
    if not utiles:
        return False, Confianza.BAJA
    for t in utiles:
        p = plegar(re.sub(r"[^\wÁ-ÿ]", "", t))
        if not p:
            return False, Confianza.BAJA
        if p in LX.PALABRAS_NO_NOMBRE:
            return False, Confianza.BAJA
        if any(ch.isdigit() for ch in t):
            return False, Confianza.BAJA
    conocidos = sum(
        1
        for t in utiles
        if plegar(t) in LX.NOMBRES_PILA or plegar(t) in LX.APELLIDOS_FRECUENTES
    )
    if conocidos >= 1 and len(utiles) >= 2:
        return True, Confianza.ALTA
    if len(utiles) >= 2:
        return True, Confianza.MEDIA
    if conocidos >= 1:
        return True, Confianza.MEDIA
    return False, Confianza.BAJA


# Etiquetas cuyo VALOR es identificador aunque no lo reconozca ningun lexico:
# el nombre del empleador, del municipio o de la aseguradora no se pueden
# enumerar, pero la etiqueta que los precede si.
ETIQUETAS_VALOR_IDENTIFICADOR = {
    "empleador": "empleador", "empresa": "empleador", "patrono": "empleador",
    "lugar de trabajo": "empleador", "institucion": "institucion",
    "institución": "institucion", "entidad": "institucion",
    "sede": "institucion", "ips": "institucion", "eps": "aseguradora",
    "asegurador": "aseguradora", "aseguradora": "aseguradora",
    "seguro": "aseguradora", "plan": "aseguradora",
    "municipio": "localidad", "ciudad": "localidad", "localidad": "localidad",
    "barrio": "localidad", "vereda": "localidad", "corregimiento": "localidad",
    "departamento": "localidad", "residencia": "localidad",
    "lugar de nacimiento": "localidad", "procedencia": "localidad",
    "ocupacion": "ocupacion", "ocupación": "ocupacion",
    "profesion": "ocupacion", "profesión": "ocupacion",
    "oficio": "ocupacion", "cargo": "ocupacion",
    "edad": "edad",
}

_ETQ_VAL_RE = "|".join(
    re.escape(e) for e in sorted(ETIQUETAS_VALOR_IDENTIFICADOR, key=len, reverse=True)
)
RE_ETIQUETA_VALOR = re.compile(
    r"(?<![a-záéíóúñ])(?P<etq>" + _ETQ_VAL_RE + r")\s*[:=]\s*(?P<val>[^\n\t|;]{2,60})",
    re.IGNORECASE,
)


def _tipo_por_etiqueta(etiqueta: str):
    return ETIQUETAS_VALOR_IDENTIFICADOR.get(
        plegar(str(etiqueta or "")).strip(" :=.-")
    )


def detectar(unidad, spans_clinicos=None) -> list:
    """Devuelve los hallazgos directos de una unidad de texto."""
    texto = unidad.texto or ""
    hallazgos: list[Hallazgo] = []

    def nuevo(tipo, ini, fin, conf, nota="", ambito=None):
        if fin <= ini:
            return
        a_ini, a_fin = ambito if ambito else (ini, fin)
        hallazgos.append(
            Hallazgo(
                uid_unidad=unidad.uid,
                categoria=Categoria.DIRECTO,
                tipo=tipo,
                texto=texto[ini:fin],
                inicio=ini,
                fin=fin,
                capa=unidad.capa if isinstance(unidad.capa, Capa) else Capa.CONTENIDO,
                confianza=conf,
                detector=DETECTOR,
                nota=nota,
                ruta=unidad.ruta,
                amb_ini=a_ini,
                amb_fin=a_fin,
            )
        )

    for tipo, patron, conf in PATRONES:
        for m in patron.finditer(texto):
            if "val" in (patron.groupindex or {}):
                ini, fin = m.start("val"), m.end("val")
                # se elimina el valor, la etiqueta se conserva para legibilidad
            else:
                ini, fin = m.start(), m.end()
            nuevo(tipo, ini, fin, conf, ambito=(m.start(), m.end()))

    # campos cuyo valor identifica aunque el valor no este en ningun lexico
    for m in RE_ETIQUETA_VALOR.finditer(texto):
        tipo = _tipo_por_etiqueta(m.group("etq"))
        valor = _limpiar_valor(m.group("val"))
        if tipo and valor and not _parece_clinico(valor):
            nuevo(tipo, m.start("val"), m.start("val") + len(valor), Confianza.ALTA,
                  "campo '" + plegar(m.group("etq")) + "'",
                  ambito=(m.start(), m.start("val") + len(valor)))

    # celda de tabla cuya etiqueta esta en la celda de al lado
    tipo_celda = _tipo_por_etiqueta((unidad.meta or {}).get("etiqueta_previa", ""))
    if tipo_celda and texto.strip() and not _parece_clinico(texto):
        nuevo(tipo_celda, 0, len(texto.rstrip()), Confianza.ALTA,
              "valor de la celda etiquetada '"
              + plegar(unidad.meta["etiqueta_previa"]).strip() + "'")

    # nombres etiquetados
    for m in RE_ETIQUETA_NOMBRE.finditer(texto):
        bruto = m.group("val")
        limpio = _limpiar_valor(bruto)
        if not limpio:
            continue
        ini = m.start("val")
        fin = ini + len(limpio)
        es, conf = _parece_nombre(limpio)
        etiqueta = plegar(m.group("etq"))
        if es:
            nuevo("nombre_persona", ini, fin, Confianza.ALTA,
                  "etiqueta: " + etiqueta, ambito=(m.start(), fin))
        elif re.search(r"[A-Za-zÁ-ÿ]", limpio) and len(limpio) > 2:
            # el campo existe pero no parece nombre: se marca sin borrar
            nuevo("campo_identificador_dudoso", ini, fin, Confianza.BAJA,
                  "etiqueta '" + etiqueta + "' con valor no clasificable")

    # Dr./Dra. + nombre
    for m in RE_TRATAMIENTO.finditer(texto):
        limpio = _limpiar_valor(m.group("val"))
        if not limpio:
            continue
        es, conf = _parece_nombre(limpio)
        if es:
            nuevo("nombre_profesional", m.start("val"), m.start("val") + len(limpio),
                  Confianza.ALTA, "precedido por tratamiento",
                  ambito=(m.start(), m.start("val") + len(limpio)))

    # heuristica de capitalizadas
    ocupados = [h.ambito for h in hallazgos]
    for m in RE_CAPITALIZADAS.finditer(texto):
        if any(m.start() < f and i < m.end() for i, f in ocupados):
            continue
        es, conf = _parece_nombre(m.group(0))
        if es and conf == Confianza.ALTA:
            nuevo("nombre_persona", m.start(), m.end(), Confianza.ALTA,
                  "coincide con lexico de nombres/apellidos")
        elif es:
            nuevo("posible_nombre", m.start(), m.end(), Confianza.MEDIA,
                  "secuencia capitalizada sin respaldo en lexico")
    return hallazgos
