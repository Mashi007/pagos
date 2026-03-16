# Fix GEMINI_PROMPT: add bilingual (EN+ES) instruction as a single concatenated string
import os
import re
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(base, "app", "services", "pagos_gmail", "gemini_service.py")

with open(path, "r", encoding="utf-8", errors="replace") as f:
    c = f.read()

# Remove the broken block (lines that start with "[EN]" or "[ES]" and the stray quote/newline)
# Pattern: from "[EN]" up to and including the closing quote before "Eres un asistente"
c_fixed = re.sub(
    r'\s*"\[EN\].*?sources\.\s*"\s*\n\s*"\s*\n\s*"\[ES\].*?fuente\.\s*"\s*\n\s*"\s*\n',
    '',
    c,
    flags=re.DOTALL
)
if c_fixed == c:
    # Try simpler: remove lines 29-37 (0-indexed 28-36) if they contain [EN] or [ES]
    lines = c.split('\n')
    out = []
    skip_until_eres = False
    for i, line in enumerate(lines):
        if '[EN]' in line and 'You MUST review' in line:
            skip_until_eres = True
        if skip_until_eres:
            if 'Eres un asistente' in line and line.strip().startswith('"'):
                skip_until_eres = False
                # Insert bilingual on one line before this
                out.append('    "[EN] You MUST review ALL available information: email SUBJECT, message BODY, and ATTACHMENTS (images/PDFs). Extract from any source or combination. Respond ONLY with JSON. [ES] DEBES revisar TODA la informacion: ASUNTO, CUERPO y ADJUNTOS. Extrae de cualquier fuente o combinacion. Responde UNICAMENTE con JSON.\\n\\n"')
                out.append(line)
            continue
        out.append(line)
    c_fixed = '\n'.join(out)

if c_fixed != c:
    with open(path, "w", encoding="utf-8") as f:
        f.write(c_fixed)
    print("Fixed and added one-line bilingual instruction")
else:
    # File was not broken or already fixed - ensure we have at least bilingual
    if "[EN]" not in c or "[ES]" not in c:
        # Add single line after GEMINI_PROMPT = (
        c_fixed = re.sub(
            r'(GEMINI_PROMPT = \(\s*)("Eres un asistente)',
            r'\1"[EN] Review SUBJECT, BODY and ATTACHMENTS. [ES] Revisa ASUNTO, CUERPO y ADJUNTOS. "\n    \2',
            c,
            count=1
        )
        if c_fixed != c:
            with open(path, "w", encoding="utf-8") as f:
                f.write(c_fixed)
            print("Added bilingual line")
        else:
            print("No change")
    else:
        print("Already has EN+ES")
