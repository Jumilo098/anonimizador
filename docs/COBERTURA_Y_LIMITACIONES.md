# ANONIMIZADOR — cobertura y limitaciones

> **ANONIMIZADOR reduce información identificable pero no garantiza anonimización absoluta.
> Revise siempre el documento antes de compartirlo. La aprobación final corresponde a una persona.**

Este documento distingue tres cosas y no las mezcla:

- `IMPLEMENTADO` — está en el código, se ejecuta y hay un test que lo comprueba.
- `PARCIAL` — funciona, pero con un alcance recortado que se explica.
- `NO IMPLEMENTADO` — está diseñado o previsto, pero **no existe** todavía.

Versión: **1.0.0** · Fecha de esta revisión: **17 de agosto de 2026** ·
Entorno de verificación: Windows 11, Python 3.12.4, sin Tesseract instalado.

---

## V1 — LO QUE FUNCIONA AHORA

### Protocolo y arquitectura

| Elemento | Estado | Detalle |
| --- | --- | --- |
| A — Aclare la finalidad | `IMPLEMENTADO` | 4 finalidades configurables; por defecto *Educación / discusión académica*. Cambia qué se generaliza. |
| N — No cargue el original | `IMPLEMENTADO` | Se calcula SHA-256, se copia a un área aislada y **solo se trabaja sobre la copia**. Al final se vuelve a comprobar el hash del original. Test: `test_original_intacto`. |
| Procesamiento local | `IMPLEMENTADO` | Sin red, sin API externa, sin telemetría. `ALLOW_NETWORK=False`, `ENABLE_LLM=False`, `ENABLE_TELEMETRY=False`. Test: `test_no_hay_red_ni_ia_por_defecto`. |
| T — Tamice identificadores (5 capas) | `IMPLEMENTADO` / `PARCIAL` | Ver tabla siguiente. |
| Regla clínica innegociable | `IMPLEMENTADO` | Antes de reescribir nada se calculan *spans protegidos*; una transformación que los pise se **bloquea** y se manda a revisión. |
| Extraer y reconstruir | `IMPLEMENTADO` (TXT, DOCX) / `PARCIAL` (PDF, XLSX, imagen) | Ver "Formatos". |
| Verificación (integridad, alucinaciones, adversarial) | `IMPLEMENTADO` | Cuatro veredictos independientes en cada ejecución. |
| Riesgo residual explicable | `IMPLEMENTADO` | 5 niveles; siempre con la lista de motivos. Nunca dice "100 % anonimizado". |
| Aprobación humana | `IMPLEMENTADO` | 4 estados; la decisión se graba en `audit.json` y en `revision_humana.json`. |
| Expediente de auditoría | `IMPLEMENTADO` | `audit.json`, `transformation_matrix.csv`, `integrity_report.json`, `adversarial_scan.json`, `audit_report.html`, `RESUMEN.md`. |
| Interfaz para no técnicos | `IMPLEMENTADO` | Streamlit local: arrastrar → finalidad → ANALIZAR → GENERAR → aprobar/rechazar. |
| Expediente multi-archivo | `IMPLEMENTADO` | Varios archivos se procesan juntos; **cada uno con su propia auditoría** (los seudónimos no se comparten entre archivos, ver limitaciones). |
| Modo demostración | `IMPLEMENTADO` | 5 casos sintéticos generados al vuelo, sin ningún dato real. |
| Capa de IA opcional | `NO IMPLEMENTADO` (a propósito) | Existe la interfaz `ProveedorLLM`, apagada y sin ninguna implementación. V1 es 100 % determinista. |

### Las cinco capas de tamizado

| Capa | Estado | Qué detecta hoy |
| --- | --- | --- |
| 1. Directos | `IMPLEMENTADO` | Correo, URL, IP, usuario de red, documento de identidad (CC/TI/CE/NIT/DNI/RUT/CURP/pasaporte), historia clínica, números administrativos (orden, autorización, factura, póliza, afiliado, cama…), teléfono etiquetado y teléfono móvil, dirección postal, código postal, firma/registro médico, nombres por etiqueta (`Paciente:`, `Acompañante:`, `Madre:`, `Elaborado por:`…), nombres tras tratamiento (`Dr.`, `Dra.`, `Lic.`) y nombres por léxico. |
| 2. Indirectos | `IMPLEMENTADO` | Edad exacta, fecha de nacimiento, fechas, ocupación/cargo, institución (hospital, clínica, IPS, laboratorio…), aseguradora/EPS, localidad y departamento. |
| 3. Contextuales | `PARCIAL` | Se puntúa la **combinación residual** de cuasi-identificadores y se alerta a partir de un umbral. **No** hay cálculo de k-anonimato ni contraste contra un padrón poblacional. |
| 4. Visuales | `PARCIAL` | QR y códigos de barras: detección y **destrucción real** de píxeles, con verificación posterior. Regiones con aspecto de texto: detección morfológica. **Leer** ese texto requiere OCR (ver abajo). Como salida práctica se puede borrar la banda superior/inferior de la imagen, donde suele estar quemado el identificador. Logos y firmas manuscritas: no se reconocen como tales. |
| 5. Técnicos | `IMPLEMENTADO` | Nombre del archivo, propiedades core/app/custom de OOXML, comentarios y sus autores, control de cambios y sus autores, relaciones externas, notas al pie, metadatos y XMP de PDF, anotaciones, campos de formulario, archivos embebidos, marcadores activos (`/JavaScript`, `/OpenAction`, `/Launch`…), EXIF y chunks de texto de PNG, propiedades de XLSX. |

