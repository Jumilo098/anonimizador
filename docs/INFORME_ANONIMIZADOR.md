# ANONIMIZADOR — informe para profesionales de la salud

*Versión 1.0.0 · documento pensado para leerse sin saber programar.*

> **ANONIMIZADOR reduce información identificable pero no garantiza anonimización absoluta.
> Revise siempre el documento antes de compartirlo. La aprobación final corresponde a una persona.**

---

## 1. Qué hace

Usted arrastra un documento clínico. ANONIMIZADOR le devuelve **una versión nueva del
documento**, reconstruida y minimizada, más un **informe de auditoría** que explica, línea por
línea, qué se quitó, qué se generalizó, qué se conservó y **por qué**.

Lo que **no** hace, y conviene decirlo primero:

- No diagnostica. No opina sobre el caso.
- No reescribe la historia clínica "con sus palabras".
- No promete que el paciente sea irreconocible.
- No sustituye su criterio ni el de un comité de ética.

Su objetivo es convertir un procedimiento repetitivo y fácil de olvidar —quitar el nombre,
el documento, la fecha, la EPS, el pie de página, los metadatos de Word— en algo sistemático,
verificable y con rastro escrito.

---

## 2. Cómo funciona, en una frase

**Extrae** todo el contenido del archivo (incluido lo que no se ve), **clasifica** cada dato,
**minimiza** solo lo identificador, **reconstruye** un archivo limpio desde cero, **compara**
el antes con el después, **se ataca a sí mismo** para ver si algo sobrevivió, y **le pide a
usted** que apruebe o rechace.

```
ORIGINAL → EXTRACCIÓN → DETECCIÓN → TRANSFORMACIÓN → RECONSTRUCCIÓN
        → COMPARACIÓN → AUDITORÍA → REVISIÓN HUMANA
```

---

## 3. El protocolo "ANTES"

### A — Aclare la finalidad

Antes de tocar nada, la herramienta le pregunta **para qué** va a usar el material. No es
burocracia: cambia el resultado.

| Finalidad | Qué hace distinto |
| --- | --- |
| Educación / discusión académica *(por defecto)* | Edad en décadas, fechas como Día 1/Día 2, sin institución ni lugar preciso. |
| Publicación / caso clínico escrito | Igual, y con criterio más estricto. |
| Interconsulta / segunda opinión | **Conserva la edad y las fechas exactas**, porque pueden cambiar la interpretación clínica; avisa de que eso sube el riesgo. |
| Investigación / dataset interno | Minimización fuerte y consistente. No sustituye la aprobación del comité. |

El principio es *minimización*: se conserva **solo lo necesario para esa finalidad**.

### N — No cargue el original

Regla absoluta: **el archivo original nunca se modifica**. El sistema calcula su huella digital
(SHA-256), hace una copia en un área aislada, trabaja únicamente sobre la copia, genera un
archivo nuevo y, al terminar, vuelve a calcular la huella del original para demostrar que sigue
idéntico. Ese hash queda escrito en el informe.

Además, **todo ocurre en su computador**. No hay nube, no hay servicio externo, no hay
"inteligencia artificial en línea", no hay telemetría. Si algún día se añadiera una función que
necesitara Internet, vendría apagada de fábrica y documentada.

### T — Tamice identificadores

Se busca en **cinco capas**:

1. **Directos** — nombre, documento, historia clínica, teléfono, correo, dirección, póliza,
   firma, nombres de acompañantes y de profesionales.
2. **Indirectos** — edad exacta, fecha de nacimiento, fechas, ocupación, institución,
   aseguradora, localidad.
3. **Contextuales** — la combinación. *Mujer de 64 años, docente, de una ciudad concreta,
   atendida en tal hospital, tal día* puede identificar a una persona aunque cada dato por
   separado parezca inocuo. La herramienta cuenta cuántos de esos rasgos **sobreviven** al
   proceso y avisa cuando siguen siendo demasiados.
4. **Visuales** — texto escrito dentro de los píxeles de una imagen, códigos QR, códigos de
   barras.
