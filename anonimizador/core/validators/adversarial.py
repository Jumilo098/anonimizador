"""Prueba adversarial (bloque 23): atacar nuestro propio resultado.

Se vuelve a abrir el archivo generado como si intentaramos reidentificar al
paciente: texto, metadatos, anotaciones, comentarios, XML, QR, nombre del
archivo. Si reaparece algo que se suponia eliminado -> FAIL.
"""
from __future__ import annotations

import re
from pathlib import Path

from ...models import Accion, Alerta
from ...util.hashing import enmascarar, hash_hallazgo, normalizar
from ...util.texto import plegar
from ..detectors import detectar_documento

MODULO_POR_CAPA = {
    "metadatos": "manejador de formato (saneado de metadatos)",
    "comentario": "manejador de formato (comentarios)",
    "control_cambios": "manejador de formato (control de cambios)",
    "anotacion": "manejador de PDF (anotaciones)",
    "formulario": "manejador de PDF (formularios)",
    "imagen_pixeles": "manejador de imagen (pixeles / OCR)",
    "nombre_archivo": "nombrado del archivo de salida",
    "contenido": "transformador de texto",
    "tabla": "transformador de texto (tablas)",
    "encabezado": "manejador de formato (encabezados)",
    "pie": "manejador de formato (pies)",
    "hoja_calculo": "manejador de XLSX",
    "codigo_grafico": "manejador de imagen (QR/barcode)",
}


def escanear(ruta_resultado, manejador, transformaciones, valores_originales=None,
             valores_generados=None, autor_declarado=""):
    """Reanaliza el resultado como si quisieramos reidentificar al paciente.

    valores_originales: textos crudos que DEBIAN desaparecer (solo memoria).
    valores_generados: etiquetas y generalizaciones que ESCRIBIO ANONIMIZADOR;
      volver a detectarlas no es una fuga, es ruido de nuestro propio proceso.
    """
    ruta = Path(ruta_resultado)
    generados = {plegar(v) for v in (valores_generados or []) if v}
    from ..transformers.politica import ELIMINAR_DIRECTO
    generados |= {plegar(v) for v in ELIMINAR_DIRECTO.values()}
    generados |= {plegar(v) for v in
                  ("institucion de salud", "[ASEGURADORA]", "[LOCALIDAD]",
                   "[OCUPACION NO CLASIFICADA]", "[MES/ANO ELIMINADO]",
                   "[PACIENTE]", "[EDAD]")}

    def es_generado(texto):
        t = plegar(texto).strip()
        if not t:
            return True
        return any(t in g or g in t for g in generados if len(g) >= 3)

    informe = {
        "archivo": ruta.name,
        "fugas": [],
        "identificadores_residuales": [],
        "metadatos_residuales": {},
        "codigos_graficos_residuales": [],
        "capas_revisadas": [],
        "autoria_declarada": None,
        "veredicto": "PASS",
    }

    try:
        extraido = manejador.reescanear(ruta)
    except Exception as exc:
        informe["veredicto"] = "NO_EVALUABLE"
        informe["error"] = str(exc)[:200]
        return informe, [
            Alerta("critica", "ADVERSARIAL_FALLIDO",
                   "No se pudo reanalizar el archivo generado.", str(exc)[:200])
        ]

    informe["capas_revisadas"] = sorted({
        (u.capa.value if hasattr(u.capa, "value") else str(u.capa))
        for u in extraido.unidades
    })
    texto_total = "\n".join(u.texto for u in extraido.unidades)
    texto_plano = plegar(texto_total)

    # 1) metadatos que deberian estar vacios o ser neutros
    for clave, valor in (extraido.metadatos or {}).items():
        texto = str(valor).strip()
        if not texto:
            continue
        if _metadato_neutro(clave, texto):
            continue
        if autor_declarado and plegar(texto) == plegar(autor_declarado):
            # No es una fuga: es la autoria que el usuario pidio escribir.
            # Aun asi se reporta aparte, porque identifica a quien preparo el
            # material y viaja dentro del archivo.
            informe["autoria_declarada"] = {
                "campo": clave,
                "valor": texto,
                "nota": "identifica a quien preparo el material, no al paciente; "
                        "se escribio porque se pidio de forma explicita",
            }
            continue
        informe["metadatos_residuales"][clave] = enmascarar(texto)

    # 2) codigos graficos que debian desaparecer
    informe["codigos_graficos_residuales"] = extraido.info.get("codigos_graficos", [])

    # 3) los identificadores neutralizados NO pueden reaparecer
    esperados_fuera = {}
    for t in transformaciones:
        if t.accion in (Accion.ELIMINAR, Accion.SUSTITUIR, Accion.GENERALIZAR,
                        Accion.DESTRUIR_PIXELES):
            esperados_fuera[t.hallazgo_hash] = t

    for crudo in (valores_originales or []):
        texto = (crudo or "").strip()
        if len(texto) < 4:
            continue
        h = hash_hallazgo(texto)
        if h not in esperados_fuera:
            continue
        if _aparece(texto, texto_plano):
            t = esperados_fuera[h]
            informe["fugas"].append({
                "tipo": t.tipo,
                "capa": t.capa,
                "hash": h,
                "valor_enmascarado": enmascarar(texto),
                "modulo_responsable": MODULO_POR_CAPA.get(t.capa, "desconocido"),
                "detalle": "el identificador transformado reaparece en el resultado",
            })

    # 4) deteccion desde cero sobre el resultado
    hallazgos, _ = detectar_documento(extraido.unidades)
    for h in hallazgos:
        # Estos tipos son marcas de baja confianza que el propio pipeline deja
        # a proposito para revision humana; no son fugas del resultado.
        if h.tipo in ("posible_nombre", "campo_identificador_dudoso",
                      "posible_ocupacion"):
            continue
        if _es_marcador(h.texto) or es_generado(h.texto):
            continue
        capa = h.capa.value if hasattr(h.capa, "value") else str(h.capa)
        entrada = {
            "tipo": h.tipo,
            "capa": capa,
            "confianza": h.confianza.value if hasattr(h.confianza, "value") else str(h.confianza),
            "valor_enmascarado": enmascarar(h.texto),
            "hash": hash_hallazgo(h.texto),
            "ruta": h.ruta,
            "modulo_responsable": MODULO_POR_CAPA.get(capa, "desconocido"),
        }
        informe["identificadores_residuales"].append(entrada)
        if entrada["hash"] in esperados_fuera:
            entrada["detalle"] = "coincide con un identificador que se dio por eliminado"
            informe["fugas"].append(entrada)

    alertas = []
    if informe["fugas"]:
        informe["veredicto"] = "FAIL"
        alertas.append(
            Alerta("critica", "FUGA_ADVERSARIAL",
                   "La prueba adversarial encontro %d fuga(s)." % len(informe["fugas"]),
                   "Modulos implicados: " + ", ".join(sorted({
                       f.get("modulo_responsable", "?") for f in informe["fugas"]})))
        )
    if informe["metadatos_residuales"]:
        informe["veredicto"] = "FAIL" if informe["fugas"] else "REVISAR"
        alertas.append(
            Alerta("advertencia", "METADATOS_RESIDUALES",
                   "Quedan %d metadato(s) con contenido en el archivo generado."
                   % len(informe["metadatos_residuales"]),
                   "Campos: " + ", ".join(sorted(informe["metadatos_residuales"])))
        )
    if informe["codigos_graficos_residuales"]:
        informe["veredicto"] = "FAIL"
        alertas.append(
            Alerta("critica", "QR_RESIDUAL",
                   "El resultado todavia contiene codigos QR/barras.")
        )
    if informe["identificadores_residuales"] and informe["veredicto"] == "PASS":
        informe["veredicto"] = "REVISAR"
        alertas.append(
            Alerta("advertencia", "IDENTIFICADORES_EN_RESULTADO",
                   "El reanalisis detecto %d elemento(s) potencialmente "
                   "identificadores en el resultado."
                   % len(informe["identificadores_residuales"]),
                   "Puede haber falsos positivos, pero deben revisarse a mano.")
        )
    return informe, alertas


