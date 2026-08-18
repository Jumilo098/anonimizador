"""Validacion de integridad clinica (bloque 14).

Compara el ANTES y el DESPUES a nivel de valores clinicos atomicos y
clasifica cada diferencia. Un UNEXPECTED_CHANGE, un MISSING clinico o un
NEW_CONTENT detienen la aprobacion automatica.
"""
from __future__ import annotations

from collections import Counter

from ...models import Integridad
from ..detectors import clinico

CLASES_CRITICAS = {
    "numero_unidad", "analito_valor", "signo_vital", "dosis", "medida",
    "porcentaje", "anatomia", "lateralidad", "medicamento", "procedimiento",
    "diagnostico", "negacion", "certeza",
}


def _contar(valores):
    return Counter(v.key() for v in valores)


def _indice(valores):
    idx = {}
    for v in valores:
        idx.setdefault(v.key(), v)
    return idx


def _familia(clave):
    """Agrupa valores comparables: mismo analito o misma unidad."""
    clase, norm = clave
    if clase == "numero_unidad":
        partes = norm.split(" ", 1)
        return (clase, partes[1] if len(partes) > 1 else "")
    if clase == "analito_valor":
        return (clase, norm.split("=")[0])
    if clase in ("medida", "porcentaje", "dosis", "signo_vital"):
        return (clase, "")
    return None


def comparar(texto_original: str, texto_resultante: str, cambios=None) -> dict:
    """cambios: [{'orig':..., 'nuevo':...}] con los reemplazos aplicados."""
    cambios = cambios or []
    vo = clinico.extraer_valores(texto_original)
    vr = clinico.extraer_valores(texto_resultante)
    co, cr = _contar(vo), _contar(vr)
    idx_o, idx_r = _indice(vo), _indice(vr)

    esperados_fuera = Counter()
    esperados_dentro = Counter()
    for c in cambios:
        esperados_fuera.update(_contar(clinico.extraer_valores(c.get("orig", ""))))
        esperados_dentro.update(_contar(clinico.extraer_valores(c.get("nuevo", ""))))

    exactos = co & cr
    faltantes = co - cr
    nuevos = cr - co

    filas = []
    inesperados = []
    missing = []
    new_content = []

    for clave, n in sorted(exactos.items()):
        v = idx_o[clave]
        filas.append({
            "clase": clave[0], "valor": v.texto, "normalizado": clave[1],
            "veces": n, "estado": Integridad.EXACT_MATCH.value,
        })

    faltantes_rest = Counter(faltantes)
    nuevos_rest = Counter(nuevos)

    # 1) transformaciones esperadas
    for clave, n in list(faltantes_rest.items()):
        esperado = min(n, esperados_fuera.get(clave, 0))
        if esperado:
            faltantes_rest[clave] -= esperado
            filas.append({
                "clase": clave[0], "valor": idx_o[clave].texto,
                "normalizado": clave[1], "veces": esperado,
                "estado": Integridad.EXPECTED_TRANSFORMATION.value,
                "nota": "el valor formaba parte de un identificador transformado",
            })
    for clave, n in list(nuevos_rest.items()):
        esperado = min(n, esperados_dentro.get(clave, 0))
        if esperado:
            nuevos_rest[clave] -= esperado
            filas.append({
                "clase": clave[0], "valor": idx_r[clave].texto,
                "normalizado": clave[1], "veces": esperado,
                "estado": Integridad.EXPECTED_TRANSFORMATION.value,
                "nota": "el valor lo introdujo una generalizacion registrada",
            })

    faltantes_rest = +faltantes_rest
    nuevos_rest = +nuevos_rest

    # 2) cambios inesperados: mismo analito/unidad con valor distinto
    for clave, n in list(faltantes_rest.items()):
        fam = _familia(clave)
        if not fam:
            continue
        for clave_n, m in list(nuevos_rest.items()):
            if m <= 0 or _familia(clave_n) != fam:
                continue
            usados = min(n, m)
            faltantes_rest[clave] -= usados
            nuevos_rest[clave_n] -= usados
            n -= usados
            fila = {
                "clase": clave[0],
                "valor_original": idx_o[clave].texto,
                "valor_resultante": idx_r[clave_n].texto,
                "veces": usados,
                "estado": Integridad.UNEXPECTED_CHANGE.value,
                "contexto": idx_o[clave].contexto,
            }
            filas.append(fila)
            inesperados.append(fila)
            if n <= 0:
                break

    faltantes_rest = +faltantes_rest
    nuevos_rest = +nuevos_rest

    # 3) lo que queda
    for clave, n in sorted(faltantes_rest.items()):
        fila = {
            "clase": clave[0], "valor": idx_o[clave].texto,
            "normalizado": clave[1], "veces": n,
            "estado": Integridad.MISSING.value,
            "contexto": idx_o[clave].contexto,
        }
        filas.append(fila)
        if clave[0] in CLASES_CRITICAS:
            missing.append(fila)
    for clave, n in sorted(nuevos_rest.items()):
        fila = {
            "clase": clave[0], "valor": idx_r[clave].texto,
            "normalizado": clave[1], "veces": n,
            "estado": Integridad.NEW_CONTENT.value,
            "contexto": idx_r[clave].contexto,
        }
        filas.append(fila)
        if clave[0] in CLASES_CRITICAS:
            new_content.append(fila)

    resumen = Counter(f["estado"] for f in filas)
    bloquea = bool(inesperados or missing or new_content)
    return {
        "total_valores_original": len(vo),
        "total_valores_resultante": len(vr),
        "resumen": dict(resumen),
        "por_clase_original": clinico.resumen_valores(vo),
        "por_clase_resultante": clinico.resumen_valores(vr),
        "filas": filas,
        "unexpected_change": inesperados,
        "missing": missing,
        "new_content": new_content,
        "bloquea_aprobacion": bloquea,
        "veredicto": "FAIL" if bloquea else "PASS",
    }