5. **Técnicos** — todo lo que el archivo arrastra sin que usted lo vea. Ver sección 6.

---

## 4. Qué revisa, y la diferencia entre lo visible y lo invisible

Esta es la parte que más sorprende a quien no trabaja con documentos electrónicos.

Un archivo de Word **no es** lo que usted ve en pantalla. Es un paquete comprimido con más de
una docena de piezas. Dentro pueden estar, sin aparecer en la hoja:

- el **autor** y el **último autor** que lo guardó (a veces, un correo institucional completo);
- la **empresa** y el nombre de la **plantilla** usada;
- **comentarios** con sus autores e iniciales;
- el **control de cambios**: texto que alguien borró y que sigue guardado en el archivo;
- **propiedades personalizadas** creadas por el sistema del hospital (número de paciente,
  médico tratante, correo de contacto);
- **encabezados y pies** que se repiten en todas las páginas;
- imágenes, objetos incrustados y, en algunos casos, macros.

En el caso de demostración que viene incluido, el nombre y la cédula de la paciente estaban
**tres veces**: en el texto visible, en el texto borrado con control de cambios, y en las
propiedades del archivo. Un documento del que usted hubiera "quitado el nombre" a mano seguiría
llevándolos.

**Un rectángulo negro encima de un texto no borra nada.** En un PDF, ese texto sigue siendo
seleccionable, copiable y extraíble por cualquier programa. Por eso ANONIMIZADOR **no tapa**:
reconstruye el documento sin ese texto.

---

## 5. Qué pasa con la información clínica (la regla innegociable)

ANONIMIZADOR **no tiene autorización** para cambiar información clínica.

Antes de reescribir cualquier cosa, marca en el texto unas *zonas protegidas*: cifras con
unidades, valores de laboratorio, dosis, signos vitales, medidas, términos anatómicos,
lateralidad, medicamentos, procedimientos, diagnósticos, negaciones y grados de certeza.
Si una transformación fuese a tocar una de esas zonas, **la transformación se bloquea**, se
anota en la auditoría y el caso se manda a revisión humana. Prefiere no borrar un identificador
antes que alterar un dato clínico.

Después de procesar, compara el antes y el después **valor por valor** y clasifica cada
diferencia:

| Clasificación | Significado |
| --- | --- |
| `EXACT_MATCH` | El dato clínico salió idéntico. |
| `EXPECTED_TRANSFORMATION` | Cambió porque formaba parte de algo que se decidió minimizar (p. ej. la edad). |
| `UNEXPECTED_CHANGE` | 🔴 Un valor cambió sin motivo. **Detiene la aprobación automática.** |
| `MISSING` | 🔴 Un dato clínico desapareció. **Detiene la aprobación automática.** |
| `NEW_CONTENT` | 🔴 Apareció un dato que no estaba. **Detiene la aprobación automática.** |

Si `Hemoglobina: 8.9 g/dL` sale como `8.8`, como `9.8` o desaparece, el sistema **falla a
propósito** y se niega a dar el documento por bueno. Si `colon ascendente` se convirtiera en
`colon sigmoide`, lo mismo.

Además hay un detector de **información no soportada**: cualquier dato clínico que aparezca en
el resultado y no exista en el original se marca como *POSIBLE ALUCINACIÓN / INFORMACIÓN NO
SOPORTADA*. En V1 la reconstrucción es puramente determinista (sustituciones controladas), así
que esto no debería ocurrir nunca; el detector existe para cazar un error del propio programa
y para ser el guardián obligatorio si algún día se conectara un modelo de lenguaje.

---

## 6. Qué pasa con los metadatos

