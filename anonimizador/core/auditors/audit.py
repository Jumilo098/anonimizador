"""Expediente tecnico de cada ejecucion (bloque 16).

Produce:
  audit.json, transformation_matrix.csv, integrity_report.json,
  adversarial_scan.json, audit_report.html y RESUMEN.md

Regla: en los informes NO se escriben identificadores completos. Se guardan
enmascarados y con un hash salado que permite rastrearlos sin exponerlos.
"""
from __future__ import annotations

import csv
import html
import json
import platform
from datetime import datetime
from pathlib import Path

from ...config import AVISO_PERMANENTE, ESTADO_TEXTO, APP_VERSION
from ...models import Accion

COLUMNAS = [
    "categoria", "tipo", "capa", "hallazgo_enmascarado", "hallazgo_hash",
    "accion", "resultado", "motivo", "integridad_clinica", "riesgo_residual",
    "ruta", "confianza", "requiere_revision",
]


def _fila(t):
    d = t.as_row()
    return {c: d.get(c, "") for c in COLUMNAS}


def escribir_matriz(destino: Path, transformaciones):
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS, delimiter=";")
        w.writeheader()
        for t in transformaciones:
            w.writerow(_fila(t))
    return destino


def construir_auditoria(ctx) -> dict:
    """ctx es el diccionario que arma el pipeline."""
    conteo = {}
    for t in ctx["transformaciones"]:
        clave = t.accion.value if isinstance(t.accion, Accion) else str(t.accion)
        conteo[clave] = conteo.get(clave, 0) + 1
    por_categoria = {}
    for h in ctx["hallazgos"]:
        cat = h.categoria.value if hasattr(h.categoria, "value") else str(h.categoria)
        por_categoria.setdefault(cat, {})
        por_categoria[cat][h.tipo] = por_categoria[cat].get(h.tipo, 0) + 1

    return {
        "anonimizador": {
            "version": APP_VERSION,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "python": platform.python_version(),
            "sistema": platform.system() + " " + platform.release(),
            "procesamiento": "100% local, sin red, sin telemetria",
        },
        "ejecucion": {
            "id": ctx["ejecucion_id"],
            "finalidad": ctx["finalidad"],
            "finalidad_descripcion": ctx["finalidad_descripcion"],
            "opciones": ctx["opciones"],
        },
        "archivo_original": {
            "nombre_saneado": ctx["nombre_original"],
            "formato": ctx["formato"],
            "sha256": ctx["hash_original"],
            "bytes": ctx["tam_original"],
            "intacto_tras_el_proceso": ctx["original_intacto"],
        },
        "archivo_resultante": {
            "nombre": ctx["nombre_resultado"],
            "sha256": ctx["hash_resultado"],
            "bytes": ctx["tam_resultado"],
            "reconstruccion": ctx["modo_reconstruccion"],
            "capas_descartadas": ctx["capas_descartadas"],
        },
        "deteccion": {
            "unidades_de_texto": ctx["n_unidades"],
            "capas_inspeccionadas": ctx["capas"],
            "identificadores_por_categoria": por_categoria,
            "metadatos_detectados": ctx["metadatos_detectados"],
            "metadatos_eliminados": ctx["metadatos_eliminados"],
        },
        "transformaciones": {
            "total": len(ctx["transformaciones"]),
            "por_accion": conteo,
            "matriz": [_fila(t) for t in ctx["transformaciones"]],
        },
        "integridad_clinica": {
            "transformacion": ctx["integridad"],
            "reconstruccion": ctx["integridad_reconstruccion"],
            "alucinaciones": ctx["alucinaciones"],
        },
        "contexto": ctx["contextual"],
        "adversarial": ctx["adversarial"],
        "riesgo_residual": {
            "nivel": ctx["riesgo"],
            "motivos": ctx["motivos_riesgo"],
            "aviso": "Este puntaje no constituye una certificacion legal.",
        },
        "alertas": [
            {"nivel": a.nivel, "codigo": a.codigo, "mensaje": a.mensaje,
             "detalle": a.detalle}
            for a in ctx["alertas"]
        ],
        "revision_humana": {
            "estado": ctx["estado"],
            "aviso": AVISO_PERMANENTE,
            "texto_estado": ESTADO_TEXTO,
        },
    }


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
CSS = """
:root{color-scheme:light dark}
body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
 margin:0;padding:0 0 60px;background:#f6f7f9;color:#14181f}
.wrap{max-width:1100px;margin:0 auto;padding:24px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:28px 0 10px;
 border-bottom:2px solid #dfe3e8;padding-bottom:6px}
.aviso{background:#fff6e5;border:1px solid #f0c36d;padding:12px 14px;
 border-radius:8px;font-size:13px;margin:16px 0}
.card{background:#fff;border:1px solid #e2e6ea;border-radius:10px;padding:14px 16px;
 margin:10px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}
.kv{font-size:13px}.kv b{display:block;color:#5b6673;font-weight:600;font-size:11px;
 text-transform:uppercase;letter-spacing:.04em}
code{font-family:ui-monospace,Consolas,monospace;font-size:12px;word-break:break-all}
table{width:100%;border-collapse:collapse;font-size:12px;background:#fff}
th,td{border:1px solid #e2e6ea;padding:6px 8px;text-align:left;vertical-align:top}
th{background:#eef1f4;position:sticky;top:0}
.tabla-scroll{max-height:520px;overflow:auto;border:1px solid #e2e6ea;border-radius:8px}
.badge{display:inline-block;padding:3px 9px;border-radius:999px;font-size:11px;
 font-weight:700;letter-spacing:.03em}
.r-muybajo{background:#d8f5e3;color:#0d5c33}.r-bajo{background:#e3f2d8;color:#3a5c0d}
.r-moderado{background:#fff0cc;color:#7a5200}.r-alto{background:#ffdcdc;color:#8a1414}
.r-noevaluable{background:#e3e6ea;color:#3a4149}
.a-critica{border-left:4px solid #d33}.a-advertencia{border-left:4px solid #e8a33d}
.a-info{border-left:4px solid #5b9bd5}
.pass{color:#0d5c33;font-weight:700}.fail{color:#a11;font-weight:700}
.pie{font-size:11px;color:#5b6673;margin-top:26px;text-align:center}
"""


