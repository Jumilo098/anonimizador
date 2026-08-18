"""Contrato comun de los manejadores de formato."""
from __future__ import annotations

from pathlib import Path

from ..models import Alerta, Capa, Categoria, Confianza, Hallazgo, UnidadTexto
from ..util.hashing import enmascarar

# Campos de metadatos que casi siempre identifican
CAMPOS_SENSIBLES = {
    "author", "last_modified_by", "lastmodifiedby", "creator", "producer",
    "company", "manager", "title", "subject", "keywords", "comments",
    "category", "description", "owner", "username", "user", "revision",
    "content_status", "identifier", "language", "version", "customer",
}


def unidad(uid, texto, capa=Capa.CONTENIDO, ruta="", editable=True, **meta):
    return UnidadTexto(uid=uid, texto=texto or "", capa=capa, ruta=ruta,
                       editable=editable, meta=meta)


def hallazgo_tecnico(uid, tipo, texto, capa, ruta, nota=""):
    return Hallazgo(
        uid_unidad=uid,
        categoria=Categoria.TECNICO,
        tipo=tipo,
        texto=str(texto),
        inicio=0,
        fin=len(str(texto)),
        capa=capa,
        confianza=Confianza.ALTA,
        detector="metadatos",
        nota=nota,
        ruta=ruta,
    )


def hallazgos_de_metadatos(metadatos, uid="meta", capa=Capa.METADATOS):
    """Todo metadato NO vacio es un hallazgo tecnico: se elimina o se neutraliza."""
    salida = []
    for clave, valor in (metadatos or {}).items():
        if valor in (None, "", [], {}):
            continue
        texto = str(valor)
        if len(texto) > 300:
            texto = texto[:300]
        sensible = clave.lower().replace(" ", "_") in CAMPOS_SENSIBLES
        salida.append(
            hallazgo_tecnico(
                uid, "metadato", texto, capa, clave,
                nota="campo sensible conocido" if sensible else "metadato del archivo",
            )
        )
    return salida


class ManejadorFormato:
    """Interfaz. Cada formato implementa extraer / reconstruir."""

    extensiones: tuple = ()
    nombre: str = "generico"
    reconstruccion: str = "completa"   # completa | parcial | no_soportada
    # Capas cuyo contenido NO se copia nunca al archivo reconstruido.
    capas_no_copiadas: frozenset = frozenset()

    def extraer(self, ruta: Path):
        raise NotImplementedError

    def reconstruir(self, extraido, unidades_nuevas, destino: Path, contexto=None):
        raise NotImplementedError

    def reescanear(self, ruta: Path):
        """Lectura adversarial del resultado (por defecto, la misma extraccion)."""
        return self.extraer(ruta)

    # utilidades ---------------------------------------------------------
    @staticmethod
    def alerta(nivel, codigo, mensaje, detalle=""):
        return Alerta(nivel=nivel, codigo=codigo, mensaje=mensaje, detalle=detalle)

    @staticmethod
    def mascara(valor):
        return enmascarar(str(valor))
