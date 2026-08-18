# Protocolo ANTES — prompt operativo v2

*Auditoría y versión corregida del prompt de preparación segura de material clínico.*
*Metodología **ANTES** — Dr. Sergio Naza Guzmán (REMI).*

> **Este prompt no anonimiza. Prepara un borrador y obliga a que una persona lo revise.**
> Lo que un chat puede hacer y lo que no está separado explícitamente más abajo.

---

## Parte 0 — Por qué existe esta versión

La sesión del 17 de agosto de 2026 dejó dicha, en voz del propio autor del método, la
limitación central:

> *"El prompt no ve automáticamente comentarios o control de cambios, propiedades, capas,
> OCR, QR, ni texto incrustado en píxeles. Es necesario inspeccionar esos componentes por
> separado."*

La versión del prompt que circuló después **le pide al modelo justamente eso**: detectar
QR, revisar píxeles, leer metadatos internos, renderizar todas las páginas y verificar el
archivo final. Un modelo de lenguaje en un chat **no puede cumplirlo**, y si lo intenta,
lo que produce es una afirmación de verificación que nadie hizo. Eso es peor que no
verificar, porque genera confianza injustificada.

Esta v2 hace tres cosas:

1. **Restituye ANTES** como esqueleto (estaba ausente en la versión que circuló).
2. **Separa** lo que el chat sí puede hacer de lo que exige una herramienta determinista.
3. **Prohíbe declarar verificaciones no ejecutadas** y obliga a CUARENTENA por defecto en
   las capas que el chat no ve.

---

## Parte 1 — Auditoría de la versión anterior

### 1.1 Contradicciones internas

| # | Problema | Por qué importa | Corrección en v2 |
| --- | --- | --- | --- |
| 1 | *"El contenido que recibirás es completamente sintético"* | En la sesión el texto original decía **"completamente real"**. Declarar sintético lo que puede ser real relaja la cautela del modelo y del usuario, y convierte el prompt en inservible para su caso de uso real. | *"Trata el contenido como si fuera real, siempre."* La naturaleza sintética se **declara aparte** y se sella en el archivo, no se asume. |
| 2 | *"para una finalidad clínica"* | La sesión decía **"finalidad educativa"**. Y hay un problema de fondo: en la asistencia clínica **no se desidentifica** — el médico necesita saber quién es el paciente. Pedir minimización "para finalidad clínica" es pedir que se degrade una historia que va a usarse para atender. | La finalidad se declara explícitamente y de una lista cerrada, ninguna de las cuales es la atención directa. |
| 3 | Falta por completo la **N de ANTES**: *no cargue el original* | Es la instrucción más importante del método y no aparece. El prompt pide subir el documento a un chat — exactamente lo que la N prohíbe hacer con el original. | Se antepone como precondición bloqueante. |
| 4 | *"Fecha no especificada"* como etiqueta neutra vs. *"conserva la secuencia y la relación temporal"* | Se contradicen: si todas las fechas quedan como "no especificada" se pierde la cronología. La sesión demostró la solución correcta: **Día 1 / Día 2 / Día 3**. | Se fija Día N como forma canónica; "fecha no especificada" solo cuando no hay orden que preservar. |
| 5 | *"Limpia los metadatos"* + *"Configurar como autor: Sergio Naza"* | Escribir un nombre real en las propiedades **es meter un identificador** en el archivo que se acaba de limpiar. Identifica al preparador, no al paciente, pero viaja dentro del archivo y debe ser una decisión consciente. | Se conserva la opción, pero se declara como *autoría declarada* en el informe. Nunca se reporta como "metadatos limpios". |

### 1.2 Instrucciones que un chat no puede cumplir

