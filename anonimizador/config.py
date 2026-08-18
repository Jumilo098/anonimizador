"""Configuracion global de ANONIMIZADOR.

Todo es local por diseno. Ninguna opcion de red esta activada.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from . import __version__

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = Path(os.environ.get("ANONIMIZADOR_REPORTS", BASE_DIR / "reports"))
SAMPLES_DIR = BASE_DIR / "samples"
WORKSPACE_DIR = Path(os.environ.get("ANONIMIZADOR_WORKSPACE", BASE_DIR / ".trabajo"))

# ---------------------------------------------------------------------------
# Limites de seguridad (bloque 29)
# ---------------------------------------------------------------------------
MAX_FILE_BYTES = 40 * 1024 * 1024          # 40 MB por archivo
MAX_FILES_PER_EXPEDIENTE = 40
MAX_TEXT_CHARS = 4_000_000                  # tope de texto procesado
MAX_IMAGE_PIXELS = 60_000_000               # anti "decompression bomb"
MAX_PDF_PAGES = 400

ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".docx", ".pdf", ".png", ".jpg", ".jpeg", ".xlsx",
}

# MIME/firma esperada por extension (validacion real, no confiar en el nombre)
MAGIC_SIGNATURES = {
    ".docx": [b"PK\x03\x04"],
    ".xlsx": [b"PK\x03\x04"],
    ".pdf": [b"%PDF-"],
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
}

# ---------------------------------------------------------------------------
# Red / IA: APAGADAS POR DEFECTO Y NO IMPLEMENTADAS EN V1
# ---------------------------------------------------------------------------
ALLOW_NETWORK = False          # V1: jamas se envia nada fuera del equipo
ENABLE_LLM = False             # capa opcional, desactivada
LLM_PROVIDER = None
ENABLE_TELEMETRY = False       # no existe telemetria

# ---------------------------------------------------------------------------
# Finalidades (bloque 2-A: ACLARE LA FINALIDAD)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finalidad:
    clave: str
    nombre: str
    descripcion: str
    # que categorias se minimizan agresivamente
    generalizar_edad: bool = True
    generalizar_fechas: bool = True
    generalizar_lugar: bool = True
    generalizar_ocupacion: bool = True
    eliminar_institucion: bool = True
    conservar_cronologia_relativa: bool = True
    notas: str = ""


FINALIDADES: dict[str, Finalidad] = {
    "educacion": Finalidad(
        clave="educacion",
        nombre="Educacion / discusion academica",
        descripcion=(
            "Material para clase, ateneo o discusion de caso. Se conserva solo lo "
            "clinicamente relevante; todo dato administrativo se elimina."
        ),
        notas="Valor predeterminado.",
    ),
    "publicacion": Finalidad(
        clave="publicacion",
        nombre="Publicacion / caso clinico escrito",
        descripcion=(
            "Minimizacion mas estricta: edad en decadas, sin lugar preciso, sin "
            "institucion, cronologia relativa (Dia 1, Dia 2...)."
        ),
    ),
    "interconsulta": Finalidad(
        clave="interconsulta",
        nombre="Interconsulta / segunda opinion",
        descripcion=(
            "Se preserva mas contexto temporal porque la cronologia exacta puede "
            "importar. Se eliminan identificadores directos igualmente."
        ),
        generalizar_fechas=False,
        generalizar_edad=False,
        notas="La edad exacta se conserva porque puede alterar la interpretacion.",
    ),
    "docencia_sintetica": Finalidad(
        clave="docencia_sintetica",
        nombre="Docencia con material declarado sintetico",
        descripcion=(
            "Caso construido para ensenar, sin paciente detras. Se minimiza "
            "igual que en educacion, y el archivo se sella como SINTETICO para "
            "que nadie lo confunda con un documento asistencial."
        ),
        notas="El sello no convierte en sintetico un documento real.",
    ),
    "investigacion": Finalidad(
        clave="investigacion",
        nombre="Investigacion / dataset interno",
        descripcion=(
            "Minimizacion fuerte y consistente. Requiere aprobacion del comite "
            "correspondiente: ANONIMIZADOR no la sustituye."
        ),
    ),
}

FINALIDAD_POR_DEFECTO = "educacion"

# ---------------------------------------------------------------------------
# Aviso permanente (bloque 33)
# ---------------------------------------------------------------------------
AVISO_PERMANENTE = (
    "ANONIMIZADOR reduce informacion identificable pero no garantiza "
    "anonimizacion absoluta. Revise siempre el documento antes de compartirlo. "
    "La aprobacion final corresponde a una persona."
)

ESTADO_TEXTO = (
    "Documento procesado mediante protocolo de desidentificacion. "
    "Existe riesgo residual. Requiere revision humana antes de compartir."
)

# Sello que se escribe DENTRO del documento generado, visible al abrirlo.
# Nunca dice "anonimizado", "irreversible" ni "riesgo cero".
AVISO_EN_DOCUMENTO = (
    "VERSION MINIMIZADA SUJETA A REVISION Y APROBACION HUMANA."
)
AVISO_EN_DOCUMENTO_SINTETICO = (
    "DOCUMENTO CLINICO SINTETICO. VERSION MINIMIZADA SUJETA A REVISION "
    "Y APROBACION HUMANA."
)

APP_VERSION = __version__


@dataclass
class Opciones:
    """Opciones por ejecucion."""

    finalidad: str = FINALIDAD_POR_DEFECTO
    redactar_regiones_imagen: bool = False   # destruir pixeles de regiones detectadas
    # Bandas superior/inferior de la imagen a borrar sin preguntar. En los
    # estudios (endoscopia, ecografia, radiologia) el nombre del paciente casi
    # siempre esta quemado ahi, y el area clinica esta en el centro. 0 = apagado.
    banda_superior_imagen: float = 0.0
    banda_inferior_imagen: float = 0.0
    eliminar_qr: bool = True                 # los QR/barcodes SI se destruyen
    # Sustituir candidatos a nombre de baja confianza. APAGADO por defecto:
    # borrar a ciegas una palabra capitalizada puede destrozar un termino
    # clinico que no este en el lexico (marca de un farmaco, epinimo...).
    sustituir_posibles_nombres: bool = False
    # --- entrega ---------------------------------------------------------
    # Autor que quedara en las propiedades del archivo generado. OJO: es un
    # identificador de QUIEN PREPARO el material, no del paciente; se escribe
    # solo si alguien lo pide de forma explicita.
    autor_salida: str = ""
    # Aviso visible dentro del documento (bloque 33 del protocolo).
    estampar_aviso: bool = True
    # Nombre del archivo generado, sin extension. Debe ser neutro.
    nombre_salida: str = "documento_desidentificado"
    conservar_copia_trabajo: bool = True
    etiquetas_personalizadas: dict = field(default_factory=dict)

    def finalidad_obj(self) -> Finalidad:
        return FINALIDADES.get(self.finalidad, FINALIDADES[FINALIDAD_POR_DEFECTO])
