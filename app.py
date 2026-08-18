"""ANONIMIZADOR - interfaz local (Streamlit).

Arrancar con:  iniciar.bat   (Windows)   /   ./start.sh   (macOS y Linux)
o bien:        streamlit run app.py

Todo el procesamiento ocurre en este equipo. No hay red, ni nube, ni telemetria.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from anonimizador import __version__, casos_sinteticos  # noqa: E402
from anonimizador.config import (  # noqa: E402
    AVISO_PERMANENTE,
    ESTADO_TEXTO,
    FINALIDADES,
    FINALIDAD_POR_DEFECTO,
    MAX_FILE_BYTES,
    Opciones,
    REPORTS_DIR,
    WORKSPACE_DIR,
)
from anonimizador.core import pipeline  # noqa: E402
from anonimizador.formats import registry  # noqa: E402
from anonimizador.formats.image_handler import ocr_disponible  # noqa: E402
from anonimizador.models import EstadoRevision, Riesgo  # noqa: E402
from anonimizador.util import workspace  # noqa: E402
from anonimizador.util.safety import sanear_nombre  # noqa: E402

COLOR_RIESGO = {
    Riesgo.MUY_BAJO.value: "#0d5c33",
    Riesgo.BAJO.value: "#3a5c0d",
    Riesgo.MODERADO.value: "#8a6200",
    Riesgo.ALTO.value: "#8a1414",
    Riesgo.NO_EVALUABLE.value: "#3a4149",
}

st.set_page_config(page_title="ANONIMIZADOR", page_icon="🩺", layout="wide")

ENTRADA = WORKSPACE_DIR / "_entrada"


def _guardar_subidos(archivos):
    ENTRADA.mkdir(parents=True, exist_ok=True)
    rutas = []
    for archivo in archivos:
        nombre = sanear_nombre(archivo.name)
        destino = ENTRADA / nombre
        destino.write_bytes(archivo.getbuffer())
        rutas.append(destino)
    return rutas


def _badge(texto, color):
    st.markdown(
        "<span style='background:%s;color:#fff;padding:4px 12px;border-radius:999px;"
        "font-weight:700;font-size:13px'>%s</span>" % (color, texto),
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Cabecera + aviso permanente (bloque 33)
# ---------------------------------------------------------------------------
st.title("ANONIMIZADOR")
st.caption("Desidentificacion local de documentos clinicos - version " + __version__)
st.warning("**" + AVISO_PERMANENTE + "**")

# ---------------------------------------------------------------------------
# Barra lateral
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("1. Finalidad")
    st.caption("Se conserva solo lo necesario para esta finalidad.")
    claves = list(FINALIDADES)
    finalidad = st.selectbox(
        "¿Para que va a usar el material?",
        claves,
        index=claves.index(FINALIDAD_POR_DEFECTO),
        format_func=lambda k: FINALIDADES[k].nombre,
    )
    st.info(FINALIDADES[finalidad].descripcion)

    st.header("2. Opciones")
    eliminar_qr = st.checkbox(
        "Destruir codigos QR / barras encontrados en imagenes", value=True,
        help="Se sobreescriben los pixeles. Nunca se abre la URL del QR.")
    redactar_regiones = st.checkbox(
        "Redactar TODAS las regiones con aspecto de texto en imagenes", value=False,
        help="Apagado por defecto: sin OCR no se puede saber si esa region es "
             "informacion clinica. Encenderlo puede tapar parte de la imagen.")
    posibles_nombres = st.checkbox(
        "Sustituir tambien candidatos a nombre de baja confianza", value=False,
        help="Apagado por defecto: podria borrar un termino clinico que no este "
             "en el lexico (una marca comercial, un epinimo).")

    st.header("3. Privacidad")
    st.success("Procesamiento 100% local. Sin nube, sin API externa, sin telemetria.")
    hay_ocr, detalle_ocr = ocr_disponible()
    if hay_ocr:
        st.caption("OCR local disponible: " + detalle_ocr)
    else:
        st.caption("OCR NO disponible (" + detalle_ocr + "). El texto dentro de "
                   "imagenes se detecta como region pero no se puede leer.")
    st.caption("Archivos temporales: `" + str(WORKSPACE_DIR) + "`")
    st.caption("Informes: `" + str(REPORTS_DIR) + "`")
    if st.button("🗑️ ELIMINAR ARCHIVOS DE TRABAJO", use_container_width=True):
        borrados = workspace.eliminar_archivos_de_trabajo(incluir_reportes=False)
        st.session_state.pop("analisis", None)
        st.session_state.pop("resultados", None)
        st.success("Copias de trabajo eliminadas: %d" % borrados["trabajo"])
    if st.button("🧹 Eliminar tambien los informes", use_container_width=True):
        borrados = workspace.eliminar_archivos_de_trabajo(incluir_reportes=True)
        st.session_state.pop("analisis", None)
        st.session_state.pop("resultados", None)
        st.success("Informes eliminados: %d" % borrados["reportes"])

opciones = Opciones(
    finalidad=finalidad,
    eliminar_qr=eliminar_qr,
    redactar_regiones_imagen=redactar_regiones,
    sustituir_posibles_nombres=posibles_nombres,
)

# ---------------------------------------------------------------------------
# Entrada de archivos
# ---------------------------------------------------------------------------
st.subheader("Documentos")
col_a, col_b = st.columns([3, 1])
with col_a:
    subidos = st.file_uploader(
        "Arrastre aqui uno o varios archivos (se procesan como un expediente)",
        type=[e.lstrip(".") for e in registry.extensiones_soportadas()],
        accept_multiple_files=True,
    )
    st.caption("Formatos: " + ", ".join(registry.extensiones_soportadas())
               + " · limite " + str(int(MAX_FILE_BYTES / 1e6)) + " MB por archivo")
with col_b:
    st.write("")
    st.write("")
    if st.button("📁 CARGAR CASO SINTETICO\nDE DEMOSTRACION", use_container_width=True):
        rutas = casos_sinteticos.generar(forzar=True)
        st.session_state["rutas"] = [str(r) for r in rutas]
        st.session_state.pop("analisis", None)
        st.session_state.pop("resultados", None)
        st.success("Cargados %d casos ficticios de demostracion." % len(rutas))

if subidos:
    st.session_state["rutas"] = [str(r) for r in _guardar_subidos(subidos)]
    st.session_state.pop("analisis", None)
    st.session_state.pop("resultados", None)

rutas = [Path(r) for r in st.session_state.get("rutas", []) if Path(r).exists()]

if not rutas:
    st.info("Cargue un documento o pulse **CARGAR CASO SINTETICO DE DEMOSTRACION**.")
    st.stop()

st.write("**Archivos en el expediente:** " + ", ".join(r.name for r in rutas))

# ---------------------------------------------------------------------------
# ANALIZAR
# ---------------------------------------------------------------------------
c1, c2 = st.columns(2)
with c1:
    analizar = st.button("🔍 ANALIZAR", use_container_width=True, type="secondary")
with c2:
    generar = st.button("🛡️ GENERAR VERSION DESIDENTIFICADA",
                        use_container_width=True, type="primary")

if analizar:
    with st.spinner("Analizando localmente..."):
        st.session_state["analisis"] = {
            r.name: pipeline.analizar(r, opciones=opciones) for r in rutas
        }

if st.session_state.get("analisis"):
    st.subheader("Analisis previo")
    for nombre, a in st.session_state["analisis"].items():
        with st.expander("📄 " + nombre, expanded=len(rutas) == 1):
            if not a.get("ok"):
                st.error(a.get("error"))
                continue
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Tipo de documento", a["formato"])
            m2.metric("Identificadores", a["total_identificadores"])
            m3.metric("Metadatos", a["n_metadatos"])
            m4.metric("Datos clinicos", a["total_datos_clinicos"])
            _badge("Riesgo inicial: " + a["riesgo_inicial"],
                   COLOR_RIESGO.get(a["riesgo_inicial"], "#555"))
            st.write("**Capas inspeccionadas:** " + ", ".join(a["capas"]))
            st.write("**Reconstruccion prevista:** " + a["reconstruccion"])
            if a["identificadores"]:
                st.write("**Identificadores por categoria**")
                st.json(a["identificadores"], expanded=False)
            if a["datos_clinicos"]:
                st.write("**Datos clinicos detectados (se preservan literalmente)**")
                st.json(a["datos_clinicos"], expanded=False)
            if a["inciertos"]:
                st.write("**Posibles datos sensibles a modificacion "
                         "(requieren criterio humano)**")
                st.dataframe(a["inciertos"], use_container_width=True)
            if a["metadatos"]:
                st.write("**Metadatos encontrados:** " + ", ".join(a["metadatos"]))
            for al in a["alertas"]:
                (st.error if al["nivel"] == "critica" else st.warning)(
                    al["codigo"] + ": " + al["mensaje"] + " " + al["detalle"])

# ---------------------------------------------------------------------------
# GENERAR
# ---------------------------------------------------------------------------
if generar:
    with st.spinner("Procesando y verificando..."):
        st.session_state["resultados"] = {
            r.name: pipeline.procesar(r, opciones=opciones) for r in rutas
        }

resultados = st.session_state.get("resultados") or {}
if resultados:
    st.subheader("Resultado")
    st.info(ESTADO_TEXTO)

for nombre, r in resultados.items():
    st.markdown("---")
    st.markdown("### 📄 " + nombre)
    if not r.ok:
        st.error(r.error)
        continue

    aud = r.auditoria
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        _badge("Riesgo residual: " + r.riesgo.value,
               COLOR_RIESGO.get(r.riesgo.value, "#555"))
    with c2:
        _badge("Estado: " + r.estado.value,
               "#8a1414" if r.estado == EstadoRevision.REQUIRES_MANUAL_REVIEW
               else "#3a4149")
    with c3:
        v = aud["integridad_clinica"]
        st.caption(
            "Integridad clinica: **%s** · Reconstruccion: **%s** · "
            "Alucinaciones: **%s** · Adversarial: **%s**"
            % (v["transformacion"].get("veredicto"),
               v["reconstruccion"].get("veredicto"),
               v["alucinaciones"].get("veredicto"),
               aud["adversarial"].get("veredicto"))
        )

    st.write("**Por que ese riesgo**")
    for motivo in r.motivos_riesgo:
        st.write("- " + motivo)

    for al in r.alertas:
        texto = al.codigo + ": " + al.mensaje + (" " + al.detalle if al.detalle else "")
        if al.nivel == "critica":
            st.error(texto)
        elif al.nivel == "advertencia":
            st.warning(texto)
        else:
            st.info(texto)

    pest = st.tabs(["Antes / Despues", "Matriz de transformacion",
                    "Integridad clinica", "Prueba adversarial", "Archivos"])

    with pest[0]:
        if r.texto_original.strip() or r.texto_resultante.strip():
            a, b = st.columns(2)
            a.text_area("ANTES (original)", r.texto_original, height=420)
            b.text_area("DESPUES (desidentificado)", r.texto_resultante, height=420)
        else:
            st.caption("Este formato no produce texto comparable (imagen).")
        ruta_salida = Path(r.archivos["resultado"])
        if ruta_salida.suffix.lower() in (".png", ".jpg", ".jpeg"):
            a, b = st.columns(2)
            copia = Path(r.archivos.get("copia_trabajo", ""))
            if copia.exists():
                a.image(str(copia), caption="ANTES", use_container_width=True)
            b.image(str(ruta_salida), caption="DESPUES", use_container_width=True)
            regiones = r.auditoria.get("adversarial", {})
            st.caption("Toda alteracion de pixeles queda listada en el informe "
                       "de auditoria.")

    with pest[1]:
        filas = [t.as_row() for t in r.transformaciones]
        st.caption("Los identificadores aparecen enmascarados y con hash: el informe "
                   "no debe convertirse en una tabla de reidentificacion.")
        st.dataframe(filas, use_container_width=True, height=420)

    with pest[2]:
        v = aud["integridad_clinica"]
        st.write("**Transformacion:** " + str(v["transformacion"].get("veredicto")))
        st.json(v["transformacion"].get("resumen", {}), expanded=False)
        problemas = (v["transformacion"].get("unexpected_change", [])
                     + v["transformacion"].get("missing", [])
                     + v["transformacion"].get("new_content", []))
        if problemas:
            st.error("Hay discrepancias clinicas: NO se aprueba de forma automatica.")
            st.dataframe(problemas, use_container_width=True)
        else:
            st.success("Todos los valores clinicos comparados coinciden o "
                       "corresponden a transformaciones esperadas.")
        if v["alucinaciones"].get("hay_sospechas"):
            st.error("POSIBLE ALUCINACION / INFORMACION NO SOPORTADA")
            st.dataframe(v["alucinaciones"]["sospechas"], use_container_width=True)

    with pest[3]:
        adv = aud["adversarial"]
        st.write("**Veredicto:** " + str(adv.get("veredicto")))
        st.caption("Se vuelve a abrir el archivo generado e intentamos "
                   "reidentificar al paciente con las mismas herramientas.")
        st.write("Capas revisadas: " + ", ".join(adv.get("capas_revisadas", [])))
        if adv.get("fugas"):
            st.error("Fugas encontradas")
            st.dataframe(adv["fugas"], use_container_width=True)
        if adv.get("identificadores_residuales"):
            st.warning("Elementos que el reanalisis no pudo descartar")
            st.dataframe(adv["identificadores_residuales"], use_container_width=True)
        if adv.get("metadatos_residuales"):
            st.warning("Metadatos residuales")
            st.json(adv["metadatos_residuales"])
        if not adv.get("fugas") and not adv.get("identificadores_residuales"):
            st.success("El reanalisis no recupero identificadores.")

    with pest[4]:
        st.code(r.archivos["carpeta"])
        salida = Path(r.archivos["resultado"])
        st.download_button("⬇️ Descargar documento desidentificado",
                           salida.read_bytes(), file_name=salida.name,
                           use_container_width=True, key="dl_" + r.ejecucion_id)
        for etiqueta, clave in (("Informe de auditoria (HTML)", "html"),
                                ("audit.json", "audit_json"),
                                ("transformation_matrix.csv", "matriz_csv"),
                                ("integrity_report.json", "integridad_json"),
                                ("adversarial_scan.json", "adversarial_json"),
                                ("RESUMEN.md", "resumen_md")):
            ruta = Path(r.archivos[clave])
            st.download_button("⬇️ " + etiqueta, ruta.read_bytes(),
                               file_name=ruta.name, use_container_width=True,
                               key="dl_" + clave + "_" + r.ejecucion_id)

    st.write("**Aprobacion humana** — la maquina no aprueba sola.")
    revisor = st.text_input("Quien revisa (opcional)", key="rev_" + r.ejecucion_id)
    comentario = st.text_input("Comentario (opcional)", key="com_" + r.ejecucion_id)
    b1, b2, b3 = st.columns(3)
    if b1.button("✅ Aprobar", key="ok_" + r.ejecucion_id, use_container_width=True):
        pipeline.registrar_revision(r.archivos["carpeta"],
                                    EstadoRevision.APPROVED_BY_HUMAN,
                                    revisor, comentario)
        st.success("Registrado: APPROVED_BY_HUMAN. Revise igualmente antes de "
                   "compartir el archivo.")
    if b2.button("❌ Rechazar", key="no_" + r.ejecucion_id, use_container_width=True):
        pipeline.registrar_revision(r.archivos["carpeta"],
                                    EstadoRevision.REJECTED_BY_HUMAN,
                                    revisor, comentario)
        st.warning("Registrado: REJECTED_BY_HUMAN.")
    if b3.button("🔁 Volver a procesar", key="re_" + r.ejecucion_id,
                 use_container_width=True):
        st.session_state["resultados"][nombre] = pipeline.procesar(
            r.archivos["copia_trabajo"], opciones=opciones
        )
        st.rerun()

st.markdown("---")
st.caption(AVISO_PERMANENTE)