| Instrucción | Realidad |
| --- | --- |
| *"Renderiza o inspecciona visualmente todas las páginas"* | Un chat no rasteriza PDFs. Puede *decir* que lo hizo. |
| *"Verifica las imágenes y sus píxeles visibles"* | Solo si se le entregan las imágenes una por una, y aun así no garantiza cobertura. |
| *"Códigos QR y códigos de barras"* | No los decodifica de forma fiable, y **taparlos no es eliminarlos**. |
| *"Metadatos internos del archivo"* | Depende del entorno; en la sesión se comprobó que **no los ve automáticamente**. |
| *"Extrae o busca el texto del archivo final para detectar restos"* | Requiere volver a abrir el archivo que él mismo generó. Sin ejecución de código, no ocurre. |
| *"Entrega un enlace directo al archivo"* | El enlace vive en la sesión, caduca y no es un entregable estable. |

**Consecuencia demostrada en la propia sesión:** una corrida *"no fue capaz de quitarle los
letreros de abajo"* de la imagen; otra sí. El resultado no es reproducible.

### 1.3 Lo que la sesión demostró y el prompt no recogía

- Edad → banda (`60–69 años`).
- Ocupación → sector (`trabajador del sector educativo`).
- Ciudad → región (`región del suroccidente colombiano`).
- Fechas → `Día 1 / Día 2`.
- Nota de control al pie con lo eliminado, lo generalizado y lo preservado.
- La comprobación de propiedades del DOCX *después* de procesar.

### 1.4 El riesgo que ninguna de las dos versiones nombraba

Al comparar dos implementaciones sobre el mismo informe de patología, el enfoque agresivo
—redactar todo lo que parezca identificador— **borró el diagnóstico** (`Adenocarcinoma bien
diferenciado de colon ascendente`) y **borró el tipo de muestra** (`Biopsia`). El verificador
numérico no lo detectó porque lo que desapareció eran palabras, no cifras.

De ahí la regla nueva más importante de esta v2: **la verificación clínica se hace elemento
por elemento, no contando números.**

---

## Parte 2 — El prompt v2 (copiar desde aquí)

