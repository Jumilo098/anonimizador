"""Riesgo residual explicable (bloque 17).

No es una certificacion legal. Es una escala interna que SIEMPRE dice por que.
"""
from __future__ import annotations

from ...models import ORDEN_RIESGO, Accion, Riesgo


def _peor(a: Riesgo, b: Riesgo) -> Riesgo:
    return a if ORDEN_RIESGO[a] >= ORDEN_RIESGO[b] else b


def calcular(transformaciones, alertas, integridad, alucinaciones, contexto_eval,
             adversarial, info_formato=None) -> tuple:
    """Devuelve (Riesgo, [motivos])."""
    info = info_formato or {}
    riesgo = Riesgo.MUY_BAJO
    motivos = []

    def subir(nivel, motivo):
        nonlocal riesgo
        riesgo = _peor(riesgo, nivel)
        motivos.append(motivo)

    # --- bloqueos duros ---------------------------------------------------
    if adversarial.get("veredicto") == "FAIL":
        subir(Riesgo.ALTO,
              "La prueba adversarial encontro fugas en el archivo generado.")
    elif adversarial.get("veredicto") == "NO_EVALUABLE":
        subir(Riesgo.NO_EVALUABLE,
              "No se pudo reanalizar el archivo generado: la verificacion "
              "adversarial no es concluyente.")
    elif adversarial.get("veredicto") == "REVISAR":
        subir(Riesgo.MODERADO,
              "El reanalisis del resultado detecto elementos que podrian "
              "identificar y no se pudieron descartar de forma automatica.")

    if integridad.get("bloquea_aprobacion"):
        detalle = []
        if integridad.get("unexpected_change"):
            detalle.append("%d cambio(s) clinico(s) inesperado(s)"
                           % len(integridad["unexpected_change"]))
        if integridad.get("missing"):
            detalle.append("%d valor(es) clinico(s) desaparecido(s)"
                           % len(integridad["missing"]))
        if integridad.get("new_content"):
            detalle.append("%d valor(es) clinico(s) nuevo(s)"
                           % len(integridad["new_content"]))
        subir(Riesgo.ALTO,
              "La validacion de integridad clinica fallo: " + ", ".join(detalle) + ".")

    if alucinaciones.get("hay_sospechas"):
        subir(Riesgo.ALTO,
              "Se detecto contenido clinico en el resultado que no esta en el "
              "original (posible alucinacion / informacion no soportada).")

    # --- transformaciones bloqueadas o pendientes -------------------------
    bloqueadas = [t for t in transformaciones
                  if t.accion == Accion.NO_APLICADA_POR_SEGURIDAD_CLINICA]
    if bloqueadas:
        subir(Riesgo.MODERADO,
              "%d identificador(es) no se pudieron transformar porque tocaban "
              "informacion clinica; siguen en el documento." % len(bloqueadas))

    marcados = [t for t in transformaciones if t.accion == Accion.MARCAR_REVISION]
    if marcados:
        subir(Riesgo.MODERADO,
              "%d elemento(s) quedaron marcados para revision humana en lugar de "
              "transformarse automaticamente." % len(marcados))

    preservados = [t for t in transformaciones
                   if t.accion == Accion.PRESERVAR and t.categoria != "dato_clinico"]
    if preservados:
        subir(Riesgo.MODERADO,
              "%d cuasi-identificador(es) se conservaron por decision de la "
              "finalidad elegida." % len(preservados))

    # --- combinacion contextual -------------------------------------------
    nivel_ctx = contexto_eval.get("nivel")
    if nivel_ctx == "alto":
        subir(Riesgo.ALTO,
              "Sobreviven varios cuasi-identificadores que combinados podrian "
              "singularizar al paciente (%s)."
              % ", ".join(contexto_eval.get("variables_residuales", {})))
    elif nivel_ctx == "moderado":
        subir(Riesgo.MODERADO,
              "Combinacion de cuasi-identificadores residuales: "
              + ", ".join(contexto_eval.get("variables_residuales", {})) + ".")

    # --- capas no evaluables ----------------------------------------------
    if info.get("probablemente_escaneado"):
        subir(Riesgo.NO_EVALUABLE,
              "El documento parece escaneado: casi no hay texto extraible, asi que "
              "el analisis de identificadores NO es concluyente y la reconstruccion "
              "de solo texto perderia el contenido.")
    if info.get("imagenes"):
        subir(Riesgo.MODERADO,
              "El documento contiene %d imagen(es) cuyo contenido de pixeles no "
              "se analiza en V1 y que no se transfieren al resultado."
              % info["imagenes"])
    regiones = info.get("regiones_texto") or []
    if regiones and not info.get("ocr_disponible"):
        subir(Riesgo.MODERADO,
              "Se detecto texto dentro de una imagen que no pudo clasificarse de "
              "forma segura (%d region(es), sin OCR instalado)." % len(regiones))
    if info.get("codigos_graficos"):
        motivos.append("Se detectaron codigos QR/barras; se destruyeron en el "
                       "resultado y se verifico que no quedan.")

    # --- metadatos ---------------------------------------------------------
    if adversarial.get("metadatos_residuales"):
        subir(Riesgo.MODERADO,
              "Quedan metadatos con contenido en el archivo generado: "
              + ", ".join(sorted(adversarial["metadatos_residuales"])) + ".")

    criticas = [a for a in alertas if a.nivel == "critica"]
    if criticas:
        subir(Riesgo.MODERADO,
              "Hay %d alerta(s) critica(s) del analisis: %s."
              % (len(criticas), ", ".join(sorted({a.codigo for a in criticas}))))

    # --- suelo: nunca decimos "sin riesgo" --------------------------------
    if riesgo == Riesgo.MUY_BAJO:
        riesgo = Riesgo.BAJO
        motivos.append(
            "No se detectaron identificadores residuales, los valores clinicos "
            "coinciden y la prueba adversarial no encontro fugas. Aun asi el "
            "riesgo nunca es cero: la revision humana sigue siendo obligatoria."
        )
    return riesgo, motivos


def explicacion(riesgo: Riesgo, motivos) -> str:
    lineas = ["Riesgo residual: " + riesgo.value + "."]
    for m in motivos:
        lineas.append("  - " + m)
    lineas.append("Este puntaje NO constituye una certificacion legal.")
    return "\n".join(lineas)
