"""Lexicos deterministas en espanol clinico (LatAm / Espana).

Son listas explicitas y auditables: se pueden leer, discutir y ampliar.
Nada de esto depende de un modelo de lenguaje.
"""
from __future__ import annotations

from ..util.hashing import normalizar

# ---------------------------------------------------------------------------
# 1. NOMBRES DE PILA (para elevar la confianza de un candidato a nombre)
#    Lista corta y ampliable: NO pretende ser exhaustiva.
# ---------------------------------------------------------------------------
NOMBRES_PILA = {
    "juan", "jose", "luis", "carlos", "jorge", "miguel", "pedro", "antonio",
    "manuel", "francisco", "javier", "andres", "diego", "david", "daniel",
    "sergio", "alberto", "ricardo", "fernando", "rafael", "eduardo", "oscar",
    "raul", "victor", "hector", "julio", "mario", "ruben", "ivan", "camilo",
    "santiago", "sebastian", "nicolas", "mateo", "samuel", "felipe", "esteban",
    "maria", "ana", "laura", "carmen", "rosa", "isabel", "patricia", "claudia",
    "sandra", "monica", "adriana", "diana", "paola", "andrea", "carolina",
    "natalia", "lucia", "elena", "marta", "beatriz", "sofia", "valentina",
    "gabriela", "daniela", "alejandra", "veronica", "silvia", "julia", "clara",
    "martha", "gloria", "yolanda", "amparo", "consuelo", "esperanza", "olga",
    "alejandro", "gustavo", "hernan", "alvaro", "arturo", "ramon", "cesar",
    "emilio", "ignacio", "lorenzo", "marcos", "pablo", "rodrigo", "tomas",
    "vicente", "guillermo", "leonardo", "mauricio", "orlando", "wilson",
}

APELLIDOS_FRECUENTES = {
    "garcia", "rodriguez", "gonzalez", "fernandez", "lopez", "martinez",
    "sanchez", "perez", "gomez", "martin", "jimenez", "ruiz", "hernandez",
    "diaz", "moreno", "alvarez", "munoz", "romero", "alonso", "gutierrez",
    "navarro", "torres", "dominguez", "vazquez", "ramos", "gil", "ramirez",
    "serrano", "blanco", "molina", "morales", "suarez", "ortega", "delgado",
    "castro", "ortiz", "rubio", "marin", "sanz", "nunez", "iglesias", "medina",
    "garrido", "cortes", "castillo", "santos", "lozano", "guerrero", "cano",
    "prieto", "mendez", "cruz", "herrera", "pena", "flores", "cabrera",
    "campos", "vega", "fuentes", "carrasco", "diez", "caballero", "reyes",
    "rico", "quintero", "arias", "acosta", "rojas", "cardenas", "bermudez",
}

PARTICULAS_APELLIDO = {"de", "del", "la", "las", "los", "van", "von", "da", "di"}

TRATAMIENTOS = {
    "dr", "dra", "doctor", "doctora", "sr", "sra", "srta", "lic", "licenciado",
    "licenciada", "ing", "prof", "profesor", "profesora", "md", "enf",
}

# ---------------------------------------------------------------------------
# 2. OCUPACIONES -> SECTOR (generalizacion controlada)
# ---------------------------------------------------------------------------
OCUPACION_A_SECTOR = {
    "medico": "sector salud", "medica": "sector salud",
    "enfermero": "sector salud", "enfermera": "sector salud",
    "odontologo": "sector salud", "fisioterapeuta": "sector salud",
    "psicologo": "sector salud", "auxiliar de enfermeria": "sector salud",
    "bacteriologa": "sector salud",
    "docente": "sector educacion", "profesor": "sector educacion",
    "profesora": "sector educacion", "maestro": "sector educacion",
    "maestra": "sector educacion", "rector": "sector educacion",
    "abogado": "sector servicios profesionales",
    "abogada": "sector servicios profesionales",
    "contador": "sector servicios profesionales",
    "contadora": "sector servicios profesionales",
    "arquitecto": "sector servicios profesionales",
    "notario": "sector servicios profesionales",
    "ingeniero": "sector tecnico", "ingeniera": "sector tecnico",
    "tecnico": "sector tecnico", "mecanico": "sector tecnico",
    "electricista": "sector tecnico", "soldador": "sector tecnico",
    "programador": "sector tecnico", "piloto": "sector transporte",
    "conductor": "sector transporte", "taxista": "sector transporte",
    "camionero": "sector transporte", "agricultor": "sector agropecuario",
    "campesino": "sector agropecuario", "ganadero": "sector agropecuario",
    "minero": "sector extractivo", "obrero": "sector construccion",
    "albanil": "sector construccion", "constructor": "sector construccion",
    "comerciante": "sector comercio", "vendedor": "sector comercio",
    "tendero": "sector comercio", "cajero": "sector comercio",
    "militar": "sector seguridad", "policia": "sector seguridad",
    "soldado": "sector seguridad", "vigilante": "sector seguridad",
    "bombero": "sector seguridad", "peluquero": "sector servicios",
    "cocinero": "sector servicios", "mesero": "sector servicios",
    "ama de casa": "labores del hogar", "hogar": "labores del hogar",
    "estudiante": "estudiante", "jubilado": "persona jubilada",
    "pensionado": "persona jubilada",
    "desempleado": "sin ocupacion registrada",
    "futbolista": "sector deportivo", "deportista": "sector deportivo",
    "sacerdote": "sector religioso", "musico": "sector artistico",
    "actor": "sector artistico", "actriz": "sector artistico",
    "periodista": "sector comunicaciones", "locutor": "sector comunicaciones",
}