Se leen **todos** los que el formato permita, se listan en el informe y **ninguno se copia** al
archivo nuevo. El archivo resultante se construye desde cero con propiedades neutras
(autor vacío, título "Documento desidentificado", estado "DESIDENTIFICADO — PENDIENTE DE
REVISIÓN", fecha neutra). Incluso el nombre del archivo de salida es neutro: si el original se
llamaba `HC_Lopez_Quintero.docx`, el resultado se llama `documento_desidentificado.docx`.

---

## 7. Qué pasa con Word (.docx)

Se abre el paquete interno y se inspeccionan texto, encabezados, pies, tablas, cuadros de
texto, notas al pie, comentarios (y sus autores), control de cambios (y sus autores),
propiedades core / app / personalizadas, relaciones externas, imágenes, objetos incrustados y
macros.

El resultado **se reconstruye desde cero**: párrafos, títulos y tablas, más dos anexos
claramente rotulados con el texto de los encabezados y pies ya minimizados, para que no se
pierda información clínica que viviera ahí.

**No se copian** al resultado: comentarios, control de cambios, macros, objetos incrustados,
imágenes, propiedades ni miniatura. Está comprobado en las pruebas que los identificadores no
aparecen **ni siquiera dentro del XML comprimido** del archivo generado.

---

## 8. Qué pasa con PDF

Se extraen texto, metadatos, XMP, anotaciones, campos de formulario, enlaces, imágenes y
archivos incrustados; se detectan códigos QR renderizando cada página; y se buscan marcadores
de contenido activo (`/JavaScript`, `/OpenAction`, `/Launch`) que **nunca se ejecutan**.

Después se **escribe un PDF nuevo**, solo con el texto ya minimizado. No comparte un solo
objeto con el original.

Terminado el archivo, el sistema **vuelve a abrirlo e intenta extraer identificadores**. Si
reaparece alguno que se daba por eliminado, el resultado es `FAIL`, el documento no se aprueba
y el informe dice **qué módulo falló**.

Limitación honesta: la versión reconstruida es **solo texto**. Las imágenes del PDF original no
se transfieren (se avisa). Y si el PDF es un **escaneo** —una foto de un papel, sin texto
extraíble— el sistema lo detecta, lo marca como **NO EVALUABLE** y le dice que no use ese
resultado.

---

## 9. Qué pasa con las imágenes

Las imágenes son el punto más delicado, porque el nombre del paciente puede estar **pintado en
los píxeles**, donde ningún "quitar metadatos" llega.

Lo que V1 hace:

- **Elimina EXIF y XMP** reescribiendo la imagen píxel a píxel en un archivo nuevo.
- **Detecta códigos QR y de barras**, los **destruye de verdad** (sobrescribe los píxeles) y
  **comprueba después** que ya no se detecta ninguno. Nunca abre la URL que contenga un QR.
- **Detecta regiones con aspecto de texto** mediante análisis morfológico y las lista.

Lo que V1 **no** hace por defecto, y por qué: sin OCR instalado no puede saber si esa franja de
texto es "MARÍA FERNANDA LÓPEZ" o una escala de medida junto a la lesión. Como **no dañar la
información clínica** manda sobre todo lo demás, **no borra a ciegas**: marca la región, sube el
riesgo residual y pide revisión humana. Si usted decide que da igual tapar parte de la imagen,
hay una casilla para redactar todas las regiones detectadas; entonces sí se destruyen los
píxeles, y queda registrado en el informe.

Toda alteración de píxeles aparece en la auditoría.

---

## 10. Qué es el riesgo residual

Una escala de cinco niveles que **siempre viene con sus motivos**:

| Nivel | Cuándo aparece |
| --- | --- |
| **MUY BAJO** | Reservado; V1 nunca lo emite, porque el riesgo nunca es cero. |
| **BAJO** | No quedaron identificadores detectables, los valores clínicos coinciden y el ataque al resultado no encontró nada. |
| **MODERADO** | Algo quedó marcado para revisión: un candidato incierto, texto dentro de una imagen, un cuasi-identificador que la finalidad pidió conservar, metadatos residuales. |
| **ALTO** | Falló una verificación: fuga adversarial, discrepancia clínica, contenido no soportado, o demasiados cuasi-identificadores combinados. |
| **NO EVALUABLE** | El documento no se pudo analizar de forma concluyente (por ejemplo, un PDF escaneado). |

Ejemplo real de la salida:

> Riesgo residual: **MODERADO**.
> — Se detectó texto dentro de una imagen que no pudo clasificarse de forma segura (6 regiones, sin OCR instalado).
> — Se detectaron códigos QR/barras; se destruyeron en el resultado y se verificó que no quedan.

**Este puntaje no es una certificación legal.** Es una ayuda para decidir cuánto mirar.

---

## 11. Por qué la revisión humana sigue siendo obligatoria

Porque hay cosas que ninguna regla puede resolver sola:

- Un caso clínico raro puede identificar al paciente **sin que aparezca ni un dato personal**:
  la enfermedad, la fecha y el servicio bastan si el diagnóstico es infrecuente.
- El programa no sabe quién más tiene acceso al contexto (colegas, familia, la propia institución).
- Los léxicos de nombres son listas humanas, siempre incompletas.
- Un texto quemado en una imagen puede ser información clínica esencial o el nombre del paciente,
  y hoy la herramienta no puede distinguirlos sin OCR.

Por eso todo documento sale en estado `PENDING_REVIEW` o `REQUIRES_MANUAL_REVIEW`, nunca
aprobado. La aprobación (`APPROVED_BY_HUMAN`) solo puede registrarla una persona, y queda
firmada con su nombre, comentario y fecha en el expediente.

---

## 12. Qué cubre V1

- Formatos: **TXT/MD, DOCX, PDF, PNG/JPG, XLSX**.
- Cinco capas de detección con reglas explícitas y auditables.
- Reconstrucción limpia (completa en TXT y DOCX; parcial en PDF, XLSX e imagen).
- Cuatro verificaciones automáticas independientes.
- Riesgo residual explicable + estados de revisión humana.
- Expediente de auditoría: `audit.json`, `transformation_matrix.csv`, `integrity_report.json`,
  `adversarial_scan.json`, `audit_report.html`, `RESUMEN.md`.
- Interfaz local en el navegador, con modo demostración de casos ficticios.
- 37 pruebas automáticas.
- Cero red, cero nube, cero IA.

## 13. Qué NO cubre V1

- **OCR** (requiere instalar Tesseract aparte).
- **DICOM**, PACS, HL7/FHIR.
- Imágenes dentro de DOCX/PDF: se reportan pero no se transfieren ni se analizan.
- PDF escaneado.
- Firmas manuscritas, sellos y logotipos.
- k-anonimato real sobre una población.
- Formatos: PPTX, ODT, RTF, CSV, EML/MSG, ZIP, audio, vídeo.
- Cualquier afirmación de cumplimiento legal.

El detalle completo, con el estado `IMPLEMENTADO` / `PARCIAL` / `NO IMPLEMENTADO` de cada
elemento, está en **`docs/COBERTURA_Y_LIMITACIONES.md`**.

---

## 14. Próximos pasos (V2 y V3)

**V2** — OCR local con redacción selectiva; transferir imágenes ya procesadas al documento
reconstruido; PDF escaneado vía OCR; seudónimos coherentes en todo un expediente; más formatos;
diccionarios ampliables desde la interfaz; firma criptográfica del expediente de auditoría.

**V3** — DICOM completo, integración PACS/HIS, modelos NER clínicos y de visión como capa
*sugerente* (nunca decisoria), procesamiento masivo, autenticación y roles, cifrado y
almacenamiento seguro, auditoría institucional, y revisión jurídica y regulatoria formal.

---

## 15. Versión en PDF

Este informe existe también como **`docs/INFORME_ANONIMIZADOR.pdf`**, generado localmente con
la misma librería que ya usa el proyecto (reportlab), sin añadir ninguna dependencia nueva ni
pasar por Internet. Para volver a generarlo tras editar el Markdown:

```bash
python docs/generar_pdf.py
```

El Markdown es siempre la fuente; el PDF es una copia para imprimir o circular.

---

> **Recuerde: ANONIMIZADOR reduce información identificable pero no garantiza anonimización
> absoluta. Revise siempre el documento antes de compartirlo. La aprobación final corresponde
> a una persona.**
