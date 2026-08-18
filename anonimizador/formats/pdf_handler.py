"""PDF: nada de falsa redaccion.

Un rectangulo negro encima de un texto seleccionable NO elimina nada.
Aqui se EXTRAE el texto, se minimiza y se ESCRIBE UN PDF NUEVO desde cero
con reportlab. El PDF resultante no comparte ni un objeto con el original.

Limitacion honesta de V1: la version reconstruida es SOLO TEXTO. Las
imagenes del PDF original no se transfieren (se reportan). Ver
docs/COBERTURA_Y_LIMITACIONES.md
"""
from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF
from reportlab import rl_config
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as rl_canvas

from ..config import MAX_PDF_PAGES
from ..models import Alerta, Capa, DocumentoExtraido
from . import codigos
from .base import (
    ManejadorFormato,
    aviso_documento,
    hallazgos_de_metadatos,
    unidad,
)

rl_config.invariant = 1  # sin fecha de creacion real: no filtramos cuando se proceso

MARCADORES_ACTIVOS = [
    (b"/JavaScript", "JavaScript embebido"),
    (b"/JS", "accion JavaScript"),
    (b"/OpenAction", "accion automatica al abrir"),
    (b"/Launch", "accion de lanzar programa"),
    (b"/EmbeddedFile", "archivo embebido"),
    (b"/RichMedia", "contenido multimedia"),
    (b"/AA", "acciones adicionales"),
]