# ---------------------------------------------------------------------------
# 3. CIUDADES -> REGION
# ---------------------------------------------------------------------------
CIUDAD_A_REGION = {
    "bogota": "region andina (Colombia)",
    "medellin": "region andina (Colombia)",
    "cali": "region pacifica (Colombia)",
    "barranquilla": "region caribe (Colombia)",
    "cartagena": "region caribe (Colombia)",
    "bucaramanga": "region andina (Colombia)",
    "pereira": "region andina (Colombia)",
    "manizales": "region andina (Colombia)",
    "armenia": "region andina (Colombia)",
    "ibague": "region andina (Colombia)",
    "neiva": "region andina (Colombia)",
    "villavicencio": "region orinoquia (Colombia)",
    "santa marta": "region caribe (Colombia)",
    "monteria": "region caribe (Colombia)",
    "cucuta": "region andina (Colombia)",
    "popayan": "region pacifica (Colombia)",
    "pasto": "region andina (Colombia)",
    "tunja": "region andina (Colombia)",
    "candelaria": "region pacifica (Colombia)",
    "palmira": "region pacifica (Colombia)",
    "buenaventura": "region pacifica (Colombia)",
    "leticia": "region amazonica (Colombia)",
    "madrid": "Espana", "barcelona": "Espana", "valencia": "Espana",
    "sevilla": "Espana", "zaragoza": "Espana", "bilbao": "Espana",
    "malaga": "Espana", "murcia": "Espana",
    "ciudad de mexico": "Mexico", "guadalajara": "Mexico",
    "monterrey": "Mexico", "puebla": "Mexico",
    "lima": "Peru", "arequipa": "Peru", "quito": "Ecuador",
    "guayaquil": "Ecuador", "buenos aires": "Argentina",
    "montevideo": "Uruguay", "caracas": "Venezuela", "panama": "Panama",
    "la paz": "Bolivia", "asuncion": "Paraguay",
    "miami": "Estados Unidos", "nueva york": "Estados Unidos",
}

DEPARTAMENTOS = {
    "antioquia", "cundinamarca", "valle del cauca", "atlantico", "santander",
    "bolivar", "narino", "cauca", "tolima", "huila", "caldas", "risaralda",
    "quindio", "meta", "cesar", "cordoba", "magdalena", "boyaca", "sucre",
}

# ---------------------------------------------------------------------------
# 4. INSTITUCIONES Y ASEGURADORAS
# ---------------------------------------------------------------------------
PREFIJOS_INSTITUCION = [
    "hospital universitario", "hospital", "clinica", "policlinico",
    "sanatorio", "instituto", "centro medico", "centro de salud", "fundacion",
    "laboratorio clinico", "laboratorio", "ips", "eps", "unidad medica",
    "consultorio",
]

ASEGURADORAS = {
    "sura", "sanitas", "compensar", "famisanar", "nueva eps", "salud total",
    "coomeva", "medimas", "colsanitas", "colmedica", "seguros bolivar",
    "adres", "sisben", "imss", "issste", "essalud", "fonasa", "osde",
    "adeslas", "asisa", "dkv", "mapfre salud",
}

