"""Capa 3: IDENTIFICADORES CONTEXTUALES.

Ninguna de estas variables identifica sola. La combinacion si puede.
Ejemplo clasico: edad exacta + profesion + ciudad + institucion + fecha.

Este modulo NO transforma nada: cuenta cuasi-identificadores y marca el caso
para revision humana cuando la combinacion sigue siendo singularizante DESPUES
de las transformaciones.
"""
from __future__ import annotations

from ...models import Alerta

# Peso de cada cuasi-identificador que SOBREVIVE al proceso
PESOS = {
    "edad": 2,
    "fecha_nacimiento": 3,
    "ocupacion": 2,
    "localidad": 2,
    "institucion": 2,
    "aseguradora": 1,
    "empleador": 2,
    "fecha": 1,
    "sexo": 1,
    "posible_nombre": 3,
    "campo_identificador_dudoso": 2,
    "posible_ocupacion": 1,
}

UMBRAL_MODERADO = 4
UMBRAL_ALTO = 6


def evaluar(hallazgos, transformaciones) -> dict:
    """Evalua la combinacion residual.

    Un cuasi-identificador cuenta si NO fue eliminado ni generalizado.
    """
    from ...models import Accion

    neutralizados = set()
    residuales = {}
    for t in transformaciones:
        if t.accion in (Accion.ELIMINAR, Accion.SUSTITUIR, Accion.GENERALIZAR,
                        Accion.DESTRUIR_PIXELES):
            neutralizados.add((t.tipo, t.hallazgo_hash))

    from ...util.hashing import hash_hallazgo

    for h in hallazgos:
        if h.tipo not in PESOS:
            continue
        clave = (h.tipo, hash_hallazgo(h.texto))
        if clave in neutralizados:
            continue
        residuales.setdefault(h.tipo, set()).add(hash_hallazgo(h.texto))

    puntaje = sum(PESOS[t] for t in residuales)
    tipos = sorted(residuales)
    if puntaje >= UMBRAL_ALTO:
        nivel = "alto"
    elif puntaje >= UMBRAL_MODERADO:
        nivel = "moderado"
    elif puntaje > 0:
        nivel = "bajo"
    else:
        nivel = "muy bajo"

    alertas = []
    if nivel in ("moderado", "alto"):
        alertas.append(
            Alerta(
                nivel="advertencia" if nivel == "moderado" else "critica",
                codigo="COMBINACION_CONTEXTUAL",
                mensaje=(
                    "Sobreviven " + str(len(tipos)) + " cuasi-identificadores que, "
                    "combinados, podrian permitir reidentificacion."
                ),
                detalle="Variables residuales: " + ", ".join(tipos),
            )
        )
    return {
        "nivel": nivel,
        "puntaje": puntaje,
        "variables_residuales": {k: len(v) for k, v in sorted(residuales.items())},
        "alertas": alertas,
    }
