"""Linea de comandos de ANONIMIZADOR (util para demos y para lotes pequenos).

  python -m anonimizador.cli documento.docx
  python -m anonimizador.cli carpeta/*.pdf --finalidad publicacion
  python -m anonimizador.cli --demo
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, casos_sinteticos
from .config import AVISO_PERMANENTE, FINALIDADES, FINALIDAD_POR_DEFECTO, Opciones
from .core import pipeline
from .util import workspace


def _imprimir(resultado, ruta):
    print("=" * 78)
    print("Archivo:", Path(ruta).name)
    if not resultado.ok:
        print("  RECHAZADO:", resultado.error)
        return
    aud = resultado.auditoria
    v = aud["integridad_clinica"]
    print("  estado................:", resultado.estado.value)
    print("  riesgo residual.......:", resultado.riesgo.value)
    print("  integridad clinica....:", v["transformacion"].get("veredicto"))
    print("  reconstruccion........:", v["reconstruccion"].get("veredicto"))
    print("  alucinaciones.........:", v["alucinaciones"].get("veredicto"))
    print("  prueba adversarial....:", aud["adversarial"].get("veredicto"))
    print("  transformaciones......:", aud["transformaciones"]["por_accion"])
    print("  resultado.............:", resultado.archivos["resultado"])
    print("  informes..............:", resultado.archivos["carpeta"])
    for motivo in resultado.motivos_riesgo:
        print("   -", motivo)
    for al in resultado.alertas:
        print("   [%s] %s: %s" % (al.nivel.upper(), al.codigo, al.mensaje))


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="anonimizador",
        description="Desidentificacion local de documentos clinicos. "
                    + AVISO_PERMANENTE,
    )
    p.add_argument("archivos", nargs="*", help="archivos a procesar")
    p.add_argument("--finalidad", default=FINALIDAD_POR_DEFECTO,
                   choices=list(FINALIDADES))
    p.add_argument("--demo", action="store_true",
                   help="genera y procesa los casos sinteticos de demostracion")
    p.add_argument("--solo-analizar", action="store_true",
                   help="no genera nada: solo informa que encontro")
    p.add_argument("--redactar-regiones-imagen", action="store_true")
    p.add_argument("--bandas-imagen", type=float, default=0.0, metavar="FRACCION",
                   help="borra esa fraccion superior e inferior de cada imagen "
                        "(p. ej. 0.10); ahi suele estar quemado el nombre")
    p.add_argument("--sin-eliminar-qr", action="store_true")
    p.add_argument("--limpiar", action="store_true",
                   help="elimina las copias de trabajo y termina")
    p.add_argument("--version", action="version", version="ANONIMIZADOR " + __version__)
    args = p.parse_args(argv)

    if args.limpiar:
        borrados = workspace.eliminar_archivos_de_trabajo()
        print("Copias de trabajo eliminadas:", borrados["trabajo"])
        return 0

    rutas = [Path(a) for a in args.archivos]
    if args.demo:
        rutas = list(casos_sinteticos.generar(forzar=True))
    if not rutas:
        p.print_help()
        return 2

    opciones = Opciones(
        finalidad=args.finalidad,
        redactar_regiones_imagen=args.redactar_regiones_imagen,
        banda_superior_imagen=args.bandas_imagen,
        banda_inferior_imagen=args.bandas_imagen,
        eliminar_qr=not args.sin_eliminar_qr,
    )

    print(AVISO_PERMANENTE)
    print()
    salida = 0
    for ruta in rutas:
        if args.solo_analizar:
            info = pipeline.analizar(ruta, opciones=opciones)
            print("=" * 78)
            print("Archivo:", ruta.name)
            if not info.get("ok"):
                print("  RECHAZADO:", info.get("error"))
                salida = 1
                continue
            print("  formato:", info["formato"], "| capas:", ", ".join(info["capas"]))
            print("  identificadores:", info["total_identificadores"],
                  "| metadatos:", info["n_metadatos"],
                  "| datos clinicos:", info["total_datos_clinicos"])
            print("  riesgo inicial:", info["riesgo_inicial"])
            continue
        r = pipeline.procesar(ruta, opciones=opciones)
        _imprimir(r, ruta)
        if not r.ok:
            salida = 1
    print()
    print("Recuerde: la aprobacion final corresponde a una persona.")
    return salida


if __name__ == "__main__":
    sys.exit(main())