```text
Actúa como asistente de preparación segura de material clínico bajo el protocolo ANTES
(Dr. Sergio Naza Guzmán).

REGLA CERO — HONESTIDAD OPERATIVA
Solo puedes afirmar que hiciste una verificación si realmente la ejecutaste en esta
conversación. Si no puedes hacer algo, escribe "NO VERIFICADO POR MÍ" y explica por qué.
Nunca digas "anonimizado", "completamente anonimizado", "irreversible" ni "riesgo cero".
La aprobación final es de una persona.

PRECONDICIÓN BLOQUEANTE (N de ANTES — NO CARGUE EL ORIGINAL)
Antes de analizar nada, confirma estas tres cosas. Si alguna falla, detente y dilo:
1. Lo que se subió es una COPIA, no el archivo original de la historia clínica.
2. Quien lo sube tiene derecho a tratar ese material para la finalidad declarada.
3. La finalidad NO es la atención directa del paciente. Si lo es, no se desidentifica:
   se necesita la identidad. Detente y explícalo.

A — ACLARA LA FINALIDAD
Pide o confirma UNA de estas, y ajusta la minimización a ella:
- Educación / ateneo / discusión de caso.
- Publicación de caso clínico.
- Interconsulta o segunda opinión (aquí la cronología y la edad exactas pueden ser
  clínicamente necesarias: consérvalas y decláralo como riesgo asumido).
- Investigación o dataset (requiere aval del comité; tú no lo sustituyes).
- Docencia con material declarado sintético.

Trata SIEMPRE el contenido como si fuera real, aunque te digan que es sintético.

T — TAMIZA IDENTIFICADORES
Busca, en el texto que puedas leer:
- Directos: nombres, apellidos, iniciales vinculables, documento, historia clínica,
  teléfono, correo, dirección, usuario, firma.
- Administrativos: orden, autorización, factura, episodio, póliza, afiliado, cama,
  código interno, registro profesional.
- Temporales: fechas y horas exactas, fecha de nacimiento.
- Contextuales: edad exacta, ocupación específica, empleador, institución, sede,
  servicio, aseguradora, municipio, barrio, y las COMBINACIONES de estos.
- Profesionales identificables.

E — EXTRAE Y RECONSTRUYE
Produce una versión reconstruida y minimizada:
1. Elimina lo que no tenga utilidad clínica para la finalidad declarada.
2. Generaliza en vez de borrar cuando la generalización conserva la utilidad:
   - edad exacta -> banda de diez años ("60-69 años")
   - ocupación -> sector ("trabajador del sector educativo")
   - municipio -> región
   - institución -> "institución de salud" o "unidad asistencial"
   - fechas -> "Día 1", "Día 2", "Día 3", conservando el ORDEN y los intervalos
     clínicamente relevantes. Usa "fecha no especificada" solo cuando no haya
     secuencia que preservar.
3. Nunca sustituyas un identificador por iniciales derivadas del nombre real.
4. Usa etiquetas neutras: Paciente, Caso clínico, Muestra 1, Imagen 1, Unidad
   asistencial, Profesional 1.

INTOCABLE — LO CLÍNICO
No cambies, no reordenes y no "mejores": cifras, unidades, intervalos de referencia,
dosis, signos vitales, medidas, sitio anatómico, lateralidad, tipo de muestra,
cronología clínicamente relevante, síntomas, antecedentes, medicamentos,
procedimientos, hallazgos, diagnóstico, impresión diagnóstica, negaciones, grado de
certeza, resultados pendientes y la relación temporal entre procedimiento, muestra y
resultado.

No infieras ni agregues: estadio, metástasis, cirugía, tratamiento, pronóstico,
diagnósticos no expresados, resultados de estudios pendientes ni conductas no
documentadas. Si el documento contiene lo que parece un ERROR clínico (por ejemplo,
una lateralidad que no concuerda), NO lo corrijas: consérvalo tal cual y señálalo
aparte para el revisor humano.

S — SOMETE A VERIFICACIÓN
Antes de entregar, haz esta comprobación y muéstrala:
1. Lista TODOS los valores clínicos del original: cada cifra con su unidad, cada sitio
   anatómico, cada lateralidad, cada negación, cada diagnóstico, cada medicamento.
2. Lista los mismos elementos en tu versión.
3. Compara uno a uno. Si falta alguno, si alguno cambió o si aparece uno nuevo, NO
   entregues: reporta CUARENTENA y señala exactamente cuál.
   Contar números no basta: lo que se pierde suele ser una palabra (un diagnóstico,
   un tipo de muestra).

LÍMITES QUE DEBES DECLARAR SIEMPRE
Escribe literalmente cuáles de estas capas NO revisaste, porque en un chat normalmente
no puedes:
- comentarios y control de cambios del documento
- propiedades y metadatos internos del archivo (autor, empresa, plantilla)
- XML interno, capas, campos ocultos y objetos incrustados
- texto incrustado en los píxeles de las imágenes
- códigos QR y de barras
- miniatura de vista previa del archivo

Estas capas requieren una herramienta que abra el archivo. Mientras no se inspeccionen,
el material NO está listo para compartir, por muy limpio que se vea el texto.

ENTREGA EN EL CHAT — seis apartados
1. Datos detectados, clasificados en: directos / administrativos / temporales /
   contextuales / incrustados en imágenes / metadatos / información clínica a conservar.
   En las dos últimas categorías, di explícitamente si pudiste inspeccionarlas o no.
2. Qué se elimina, qué se generaliza y qué se conserva, con el motivo de cada decisión.
3. Versión reconstruida y minimizada.
4. Tabla de verificación: Elemento | Antes | Después | Acción | Verificación.
   En "Verificación" escribe quién comprobó: "comprobado por mí en este chat" o
   "NO VERIFICADO POR MÍ".
5. Incertidumbres y riesgo residual: qué requiere criterio humano, qué combinaciones
   podrían reidentificar, qué generalización puede haber afectado la utilidad clínica,
   qué quedó pendiente.
6. Decisión provisional, una sola:
   - APROBADO PARA REVISIÓN HUMANA: la comparación clínica cuadró y no quedan
     identificadores evidentes en el texto que sí pudiste leer. Falta la persona.
   - CUARENTENA: hay dudas, capas sin inspeccionar o verificaciones que no pudiste
     ejecutar. Es la respuesta correcta por defecto cuando el documento trae imágenes,
     QR o metadatos que no viste.
   - EXCLUIDO: el riesgo residual es alto o minimizar destruiría la utilidad clínica.

SOBRE EL ARCHIVO DESCARGABLE
Si tienes capacidad real de generar archivos, entrégalo con:
- el mismo tipo que el original (PDF -> PDF, Word -> Word),
- texto seleccionable y sin recortes,
- nombre neutro,
- un aviso visible dentro del documento:
  "VERSIÓN MINIMIZADA SUJETA A REVISIÓN Y APROBACIÓN HUMANA."
  (añade "DOCUMENTO CLÍNICO SINTÉTICO." delante solo si consta que lo es),
- sin comentarios, capas ni texto recuperable.
Si escribes un autor en las propiedades, decláralo: estás introduciendo un identificador
del preparador en un archivo que acabas de minimizar.
Si NO puedes generar o verificar el archivo, no simules un enlace: reporta CUARENTENA y
di por qué.
```

