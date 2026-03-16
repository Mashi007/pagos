# Fix broken bilingual block in gemini_service.py
import os
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(base, "app", "services", "pagos_gmail", "gemini_service.py")

with open(path, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

old_broken = """GEMINI_PROMPT = (
    
    "[EN] You MUST review ALL available information: email SUBJECT, message BODY, and ATTACHMENTS (images/PDFs). "
    "Extract the 4 fields from any of these sources or their combination. Do not skip any source. "
    "Respond ONLY with valid JSON, no markdown, no extra text. Do not invent data; use 'NA' only when the value is absent in ALL sources.

"
    "[ES] DEBES revisar TODA la informacion disponible: ASUNTO del correo, CUERPO del mensaje y ADJUNTOS (imagenes/PDFs). "
    "Extrae los 4 campos de cualquiera de estas fuentes o su combinacion. No omitas ninguna fuente. "
    "Responde UNICAMENTE con JSON valido, sin markdown ni texto extra. No inventes datos; usa 'NA' solo cuando el valor no aparezca en NINGUNA fuente.

"
    "Eres un asistente especializado en extraer datos de pagos venezolanos. """

new_ok = """GEMINI_PROMPT = (
    "[EN] You MUST review ALL available information: email SUBJECT, message BODY, and ATTACHMENTS (images/PDFs). Extract the 4 fields from any source or combination. Respond ONLY with valid JSON. [ES] DEBES revisar TODA la informacion: ASUNTO, CUERPO y ADJUNTOS. Extrae los 4 campos de cualquier fuente o combinacion. Responde UNICAMENTE con JSON. "
    "Eres un asistente especializado en extraer datos de pagos venezolanos. """

if old_broken in content:
    content = content.replace(old_broken, new_ok)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Fixed")
else:
    # Try without the leading blank line
    old2 = 'GEMINI_PROMPT = (\n    \n    "[EN]'
    if old2 in content:
        # Replace from GEMINI_PROMPT until "Eres un asistente" with fixed version
        import re
        content = re.sub(
            r'GEMINI_PROMPT = \(\s+\s+"\[EN\].*?"Eres un asistente especializado',
            'GEMINI_PROMPT = (\n    "[EN] You MUST review ALL available information: email SUBJECT, message BODY, and ATTACHMENTS (images/PDFs). Extract the 4 fields from any source or combination. Respond ONLY with valid JSON. [ES] DEBES revisar TODA la informacion: ASUNTO, CUERPO y ADJUNTOS. Extrae los 4 campos de cualquier fuente o combinacion. Responde UNICAMENTE con JSON. "\n    "Eres un asistente especializado',
            content,
            count=1,
            flags=re.DOTALL
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Fixed (regex)")
    else:
        print("Block not found; file may already be fixed")
        # Check syntax
        import py_compile
        try:
            py_compile.compile(path, doraise=True)
            print("Syntax OK")
        except py_compile.PyCompileError as e:
            print("Syntax error:", e)
