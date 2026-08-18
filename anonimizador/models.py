"""Modelo de datos comun del pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enumeraciones
# ---------------------------------------------------------------------------
class Capa(str, Enum):
    """Donde vive la informacion dentro del documento."""

    CONTENIDO = "contenido"
    ENCABEZADO = "encabezado"
    PIE = "pie"
    TABLA = "tabla"
    COMENTARIO = "comentario"
    CONTROL_CAMBIOS = "control_cambios"
    METADATOS = "metadatos"
    NOMBRE_ARCHIVO = "nombre_archivo"
    ANOTACION = "anotacion"
    FORMULARIO = "formulario"
    PIXELES = "imagen_pixeles"
    XML_INTERNO = "xml_interno"
    OBJETO_EMBEBIDO = "objeto_embebido"
    CODIGO_GRAFICO = "codigo_grafico"   # QR / barcode
    HOJA_CALCULO = "hoja_calculo"


class Categoria(str, Enum):
    """Las cinco capas de tamizado del bloque 2-T."""

    DIRECTO = "identificador_directo"
    INDIRECTO = "identificador_indirecto"
    CONTEXTUAL = "identificador_contextual"
    VISUAL = "identificador_visual"
    TECNICO = "identificador_tecnico"
    CLINICO = "dato_clinico"            # NO es identificador: se protege


class Accion(str, Enum):
    ELIMINAR = "eliminar"
    SUSTITUIR = "sustituir"
    GENERALIZAR = "generalizar"
    PRESERVAR = "preservar"
    MARCAR_REVISION = "marcar_para_revision"
    DESTRUIR_PIXELES = "destruir_pixeles"
    NO_APLICADA_POR_SEGURIDAD_CLINICA = "bloqueada_por_integridad_clinica"


class Integridad(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    EXPECTED_TRANSFORMATION = "EXPECTED_TRANSFORMATION"
    UNEXPECTED_CHANGE = "UNEXPECTED_CHANGE"
    MISSING = "MISSING"
    NEW_CONTENT = "NEW_CONTENT"
    NO_APLICA = "N/A"


class Riesgo(str, Enum):
    MUY_BAJO = "MUY BAJO"
    BAJO = "BAJO"
    MODERADO = "MODERADO"
    ALTO = "ALTO"
    NO_EVALUABLE = "NO EVALUABLE"


ORDEN_RIESGO = {
    Riesgo.MUY_BAJO: 0,
    Riesgo.BAJO: 1,
    Riesgo.MODERADO: 2,
    Riesgo.ALTO: 3,
    Riesgo.NO_EVALUABLE: 4,
}


class EstadoRevision(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED_BY_HUMAN = "APPROVED_BY_HUMAN"
    REJECTED_BY_HUMAN = "REJECTED_BY_HUMAN"
    REQUIRES_MANUAL_REVIEW = "REQUIRES_MANUAL_REVIEW"


class Confianza(str, Enum):
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


# ---------------------------------------------------------------------------
# Unidades de texto
# ---------------------------------------------------------------------------
@dataclass
class UnidadTexto:
    """Un fragmento de texto con su procedencia dentro del documento."""

    uid: str
    texto: str
    capa: Capa = Capa.CONTENIDO
    ruta: str = ""            # p.ej. "parrafo[3]" / "docProps/core.xml:author"
    editable: bool = True     # si False, solo se reporta (no se reescribe)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Hallazgo:
    """Algo potencialmente identificador (o clinico protegido) detectado."""

    uid_unidad: str
    categoria: Categoria
    tipo: str                  # "email", "telefono", "edad", "hemoglobina"...
    texto: str
    inicio: int
    fin: int
    capa: Capa = Capa.CONTENIDO
    confianza: Confianza = Confianza.ALTA
    detector: str = ""
    nota: str = ""
    ruta: str = ""
    # "ambito" = trozo completo que reconocio el patron (etiqueta incluida).
    # Se usa SOLO para resolver solapes entre detectores; la transformacion
    # siempre se aplica sobre (inicio, fin).
    amb_ini: int = -1
    amb_fin: int = -1

    @property
    def longitud(self) -> int:
        return self.fin - self.inicio

    @property
    def ambito(self) -> tuple:
        ini = self.amb_ini if self.amb_ini >= 0 else self.inicio
        fin = self.amb_fin if self.amb_fin >= 0 else self.fin
        return (min(ini, self.inicio), max(fin, self.fin))


@dataclass
class Transformacion:
    """Una fila de la matriz de transformacion (bloque 13)."""

    categoria: str
    tipo: str
    capa: str
    hallazgo_enmascarado: str
    hallazgo_hash: str
    accion: Accion
    resultado: str
    motivo: str
    integridad_clinica: str
    riesgo_residual: str
    ruta: str = ""
    confianza: str = Confianza.ALTA.value
    requiere_revision: bool = False

    def as_row(self) -> dict[str, Any]:
        d = asdict(self)
        d["accion"] = self.accion.value if isinstance(self.accion, Accion) else self.accion
        return d


@dataclass
class Alerta:
    nivel: str            # "info" | "advertencia" | "critica"
    codigo: str
    mensaje: str
    detalle: str = ""


@dataclass
class ValorClinico:
    """Unidad atomica que la validacion de integridad compara."""

    clase: str            # numero_unidad | signo_vital | anatomia | lateralidad ...
    texto: str
    normalizado: str
    contexto: str = ""

    def key(self) -> tuple[str, str]:
        return (self.clase, self.normalizado)


@dataclass
class DocumentoExtraido:
    """Lo que un handler de formato entrega al pipeline."""

    formato: str
    unidades: list[UnidadTexto] = field(default_factory=list)
    metadatos: dict[str, Any] = field(default_factory=dict)
    activos: list[dict[str, Any]] = field(default_factory=list)   # imagenes, embebidos
    hallazgos_tecnicos: list[Hallazgo] = field(default_factory=list)
    alertas: list[Alerta] = field(default_factory=list)
    info: dict[str, Any] = field(default_factory=dict)

    def texto_plano(self) -> str:
        return "\n".join(u.texto for u in self.unidades if u.texto)


@dataclass
class ResultadoPipeline:
    ejecucion_id: str
    estado: EstadoRevision = EstadoRevision.PENDING_REVIEW
    riesgo: Riesgo = Riesgo.NO_EVALUABLE
    motivos_riesgo: list[str] = field(default_factory=list)
    transformaciones: list[Transformacion] = field(default_factory=list)
    alertas: list[Alerta] = field(default_factory=list)
    hallazgos: list[Hallazgo] = field(default_factory=list)
    integridad: dict[str, Any] = field(default_factory=dict)
    adversarial: dict[str, Any] = field(default_factory=dict)
    auditoria: dict[str, Any] = field(default_factory=dict)
    archivos: dict[str, str] = field(default_factory=dict)
    texto_original: str = ""
    texto_resultante: str = ""
    ok: bool = True
    error: str = ""
