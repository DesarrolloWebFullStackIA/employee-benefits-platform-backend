import os
import re
import sqlite3
import uuid
from datetime import date
import json

from fpdf import FPDF
from ollama import Client

DB_PATH = os.getenv("DB_PATH", "db.sqlite3")
PDF_DIR = "pdfs"
MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

os.makedirs(PDF_DIR, exist_ok=True)
client = Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))


def _query(sql: str, params: tuple = ()) -> list[dict]:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, params).fetchall()]
    finally:
        con.close()


def _esquema() -> str:
    filas = _query("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return "\n".join(f["sql"] for f in filas if f["sql"])


def _validar_sql(sql: str) -> str:
    s = sql.strip().rstrip(";")
    if ";" in s or not re.match(r"(?is)^(select|with)\b", s):
        raise ValueError("Solo se permite UNA consulta SELECT.")
    if re.search(r"(?i)\b(insert|update|delete|drop|alter|create|attach|pragma|replace)\b", s):
        raise ValueError("Consulta no permitida.")
    return s


def _ejecutar_consulta(sql: str, limite: int = 500) -> list[dict]:
    s = _validar_sql(sql)
    return _query(f"SELECT * FROM ({s}) LIMIT {int(limite)}")


def consultar_bd(sql: str) -> list[dict] | dict:
    """Ejecuta una consulta SQL de SOLO LECTURA (SELECT) sobre la base de datos y devuelve las filas.
    Úsala para responder cualquier pregunta sobre los datos. Si da error, corrige la consulta y reintenta."""
    try:
        return _ejecutar_consulta(sql, limite=200)
    except Exception as e:
        return {"error": str(e)}



ETIQUETAS = {
    "first_name": "Nombre",
    "last_name": "Apellido",
    "name": "Nombre",
    "email": "Email",
    "department": "Departamento",
    "role": "Cargo",
    "position": "Cargo",
    "employee": "Empleado",
    "category": "Categoría",
    "concept": "Concepto",
    "description": "Descripción",
    "amount": "Importe",
    "date": "Fecha",
    "status": "Estado",
    "assigned_amount": "Importe asignado",
    "max_budget": "Presupuesto máx.",
    "total": "Total",
    "total_spent": "Total gastado",
    "total_amount": "Importe total",
    "num_expenses": "Nº de gastos",
}

VALORES = {"PENDING": "Pendiente", "APPROVED": "Aprobado", "REJECTED": "Rechazado"}


COLUMNAS_OCULTAS = re.compile(r"^(id|.+_id|created_at|updated_at)$", re.IGNORECASE)


def _etiqueta(columna: str) -> str:
    clave = str(columna).lower()
    if clave in ETIQUETAS:
        return ETIQUETAS[clave]
    texto = str(columna).replace("_", " ").strip()
    return texto[:1].upper() + texto[1:]


def generar_pdf_consulta(titulo: str, sql: str) -> dict:
    """Ejecuta un SELECT y genera un PDF corporativo con el resultado.
    Devuelve el enlace de descarga. Úsala cuando el usuario pida un PDF o informe."""
    try:
        filas = _ejecutar_consulta(sql)
    except Exception as e:
        return {"error": str(e)}
    if not filas:
        return {"error": "La consulta no devolvió datos, no se generó el PDF."}

    def t(texto):
        return str(texto).encode("latin-1", "replace").decode("latin-1")

    AZUL = (30, 34, 170)
    GRIS_FILA = (245, 245, 245)
    GRIS_TEXTO = (80, 80, 80)

    todas = list(filas[0].keys())
    columnas = [c for c in todas if not COLUMNAS_OCULTAS.match(str(c))] or todas

    pdf = FPDF(orientation="L" if len(columnas) > 6 else "P")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    logo_path = os.path.join(PDF_DIR, "logo.png")
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=12, y=12, w=15)

    pdf.set_y(15)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*AZUL)
    pdf.cell(0, 10, t("Pluxee Enterprise"), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*GRIS_TEXTO)
    pdf.cell(0, 6, t("Gestión de Beneficios"), align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_draw_color(*AZUL)
    pdf.set_line_width(0.8)
    pdf.line(10, 35, pdf.w - 10, 35)

    pdf.set_y(42)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, t(titulo), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GRIS_TEXTO)
    pdf.cell(0, 6, t(f"Generado el {date.today().strftime('%d/%m/%Y')} · {len(filas)} registros"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Cada columna ocupa un ancho proporcional a lo que contiene (así los emails no se cortan)
    pesos = {}
    for c in columnas:
        mayor = max(
            [len(_etiqueta(c))]
            + [len(str(f.get(c)) if f.get(c) is not None else "") for f in filas]
        )
        pesos[c] = min(max(mayor, 6), 40)
    ancho_pag = pdf.w - 20
    anchos = {c: ancho_pag * pesos[c] / sum(pesos.values()) for c in columnas}

    pdf.set_fill_color(*AZUL)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    for col in columnas:
        pdf.cell(anchos[col], 8, t(_etiqueta(col)), border=0, fill=True, align="L")
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 9)
    for i, f in enumerate(filas):
        if i % 2 == 0:
            pdf.set_fill_color(*GRIS_FILA)
        else:
            pdf.set_fill_color(255, 255, 255)
        for c in columnas:
            valor = f.get(c)
            texto = "" if valor is None else str(valor)
            texto = VALORES.get(texto, texto)
            limite = max(int(anchos[c] / 1.8), 4)  # caracteres que caben en la columna
            if len(texto) > limite:
                texto = texto[:limite - 3] + "..."
            pdf.cell(anchos[c], 7, t(texto), border=0, fill=True, align="L")
        pdf.ln()

    pdf.set_y(-15)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*GRIS_TEXTO)
    pdf.cell(0, 5, t(f"Pluxee Enterprise · Documento confidencial · {date.today().isoformat()}"),
             align="C")

    nombre_base = re.sub(r'[^a-zA-Z0-9_\-]', '_', titulo.lower())
    nombre = f"{nombre_base}_{uuid.uuid4().hex[:6]}.pdf"

    pdf.output(os.path.join(PDF_DIR, nombre))
    return {"url": f"/chat/pdf/{nombre}", "titulo": titulo, "num_filas": len(filas)}


