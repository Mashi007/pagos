# Patch GEMINI_PROMPT: add English + Spanish instructions to avoid rule evasion
import os
import re
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(base, "app", "services", "pagos_gmail", "gemini_service.py")

with open(path, "r", encoding="utf-8", errors="replace") as f:
    c = f.read()

if "You MUST review ALL available" in c and "DEBES revisar TODA" in c:
    print("Prompt already bilingual")
    exit(0)

# Bilingual header to prepend (after "GEMINI_PROMPT = (")
bilingual_header = '''
    "[EN] You MUST review ALL available information: email SUBJECT, message BODY, and ATTACHMENTS (images/PDFs). "
    "Extract the 4 fields from any of these sources or their combination. Do not skip any source. "
    "Respond ONLY with valid JSON, no markdown, no extra text. Do not invent data; use 'NA' only when the value is absent in ALL sources.\\n\\n"
    "[ES] DEBES revisar TODA la informacion disponible: ASUNTO del correo, CUERPO del mensaje y ADJUNTOS (imagenes/PDFs). "
    "Extrae los 4 campos de cualquiera de estas fuentes o su combinacion. No omitas ninguna fuente. "
    "Responde UNICAMENTE con JSON valido, sin markdown ni texto extra. No inventes datos; usa 'NA' solo cuando el valor no aparezca en NINGUNA fuente.\\n\\n"
'''

# Insert after "GEMINI_PROMPT = (" and before "Eres un asistente"
pattern = r'(GEMINI_PROMPT = \(\s*)("Eres un asistente)'
replacement = r'\1' + bilingual_header + r'    \2'
c2 = re.sub(pattern, replacement, c, count=1)
if c2 == c:
    print("Pattern not found")
    exit(1)
with open(path, "w", encoding="utf-8") as f:
    f.write(c2)
print("Patched: prompt now has EN+ES instructions at the start")
