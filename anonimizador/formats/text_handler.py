"""Texto plano (.txt, .md). El caso mas simple y el mas facil de verificar."""
from __future__ import annotations

from pathlib import Path

from ..config import MAX_TEXT_CHARS
from ..models import Capa, DocumentoExtraido
from ..util.safety import leer_texto
from .base import ManejadorFormato, hallazgos_de_metadatos, unidad


class ManejadorTexto(ManejadorFormato):
    extensiones = (".txt", ".md")
    nombre = "texto"
    reconstruccion = "completa"

    def extraer(self, ruta: Path) -> DocumentoExtraido:
        ruta = Path(ruta)
        texto = leer_texto(ruta)[:MAX_TEXT_CHARS]
        doc = DocumentoExtraido(formato="txt")
        doc.unidades.append(unidad("cuerpo", texto, Capa.CONTENIDO, "documento"))
        doc.unidades.append(
            unidad("nombre_archivo", ruta.stem, Capa.NOMBRE_ARCHIVO,
                   "nombre del archivo")
        )
        doc.metadatos = {}
        doc.hallazgos_tecnicos = hallazgos_de_metadatos(doc.metadatos)
        doc.info = {"caracteres": len(texto), "lineas": texto.count("\n") + 1}
        return doc

    def reconstruir(self, extraido, unidades_nuevas, destino: Path, contexto=None):
        cuerpo = next((u for u in unidades_nuevas if u.uid == "cuerpo"), None)
        texto = cuerpo.texto if cuerpo else ""
        destino = Path(destino)
        destino.write_text(texto, encoding="utf-8")
        return {
            "texto_esperado": texto,
            "capas_descartadas": [],
            "notas": ["Archivo de texto reescrito desde cero, sin metadatos."],
        }