_NEUTROS = {
    "", "anonimizador", "documento desidentificado", "libro desidentificado",
    "desidentificado - pendiente de revision",
    "generado por anonimizador. requiere revision humana.",
    "reportlab pdf library - www.reportlab.com", "pdf", "docx", "xlsx",
}


def _metadato_neutro(clave: str, valor: str) -> bool:
    v = normalizar(valor)
    if v in _NEUTROS:
        return True
    if "anonimizador" in v or "desidentificado" in v:
        return True
    c = normalizar(clave)
    if c.endswith("created") or c.endswith("modified") or "date" in c:
        return True
    # campos tecnicos que no dicen nada de una persona
    tecnicos = {
        "format", "encryption", "trapped", "revision", "totaltime", "lastprinted",
        "pages", "words", "characters", "charactersWithSpaces", "lines",
        "paragraphs", "application", "appversion", "template", "docsecurity",
        "scalecrop", "linksuptodate", "sharedoc", "hyperlinkschanged",
        "contentstatus", "language", "version",
    }
    # OJO: 'creator', 'producer', 'author' y 'company' NO entran aqui a
    # proposito: si sobreviven con contenido real, hay que verlo.
    if c.split(":")[-1] in tecnicos:
        return True
    if "reportlab" in v or "python-docx" in v or "openpyxl" in v:
        return True
    return False


def _es_marcador(texto: str) -> bool:
    t = (texto or "").strip()
    return t.startswith("[") and t.endswith("]")


def _aparece(valor: str, texto_plegado: str) -> bool:
    """¿El identificador reaparece REALMENTE en el resultado?

    Con `in` a secas, un valor corto como la ciudad "Cali" daba positivo dentro
    de "localizado" o incluso dentro de nuestro propio marcador "[LOCALIDAD]".
    Se exige que el valor aparezca como palabra completa.
    """
    v = plegar(valor).strip()
    if not v:
        return False
    # se ignora lo que este dentro de un marcador nuestro: [PACIENTE], [LOCALIDAD]...
    limpio = re.sub(r"\[[^\]]{0,60}\]", " ", texto_plegado)
    patron = r"(?<![0-9a-z])" + re.escape(v) + r"(?![0-9a-z])"
    return re.search(patron, limpio) is not None
