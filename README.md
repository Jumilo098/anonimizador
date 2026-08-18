# ANONIMIZADOR

Herramienta **local** para desidentificar documentos clínicos: quita identificadores,
preserva la información clínica y deja un informe de auditoría verificable.

> ⚠️ **ANONIMIZADOR reduce información identificable pero no garantiza anonimización absoluta.
> Revise siempre el documento antes de compartirlo. La aprobación final corresponde a una persona.**

- 🔒 **Todo ocurre en su computador.** Sin nube, sin API externa, sin telemetría.
- 🧪 **El original nunca se modifica.** Se copia, se procesa la copia y se comprueba el hash.
- 🩺 **La información clínica es intocable.** Si una transformación fuese a alterarla, se bloquea.
- 📋 **Cada ejecución deja expediente**: matriz de transformación, auditoría, verificaciones.
- 👤 **La máquina no aprueba sola.**

---

## 1. Instalar Python (una sola vez)

**Windows** — descargue Python 3.12 desde <https://www.python.org/downloads/> y, durante la
instalación, **marque la casilla “Add Python to PATH”**.

**macOS** — `brew install python@3.12` o el instalador de python.org.

**Linux** — `sudo apt install python3 python3-venv python3-pip`.

Para comprobar que quedó bien, abra una terminal y escriba:

```bash
python --version
```

Debe responder `Python 3.12.x` (o superior).

---

## 2. Instalar ANONIMIZADOR

### Windows (lo más fácil)

Haga **doble clic** en:

```
instalar.bat
```

### macOS / Linux

```bash
cd ruta/al/proyecto/anonimizador
./install.sh
```

### Manual (cualquier sistema)

```bash
cd anonimizador
python -m venv .venv
# Windows:        .venv\Scripts\python.exe -m pip install -r requirements.txt
# macOS / Linux:  ./.venv/bin/python -m pip install -r requirements.txt
```

---

## 3. Iniciar

### Windows

Doble clic en:

```
iniciar.bat
```

### macOS / Linux

```bash
./start.sh
```

### Manual

```bash
python -m streamlit run app.py --server.address=127.0.0.1
```

Se abre en su navegador, en `http://127.0.0.1:8501`. **Para cerrar**: `Ctrl + C` en la terminal.

---

## 4. Usarlo

1. En la barra lateral, elija la **finalidad** (por defecto: *Educación / discusión académica*).
2. **Arrastre** su archivo a la zona de carga. Puede soltar varios: se procesan como un expediente.
   *(¿Solo quiere verlo funcionar? Pulse **CARGAR CASO SINTÉTICO DE DEMOSTRACIÓN**: 5 casos
   completamente ficticios, sin ningún dato real.)*
3. Pulse **🔍 ANALIZAR**. Verá el tipo de documento, los identificadores encontrados por capa,
   los metadatos, los datos clínicos detectados y el riesgo inicial.
4. Pulse **🛡️ GENERAR VERSIÓN DESIDENTIFICADA**.
5. Revise las pestañas: **Antes / Después**, **Matriz de transformación**, **Integridad clínica**,
   **Prueba adversarial** y **Archivos**.
6. Descargue el documento y, cuando esté conforme, pulse **✅ Aprobar** o **❌ Rechazar**.
   Su decisión queda escrita en el expediente.

Formatos soportados en V1: `.txt` `.md` `.docx` `.pdf` `.png` `.jpg` `.jpeg` `.xlsx`

---

## 5. Dónde quedan las cosas

| Qué | Dónde |
| --- | --- |
| Copias de trabajo temporales | `.trabajo/<id-de-ejecución>/` |
| Documento desidentificado + informes | `reports/<id-de-ejecución>/` |
| Casos sintéticos de demostración | `samples/` |

Dentro de cada carpeta de `reports/`:

| Archivo | Para qué sirve |
| --- | --- |
| `documento_desidentificado.*` | **El resultado.** |
| `audit_report.html` | Informe visual completo. Ábralo con doble clic. |
| `RESUMEN.md` | Resumen corto y legible. |
| `transformation_matrix.csv` | Una fila por cada cosa que se detectó y qué se hizo con ella. |
| `audit.json` | Auditoría completa en formato máquina. |
| `integrity_report.json` | Comparación clínica antes/después. |
| `adversarial_scan.json` | Resultado del ataque al propio resultado. |
| `notas_reconstruccion.txt` | Qué se descartó al reconstruir. |

**Para borrar los temporales**: botón **🗑️ ELIMINAR ARCHIVOS DE TRABAJO** en la barra lateral
(o `python -m anonimizador.cli --limpiar`).

---

## 6. Desde la terminal (opcional)

