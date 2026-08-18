"""Convierte los documentos Markdown de docs/ a PDF con reportlab (local).

Uso:
    python docs/generar_pdf.py                 # convierte los dos informes
    python docs/generar_pdf.py archivo.md      # convierte uno concreto

Soporta lo que usan estos documentos: titulos, parrafos, listas, tablas,
citas, codigo y separadores. No pretende ser un renderizador Markdown
completo; es suficiente y no anade ninguna dependencia nueva.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

DOCS = Path(__file__).resolve().parent

BASE = getSampleStyleSheet()
ESTILOS = {
    "h1": ParagraphStyle("h1", parent=BASE["Heading1"], fontSize=19, spaceBefore=14,
                         spaceAfter=10, textColor=colors.HexColor("#14181f")),
    "h2": ParagraphStyle("h2", parent=BASE["Heading2"], fontSize=14, spaceBefore=14,
                         spaceAfter=8, textColor=colors.HexColor("#1e3a5f")),
    "h3": ParagraphStyle("h3", parent=BASE["Heading3"], fontSize=11.5, spaceBefore=10,
                         spaceAfter=6, textColor=colors.HexColor("#1e3a5f")),
    "p": ParagraphStyle("p", parent=BASE["BodyText"], fontSize=9.5, leading=13.5,
                        alignment=TA_JUSTIFY, spaceAfter=6),
    "li": ParagraphStyle("li", parent=BASE["BodyText"], fontSize=9.5, leading=13),
    "cita": ParagraphStyle("cita", parent=BASE["BodyText"], fontSize=9.5, leading=13.5,
                           leftIndent=12, borderPadding=6, backColor=colors.HexColor("#fff6e5"),
                           borderColor=colors.HexColor("#f0c36d"), borderWidth=0.8,
                           spaceBefore=6, spaceAfter=8),
    "codigo": ParagraphStyle("codigo", parent=BASE["Code"], fontSize=8.3, leading=11,
                             backColor=colors.HexColor("#f2f4f6"), borderPadding=6,
                             spaceBefore=4, spaceAfter=8),
    "celda": ParagraphStyle("celda", parent=BASE["BodyText"], fontSize=8, leading=10.5),
    "celda_th": ParagraphStyle("celda_th", parent=BASE["BodyText"], fontSize=8,
                               leading=10.5, textColor=colors.white),
}

_EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF☀-➿️←-⇿⬀-⯿]+"
)


def _inline(texto: str) -> str:
    """Markdown en linea -> etiquetas que entiende reportlab."""
    t = _EMOJI.sub("", texto)
    t = html.escape(t)
    t = re.sub(r"`([^`]+)`", r'<font face="Courier" size="8.5">\1</font>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'\1 <font color="#365f9c">(\2)</font>', t)
    t = re.sub(r"&lt;(https?://[^&]+)&gt;", r'<font color="#365f9c">\1</font>', t)
    return t


def _tabla(filas, ancho_util):
    encabezado = [Paragraph(_inline(c), ESTILOS["celda_th"]) for c in filas[0]]
    cuerpo = [[Paragraph(_inline(c), ESTILOS["celda"]) for c in fila]
              for fila in filas[1:]]
    columnas = max(len(f) for f in filas)
    ancho = ancho_util / columnas
    t = Table([encabezado] + cuerpo, colWidths=[ancho] * columnas, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9cfd6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f6f7f9")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def convertir(md: Path, pdf: Path | None = None) -> Path:
    pdf = pdf or md.with_suffix(".pdf")
    lineas = md.read_text(encoding="utf-8").splitlines()
    ancho_util = A4[0] - 4 * cm

    flujo = []
    i = 0
    while i < len(lineas):
        linea = lineas[i]
        desnuda = linea.strip()

        if not desnuda:
            i += 1
            continue

        if desnuda.startswith("```"):
            i += 1
            bloque = []
            while i < len(lineas) and not lineas[i].strip().startswith("```"):
                bloque.append(lineas[i])
                i += 1
            i += 1
            texto = html.escape("\n".join(bloque)).replace(" ", "&nbsp;")
            flujo.append(Paragraph(texto.replace("\n", "<br/>"), ESTILOS["codigo"]))
            continue

        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", desnuda):
            flujo.append(Spacer(1, 4))
            flujo.append(HRFlowable(width="100%", color=colors.HexColor("#c9cfd6")))
            flujo.append(Spacer(1, 6))
            i += 1
            continue

        if desnuda.startswith("|"):
            filas = []
            while i < len(lineas) and lineas[i].strip().startswith("|"):
                celdas = [c.strip() for c in lineas[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c or "-") for c in celdas):
                    filas.append(celdas)
                i += 1
            if filas:
                flujo.append(_tabla(filas, ancho_util))
                flujo.append(Spacer(1, 8))
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", desnuda)
        if m:
            nivel = min(len(m.group(1)), 3)
            if nivel == 1 and flujo:
                flujo.append(PageBreak())
            flujo.append(Paragraph(_inline(m.group(2)), ESTILOS["h%d" % nivel]))
            i += 1
            continue

        if desnuda.startswith(">"):
            bloque = []
            while i < len(lineas) and lineas[i].strip().startswith(">"):
                bloque.append(lineas[i].strip().lstrip(">").strip())
                i += 1
            flujo.append(Paragraph(_inline(" ".join(bloque)), ESTILOS["cita"]))
            continue

        if re.match(r"^([-*+]|\d+\.)\s+", desnuda):
            elementos = []
            while i < len(lineas) and re.match(r"^\s*([-*+]|\d+\.)\s+", lineas[i]):
                texto = re.sub(r"^\s*([-*+]|\d+\.)\s+", "", lineas[i])
                i += 1
                while (i < len(lineas) and lineas[i].startswith("  ")
                       and not re.match(r"^\s*([-*+]|\d+\.)\s+", lineas[i])
                       and lineas[i].strip()):
                    texto += " " + lineas[i].strip()
                    i += 1
                elementos.append(ListItem(Paragraph(_inline(texto), ESTILOS["li"]),
                                          leftIndent=14))
            flujo.append(ListFlowable(elementos, bulletType="bullet",
                                      start="•", leftIndent=14))
            flujo.append(Spacer(1, 6))
            continue

        parrafo = [desnuda]
        i += 1
        while i < len(lineas) and lineas[i].strip() and not re.match(
                r"^(#{1,6}\s|\||>|```|[-*+]\s|\d+\.\s|-{3,}$)", lineas[i].strip()):
            parrafo.append(lineas[i].strip())
            i += 1
        flujo.append(Paragraph(_inline(" ".join(parrafo)), ESTILOS["p"]))

    doc = SimpleDocTemplate(
        str(pdf), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title=md.stem, author="ANONIMIZADOR", subject="",
    )

    def pie(canvas, documento):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#6b7480"))
        canvas.drawString(2 * cm, 1.1 * cm,
                          "ANONIMIZADOR - no garantiza anonimizacion absoluta; "
                          "la aprobacion final corresponde a una persona.")
        canvas.drawRightString(A4[0] - 2 * cm, 1.1 * cm, str(documento.page))
        canvas.restoreState()

    doc.build(flujo, onFirstPage=pie, onLaterPages=pie)
    return pdf


def main(argv=None):
    argv = argv or sys.argv[1:]
    objetivos = [Path(a) for a in argv] or sorted(DOCS.glob("*.md"))
    for md in objetivos:
        salida = convertir(md)
        print("generado:", salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