### Formatos

| Formato | Reconstrucción | Estado | Qué se conserva / qué se pierde |
| --- | --- | --- | --- |
| `.txt` / `.md` | Completa | `IMPLEMENTADO` | Texto íntegro reescrito desde cero. |
| `.docx` | Completa | `IMPLEMENTADO` | Se reconstruye con párrafos, títulos y tablas, más anexos con el texto de encabezados y pies. **No se copian**: comentarios, control de cambios, macros, objetos embebidos, imágenes, propiedades, plantillas, miniatura. Verificado: los identificadores no aparecen ni en el XML interno del ZIP. |
| `.pdf` | Parcial (solo texto) | `PARCIAL` | Se genera un PDF nuevo con reportlab. **No se copian**: imágenes, anotaciones, formularios, QR, capas, objetos ni metadatos. Un PDF escaneado se marca `NO EVALUABLE` y no se da por bueno. |
| `.png` / `.jpg` | Parcial (píxeles) | `PARCIAL` | Se reescribe la imagen sin EXIF/XMP. QR y barcodes se destruyen de verdad. Las regiones con aspecto de texto **no se borran por defecto** (ver "la decisión difícil"). |
| `.xlsx` | Parcial (valores) | `PARCIAL` | Valores de texto minimizados y números copiados sin tocar. **No se copian**: fórmulas, comentarios de celda, formato, gráficos, imágenes, macros. |

### Verificaciones automáticas

| Verificación | Estado | Qué hace |
| --- | --- | --- |
| Integridad clínica de la transformación | `IMPLEMENTADO` | Compara original vs. minimizado a nivel de valor atómico (número+unidad, analito=valor, signo vital, dosis, medida, porcentaje, anatomía, lateralidad, medicamento, procedimiento, diagnóstico, negación, certeza) y clasifica en `EXACT_MATCH`, `EXPECTED_TRANSFORMATION`, `UNEXPECTED_CHANGE`, `MISSING`, `NEW_CONTENT`. |
| Integridad de la reconstrucción | `IMPLEMENTADO` | Compara lo que se **quiso** escribir con lo que se puede **volver a leer** del archivo generado. Atrapa pérdidas del escritor de formato. |
| Detección de alucinaciones | `IMPLEMENTADO` | Marca todo valor clínico del resultado que el original no respalda, y localiza la frase donde aparece. |
| Prueba adversarial | `IMPLEMENTADO` | Reabre el archivo generado y vuelve a atacarlo: texto, metadatos, comentarios, XML, anotaciones, QR y nombre del archivo. Una fuga baja el estado a `REQUIRES_MANUAL_REVIEW` y **señala el módulo responsable**. |

### Seguridad

`IMPLEMENTADO`: sin `eval`; no se ejecutan macros ni JavaScript de PDF; no se abre ninguna URL
(tampoco la de un QR); no se confía en la extensión (se valida la firma binaria); límite de
tamaño de archivo, de páginas de PDF y de píxeles de imagen; nombres de archivo saneados;
directorio de trabajo aislado; archivos corruptos se reportan sin ejecutarse; el archivo de
salida se nombra de forma neutra.

---

## La decisión difícil de V1, explicada

Hay dos sitios donde ANONIMIZADOR **prefiere no tocar** y pedir revisión humana, porque la
regla clínica está por encima de la privacidad automática:

1. **Candidatos a nombre de baja confianza.** Una secuencia capitalizada que no está en el
   léxico de nombres podría ser un nombre… o una marca comercial de un fármaco, o un epónimo
   (*maniobra de Valsalva*). Borrarla a ciegas sería alterar la información clínica. Por eso
   se marca, sube el riesgo a `MODERADO` y se pide revisión. Puede forzarse la sustitución con
   la casilla *"Sustituir también candidatos a nombre de baja confianza"*.
2. **Texto dentro de los píxeles de una imagen.** Sin OCR no se puede saber si esa franja de
   texto es el nombre del paciente o una escala de medida. Se detecta la región, se informa y
   se pide revisión. Puede forzarse la redacción con la casilla *"Redactar TODAS las regiones
   con aspecto de texto"*, asumiendo que puede tapar parte de la imagen.

En ambos casos el sistema **dice lo que hizo y lo que no hizo**. No simula que quedó resuelto.

---

## Limitaciones conocidas de V1 (léalas antes de confiar)

