"""Deteccion de contenido no soportado por el original (bloque 15).

En V1 la reconstruccion es determinista (reemplazos sobre el texto extraido),
asi que en teoria no puede aparecer contenido nuevo. Este validador existe
igualmente por dos razones:
  1. atrapa errores del propio ANONIMIZADOR;
  2. es el guardian obligatorio si algun dia se enchufa una capa de IA.
"""
from __future__ import annotations

import re

from ...models import Alerta
from ...util.hashing import normalizar
from ..detectors import clinico

CLASES_VIGILADAS = {
    "diagnostico", "medicamento", "procedimiento", "numero_unidad",
    "analito_valor", "dosis", "signo_vital", "medida", "porcentaje",
    "anatomia", "lateralidad",
}

_SEPARADOR = re.compile(r"(?<=[.;:\n])\s+")


def _frases(texto):
    return [normalizar(f) for f in _SEPARADOR.split(texto or "") if f.strip()]


def _partir(texto):
    """Frases tal cual (sin normalizar) para poder citarlas en el informe."""
    return [f for f in _SEPARADOR.split(texto or "") if f.strip()]


def revisar(texto_original: str, texto_resultante: str, integridad: dict,
            cambios=None) -> dict:
    """Devuelve el informe de posibles alucinaciones."""
    cambios = cambios or []
    sospechas = []

    # 1) valores clinicos nuevos que la comparacion marco como NEW_CONTENT
    for fila in integridad.get("new_content", []):
        if fila.get("clase") in CLASES_VIGILADAS:
            sospechas.append({
                "tipo": "valor_clinico_nuevo",
                "clase": fila.get("clase"),
                "valor": fila.get("valor"),
                "contexto": fila.get("contexto", ""),
                "gravedad": "critica",
            })

    # 2) frases del resultado que contienen algun valor clinico que el original
    #    no respalda. Localiza el problema; no basta con contarlo globalmente.
    respaldados = {v.key() for v in clinico.extraer_valores(texto_original)}
    for c in cambios:
        respaldados |= {v.key() for v in clinico.extraer_valores(c.get("nuevo", ""))}

    for frase in _partir(texto_resultante):
        sin_respaldo = [
            v for v in clinico.extraer_valores(frase)
            if v.clase in CLASES_VIGILADAS and v.key() not in respaldados
        ]
        if sin_respaldo:
            sospechas.append({
                "tipo": "frase_clinica_no_soportada",
                "clase": "frase",
                "valor": " ".join(frase.split())[:160],
                "contexto": ", ".join(v.texto for v in sin_respaldo[:5]),
                "gravedad": "critica",
            })

    alertas = []
    if sospechas:
        alertas.append(
            Alerta(
                nivel="critica",
                codigo="POSIBLE_ALUCINACION",
                mensaje="POSIBLE ALUCINACION / INFORMACION NO SOPORTADA",
                detalle=(
                    "Se detectaron " + str(len(sospechas))
                    + " elementos clinicos en el resultado que no estan en el original."
                ),
            )
        )
    return {
        "hay_sospechas": bool(sospechas),
        "total": len(sospechas),
        "sospechas": sospechas[:100],
        "alertas": alertas,
        "veredicto": "FAIL" if sospechas else "PASS",
    }