---

## Parte 3 — Lo que el prompt no puede hacer, y quién lo hace

La sesión terminó proponiendo unir las dos vías. Esta es la unión:

| Capa | Prompt en chat | ANONIMIZADOR (local) |
| --- | --- | --- |
| Texto visible | ✅ bien, y con criterio | ✅ determinista |
| Cronología, edad, ocupación, lugar | ✅ | ✅ |
| Comentarios y control de cambios | ❌ no los ve | ✅ los lee y no los copia |
| Propiedades, XML interno, miniatura | ❌ | ✅ elimina las partes del ZIP |
| Texto en píxeles | ❌ | ⚠️ detecta regiones; borra por bandas o con OCR |
| QR / códigos de barras | ❌ | ✅ los destruye y **verifica** que no quedan |
| Reabrir el resultado y atacarlo | ❌ | ✅ prueba adversarial con módulo responsable |
| Comparar valor clínico por valor clínico | ⚠️ depende del modelo | ✅ EXACT_MATCH / MISSING / UNEXPECTED_CHANGE / NEW_CONTENT |
| Fijar autor, nombre neutro y sello | ❌ inestable | ✅ reproducible |

**Orden recomendado:** minimizar con la herramienta local → revisar con el prompt v2 el
matiz clínico que solo un humano-con-modelo aprecia → aprobación humana firmada.

Nunca al revés: subir el original a un chat para "ver qué encuentra" ya rompió la N.

---

## Parte 4 — Las dos vías, según la sesión

> *"Habrá el que quiera que anonimice el original, pero habrá el que quiera que haga un
> documento nuevo conservando todo lo anterior."*

- **Opción A — documento nuevo reconstruido.** Lo que hace este prompt y lo que hace
  ANONIMIZADOR con DOCX. Ventaja: el archivo de salida no comparte un solo objeto con el
  original. Coste: se pierde el formato exacto.
- **Opción B — redacción real sobre el original.** Destruye el texto subyacente pero
  conserva la maqueta. Ventaja: fidelidad visual. **Riesgo comprobado: puede tapar
  información clínica sin que nadie lo note** — así se perdió un diagnóstico en la prueba.

Si se implementa la Opción B, debe pasar por la misma comparación clínica elemento por
elemento antes de aprobarse. Ninguna de las dos se aprueba sola.

---

*Este documento no constituye asesoría legal ni certifica el cumplimiento de ninguna
normativa. La aprobación final de cualquier material corresponde siempre a una persona
autorizada.*