TOOLS = [consultar_bd, generar_pdf_consulta]



def _como_tabla(resultado):
    """Si la herramienta devolvió datos tabulares, los convierte a {columnas, filas}."""
    if isinstance(resultado, dict) and "columnas" in resultado and "filas" in resultado:
        columnas, filas = resultado["columnas"], resultado["filas"]
    elif isinstance(resultado, list) and resultado and all(isinstance(r, dict) for r in resultado):
        columnas = list(resultado[0].keys())
        filas = [[r.get(c) for c in columnas] for r in resultado]
    else:
        return None
    if len(filas) == 1 and len(columnas) == 1:
        return None 
    return {"columnas": columnas, "filas": filas}


def _limpiar_texto(texto: str, hay_tabla: bool) -> str:
    """Quita del texto del modelo cualquier tabla (JSON o Markdown) que haya escrito por su cuenta."""
   
    texto = re.sub(
        r"```(?:json)?\s*([\s\S]*?)```",
        lambda m: "" if '"columnas"' in m.group(1) or '"tabla"' in m.group(1) else m.group(0),
        texto,
    )

    decoder = json.JSONDecoder()
    for marca in ('{"tabla"', '{"columnas"'):
        i = texto.find(marca)
        while i != -1:
            try:
                _, fin = decoder.raw_decode(texto[i:])
            except ValueError:
                break
            texto = texto[:i] + texto[i + fin:]
            i = texto.find(marca)
   
    if hay_tabla:
        texto = re.sub(r"^\s*\|.*\|\s*$\n?", "", texto, flags=re.M)
    return texto.strip()