```bash
python -m anonimizador.cli documento.docx
python -m anonimizador.cli *.pdf --finalidad publicacion
python -m anonimizador.cli documento.pdf --solo-analizar
python -m anonimizador.cli estudio.png --bandas-imagen 0.10
python -m anonimizador.cli --demo        # genera y procesa los casos sintéticos
python -m anonimizador.cli --limpiar     # borra las copias de trabajo
```

---

## 7. OCR (opcional, para leer texto dentro de imágenes)

Sin OCR, ANONIMIZADOR **detecta** que hay texto dentro de una imagen pero **no puede leerlo**,
así que no lo borra automáticamente (podría estar tapando información clínica) y sube el riesgo
residual a MODERADO. Mientras tanto tiene dos salidas manuales: la casilla **“Borrar la banda
superior e inferior”** (en endoscopia, ecografía o radiología el nombre casi siempre está
quemado ahí y el área clínica está en el centro) y la de **redactar todas las regiones**
detectadas. Para activarlo instale el motor Tesseract:

- **Windows**: <https://github.com/UB-Mannheim/tesseract/wiki> (marque el idioma español)
- **macOS**: `brew install tesseract tesseract-lang`
- **Linux**: `sudo apt install tesseract-ocr tesseract-ocr-spa`

La barra lateral le dirá si lo detectó.

---

## 8. Comprobar que funciona

```bash
python -m pytest tests -q
```

49 pruebas: que los identificadores desaparecen (incluso del XML interno de un DOCX), que
`Hemoglobina: 8.9 g/dL` sale exactamente igual, que `colon ascendente` no se convierte en otra
cosa, que los metadatos se saneen, que el original queda intacto, que un cambio clínico
inesperado produce `FAIL` y que la prueba adversarial caza una fuga inyectada a propósito.

---

## 9. Estructura del proyecto

```
anonimizador/
├── app.py                     # interfaz local (Streamlit)
├── requirements.txt
├── instalar.bat / iniciar.bat        # Windows
├── install.sh  / start.sh            # macOS y Linux
├── anonimizador/
│   ├── config.py              # finalidades, límites, banderas (red e IA apagadas)
│   ├── models.py              # capas, categorías, acciones, riesgos, estados
│   ├── cli.py                 # línea de comandos
│   ├── casos_sinteticos.py    # generador de casos ficticios
│   ├── core/
│   │   ├── pipeline.py        # orquestación de punta a punta
│   │   ├── detectors/         # directos, indirectos, contextuales, clínico (protección)
│   │   ├── transformers/      # política de decisión + aplicación
│   │   ├── validators/        # integridad, alucinaciones, adversarial
│   │   ├── auditors/          # audit.json, CSV, HTML, RESUMEN.md
│   │   ├── risk/              # riesgo residual explicable
│   │   └── llm/               # interfaz de IA, APAGADA en V1
│   ├── formats/               # docx, pdf, imagen, texto, xlsx, códigos QR
│   ├── resources/lexicos.py   # léxicos clínicos y de identificadores
│   └── util/                  # hashes, seguridad de entrada, área de trabajo, texto
├── tests/
├── samples/                   # casos SINTÉTICOS (nunca guarde pacientes reales aquí)
├── reports/                   # salidas y expedientes de auditoría
└── docs/
    ├── INFORME_ANONIMIZADOR.md        # informe para profesionales de salud
    └── COBERTURA_Y_LIMITACIONES.md    # qué está implementado y qué no
```

---

## 10. Léalo antes de confiar

- **`docs/COBERTURA_Y_LIMITACIONES.md`** — qué funciona hoy (`IMPLEMENTADO`), qué funciona a
  medias (`PARCIAL`) y qué solo está diseñado (`NO IMPLEMENTADO`).
- **`docs/INFORME_ANONIMIZADOR.md`** — explicación completa para profesionales de la salud.

Ambos están también en **PDF** (`docs/*.pdf`). Se regeneran localmente, sin Internet, con:

```bash
python docs/generar_pdf.py
```

---

## 11. Privacidad y seguridad

- Localhost, archivos locales, sin nube, sin API externa, sin analítica ni tracking.
- No se ejecutan macros ni JavaScript de PDF. **Nunca** se abre la URL de un QR.
- No se confía en la extensión del archivo: se valida la firma binaria real.
- Límites de tamaño de archivo, de páginas y de píxeles; nombres de archivo saneados.
- Los informes guardan los identificadores **enmascarados y con hash**, para no convertirse
  ellos mismos en una tabla de reidentificación.

## Licencia y responsabilidad

Herramienta de apoyo. **No** constituye asesoría legal ni certificación de cumplimiento
normativo (Ley 1581/2015, Resolución 1995/1999, RGPD, HIPAA u otras). La responsabilidad sobre
qué se comparte y con quién es siempre de la persona que aprueba el documento.
