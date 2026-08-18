"""Motor de deteccion: cinco capas, todo determinista."""
from __future__ import annotations

from ...models import Hallazgo
from . import clinico, contextual, directos, indirectos

# Prioridad para resolver solapes (numero bajo = gana)
PRIORIDAD = {
    "email": 5, "url": 5, "ip": 5, "usuario_red": 12,
    "documento_identidad": 5, "historia_clinica": 5,
    "numero_administrativo": 6, "telefono_etiquetado": 5, "telefono": 8,
    "direccion": 9, "codigo_postal": 9, "firma_digital": 6,
    "nombre_persona": 10, "nombre_profesional": 10,
    "fecha_nacimiento": 11, "institucion": 14, "aseguradora": 16,
    "fecha": 18, "ocupacion": 20, "localidad": 22, "edad": 24,
    "posible_nombre": 40, "campo_identificador_dudoso": 45,
}
PRIORIDAD_POR_DEFECTO = 50


def _prio(h: Hallazgo) -> int:
    return PRIORIDAD.get(h.tipo, PRIORIDAD_POR_DEFECTO)


def resolver_solapes(hallazgos):
    """Deja un solo hallazgo por region de texto, el de mayor prioridad."""
    por_unidad = {}
    for h in hallazgos:
        por_unidad.setdefault(h.uid_unidad, []).append(h)
    salida = []
    for uid, lista in por_unidad.items():
        lista.sort(key=lambda h: (_prio(h), -(h.fin - h.inicio), h.inicio))
        aceptados = []
        for h in lista:
            hi, hf = h.ambito
            if any(hi < a.ambito[1] and a.ambito[0] < hf for a in aceptados):
                continue
            aceptados.append(h)
        salida.extend(sorted(aceptados, key=lambda h: h.inicio))
    return salida


def detectar_unidad(unidad):
    spans = clinico.spans_protegidos(unidad.texto)
    hallazgos = []
    hallazgos.extend(directos.detectar(unidad, spans))
    hallazgos.extend(indirectos.detectar(unidad, spans))
    return resolver_solapes(hallazgos), spans


def detectar_documento(unidades):
    """Devuelve (hallazgos, spans_clinicos_por_unidad)."""
    todos = []
    spans_por_unidad = {}
    for u in unidades:
        h, spans = detectar_unidad(u)
        todos.extend(h)
        spans_por_unidad[u.uid] = spans
    return todos, spans_por_unidad


__all__ = [
    "clinico",
    "contextual",
    "directos",
    "indirectos",
    "detectar_unidad",
    "detectar_documento",
    "resolver_solapes",
]