def _system_prompt() -> str:
    return (
        "Eres el asistente virtual de Pluxee Enterprise, plataforma profesional de gestión de beneficios para empleados. "
        f"Hoy es {date.today().isoformat()}. "
        "Habla siempre en español, con tono profesional, claro y cercano. "
        "Preséntate como 'el asistente de Pluxee Enterprise' cuando corresponda. "
        "Nunca menciones SQL, bases de datos, tablas ni herramientas técnicas. "
        "Para responder, consulta los datos con la herramienta consultar_bd (solo lectura). "
        "Estructura interna de los datos (NO la menciones al usuario):\n"
        + _esquema() + "\n"
        "Pautas ESTRICTAS:\n"
        "- Responde como un asistente de empresa, no como un programador.\n"
        "- SIEMPRE que te pregunten por datos de la empresa (empleados, gastos, categorías, importes...), "
        "llama primero a consultar_bd, aunque ya lo hayas hecho antes en la conversación. "
        "NUNCA respondas de memoria, del historial ni con datos de ejemplo: solo con lo que devuelva la consulta.\n"
        "- Si piden 'los empleados', 'los gastos', 'las categorías', 'dame...', 'muéstrame...' o 'listado', "
        "consulta las FILAS con sus columnas útiles (nombre, departamento, importe, fecha, estado...), nunca solo un conteo. "
        "Usa COUNT únicamente si preguntan 'cuántos'.\n"
        "- En las consultas, pon a CADA columna un nombre en español, claro y sin guiones bajos, usando AS "
        "(por ejemplo: first_name AS \"Nombre\", SUM(amount) AS \"Total gastado\"). "
        "No incluyas columnas de id ni fechas de creación o actualización salvo que las pidan.\n"
        "- Cuando consultes un listado de datos (empleados, gastos, categorías, etc.), "
        "la interfaz lo muestra automáticamente como una tabla debajo de tu mensaje. "
        "Por eso NO escribas tablas, ni JSON, ni listas con los datos, ni símbolos | o ---. "
        "Responde solo con una frase breve que lo resuma (cuántos registros hay, un total, algo destacable) "
        "e invita a pedir el informe en PDF si lo necesita.\n"
        "- Si el usuario pide un informe o PDF, usa generar_pdf_consulta y responde: "
        "'Aquí tienes el informe solicitado. Puedes descargarlo con el botón inferior.' "
        "NO escribas la URL, NO uses markdown, NO pongas corchetes ni enlaces.\n"
        "- No inventes datos: si no hay resultados, dilo con educación.\n"
        "- Solo lectura: no puedes modificar información."
    )


def _es_charla(texto: str) -> bool:
    """True si el mensaje es solo un saludo, un agradecimiento o una despedida (no necesita consultar datos)."""
    t = texto.lower().strip(" ¡!¿?.,")
    return bool(re.fullmatch(
        r"(hola|buenas|buenos días|buenas tardes|buenas noches|hey|gracias|muchas gracias|vale|ok|"
        r"adiós|adios|hasta luego|qué tal|que tal)( asistente)?",
        t,
    ))


def responder(message: str, history: list[dict]) -> dict:
    funciones = {f.__name__: f for f in TOOLS}
    messages = [{"role": "system", "content": _system_prompt()}]
    for h in history[-10:]:
        messages.append({
            "role": "assistant" if h["role"] == "model" else "user",
            "content": h["text"]
        })
    messages.append({"role": "user", "content": message})

    pdf_url = None
    pdf_titulo = None
    tabla = None
    uso_herramienta = False
    reintentos = 0

    for _ in range(5):
        resp = client.chat(model=MODEL, messages=messages, tools=TOOLS)
        messages.append(resp.message)

        if not resp.message.tool_calls:
            contenido = resp.message.content or ""

            if not uso_herramienta and reintentos < 2 and not _es_charla(message):
                reintentos += 1
                messages.append({
                    "role": "user",
                    "content": "Antes de responder debes obtener los datos reales con la herramienta consultar_bd. "
                               "No uses datos de memoria ni de ejemplo. Hazlo ahora.",
                })
                continue

            reply = _limpiar_texto(resp.message.content or "", hay_tabla=tabla is not None)
            if not reply:
                if tabla:
                    reply = f"Aquí tienes los resultados ({len(tabla['filas'])} registros)."
                else:
                    reply = "No he podido generar una respuesta."
            return {
                "reply": reply,
                "tabla": tabla,
                "pdf_url": pdf_url,
                "pdf_titulo": pdf_titulo,
            }

        for call in resp.message.tool_calls:
            uso_herramienta = True
            funcion = funciones.get(call.function.name)
            try:
                resultado = funcion(**call.function.arguments) if funcion else {"error": "Herramienta desconocida"}
            except Exception as e:
                resultado = {"error": str(e)}

            if isinstance(resultado, dict) and "url" in resultado:
                pdf_url = resultado["url"]
                pdf_titulo = resultado.get("titulo", "informe")

            tabla_res = _como_tabla(resultado)
            if tabla_res:
                tabla = tabla_res
                resultado = {
                    **tabla_res,
                    "nota": "La interfaz ya muestra estos datos como tabla. "
                            "NO copies la tabla ni escribas JSON; responde con una frase breve.",
                }

            messages.append({
                "role": "tool",
                "tool_name": call.function.name,
                "content": json.dumps(resultado, default=str, ensure_ascii=False),
            })

    return {
        "reply": "No he conseguido resolver la consulta, prueba a reformularla.",
        "tabla": None,
        "pdf_url": None,
        "pdf_titulo": None,
    }