1. **OCR no está instalado en este equipo.** `pytesseract` está en las dependencias, pero el
   binario Tesseract no. Sin él, el texto quemado en una imagen se detecta como región pero
   **no se puede leer ni clasificar**. Instrucciones de instalación en el README.
2. **Las imágenes de un DOCX o de un PDF no se transfieren al resultado** y sus píxeles no se
   analizan. Se avisa con una alerta. Si la imagen importa clínicamente, hay que exportarla y
   procesarla como archivo de imagen.
3. **PDF escaneado**: se detecta y se marca `NO EVALUABLE`. V1 no lo resuelve.
4. **Nombres no cubiertos por el léxico**: los léxicos son listas explícitas y cortas
   (~120 nombres de pila, ~70 apellidos). Un apellido poco frecuente que aparezca sin etiqueta
   y sin tratamiento cae en "posible nombre" → revisión humana, no eliminación automática.
5. **Riesgo contextual**: se puntúa la combinación, pero no hay k-anonimato real. Un caso raro
   (enfermedad infrecuente + institución + fecha) puede seguir siendo identificable aunque el
   informe diga riesgo `BAJO`. **Esto es exactamente para lo que existe la revisión humana.**
6. **Los seudónimos no se comparten entre archivos** de un mismo expediente: `[PERSONA 2]` en
   un documento no es necesariamente `[PERSONA 2]` en otro.
7. **Firmas manuscritas, logotipos y sellos** dentro de imágenes no se reconocen como tales.
8. **No hay DICOM.** Un `.dcm` no se acepta.
9. **El HTML de auditoría contiene los datos clínicos preservados** (que no son identificadores),
   por diseño, para poder revisarlos. Trátelo como material clínico, no lo publique sin más.
10. **`RTF`, `ODT`, `PPTX`, `EML`, `MSG`, `CSV`, `ZIP`, audio y vídeo**: no soportados.
11. **La detección está afinada para español clínico de LatAm/España.** En otro idioma la
    cobertura cae mucho.

---

## V2 — SIGUIENTE NIVEL (viable, requiere más desarrollo)

`NO IMPLEMENTADO` todo lo de esta sección.

- OCR local empaquetado (Tesseract embebido o `easyocr`), con clasificación de cada palabra
  reconocida y redacción **selectiva** solo de las que sean identificadores.
- Transferir imágenes al DOCX/PDF reconstruido **después** de pasarlas por el pipeline de
  imagen, en lugar de descartarlas.
- Capa de PDF escaneado: rasterizar → OCR → reconstruir PDF con texto.
- Seudónimos coherentes en todo un expediente (mismo paciente = misma etiqueta en 12 archivos).
- Formatos: `PPTX`, `ODT`, `RTF`, `CSV`, `EML`/`MSG` con adjuntos.
- Diccionarios de nombres ampliables por el usuario desde la interfaz, con lista blanca clínica.
- Detección de firmas manuscritas y logotipos por plantilla.
- Cálculo de k-anonimato sobre un lote (no sobre un documento suelto).
- Perfiles de finalidad editables y guardables por institución.
- Modo lote por línea de comandos con informe consolidado del expediente.
- Comparador visual ANTES/DESPUÉS con resaltado de diferencias palabra a palabra.
- Firma criptográfica del expediente de auditoría (para que no se pueda alterar a posteriori).

---

## V3 — NIVEL PROFESIONAL / INSTITUCIONAL

`NO IMPLEMENTADO`. Requiere presupuesto, infraestructura y, sobre todo, decisiones legales
y de gobierno del dato que no le corresponden a una herramienta.

- **DICOM**: desidentificación de cabeceras según DICOM PS3.15 Anexo E, *burned-in annotation*,
  overlays, secuencias privadas, UID remapping consistente.
- **Integración PACS / HIS / HL7 / FHIR**.
- **Modelos NER clínicos** en español (transformer local) como capa *sugerente*, siempre
  validada por las reglas deterministas.
- **Modelos de visión** para detectar texto, firmas y logotipos en imágenes médicas.
- Procesamiento masivo (miles de documentos), colas, paralelismo, reintentos.
- Autenticación, roles, trazabilidad por usuario, auditoría institucional centralizada.
- Cifrado en reposo y en tránsito, gestión de claves, borrado seguro certificado.
- Políticas organizacionales: retención, finalidad declarada, consentimiento, DPIA.
- **Revisión jurídica y regulatoria** (Ley 1581/2015 y Resolución 1995/1999 en Colombia, RGPD
  en la UE, HIPAA *Safe Harbor* / *Expert Determination* en EE. UU.). ANONIMIZADOR **no**
  certifica el cumplimiento de ninguna de ellas.
- Validación clínica formal: medir sensibilidad/especificidad de la detección contra un corpus
  anotado por profesionales.

---

## Cómo comprobar usted mismo lo que dice este documento

```bash
python -m pytest tests -q          # 49 pruebas
python -m anonimizador.cli --demo  # procesa los 5 casos sintéticos e imprime los veredictos
```

Cada ejecución deja su propio expediente en `reports/<id>/`. Ábralo: `audit_report.html`.