def _clase_riesgo(nivel: str) -> str:
    return "r-" + (nivel or "").lower().replace(" ", "")


def _esc(x):
    return html.escape(str(x if x is not None else ""))


def escribir_html(destino: Path, auditoria: dict) -> Path:
    a = auditoria
    riesgo = a["riesgo_residual"]["nivel"]
    partes = []
    ap = partes.append
    ap("<!doctype html><html lang='es'><head><meta charset='utf-8'>")
    ap("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    ap("<title>Auditoria ANONIMIZADOR</title><style>" + CSS + "</style></head><body>")
    ap("<div class='wrap'>")
    ap("<h1>ANONIMIZADOR &mdash; informe de auditoria</h1>")
    ap("<div class='kv'>Ejecucion <code>" + _esc(a["ejecucion"]["id"]) + "</code> &middot; "
       "version " + _esc(a["anonimizador"]["version"]) + " &middot; "
       + _esc(a["anonimizador"]["timestamp"]) + "</div>")
    ap("<div class='aviso'><b>" + _esc(AVISO_PERMANENTE) + "</b><br>"
       + _esc(ESTADO_TEXTO) + "</div>")

    # ficha
    ap("<h2>1. Ficha de la ejecucion</h2><div class='card grid'>")
    fichas = [
        ("Finalidad", a["ejecucion"]["finalidad"]),
        ("Formato", a["archivo_original"]["formato"]),
        ("Estado de revision", a["revision_humana"]["estado"]),
        ("Reconstruccion", a["archivo_resultante"]["reconstruccion"]),
        ("Original (bytes)", a["archivo_original"]["bytes"]),
        ("Resultado (bytes)", a["archivo_resultante"]["bytes"]),
        ("Original intacto", "SI" if a["archivo_original"]["intacto_tras_el_proceso"] else "NO"),
        ("Procesamiento", a["anonimizador"]["procesamiento"]),
    ]
    for k, v in fichas:
        ap("<div class='kv'><b>" + _esc(k) + "</b>" + _esc(v) + "</div>")
    ap("</div><div class='card'><div class='kv'><b>SHA-256 original</b><code>"
       + _esc(a["archivo_original"]["sha256"]) + "</code></div>"
       "<div class='kv' style='margin-top:8px'><b>SHA-256 resultado</b><code>"
       + _esc(a["archivo_resultante"]["sha256"]) + "</code></div></div>")

    # riesgo
    ap("<h2>2. Riesgo residual</h2><div class='card'>")
    ap("<span class='badge " + _clase_riesgo(riesgo) + "'>" + _esc(riesgo) + "</span>")
    ap("<ul>")
    for m in a["riesgo_residual"]["motivos"]:
        ap("<li>" + _esc(m) + "</li>")
    ap("</ul><p class='kv'>" + _esc(a["riesgo_residual"]["aviso"]) + "</p></div>")

    # alertas
    ap("<h2>3. Alertas</h2>")
    if not a["alertas"]:
        ap("<div class='card'>Sin alertas.</div>")
    for al in a["alertas"]:
        ap("<div class='card a-" + _esc(al["nivel"]) + "'><b>" + _esc(al["codigo"])
           + "</b> &mdash; " + _esc(al["mensaje"])
           + ("<div class='kv' style='margin-top:6px'>" + _esc(al["detalle"]) + "</div>"
              if al["detalle"] else "") + "</div>")

    # verificaciones
    ap("<h2>4. Verificaciones automaticas</h2><div class='card grid'>")
    integ = a["integridad_clinica"]["transformacion"]
    recon = a["integridad_clinica"]["reconstruccion"]
    aluc = a["integridad_clinica"]["alucinaciones"]
    adv = a["adversarial"]
    for etiqueta, veredicto in (
        ("Integridad clinica (transformacion)", integ.get("veredicto")),
        ("Integridad de la reconstruccion", recon.get("veredicto")),
        ("Deteccion de alucinaciones", aluc.get("veredicto")),
        ("Prueba adversarial", adv.get("veredicto")),
    ):
        clase = "pass" if veredicto == "PASS" else "fail"
        ap("<div class='kv'><b>" + _esc(etiqueta) + "</b><span class='" + clase
           + "'>" + _esc(veredicto) + "</span></div>")
    ap("</div>")

    filas_problema = (integ.get("unexpected_change", []) + integ.get("missing", [])
                      + integ.get("new_content", []))
    if filas_problema:
        ap("<div class='card'><b>Discrepancias clinicas</b>"
           "<div class='tabla-scroll'><table><tr><th>Estado</th><th>Clase</th>"
           "<th>Original</th><th>Resultado</th><th>Contexto</th></tr>")
        for f in filas_problema[:200]:
            ap("<tr><td>" + _esc(f.get("estado")) + "</td><td>" + _esc(f.get("clase"))
               + "</td><td>" + _esc(f.get("valor_original", f.get("valor", "")))
               + "</td><td>" + _esc(f.get("valor_resultante", ""))
               + "</td><td>" + _esc(f.get("contexto", "")) + "</td></tr>")
        ap("</table></div></div>")

    if adv.get("fugas"):
        ap("<div class='card a-critica'><b>Fugas encontradas al atacar el resultado</b>"
           "<table><tr><th>Tipo</th><th>Capa</th><th>Valor</th><th>Modulo responsable</th></tr>")
        for f in adv["fugas"][:100]:
            ap("<tr><td>" + _esc(f.get("tipo")) + "</td><td>" + _esc(f.get("capa"))
               + "</td><td>" + _esc(f.get("valor_enmascarado"))
               + "</td><td>" + _esc(f.get("modulo_responsable")) + "</td></tr>")
        ap("</table></div>")

    # matriz
    ap("<h2>5. Matriz de transformacion</h2>")
    conteo = a["transformaciones"]["por_accion"]
    ap("<div class='card' style='font-size:13px'>" + " &middot; ".join(
        _esc(k) + ": <span style='font-weight:700'>" + _esc(v) + "</span>"
        for k, v in sorted(conteo.items())) + "</div>")
    ap("<div class='tabla-scroll'><table><tr>"
       "<th>Categoria</th><th>Tipo</th><th>Capa</th><th>Hallazgo (enmascarado)</th>"
       "<th>Accion</th><th>Resultado</th><th>Motivo</th><th>Integridad clinica</th>"
       "<th>Riesgo residual</th></tr>")
    for f in a["transformaciones"]["matriz"]:
        ap("<tr><td>" + _esc(f["categoria"]) + "</td><td>" + _esc(f["tipo"])
           + "</td><td>" + _esc(f["capa"]) + "</td><td><code>"
           + _esc(f["hallazgo_enmascarado"]) + "</code></td><td>" + _esc(f["accion"])
           + "</td><td>" + _esc(f["resultado"]) + "</td><td>" + _esc(f["motivo"])
           + "</td><td>" + _esc(f["integridad_clinica"]) + "</td><td>"
           + _esc(f["riesgo_residual"]) + "</td></tr>")
    ap("</table></div>")

    # metadatos
    ap("<h2>6. Metadatos</h2><div class='card'>")
    ap("<div class='kv'><b>Detectados en el original</b>"
       + _esc(", ".join(a["deteccion"]["metadatos_detectados"]) or "ninguno") + "</div>")
    ap("<div class='kv' style='margin-top:8px'><b>Eliminados o neutralizados</b>"
       + _esc(", ".join(a["deteccion"]["metadatos_eliminados"]) or "ninguno") + "</div>")
    if adv.get("metadatos_residuales"):
        ap("<div class='kv' style='margin-top:8px'><b>Residuales en el resultado</b>"
           + _esc(", ".join(sorted(adv["metadatos_residuales"]))) + "</div>")
    ap("</div>")

    ap("<div class='pie'>ANONIMIZADOR " + _esc(a["anonimizador"]["version"])
       + " &middot; procesamiento local &middot; la aprobacion final corresponde a "
         "una persona.</div>")
    ap("</div></body></html>")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("".join(partes), encoding="utf-8")
    return destino


def escribir_resumen_md(destino: Path, auditoria: dict) -> Path:
    a = auditoria
    lineas = [
        "# ANONIMIZADOR - resumen legible",
        "",
        "> " + AVISO_PERMANENTE,
        "",
        "**" + ESTADO_TEXTO + "**",
        "",
        "| Campo | Valor |",
        "| --- | --- |",
        "| Ejecucion | `" + a["ejecucion"]["id"] + "` |",
        "| Finalidad | " + a["ejecucion"]["finalidad"] + " |",
        "| Formato | " + str(a["archivo_original"]["formato"]) + " |",
        "| Original intacto | " + ("SI" if a["archivo_original"]["intacto_tras_el_proceso"] else "NO") + " |",
        "| SHA-256 original | `" + a["archivo_original"]["sha256"][:32] + "...` |",
        "| SHA-256 resultado | `" + a["archivo_resultante"]["sha256"][:32] + "...` |",
        "| Riesgo residual | **" + a["riesgo_residual"]["nivel"] + "** |",
        "| Estado | " + a["revision_humana"]["estado"] + " |",
        "",
        "## Por que ese riesgo",
        "",
    ]
    for m in a["riesgo_residual"]["motivos"]:
        lineas.append("- " + m)
    lineas += ["", "## Verificaciones", ""]
    for etiqueta, clave in (
        ("Integridad clinica (transformacion)", "transformacion"),
        ("Integridad de la reconstruccion", "reconstruccion"),
    ):
        lineas.append("- " + etiqueta + ": **"
                      + str(a["integridad_clinica"][clave].get("veredicto")) + "**")
    lineas.append("- Deteccion de alucinaciones: **"
                  + str(a["integridad_clinica"]["alucinaciones"].get("veredicto")) + "**")
    lineas.append("- Prueba adversarial: **" + str(a["adversarial"].get("veredicto")) + "**")
    lineas += ["", "## Transformaciones", ""]
    for k, v in sorted(a["transformaciones"]["por_accion"].items()):
        lineas.append("- " + k + ": " + str(v))
    if a["alertas"]:
        lineas += ["", "## Alertas", ""]
        for al in a["alertas"]:
            lineas.append("- **" + al["nivel"].upper() + " " + al["codigo"] + "**: "
                          + al["mensaje"] + (" " + al["detalle"] if al["detalle"] else ""))
    lineas += ["", "---", "",
               "La aprobacion final corresponde a una persona. "
               "Este informe no es una certificacion legal."]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(lineas), encoding="utf-8")
    return destino


def guardar_json(destino: Path, datos) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2, default=str),
                       encoding="utf-8")
    return destino