class ManejadorPdf(ManejadorFormato):
    extensiones = (".pdf",)
    nombre = "pdf"
    reconstruccion = "parcial"   # solo texto: las imagenes no se transfieren
    capas_no_copiadas = frozenset({Capa.ANOTACION, Capa.FORMULARIO})

    def extraer(self, ruta: Path) -> DocumentoExtraido:
        ruta = Path(ruta)
        doc = DocumentoExtraido(formato="pdf")
        try:
            pdf = fitz.open(str(ruta))
        except Exception as exc:
            doc.alertas.append(
                Alerta("critica", "PDF_ILEGIBLE", "No se pudo abrir el PDF",
                       str(exc)[:200])
            )
            return doc
        if pdf.needs_pass:
            doc.alertas.append(
                Alerta("critica", "PDF_CIFRADO",
                       "El PDF esta protegido con contrasena. No se procesa.")
            )
            pdf.close()
            return doc

        paginas = min(pdf.page_count, MAX_PDF_PAGES)
        if pdf.page_count > MAX_PDF_PAGES:
            doc.alertas.append(
                Alerta("advertencia", "PDF_TRUNCADO",
                       "El PDF tiene %d paginas; se procesan las primeras %d."
                       % (pdf.page_count, MAX_PDF_PAGES))
            )

        total_imagenes = 0
        total_anotaciones = 0
        total_campos = 0
        codigos_detectados = []

        for i in range(paginas):
            pagina = pdf.load_page(i)
            texto = pagina.get_text("text")
            doc.unidades.append(
                unidad("pag%d" % (i + 1), texto, Capa.CONTENIDO,
                       "pagina[%d]" % (i + 1))
            )
            # anotaciones
            try:
                for j, anot in enumerate(pagina.annots() or []):
                    info = anot.info or {}
                    partes = [info.get("content", ""), info.get("title", ""),
                              info.get("subject", "")]
                    txt = " | ".join(p for p in partes if p)
                    if txt.strip():
                        total_anotaciones += 1
                        doc.unidades.append(
                            unidad("anot_%d_%d" % (i + 1, j), txt, Capa.ANOTACION,
                                   "pagina[%d].anotacion[%d]" % (i + 1, j),
                                   editable=False)
                        )
            except Exception:
                pass
            # formularios
            try:
                for k, w in enumerate(pagina.widgets() or []):
                    valor = " ".join(str(x) for x in
                                     [w.field_name, w.field_value] if x)
                    if valor.strip():
                        total_campos += 1
                        doc.unidades.append(
                            unidad("form_%d_%d" % (i + 1, k), valor, Capa.FORMULARIO,
                                   "pagina[%d].campo[%d]" % (i + 1, k),
                                   editable=False)
                        )
            except Exception:
                pass
            # imagenes
            try:
                imgs = pagina.get_images(full=True)
                total_imagenes += len(imgs)
                for img in imgs:
                    doc.activos.append({"tipo": "imagen", "pagina": i + 1,
                                        "xref": img[0]})
            except Exception:
                pass
            # enlaces
            try:
                for enlace in pagina.get_links() or []:
                    uri = enlace.get("uri")
                    if uri:
                        doc.unidades.append(
                            unidad("link_%d_%s" % (i + 1, uri[:12]), uri,
                                   Capa.ANOTACION, "pagina[%d].enlace" % (i + 1),
                                   editable=False)
                        )
            except Exception:
                pass
            # QR / barcodes sobre el render de la pagina
            if codigos.disponible():
                try:
                    pix = pagina.get_pixmap(dpi=150)
                    import numpy as np
                    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                        pix.height, pix.width, pix.n
                    )
                    for c in codigos.detectar_codigos(arr):
                        c["pagina"] = i + 1
                        codigos_detectados.append(c)
                except Exception:
                    pass

        # metadatos
        metadatos = dict(pdf.metadata or {})
        try:
            xmp = pdf.get_xml_metadata()
            if xmp:
                metadatos["xmp"] = xmp[:1000]
        except Exception:
            pass
        try:
            if pdf.embfile_count() > 0:
                metadatos["archivos_embebidos"] = ", ".join(pdf.embfile_names())
                doc.alertas.append(
                    Alerta("critica", "ARCHIVOS_EMBEBIDOS",
                           "El PDF contiene archivos embebidos.",
                           "No se abren ni se transfieren al resultado.")
                )
        except Exception:
            pass
        pdf.close()

        # marcadores activos en el binario (sin ejecutar nada)
        crudo = ruta.read_bytes()
        activos = [d for m, d in MARCADORES_ACTIVOS if m in crudo]
        if activos:
            doc.alertas.append(
                Alerta("advertencia", "PDF_CON_ACCIONES",
                       "El PDF declara elementos activos.",
                       "Detectado: " + ", ".join(sorted(set(activos)))
                       + ". ANONIMIZADOR no los ejecuta y no los copia.")
            )

        doc.metadatos = metadatos
        doc.hallazgos_tecnicos = hallazgos_de_metadatos(metadatos)
        doc.unidades.append(
            unidad("nombre_archivo", ruta.stem, Capa.NOMBRE_ARCHIVO,
                   "nombre del archivo")
        )
        caracteres = sum(len(u.texto or "") for u in doc.unidades
                         if u.capa == Capa.CONTENIDO)
        escaneado = bool(total_imagenes) and caracteres < 120 * max(paginas, 1)
        doc.info = {
            "paginas": paginas,
            "caracteres_texto": caracteres,
            "probablemente_escaneado": escaneado,
            "imagenes": total_imagenes,
            "anotaciones": total_anotaciones,
            "campos_formulario": total_campos,
            "codigos_graficos": codigos_detectados,
        }
        if total_imagenes:
            doc.alertas.append(
                Alerta("advertencia", "IMAGENES_EN_PDF",
                       "El PDF contiene %d imagen(es)." % total_imagenes,
                       "V1 reconstruye SOLO TEXTO: las imagenes no se transfieren "
                       "y sus pixeles no se analizan. Trate cada imagen aparte.")
            )
        if escaneado:
            doc.alertas.append(
                Alerta("critica", "PDF_PROBABLEMENTE_ESCANEADO",
                       "Este PDF casi no tiene texto extraible y si tiene imagenes: "
                       "parece un documento escaneado.",
                       "V1 reconstruye SOLO TEXTO. Con un PDF escaneado el resultado "
                       "quedaria practicamente vacio y el analisis NO es concluyente. "
                       "Exporte cada pagina como imagen y procesela por separado, o "
                       "instale OCR local. NO use este resultado sin revisarlo.")
            )
        if codigos_detectados:
            doc.alertas.append(
                Alerta("critica", "CODIGOS_GRAFICOS",
                       "Se detectaron %d codigo(s) QR/barras." % len(codigos_detectados),
                       "No se transfieren al PDF reconstruido. Nunca se abre su URL.")
            )
        return doc

    # -- reconstruccion ----------------------------------------------------
    def reconstruir(self, extraido, unidades_nuevas, destino: Path, contexto=None):
        destino = Path(destino)
        paginas = [u for u in unidades_nuevas
                   if u.capa == Capa.CONTENIDO and u.uid.startswith("pag")]
        paginas.sort(key=lambda u: int(u.uid[3:]) if u.uid[3:].isdigit() else 0)

        ancho, alto = A4
        margen = 2 * cm
        fuente, tamano, interlineado = "Helvetica", 10, 13.5
        c = rl_canvas.Canvas(str(destino), pagesize=A4)
        opciones = getattr(contexto, "opciones", None)
        aviso = aviso_documento(opciones)
        c.setTitle("Documento desidentificado")
        c.setAuthor(str(getattr(opciones, "autor_salida", "") or ""))
        c.setSubject("")
        c.setKeywords("")
        c.setCreator("ANONIMIZADOR")

        esperado = []

        def sello():
            """Aviso visible en cada pagina, fuera del cuerpo del texto."""
            if not aviso:
                return
            c.setFont("Helvetica-Bold", 7.5)
            c.drawString(margen, alto - margen + 14, aviso)
            c.setFont(fuente, tamano)

        def escribir_lineas(lineas):
            y = alto - margen
            sello()
            c.setFont(fuente, tamano)
            for linea in lineas:
                for trozo in _envolver(linea, ancho - 2 * margen, fuente, tamano):
                    if y < margen:
                        c.showPage()
                        sello()
                        c.setFont(fuente, tamano)
                        y = alto - margen
                    c.drawString(margen, y, trozo)
                    y -= interlineado
            c.showPage()

        for u in paginas:
            texto = u.texto or ""
            esperado.append(texto)
            if aviso:
                esperado.append(aviso)
            escribir_lineas(texto.split("\n"))

        anexos = [u for u in unidades_nuevas
                  if u.capa in (Capa.ANOTACION, Capa.FORMULARIO) and u.texto.strip()]
        descartadas = []
        if anexos:
            descartadas.append("anotaciones y campos de formulario (se reportan, "
                               "no se copian)")
        c.save()

        return {
            "texto_esperado": "\n".join(esperado),
            "capas_descartadas": descartadas,
            "notas": [
                "PDF generado desde cero con reportlab: solo texto.",
                "No se copian objetos, anotaciones, formularios, imagenes, "
                "codigos QR ni metadatos del original.",
                "La redaccion NO es un rectangulo encima: el texto identificador "
                "simplemente no se escribe.",
            ],
        }

    def reescanear(self, ruta: Path):
        return self.extraer(ruta)


def _envolver(linea: str, ancho_max: float, fuente: str, tamano: int):
    """Corta una linea por palabras para que quepa en la pagina."""
    if not linea:
        return [""]
    palabras = linea.split(" ")
    salida, actual = [], ""
    for palabra in palabras:
        prueba = (actual + " " + palabra).strip()
        if stringWidth(prueba, fuente, tamano) <= ancho_max:
            actual = prueba
        else:
            if actual:
                salida.append(actual)
            while stringWidth(palabra, fuente, tamano) > ancho_max and len(palabra) > 1:
                corte = max(1, int(len(palabra) * ancho_max
                                   / max(stringWidth(palabra, fuente, tamano), 1)))
                salida.append(palabra[:corte])
                palabra = palabra[corte:]
            actual = palabra
    if actual:
        salida.append(actual)
    return salida or [""]
