"""Aplicacion de la politica sobre las unidades de texto.

Aqui vive la camisa de fuerza: antes de reescribir nada se comprueba que el
rango a modificar NO pise informacion clinica. Si la pisa, la transformacion
se BLOQUEA y el documento queda marcado para revision humana.
"""
from __future__ import annotations

from ...models import Accion, Categoria, Confianza, Transformacion
from ...util.hashing import enmascarar, hash_hallazgo
from ...util.texto import aplicar_reemplazos, recortar
from ..detectors import clinico

RIESGO_POR_ACCION = {
    Accion.ELIMINAR: "bajo",
    Accion.SUSTITUIR: "bajo",
    Accion.GENERALIZAR: "bajo",
    Accion.PRESERVAR: "moderado",
    Accion.MARCAR_REVISION: "moderado",
    Accion.DESTRUIR_PIXELES: "bajo",
    Accion.NO_APLICADA_POR_SEGURIDAD_CLINICA: "moderado",
}


def transformar_unidades(unidades, hallazgos, politica, spans_por_unidad=None,
                         capas_no_copiadas=None):
    """Devuelve (unidades_nuevas, transformaciones, cambios).

    unidades_nuevas: lista de UnidadTexto con el texto ya minimizado.
    cambios: pares (original, nuevo) EN MEMORIA, para que el validador de
    integridad sepa que diferencias eran esperadas. No se persisten nunca:
    serian una tabla de reidentificacion.
    """
    politica.preparar_cronologia(hallazgos)
    por_unidad = {}
    for h in hallazgos:
        por_unidad.setdefault(h.uid_unidad, []).append(h)

    transformaciones = []
    cambios = []
    nuevas = []
    for u in unidades:
        lista = sorted(por_unidad.get(u.uid, []), key=lambda h: h.inicio)
        spans = (spans_por_unidad or {}).get(u.uid)
        if spans is None:
            spans = clinico.spans_protegidos(u.texto)
        reemplazos = []
        for h in lista:
            accion, resultado, motivo, revisar = politica.decidir(h)
            integridad = "no aplica"

            if accion in (Accion.ELIMINAR, Accion.SUSTITUIR, Accion.GENERALIZAR):
                choque = clinico.protegido(u.texto, h.inicio, h.fin, spans)
                if choque:
                    accion = Accion.NO_APLICADA_POR_SEGURIDAD_CLINICA
                    resultado = h.texto
                    motivo = (
                        "la transformacion habria alterado informacion clinica ("
                        + choque + ")"
                    )
                    integridad = "protegida: cambio bloqueado"
                    revisar = True
                else:
                    integridad = "preservada"
                    if u.editable:
                        reemplazos.append((h.inicio, h.fin, resultado))
                        cambios.append({"orig": h.texto, "nuevo": resultado,
                                        "tipo": h.tipo})
                    elif u.capa in (capas_no_copiadas or set()):
                        # La capa entera se descarta en la reconstruccion: el
                        # identificador desaparece por eliminacion de la capa.
                        accion = Accion.ELIMINAR
                        resultado = "(la capa '" + str(
                            u.capa.value if hasattr(u.capa, "value") else u.capa
                        ) + "' no se copia al archivo reconstruido)"
                        motivo = motivo + " (capa descartada por completo)"
                        revisar = False
                    else:
                        accion = Accion.MARCAR_REVISION
                        motivo = motivo + " (capa no reescribible: solo se reporta)"
                        revisar = True

            transformaciones.append(
                Transformacion(
                    categoria=h.categoria.value if hasattr(h.categoria, "value") else str(h.categoria),
                    tipo=h.tipo,
                    capa=h.capa.value if hasattr(h.capa, "value") else str(h.capa),
                    hallazgo_enmascarado=enmascarar(recortar(h.texto, 60)),
                    hallazgo_hash=hash_hallazgo(h.texto),
                    accion=accion,
                    resultado=resultado if accion != Accion.MARCAR_REVISION else "(sin cambios)",
                    motivo=motivo,
                    integridad_clinica=integridad,
                    riesgo_residual=RIESGO_POR_ACCION.get(accion, "moderado"),
                    ruta=h.ruta or u.ruta,
                    confianza=h.confianza.value if hasattr(h.confianza, "value") else str(h.confianza),
                    requiere_revision=bool(revisar),
                )
            )

        nuevo_texto = aplicar_reemplazos(u.texto, reemplazos) if reemplazos else u.texto
        copia = type(u)(
            uid=u.uid,
            texto=nuevo_texto,
            capa=u.capa,
            ruta=u.ruta,
            editable=u.editable,
            meta=dict(u.meta),
        )
        nuevas.append(copia)
    return nuevas, transformaciones, cambios


def filas_datos_clinicos(texto, limite=250):
    """Filas 'PRESERVAR' de la matriz: lo clinico que se conserva literal."""
    filas = []
    vistos = set()
    for v in clinico.extraer_valores(texto):
        if v.clase in ("negacion", "certeza"):
            continue
        clave = (v.clase, v.normalizado)
        if clave in vistos:
            continue
        vistos.add(clave)
        filas.append(
            Transformacion(
                categoria=Categoria.CLINICO.value,
                tipo=v.clase,
                capa="contenido",
                hallazgo_enmascarado=recortar(v.texto, 60),
                hallazgo_hash=hash_hallazgo(v.texto),
                accion=Accion.PRESERVAR,
                resultado=recortar(v.texto, 60),
                motivo="dato clinico: se conserva literal",
                integridad_clinica="exacta",
                riesgo_residual="n/a",
                confianza=Confianza.ALTA.value,
                requiere_revision=False,
            )
        )
        if len(filas) >= limite:
            break
    return filas