# ---------------------------------------------------------------------------
# 5. LEXICO CLINICO PROTEGIDO
#    Ningun transformador puede tocar un span que contenga estos terminos.
# ---------------------------------------------------------------------------
ANATOMIA = {
    "colon", "ascendente", "descendente", "transverso", "sigmoide", "recto",
    "ciego", "ileon", "yeyuno", "duodeno", "estomago", "esofago", "higado",
    "vesicula", "pancreas", "bazo", "rinon", "rinones", "vejiga", "uretra",
    "prostata", "utero", "ovario", "ovarios", "mama", "mamas", "pulmon",
    "pulmones", "bronquio", "traquea", "corazon", "aorta", "arteria", "vena",
    "cerebro", "cerebelo", "tronco", "medula", "hipofisis", "tiroides",
    "paratiroides", "suprarrenal", "piel", "musculo", "hueso", "femur",
    "tibia", "humero", "radio", "cubito", "clavicula", "escapula", "vertebra",
    "lumbar", "cervical", "toracico", "sacro", "cadera", "rodilla", "tobillo",
    "hombro", "codo", "muneca", "mano", "pie", "abdomen", "torax", "pelvis",
    "cuello", "craneo", "orbita", "seno", "senos", "ganglio", "ganglios",
    "peritoneo", "pleura", "pericardio", "mediastino", "apendice", "amigdala",
    "faringe", "laringe", "retina", "cornea", "timpano", "hepatico", "renal",
    "pulmonar", "gastrico", "colonico", "rectal", "biliar", "esplenico",
    "pancreatico", "ileocecal", "hepatica", "hepaticos", "mucosa", "submucosa",
}

LATERALIDAD = {
    "derecho", "derecha", "izquierdo", "izquierda", "bilateral", "unilateral",
    "proximal", "distal", "superior", "inferior", "anterior", "posterior",
    "medial", "lateral", "ipsilateral", "contralateral",
}

NEGACIONES = {
    "no", "sin", "niega", "ausencia", "ausente", "negativo", "negativa",
    "descarta", "descartado", "descartada", "nunca", "tampoco",
}

CERTEZA = {
    "probable", "posible", "sugestivo", "sugestiva", "compatible", "sospecha",
    "sospechoso", "aparente", "confirmado", "confirmada", "definitivo",
    "presuntivo", "presuntiva", "descartar", "indeterminado", "dudoso",
}

UNIDADES = [
    "mg/dl", "g/dl", "mmol/l", "mol/l", "meq/l", "ui/l", "u/l", "ng/ml",
    "pg/ml", "ug/ml", "mcg/ml", "mg/l", "g/l", "mm/h", "mmhg", "cmh2o",
    "lpm", "rpm", "kg/m2", "mg/m2", "mg/kg", "mcg/kg/min", "ml/min", "ml/h",
    "gotas/min", "celulas/ul", "x10e3/ul", "x10e6/ul", "10^3/ul", "10^6/ul",
    "/ul", "/mm3", "kg", "mg", "mcg", "ug", "ml", "dl", "cm", "mm", "cc",
    "bpm", "ui", "meq", "mmol", "g", "l", "m", "%",
]

ANALITOS = {
    "hemoglobina", "hematocrito", "leucocitos", "neutrofilos", "linfocitos",
    "plaquetas", "glucosa", "glicemia", "creatinina", "urea", "bun", "sodio",
    "potasio", "cloro", "calcio", "magnesio", "fosforo", "bilirrubina",
    "ast", "alt", "got", "gpt", "fosfatasa alcalina", "ggt", "albumina",
    "proteinas totales", "ldh", "amilasa", "lipasa", "pcr", "vsg",
    "procalcitonina", "troponina", "ck", "ckmb", "dimero d", "inr", "tp",
    "ttp", "fibrinogeno", "ferritina", "hierro", "transferrina",
    "acido folico", "tsh", "t4", "t3", "cortisol", "hba1c", "colesterol",
    "hdl", "ldl", "trigliceridos", "psa", "cea", "afp", "ph", "pco2", "po2",
    "hco3", "lactato", "saturacion", "vcm", "hcm", "rdw",
}

VITALES = {
    "ta", "tension arterial", "presion arterial", "pa", "fc",
    "frecuencia cardiaca", "fr", "frecuencia respiratoria", "temperatura",
    "temp", "sato2", "spo2", "saturacion de oxigeno", "peso", "talla", "imc",
    "glasgow", "eva", "diuresis",
}

