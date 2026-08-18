"""Politica de transformacion: que se hace con cada hallazgo.

Reglas explicitas y legibles. Nada aqui depende de un modelo.
La generalizacion NUNCA se aplica si el span pisa informacion clinica:
en ese caso la accion se degrada a "bloqueada por integridad clinica".
"""
from __future__ import annotations

import re
from datetime import date

from ...models import Accion, Confianza
from ...resources import lexicos as LX
from ...util.hashing import normalizar

# ---------------------------------------------------------------------------
# Seudonimos coherentes dentro de un mismo documento
# ---------------------------------------------------------------------------


class RegistroSeudonimos:
    """Mantiene la coherencia narrativa sin identificar.

    El mismo nombre siempre recibe la misma etiqueta dentro del documento.
    El mapa NO se guarda en la auditoria (seria una tabla de reidentificacion).
    """

    def __init__(self):
        self._mapa = {}
        self._contadores = {}

    def etiqueta(self, prefijo: str, valor: str, primero: str | None = None) -> str:
        clave = (prefijo, normalizar(valor))
        if clave in self._mapa:
            return self._mapa[clave]
        n = self._contadores.get(prefijo, 0) + 1
        self._contadores[prefijo] = n
        if n == 1 and primero:
            etq = primero
        else:
            etq = "[" + prefijo + " " + str(n) + "]"
        self._mapa[clave] = etq
        return etq

    def total(self, prefijo: str) -> int:
        return self._contadores.get(prefijo, 0)


# ---------------------------------------------------------------------------
# Generalizaciones
# ---------------------------------------------------------------------------
def banda_edad(edad: int) -> str:
    if edad < 0 or edad > 120:
        return "[EDAD]"
    if edad >= 90:
        return "90 anos o mas"
    if edad < 1:
        return "menor de 1 ano"
    base = (edad // 10) * 10
    return str(base) + "-" + str(base + 9) + " anos"


_RE_D_M_A = re.compile(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$")
_RE_A_M_D = re.compile(r"^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})$")
_RE_TEXTUAL = re.compile(
    r"^(\d{1,2})\s+de\s+([a-záéíóú]+)\s+(?:de[l]?\s+)?(\d{4})$", re.IGNORECASE
)
_RE_MES_ANO = re.compile(r"^([a-záéíóú]+)\s+(?:de[l]?\s+)?(\d{4})$", re.IGNORECASE)
_MESES_IDX = {m: i + 1 for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
     "septiembre", "octubre", "noviembre", "diciembre"])}
_MESES_IDX["setiembre"] = 9


def parsear_fecha(texto: str):
    """Devuelve (date, granularidad) o (None, '') si no se puede interpretar."""
    t = " ".join((texto or "").strip().split())
    m = _RE_D_M_A.match(t)
    if m:
        d, mes, a = int(m.group(1)), int(m.group(2)), int(m.group(3))
        a = a + 2000 if a < 100 else a
        try:
            return date(a, mes, d), "dia"
        except ValueError:
            return None, ""
    m = _RE_A_M_D.match(t)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3))), "dia"
        except ValueError:
            return None, ""
    m = _RE_TEXTUAL.match(t)
    if m:
        mes = _MESES_IDX.get(normalizar(m.group(2)))
        if mes:
            try:
                return date(int(m.group(3)), mes, int(m.group(1))), "dia"
            except ValueError:
                return None, ""
    m = _RE_MES_ANO.match(t)
    if m:
        mes = _MESES_IDX.get(normalizar(m.group(1)))
        if mes:
            return date(int(m.group(2)), mes, 1), "mes"
    return None, ""


class MapaCronologia:
    """Convierte fechas exactas en Dia 1 / Dia 2 / ... conservando el orden."""

    def __init__(self, fechas):
        unicas = sorted({f for f in fechas if f})
        self._mapa = {f: "Dia " + str(i + 1) for i, f in enumerate(unicas)}

    def etiqueta(self, f):
        return self._mapa.get(f)

    @property
    def tamano(self):
        return len(self._mapa)


# ---------------------------------------------------------------------------
# Tabla de decisiones
# ---------------------------------------------------------------------------
ELIMINAR_DIRECTO = {
    "email": "[CORREO ELIMINADO]",
    "url": "[ENLACE ELIMINADO]",
    "ip": "[IP ELIMINADA]",
    "usuario_red": "[USUARIO ELIMINADO]",
    "documento_identidad": "[DOCUMENTO ELIMINADO]",
    "historia_clinica": "[HISTORIA CLINICA ELIMINADA]",
    "numero_administrativo": "[IDENTIFICADOR ADMINISTRATIVO ELIMINADO]",
    "telefono_etiquetado": "[TELEFONO ELIMINADO]",
    "telefono": "[TELEFONO ELIMINADO]",
    "direccion": "[DIRECCION ELIMINADA]",
    "codigo_postal": "[CODIGO POSTAL ELIMINADO]",
    "firma_digital": "[FIRMA ELIMINADA]",
    "fecha_nacimiento": "[FECHA DE NACIMIENTO ELIMINADA]",
}

