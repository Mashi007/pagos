# Patch GEMINI_PROMPT: explicit instruction to review asunto, cuerpo y adjuntos
import os
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(base, "app", "services", "pagos_gmail", "gemini_service.py")

with open(path, "r", encoding="utf-8", errors="replace") as f:
    c = f.read()

if "DEBES revisar TODA la informacion disponible" in c:
    print("Prompt already patched")
    exit(0)

# Old block (allow slight encoding variants)
old = (
    'GEMINI_PROMPT = (\n'
    '    "Eres un asistente especializado en extraer datos de pagos venezolanos. "\n'
    '    "Puedes recibir UNA O MAS de estas fuentes:\\n"\n'
)
# Try with MA?S and electrnico etc
old_alt = (
    "Puedes recibir UNA O MA"
)
if old not in c and "Puedes recibir" in c:
    # Find the line and add our sentence after "Eres un asistente..."
    import re
    # Insert after first sentence (before "Puedes recibir")
    pattern = r'(Eres un asistente especializado en extraer datos de pagos venezolanos\. )\s*("Puedes recibir)'
    replacement = (
        r'\1'
        r'"DEBES revisar TODA la informacion disponible: ASUNTO del mensaje, CUERPO del mensaje y ADJUNTOS (imagenes/PDFs); '
        r'extrae los datos de cualquiera de estas fuentes o de su combinacion. "\n    '
        r'\2'
    )
    c2 = re.sub(pattern, replacement, c, count=1)
    if c2 != c:
        c = c2
        with open(path, "w", encoding="utf-8") as f:
            f.write(c)
        print("Patched: added explicit instruction to review asunto, cuerpo y adjuntos")
        exit(0)

# Fallback: append to first string
pattern2 = r'("Eres un asistente especializado en extraer datos de pagos venezolanos\. ")'
replacement2 = (
    r'\1\n'
    r'    "DEBES revisar TODA la informacion disponible: ASUNTO del mensaje, CUERPO del mensaje y ADJUNTOS (imagenes/PDFs); '
    r'extrae los datos de cualquiera de estas fuentes o de su combinacion. "'
)
c2 = re.sub(pattern2, replacement2, c, count=1)
if c2 != c:
    c = c2
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("Patched (fallback): added explicit instruction")
    exit(0)

print("Could not find insertion point")