MEDICAMENTOS = {
    "omeprazol", "metformina", "losartan", "enalapril", "amlodipino",
    "atorvastatina", "simvastatina", "acetaminofen", "paracetamol",
    "ibuprofeno", "diclofenaco", "naproxeno", "dipirona", "tramadol",
    "morfina", "fentanilo", "amoxicilina", "ampicilina", "ceftriaxona",
    "cefazolina", "meropenem", "vancomicina", "ciprofloxacina",
    "levofloxacina", "azitromicina", "claritromicina", "clindamicina",
    "metronidazol", "insulina", "levotiroxina", "warfarina", "heparina",
    "enoxaparina", "rivaroxaban", "apixaban", "clopidogrel", "aspirina",
    "furosemida", "espironolactona", "hidroclorotiazida", "prednisona",
    "dexametasona", "hidrocortisona", "salbutamol", "budesonida",
    "ondansetron", "metoclopramida", "ranitidina", "sulfato", "ferroso",
    "oxaliplatino", "capecitabina", "fluorouracilo", "carboplatino",
    "cisplatino", "paclitaxel",
}

VIAS = {"vo", "iv", "im", "sc", "sl", "rectal", "topica", "inhalada", "oral"}

PROCEDIMIENTOS = {
    "colonoscopia", "endoscopia", "gastroscopia", "biopsia", "tac", "tc",
    "resonancia", "ecografia", "ecocardiograma", "radiografia", "rx",
    "electrocardiograma", "ekg", "ecg", "espirometria", "puncion",
    "laparoscopia", "laparotomia", "colecistectomia", "apendicectomia",
    "hemicolectomia", "colectomia", "gastrectomia", "toracotomia",
    "cateterismo", "angiografia", "pet", "gammagrafia", "mamografia",
    "citologia", "hemocultivo", "urocultivo", "cultivo", "antibiograma",
}

DIAGNOSTICOS = {
    "anemia", "diabetes", "hipertension", "epoc", "asma", "neumonia",
    "sepsis", "cancer", "carcinoma", "adenocarcinoma", "linfoma", "leucemia",
    "metastasis", "cirrosis", "hepatitis", "pancreatitis", "colecistitis",
    "apendicitis", "diverticulitis", "colitis", "gastritis", "ulcera",
    "infarto", "angina", "arritmia", "fibrilacion", "insuficiencia",
    "trombosis", "embolia", "acv", "evc", "convulsion", "epilepsia",
    "migrana", "artritis", "artrosis", "osteoporosis", "fractura",
    "lesion", "polipo", "nodulo", "masa", "quiste", "tumor", "estenosis",
    "obstruccion", "hemorragia", "sangrado", "melenas", "hematoquecia",
    "ferropenica", "microcitica", "hipocromica", "adenomatoso",
}

TERMINOS_CLINICOS = (
    ANATOMIA | LATERALIDAD | ANALITOS | MEDICAMENTOS | PROCEDIMIENTOS
    | DIAGNOSTICOS | VITALES | CERTEZA | VIAS
)

MESES = {
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
    "septiembre", "setiembre", "octubre", "noviembre", "diciembre",
}

DIAS_SEMANA = {
    "lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo",
}

PALABRAS_FUNCION = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
    "y", "o", "en", "con", "sin", "por", "para", "que", "se", "su", "sus",
    "paciente", "usuario", "senor", "senora", "servicio", "consulta",
    "control", "urgencias", "hospitalizacion", "informe", "reporte",
    "resultado", "resultados", "estudio", "estudios", "examen", "examenes",
    "historia", "clinica", "nota", "evolucion", "ingreso", "egreso", "alta",
    "motivo", "antecedentes", "revision", "sistemas", "analisis", "plan",
    "conclusion", "conclusiones", "impresion", "hallazgos", "tratamiento",
    "medicamentos", "laboratorio", "laboratorios", "imagen", "imagenes",
    "patologia", "muestra", "fecha", "edad", "sexo", "masculino", "femenino",
    "hombre", "mujer", "anos", "dia", "dias", "hoy", "ayer", "actualmente",
    "refiere", "presenta", "normal", "anormal", "positivo", "negativo",
    "diagnostico", "diagnosticos", "estado", "general", "actual", "previo",
    "valor", "valores", "referencia", "unidad", "unidades", "total", "totales",
}

PALABRAS_NO_NOMBRE = (
    TERMINOS_CLINICOS | MESES | DIAS_SEMANA | PALABRAS_FUNCION | NEGACIONES
    | ASEGURADORAS | set(OCUPACION_A_SECTOR) | set(CIUDAD_A_REGION)
    | DEPARTAMENTOS
)


def es_termino_clinico(palabra: str) -> bool:
    return normalizar(palabra) in TERMINOS_CLINICOS


def sector_de(ocupacion: str):
    return OCUPACION_A_SECTOR.get(normalizar(ocupacion))


def region_de(ciudad: str):
    return CIUDAD_A_REGION.get(normalizar(ciudad))