MOTIVOS = {
    "email": "identificador directo",
    "url": "identificador directo / posible rastro externo",
    "ip": "identificador tecnico directo",
    "usuario_red": "identificador directo en redes",
    "documento_identidad": "identificador directo",
    "historia_clinica": "identificador administrativo directo",
    "numero_administrativo": "identificador administrativo",
    "telefono_etiquetado": "identificador directo",
    "telefono": "identificador directo",
    "direccion": "identificador directo de localizacion",
    "codigo_postal": "identificador de localizacion",
    "firma_digital": "identificador directo del profesional",
    "fecha_nacimiento": "cuasi-identificador fuerte",
    "nombre_persona": "identificador directo",
    "nombre_profesional": "identificador directo del profesional",
    "edad": "minimizacion para la finalidad indicada",
    "fecha": "minimizacion: se conserva la cronologia relativa",
    "ocupacion": "minimizacion: se conserva el sector",
    "institucion": "identificador indirecto de contexto",
    "aseguradora": "identificador indirecto administrativo",
    "localidad": "minimizacion: se conserva la region",
    "posible_nombre": "candidato incierto: requiere criterio humano",
    "campo_identificador_dudoso": "campo etiquetado no clasificable",
}


class Politica:
    def __init__(self, finalidad, opciones=None):
        self.finalidad = finalidad
        self.opciones = opciones
        self.seudonimos = RegistroSeudonimos()
        self.cronologia = MapaCronologia([])

    def preparar_cronologia(self, hallazgos):
        fechas = []
        for h in hallazgos:
            if h.tipo == "fecha":
                f, gran = parsear_fecha(h.texto)
                if f and gran == "dia":
                    fechas.append(f)
        self.cronologia = MapaCronologia(fechas)

    # -- decision principal ------------------------------------------------
    def decidir(self, hallazgo):
        """Devuelve (accion, resultado, motivo, requiere_revision)."""
        tipo = hallazgo.tipo
        texto = hallazgo.texto
        motivo = MOTIVOS.get(tipo, "identificador detectado")

        if tipo in ELIMINAR_DIRECTO:
            return Accion.ELIMINAR, ELIMINAR_DIRECTO[tipo], motivo, False

        if tipo == "nombre_persona":
            es_paciente = "paciente" in (hallazgo.nota or "")
            etq = self.seudonimos.etiqueta(
                "PERSONA", texto, primero="[PACIENTE]" if es_paciente else None
            )
            return Accion.SUSTITUIR, etq, motivo, False

        if tipo == "nombre_profesional":
            etq = self.seudonimos.etiqueta("PROFESIONAL", texto)
            return Accion.SUSTITUIR, etq, motivo, False

        if tipo == "edad":
            if not self.finalidad.generalizar_edad:
                return (Accion.PRESERVAR, texto,
                        "la finalidad requiere la edad exacta", True)
            m = re.search(r"\d{1,3}", texto)
            if not m:
                return Accion.MARCAR_REVISION, texto, motivo, True
            return Accion.GENERALIZAR, banda_edad(int(m.group(0))), motivo, False

        if tipo == "fecha":
            if not self.finalidad.generalizar_fechas:
                return (Accion.PRESERVAR, texto,
                        "la finalidad conserva la cronologia exacta", True)
            f, gran = parsear_fecha(texto)
            if f and gran == "dia":
                etq = self.cronologia.etiqueta(f)
                if etq:
                    return Accion.GENERALIZAR, etq, motivo, False
            if f and gran == "mes":
                return (Accion.GENERALIZAR, "[MES/ANO ELIMINADO]",
                        motivo + " (granularidad mes)", False)
            return (Accion.MARCAR_REVISION, texto,
                    "fecha no interpretable de forma segura", True)

        if tipo == "ocupacion":
            sector = LX.sector_de(texto)
            if sector:
                if not self.finalidad.generalizar_ocupacion:
                    return Accion.PRESERVAR, texto, "la finalidad conserva la ocupacion", True
                return Accion.GENERALIZAR, sector, motivo, False
            return (Accion.SUSTITUIR, "[OCUPACION NO CLASIFICADA]",
                    motivo + " (sin sector conocido)", True)

        if tipo == "institucion":
            if self.finalidad.eliminar_institucion:
                return Accion.SUSTITUIR, "institucion de salud", motivo, False
            return Accion.PRESERVAR, texto, "la finalidad conserva la institucion", True

        if tipo == "aseguradora":
            return Accion.SUSTITUIR, "[ASEGURADORA]", motivo, False

        if tipo == "localidad":
            region = LX.region_de(texto)
            if not self.finalidad.generalizar_lugar:
                return Accion.PRESERVAR, texto, "la finalidad conserva el lugar", True
            if region:
                return Accion.GENERALIZAR, region, motivo, False
            return Accion.SUSTITUIR, "[LOCALIDAD]", motivo + " (region desconocida)", True

        if tipo in ("posible_nombre", "campo_identificador_dudoso"):
            sustituir = bool(getattr(self.opciones, "sustituir_posibles_nombres", False))
            if sustituir:
                etq = self.seudonimos.etiqueta("PERSONA", texto)
                return (Accion.SUSTITUIR, etq,
                        motivo + " (sustitucion agresiva activada por el usuario)", True)
            return (Accion.MARCAR_REVISION, texto, motivo, True)

        # tipo desconocido: no se toca, se marca
        return Accion.MARCAR_REVISION, texto, "tipo no cubierto por la politica", True
