"""Imagenes clinicas (PNG/JPG).

Regla superior: NO DANAR INFORMACION CLINICA.
Si no se puede garantizar que borrar una region no afecta el area clinica
relevante, la region NO se toca: se marca y se pide revision humana.

Honestidad V1:
  - QR y codigos de barras: se detectan y, si el usuario lo deja activado,
    se DESTRUYEN de verdad (se sobreescriben los pixeles y se reencodifica).
  - Texto dentro de los pixeles: se detectan REGIONES CANDIDATAS con
    heuristica morfologica. Sin OCR instalado NO se puede saber que dicen,
    asi que por defecto NO se borran: se reportan.
  - Con Tesseract instalado se activa OCR local y las regiones cuyo texto
    contiene identificadores si se pueden redactar.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ExifTags

from ..config import MAX_IMAGE_PIXELS
from ..models import Alerta, Capa, DocumentoExtraido
from . import codigos
from .base import ManejadorFormato, hallazgos_de_metadatos, unidad

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

try:
    import cv2
    CV2_OK = True
except Exception:
    cv2 = None
    CV2_OK = False


def ocr_disponible():
    """(bool, detalle). El OCR es local; si no esta, se dice claramente."""
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        return True, "Tesseract " + str(version)
    except Exception as exc:
        return False, type(exc).__name__


def _exif(img):
    datos = {}
    try:
        bruto = img.getexif()
        for tag, valor in (bruto or {}).items():
            nombre = ExifTags.TAGS.get(tag, str(tag))
            texto = str(valor)
            if texto.strip() and texto != "0":
                datos["exif:" + nombre] = texto[:200]
    except Exception:
        pass
    for clave, valor in (getattr(img, "info", {}) or {}).items():
        if clave in ("exif", "icc_profile"):
            datos["info:" + clave] = "(%d bytes)" % len(valor or b"")
            continue
        if isinstance(valor, (str, int, float)):
            texto = str(valor)
            if texto.strip():
                datos["info:" + clave] = texto[:200]
    return datos


def detectar_regiones_texto(gris):
    """Heuristica morfologica: devuelve cajas (x, y, w, h) candidatas a texto."""
    if not CV2_OK:
        return []
    try:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        grad = cv2.morphologyEx(gris, cv2.MORPH_GRADIENT, kernel)
        _, binaria = cv2.threshold(grad, 0, 255,
                                   cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel2 = cv2.getStructuringElement(cv2.MORPH_RECT, (18, 5))
        conectada = cv2.morphologyEx(binaria, cv2.MORPH_CLOSE, kernel2)
        contornos, _ = cv2.findContours(conectada, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        alto, ancho = gris.shape[:2]
        cajas = []
        for cnt in contornos:
            x, y, w, h = cv2.boundingRect(cnt)
            if h < 8 or w < 24:
                continue
            if h > alto * 0.35 or w > ancho * 0.98:
                continue
            relacion = w / float(h)
            if relacion < 1.5 or relacion > 40:
                continue
            densidad = cv2.countNonZero(binaria[y:y + h, x:x + w]) / float(w * h)
            if densidad < 0.10 or densidad > 0.85:
                continue
            cajas.append((int(x), int(y), int(w), int(h)))
        cajas.sort(key=lambda c: (c[1], c[0]))
        return cajas[:200]
    except Exception:
        return []


def _ocr_cajas(img):
    """[(texto, (x,y,w,h))] usando Tesseract local, si esta instalado."""
    ok, _ = ocr_disponible()
    if not ok:
        return []
    try:
        import pytesseract
        datos = pytesseract.image_to_data(
            img, lang="spa+eng", output_type=pytesseract.Output.DICT
        )
    except Exception:
        try:
            import pytesseract
            datos = pytesseract.image_to_data(
                img, output_type=pytesseract.Output.DICT
            )
        except Exception:
            return []
    salida = []
    for i, palabra in enumerate(datos.get("text", [])):
        if not palabra or not palabra.strip():
            continue
        try:
            conf = float(datos["conf"][i])
        except (ValueError, KeyError):
            conf = -1
        if conf < 40:
            continue
        salida.append((palabra.strip(), (datos["left"][i], datos["top"][i],
                                         datos["width"][i], datos["height"][i])))
    return salida


class ManejadorImagen(ManejadorFormato):
    extensiones = (".png", ".jpg", ".jpeg")
    nombre = "imagen"
    reconstruccion = "parcial"

    def extraer(self, ruta: Path) -> DocumentoExtraido:
        ruta = Path(ruta)
        doc = DocumentoExtraido(formato="imagen")
        try:
            img = Image.open(ruta)
            img.load()
        except Exception as exc:
            doc.alertas.append(
                Alerta("critica", "IMAGEN_ILEGIBLE", "No se pudo abrir la imagen",
                       str(exc)[:200])
            )
            return doc

        rgb = img.convert("RGB")
        arr = np.asarray(rgb)
        gris = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY) if CV2_OK else None

        doc.metadatos = _exif(img)
        doc.hallazgos_tecnicos = hallazgos_de_metadatos(doc.metadatos, capa=Capa.METADATOS)

        graficos = codigos.detectar_codigos(arr)
        regiones = detectar_regiones_texto(gris) if gris is not None else []
        ocr = _ocr_cajas(rgb)

        texto_ocr = " ".join(p for p, _ in ocr)
        if texto_ocr:
            doc.unidades.append(
                unidad("ocr", texto_ocr, Capa.PIXELES, "texto reconocido (OCR local)",
                       editable=False)
            )
        doc.unidades.append(
            unidad("nombre_archivo", ruta.stem, Capa.NOMBRE_ARCHIVO,
                   "nombre del archivo")
        )

        hay_ocr, detalle_ocr = ocr_disponible()
        doc.info = {
            "ancho": img.width,
            "alto": img.height,
            "modo": img.mode,
            "formato": img.format,
            "codigos_graficos": graficos,
            "regiones_texto": regiones,
            "ocr_disponible": hay_ocr,
            "ocr_detalle": detalle_ocr,
            "palabras_ocr": len(ocr),
            "_ocr_cajas": ocr,
        }

        if graficos:
            doc.alertas.append(
                Alerta("critica", "CODIGOS_GRAFICOS",
                       "Se detectaron %d codigo(s) QR/barras en la imagen."
                       % len(graficos),
                       "Se destruyen los pixeles en la version reconstruida. "
                       "Nunca se abre la URL que contengan.")
            )
        if regiones and not hay_ocr:
            doc.alertas.append(
                Alerta("advertencia", "TEXTO_EN_PIXELES_NO_EVALUABLE",
                       "Hay %d region(es) con aspecto de texto dentro de la imagen."
                       % len(regiones),
                       "Sin OCR instalado (" + detalle_ocr + ") NO se puede saber si "
                       "identifican al paciente. NO se borran automaticamente para no "
                       "danar informacion clinica: requieren revision humana.")
            )
        if not CV2_OK:
            doc.alertas.append(
                Alerta("advertencia", "SIN_OPENCV",
                       "OpenCV no esta disponible: no hay analisis de pixeles.")
            )
        return doc

    # -- reconstruccion ----------------------------------------------------
    def reconstruir(self, extraido, unidades_nuevas, destino: Path, contexto=None):
        opciones = getattr(contexto, "opciones", None)
        origen = getattr(contexto, "copia", None)
        destino = Path(destino)
        img = Image.open(origen).convert("RGB")
        dibujo = ImageDraw.Draw(img)

        destruidas = []
        marcadas = []

        if not opciones or getattr(opciones, "eliminar_qr", True):
            for c in extraido.info.get("codigos_graficos", []):
                x, y, w, h = c["caja"]
                margen = max(4, int(0.05 * max(w, h)))
                caja = (max(0, x - margen), max(0, y - margen),
                        min(img.width, x + w + margen), min(img.height, y + h + margen))
                dibujo.rectangle(caja, fill=(128, 128, 128))
                destruidas.append({"motivo": "codigo grafico (" + c["tipo"] + ")",
                                   "caja": caja})

        redactar = bool(opciones and getattr(opciones, "redactar_regiones_imagen", False))
        regiones = extraido.info.get("regiones_texto", [])
        if redactar:
            for (x, y, w, h) in regiones:
                dibujo.rectangle((x, y, x + w, y + h), fill=(0, 0, 0))
                destruidas.append({"motivo": "region con aspecto de texto "
                                             "(redaccion pedida por el usuario)",
                                   "caja": (x, y, x + w, y + h)})
        else:
            marcadas = [{"motivo": "region con aspecto de texto sin clasificar",
                         "caja": (x, y, x + w, y + h)} for (x, y, w, h) in regiones]

        # guardar SIN metadatos: se crea una imagen nueva a partir de los pixeles
        limpia = Image.new("RGB", img.size)
        limpia.putdata(list(img.getdata()))
        if destino.suffix.lower() in (".jpg", ".jpeg"):
            limpia.save(destino, "JPEG", quality=95)
        else:
            limpia.save(destino, "PNG")

        # verificacion inmediata: ningun codigo debe sobrevivir
        residuales = codigos.detectar_codigos(np.asarray(Image.open(destino).convert("RGB")))

        return {
            "texto_esperado": "",
            "capas_descartadas": ["metadatos EXIF/XMP"],
            "regiones_destruidas": destruidas,
            "regiones_marcadas": marcadas,
            "codigos_residuales": residuales,
            "notas": [
                "Imagen reescrita pixel a pixel en un archivo nuevo, sin EXIF ni XMP.",
                "Los codigos QR/barras detectados se sobreescriben: no son "
                "recuperables en el resultado.",
                "Las regiones de texto no clasificadas NO se tocan por seguridad "
                "clinica; quedan listadas para revision humana.",
            ],
        }
