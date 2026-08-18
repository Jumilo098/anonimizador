"""El pipeline completo.

ORIGINAL -> EXTRACCION -> DETECCION -> TRANSFORMACION -> RECONSTRUCCION
         -> COMPARACION -> AUDITORIA -> REVISION HUMANA

Ningun documento se marca como terminado sin pasar por las validaciones.
Ninguna de ellas puede sustituir a la revision humana.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import (
    AVISO_PERMANENTE,
    FINALIDADES,
    FINALIDAD_POR_DEFECTO,
    Opciones,
)
from ..formats import registry
from ..models import (
    Accion,
    Alerta,
    Capa,
    Categoria,
    Confianza,
    EstadoRevision,
    ResultadoPipeline,
    Riesgo,
    Transformacion,
)
from ..util import workspace
from ..util.hashing import enmascarar, hash_hallazgo, sha256_archivo
from ..util.safety import ArchivoRechazado, detectar_formato, sanear_nombre
from .auditors import audit
from .detectors import contextual, detectar_documento
from .risk import scoring
from .transformers.politica import Politica
from .transformers.texto import filas_datos_clinicos, transformar_unidades
from .validators import adversarial, alucinaciones, integridad

NOMBRE_SALIDA = "documento_desidentificado"


@dataclass
class Contexto:
    """Lo que el manejador de formato necesita para reconstruir."""

    copia: Path
    opciones: Opciones
    ejecucion: object


def _texto_de(unidades, capas=None):
    return "\n".join(
        u.texto for u in unidades
        if u.texto and (capas is None or u.capa in capas)
    )


def _transformaciones_metadatos(hallazgos_tecnicos):
    filas = []
    for h in hallazgos_tecnicos:
        filas.append(
            Transformacion(
                categoria=Categoria.TECNICO.value,
                tipo="metadato",
                capa=Capa.METADATOS.value,
                hallazgo_enmascarado=h.ruta + " = " + enmascarar(h.texto),
                hallazgo_hash=hash_hallazgo(h.texto),
                accion=Accion.ELIMINAR,
                resultado="(no se copia al archivo reconstruido)",
                motivo="identificador tecnico: " + (h.nota or "metadato"),
                integridad_clinica="no aplica",
                riesgo_residual="bajo",
                ruta=h.ruta,
                confianza=Confianza.ALTA.value,
                requiere_revision=False,
            )
        )
    return filas


def procesar(origen, nombre_original=None, opciones=None) -> ResultadoPipeline:
    """Procesa UN archivo de punta a punta. Nunca toca el original."""
    opciones = opciones or Opciones()
    finalidad = FINALIDADES.get(opciones.finalidad, FINALIDADES[FINALIDAD_POR_DEFECTO])
    origen = Path(origen)

    # --- 0. seguridad de entrada -----------------------------------------
    try:
        ext = detectar_formato(origen, nombre_original)
    except ArchivoRechazado as exc:
        r = ResultadoPipeline(ejecucion_id="rechazado")
        r.ok = False
        r.error = str(exc)
        r.estado = EstadoRevision.REQUIRES_MANUAL_REVIEW
        r.riesgo = Riesgo.NO_EVALUABLE
        r.alertas.append(Alerta("critica", "ARCHIVO_RECHAZADO", str(exc)))
        return r

    manejador = registry.manejador_para(ext)
    if manejador is None:
        r = ResultadoPipeline(ejecucion_id="rechazado")
        r.ok = False
        r.error = "No hay manejador para " + ext
        r.estado = EstadoRevision.REQUIRES_MANUAL_REVIEW
        r.riesgo = Riesgo.NO_EVALUABLE
        return r

    # --- 1. copia de trabajo (el ORIGINAL no se toca) --------------------
    ej = workspace.crear_ejecucion(origen, nombre_original)
    resultado = ResultadoPipeline(ejecucion_id=ej.ejecucion_id)
    alertas = []

    # --- 2. extraccion ----------------------------------------------------
    extraido = manejador.extraer(ej.copia)
    alertas.extend(extraido.alertas)
    if not extraido.unidades and not extraido.metadatos:
        resultado.ok = False
        resultado.error = "No se pudo extraer contenido del archivo."
        resultado.estado = EstadoRevision.REQUIRES_MANUAL_REVIEW
        resultado.riesgo = Riesgo.NO_EVALUABLE
        resultado.alertas = alertas or [
            Alerta("critica", "SIN_CONTENIDO", resultado.error)
        ]
        return resultado

    # --- 3. deteccion -----------------------------------------------------
    hallazgos, spans = detectar_documento(extraido.unidades)

    # --- 4. transformacion ------------------------------------------------
    politica = Politica(finalidad, opciones)
    unidades_nuevas, transformaciones, cambios = transformar_unidades(
        extraido.unidades, hallazgos, politica, spans,
        capas_no_copiadas=getattr(manejador, "capas_no_copiadas", frozenset()),
    )
    transformaciones.extend(_transformaciones_metadatos(extraido.hallazgos_tecnicos))

    texto_original = _texto_de(extraido.unidades)
    texto_transformado = _texto_de(unidades_nuevas)
    transformaciones.extend(filas_datos_clinicos(texto_transformado))

    # --- 5. validacion de integridad de la TRANSFORMACION -----------------
    integ = integridad.comparar(texto_original, texto_transformado, cambios)
    aluc = alucinaciones.revisar(texto_original, texto_transformado, integ, cambios)
    alertas.extend(aluc.get("alertas", []))

    # --- 6. reconstruccion ------------------------------------------------
    base_salida = sanear_nombre(
        str(getattr(opciones, "nombre_salida", "") or NOMBRE_SALIDA)
    ) or NOMBRE_SALIDA
    destino = ej.dir_reporte / (Path(base_salida).stem + ext)
    ctx = Contexto(copia=ej.copia, opciones=opciones, ejecucion=ej)
    try:
        info_recon = manejador.reconstruir(extraido, unidades_nuevas, destino, ctx)
    except Exception as exc:
        resultado.ok = False
        resultado.error = "Fallo la reconstruccion: " + str(exc)[:300]
        resultado.estado = EstadoRevision.REQUIRES_MANUAL_REVIEW
        resultado.riesgo = Riesgo.NO_EVALUABLE
        alertas.append(Alerta("critica", "RECONSTRUCCION_FALLIDA", resultado.error))
        resultado.alertas = alertas
        return resultado

    # --- 7. integridad de la RECONSTRUCCION (lo escrito == lo previsto) ---
    texto_esperado = info_recon.get("texto_esperado", "")
    try:
        reextraido = manejador.reescanear(destino)
        texto_reextraido = _texto_de(
            reextraido.unidades,
            capas={Capa.CONTENIDO, Capa.TABLA, Capa.ENCABEZADO, Capa.PIE,
                   Capa.HOJA_CALCULO},
        )
    except Exception:
        reextraido = None
        texto_reextraido = ""

    if texto_esperado.strip():
        integ_recon = integridad.comparar(texto_esperado, texto_reextraido, [])
    else:
        integ_recon = {
            "veredicto": "N/A",
            "bloquea_aprobacion": False,
            "resumen": {},
            "nota": "El formato no produce texto comparable (imagen).",
            "unexpected_change": [], "missing": [], "new_content": [], "filas": [],
        }

    # --- 8. prueba adversarial -------------------------------------------
    valores_originales = [h.texto for h in hallazgos]
    adv, alertas_adv = adversarial.escanear(
        destino, manejador, transformaciones, valores_originales,
        valores_generados=[c.get("nuevo", "") for c in cambios],
        autor_declarado=str(getattr(opciones, "autor_salida", "") or ""),
    )
    alertas.extend(alertas_adv)

    # --- 9. combinacion contextual ---------------------------------------
    ctx_eval = contextual.evaluar(hallazgos, transformaciones)
    alertas.extend(ctx_eval.get("alertas", []))

    # --- 10. riesgo residual ---------------------------------------------
    info_formato = dict(extraido.info or {})
    info_formato.pop("_ocr_cajas", None)
    info_formato.pop("estructura", None)
    riesgo, motivos = scoring.calcular(
        transformaciones, alertas, integ, aluc, ctx_eval, adv, info_formato
    )

    # --- 11. estado ------------------------------------------------------
    bloqueado = (
        integ.get("bloquea_aprobacion")
        or integ_recon.get("bloquea_aprobacion")
        or aluc.get("hay_sospechas")
        or adv.get("veredicto") in ("FAIL", "NO_EVALUABLE")
        or riesgo in (Riesgo.ALTO, Riesgo.NO_EVALUABLE)
    )
    estado = (EstadoRevision.REQUIRES_MANUAL_REVIEW if bloqueado
              else EstadoRevision.PENDING_REVIEW)

    # --- 12. auditoria ----------------------------------------------------
    original_intacto = workspace.verificar_original_intacto(origen, ej.hash_original)
    if not original_intacto:
        alertas.append(
            Alerta("critica", "ORIGINAL_MODIFICADO",
                   "El hash del archivo original cambio durante el proceso.")
        )
    hash_resultado = sha256_archivo(destino)
    contexto_audit = {
        "ejecucion_id": ej.ejecucion_id,
        "finalidad": finalidad.nombre,
        "finalidad_descripcion": finalidad.descripcion,
        "opciones": {
            "redactar_regiones_imagen": opciones.redactar_regiones_imagen,
            "eliminar_qr": opciones.eliminar_qr,
            "sustituir_posibles_nombres": getattr(
                opciones, "sustituir_posibles_nombres", False),
            "banda_superior_imagen": getattr(opciones, "banda_superior_imagen", 0.0),
            "banda_inferior_imagen": getattr(opciones, "banda_inferior_imagen", 0.0),
        },
        "nombre_original": ej.nombre_original,
        "formato": ext,
        "hash_original": ej.hash_original,
        "tam_original": ej.tam_original,
        "original_intacto": original_intacto,
        "nombre_resultado": destino.name,
        "hash_resultado": hash_resultado,
        "tam_resultado": destino.stat().st_size,
        "modo_reconstruccion": manejador.reconstruccion,
        "capas_descartadas": info_recon.get("capas_descartadas", []),
        "n_unidades": len(extraido.unidades),
        "capas": sorted({(u.capa.value if hasattr(u.capa, "value") else str(u.capa))
                         for u in extraido.unidades}),
        "metadatos_detectados": sorted(extraido.metadatos or {}),
        "metadatos_eliminados": sorted(extraido.metadatos or {}),
        "hallazgos": hallazgos,
        "transformaciones": transformaciones,
        "integridad": integ,
        "integridad_reconstruccion": integ_recon,
        "alucinaciones": aluc,
        "contextual": ctx_eval,
        "adversarial": adv,
        "riesgo": riesgo.value,
        "motivos_riesgo": motivos,
        "alertas": alertas,
        "estado": estado.value,
    }
    auditoria = audit.construir_auditoria(contexto_audit)

    d = ej.dir_reporte
    archivos = {
        "resultado": str(destino),
        "copia_trabajo": str(ej.copia),
        "audit_json": str(audit.guardar_json(d / "audit.json", auditoria)),
        "matriz_csv": str(audit.escribir_matriz(d / "transformation_matrix.csv",
                                                transformaciones)),
        "integridad_json": str(audit.guardar_json(d / "integrity_report.json", {
            "transformacion": integ,
            "reconstruccion": integ_recon,
            "alucinaciones": aluc,
        })),
        "adversarial_json": str(audit.guardar_json(d / "adversarial_scan.json", adv)),
        "html": str(audit.escribir_html(d / "audit_report.html", auditoria)),
        "resumen_md": str(audit.escribir_resumen_md(d / "RESUMEN.md", auditoria)),
        "carpeta": str(d),
    }
    (d / "notas_reconstruccion.txt").write_text(
        "\n".join(info_recon.get("notas", [])) + "\n\n" + AVISO_PERMANENTE,
        encoding="utf-8",
    )

    resultado.estado = estado
    resultado.riesgo = riesgo
    resultado.motivos_riesgo = motivos
    resultado.transformaciones = transformaciones
    resultado.alertas = alertas
    resultado.hallazgos = hallazgos
    resultado.integridad = {"transformacion": integ, "reconstruccion": integ_recon,
                            "alucinaciones": aluc, "contextual": ctx_eval}
    resultado.adversarial = adv
    resultado.auditoria = auditoria
    resultado.archivos = archivos
    resultado.texto_original = texto_original
    resultado.texto_resultante = texto_transformado
    resultado.ok = True
    return resultado


def analizar(origen, nombre_original=None, opciones=None) -> dict:
    """Paso ANALIZAR de la interfaz: solo mira, no genera nada."""
    opciones = opciones or Opciones()
    origen = Path(origen)
    try:
        ext = detectar_formato(origen, nombre_original)
    except ArchivoRechazado as exc:
        return {"ok": False, "error": str(exc)}
    manejador = registry.manejador_para(ext)
    if manejador is None:
        return {"ok": False, "error": "Formato sin manejador: " + ext}

    ej = workspace.crear_ejecucion(origen, nombre_original)
    extraido = manejador.extraer(ej.copia)
    hallazgos, _ = detectar_documento(extraido.unidades)

    por_categoria = {}
    for h in hallazgos:
        cat = h.categoria.value
        por_categoria.setdefault(cat, {})
        por_categoria[cat][h.tipo] = por_categoria[cat].get(h.tipo, 0) + 1

    from .detectors import clinico as det_clinico

    texto = _texto_de(extraido.unidades)
    valores = det_clinico.extraer_valores(texto)
    inciertos = [h for h in hallazgos
                 if h.confianza in (Confianza.MEDIA, Confianza.BAJA)]
    info = dict(extraido.info or {})
    info.pop("_ocr_cajas", None)
    info.pop("estructura", None)

    # riesgo inicial, antes de transformar nada
    riesgo_inicial = Riesgo.MODERADO
    if not hallazgos and not extraido.metadatos:
        riesgo_inicial = Riesgo.BAJO
    if len(hallazgos) > 12 or info.get("codigos_graficos") or info.get("imagenes"):
        riesgo_inicial = Riesgo.ALTO

    return {
        "ok": True,
        "ejecucion_id": ej.ejecucion_id,
        "formato": ext,
        "manejador": manejador.nombre,
        "reconstruccion": manejador.reconstruccion,
        "capas": sorted({u.capa.value for u in extraido.unidades}),
        "unidades": len(extraido.unidades),
        "identificadores": por_categoria,
        "total_identificadores": len(hallazgos),
        "inciertos": [
            {"tipo": h.tipo, "capa": h.capa.value,
             "valor": enmascarar(h.texto), "confianza": h.confianza.value,
             "nota": h.nota}
            for h in inciertos[:60]
        ],
        "metadatos": sorted(extraido.metadatos or {}),
        "n_metadatos": len(extraido.metadatos or {}),
        "datos_clinicos": det_clinico.resumen_valores(valores),
        "total_datos_clinicos": len(valores),
        "alertas": [{"nivel": a.nivel, "codigo": a.codigo, "mensaje": a.mensaje,
                     "detalle": a.detalle} for a in extraido.alertas],
        "info_formato": info,
        "riesgo_inicial": riesgo_inicial.value,
        "hash_original": ej.hash_original,
        "aviso": AVISO_PERMANENTE,
    }


def registrar_revision(carpeta, estado, revisor="", comentario=""):
    """Guarda la decision humana (bloque 18). La maquina no aprueba sola."""
    import json
    from datetime import datetime

    carpeta = Path(carpeta)
    ruta_audit = carpeta / "audit.json"
    if not ruta_audit.exists():
        raise FileNotFoundError("No existe audit.json en " + str(carpeta))
    auditoria = json.loads(ruta_audit.read_text(encoding="utf-8"))
    estado_valor = estado.value if hasattr(estado, "value") else str(estado)
    auditoria["revision_humana"]["estado"] = estado_valor
    auditoria["revision_humana"]["revisor"] = revisor or "(no identificado)"
    auditoria["revision_humana"]["comentario"] = comentario
    auditoria["revision_humana"]["fecha"] = datetime.now().isoformat(timespec="seconds")
    auditoria["revision_humana"]["nota"] = (
        "La aprobacion de la maquina no sustituye al profesional. Esta decision "
        "la tomo una persona."
    )
    audit.guardar_json(ruta_audit, auditoria)
    audit.guardar_json(carpeta / "revision_humana.json",
                       auditoria["revision_humana"])
    audit.escribir_html(carpeta / "audit_report.html", auditoria)
    audit.escribir_resumen_md(carpeta / "RESUMEN.md", auditoria)
    return auditoria["revision_humana"]


def procesar_expediente(archivos, opciones=None):
    """Varios archivos como un mismo expediente."""
    salidas = []
    for entrada in archivos:
        ruta, nombre = (entrada if isinstance(entrada, (tuple, list))
                        else (entrada, None))
        salidas.append(procesar(ruta, nombre, opciones))
    return salidas
