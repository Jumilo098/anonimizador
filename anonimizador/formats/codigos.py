"""Deteccion de QR y codigos de barras (bloque 12).

Regla: NUNCA se visita la URL contenida en un QR. Solo se registra su
existencia y un hash del contenido, jamas el contenido completo.
"""
from __future__ import annotations

import numpy as np

from ..util.hashing import enmascarar, hash_hallazgo

try:
    import cv2
    CV2_OK = True
except Exception:  # pragma: no cover
    cv2 = None
    CV2_OK = False


def disponible() -> bool:
    return CV2_OK


def _a_gris(imagen):
    arr = np.asarray(imagen)
    if arr.ndim == 3:
        if arr.shape[2] == 4:
            arr = arr[:, :, :3]
        return cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    return arr


def detectar_codigos(imagen) -> list:
    """Devuelve [{tipo, caja(x,y,w,h), contenido_hash, contenido_mascara}]."""
    if not CV2_OK:
        return []
    gris = _a_gris(imagen)
    salida = []
    try:
        detector = cv2.QRCodeDetector()
        ok, textos, puntos, _ = detector.detectAndDecodeMulti(gris)
        if ok and puntos is not None:
            for i, cuadro in enumerate(puntos):
                xs = [float(p[0]) for p in cuadro]
                ys = [float(p[1]) for p in cuadro]
                contenido = textos[i] if i < len(textos) else ""
                salida.append({
                    "tipo": "qr",
                    "caja": (int(min(xs)), int(min(ys)),
                             int(max(xs) - min(xs)), int(max(ys) - min(ys))),
                    "contenido_hash": hash_hallazgo(contenido) if contenido else "",
                    "contenido_mascara": enmascarar(contenido, 4) if contenido else "",
                    "decodificado": bool(contenido),
                })
    except Exception:
        pass
    # deteccion de posicion aunque no se pueda decodificar
    if not salida:
        try:
            detector = cv2.QRCodeDetector()
            ok, puntos = detector.detectMulti(gris)
            if ok and puntos is not None:
                for cuadro in puntos:
                    xs = [float(p[0]) for p in cuadro]
                    ys = [float(p[1]) for p in cuadro]
                    salida.append({
                        "tipo": "qr",
                        "caja": (int(min(xs)), int(min(ys)),
                                 int(max(xs) - min(xs)), int(max(ys) - min(ys))),
                        "contenido_hash": "",
                        "contenido_mascara": "",
                        "decodificado": False,
                    })
        except Exception:
            pass
    # codigos de barras (segun version de OpenCV)
    try:
        if hasattr(cv2, "barcode") and hasattr(cv2.barcode, "BarcodeDetector"):
            bd = cv2.barcode.BarcodeDetector()
            ok, textos, tipos, puntos = bd.detectAndDecodeWithType(gris)
            if ok and puntos is not None:
                for i, cuadro in enumerate(puntos):
                    xs = [float(p[0]) for p in cuadro]
                    ys = [float(p[1]) for p in cuadro]
                    contenido = textos[i] if i < len(textos) else ""
                    salida.append({
                        "tipo": "barcode",
                        "caja": (int(min(xs)), int(min(ys)),
                                 int(max(xs) - min(xs)), int(max(ys) - min(ys))),
                        "contenido_hash": hash_hallazgo(contenido) if contenido else "",
                        "contenido_mascara": enmascarar(contenido, 4) if contenido else "",
                        "decodificado": bool(contenido),
                    })
    except Exception:
        pass
    return salida
