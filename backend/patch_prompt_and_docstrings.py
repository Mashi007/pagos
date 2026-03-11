# -*- coding: utf-8 -*-
"""Parche único: clarificar prompt Gemini y docstrings (pipeline + run_now)."""
import re

# --- 1) gemini_service.py: añadir al final del GEMINI_PROMPT (antes del cierre ") )
GEMINI_PATH = "app/services/pagos_gmail/gemini_service.py"
with open(GEMINI_PATH, "r", encoding="utf-8") as f:
    gemini_text = f.read()

# Buscar el cierre del GEMINI_PROMPT: "Responde SOLO el JSON." seguido de ")" y posible espacio/salto
old_end = 'Si un dato genuinamente NO aparece en la imagen, usa \'NA\'. Responde SOLO el JSON."\n)'
if old_end not in gemini_text:
    # Variante con comillas dobles dentro
    old_end = 'usa \'NA\'. Responde SOLO el JSON."'
    if old_end in gemini_text:
        # Reemplazar solo la parte final del string
        addition = (
            ' Si la imagen no es un comprobante de pago (solo logo, firma, publicidad o imagen irrelevante), '
            'devuelve los cuatro campos con valor \\'NA\\'. No inventes datos; si un dato no aparece en la imagen, usa \\'NA\\'. '
            'FORMATO: Responde UNICAMENTE con un objeto JSON valido, sin texto antes o despues y sin markdown (no uses ```json). Responde SOLO el JSON."\n)"
        )
        gemini_text = gemini_text.replace(
            'usa \'NA\'. Responde SOLO el JSON."',
            'usa \'NA\'.' + addition.split("usa ", 1)[1].replace("usa \\'NA\\'. ", "").replace(' Responde SOLO el JSON."', "")
        )
        # Simpler: just append before the closing "
        new_end = (
            'Si un dato genuinamente NO aparece en la imagen, usa \'NA\'. '
            'Si la imagen no es un comprobante de pago (solo logo, firma, publicidad o irrelevante), devuelve los cuatro campos con \'NA\'. '
            'No inventes datos. FORMATO: Responde UNICAMENTE con un objeto JSON valido, sin texto antes ni despues, sin markdown (no ```json). Responde SOLO el JSON."\n)'
        )
        gemini_text = re.sub(
            re.escape('Si un dato genuinamente NO aparece en la imagen, usa \'NA\'. Responde SOLO el JSON."') + r'\s*\)',
            new_end,
            gemini_text,
            count=1
        )
    else:
        raise SystemExit("gemini_service: no se encontro el final del GEMINI_PROMPT")
else:
    new_end = (
        'Si un dato genuinamente NO aparece en la imagen, usa \'NA\'. '
        'Si la imagen no es un comprobante (logo, firma, publicidad), devuelve los cuatro campos con \'NA\'. No inventes datos. '
        'FORMATO: Responde UNICAMENTE con un objeto JSON valido, sin texto antes ni despues, sin markdown. Responde SOLO el JSON."\n)'
    )
    gemini_text = gemini_text.replace(old_end, new_end)

with open(GEMINI_PATH, "w", encoding="utf-8") as f:
    f.write(gemini_text)
print("OK gemini_service: prompt actualizado")

# --- 2) pipeline.py: docstring "revision final" -> "ciclo de revision (hasta 10 pasadas)"
PIPELINE_PATH = "app/services/pagos_gmail/pipeline.py"
with open(PIPELINE_PATH, "r", encoding="utf-8") as f:
    pipeline_text = f.read()
pipeline_text = pipeline_text.replace(
    "7. Al terminar el ultimo del lote: volver a listar no leidos; si hay alguno\n     (re-marcado como no leido), procesarlo en la misma ejecucion (revision final).",
    "7. Al terminar el lote: ciclo de revision (hasta 10 pasadas): volver a listar no leidos; si hay alguno, procesarlos; repetir hasta que no quede ninguno o 10 pasadas."
)
pipeline_text = pipeline_text.replace(
    "(revision final).",
    "ciclo de revision (hasta 10 pasadas)."
)
with open(PIPELINE_PATH, "w", encoding="utf-8") as f:
    f.write(pipeline_text)
print("OK pipeline: docstring actualizado")

# --- 3) pagos_gmail.py (endpoint): run_now docstring force
ENDPOINT_PATH = "app/api/v1/endpoints/pagos_gmail.py"
with open(ENDPOINT_PATH, "r", encoding="utf-8") as f:
    endpoint_text = f.read()
old_run_now = (
    'Por defecto force=True (ejecucion manual desde la UI); con force=false se respeta el intervalo minimo.'
)
new_run_now = (
    'force=True (por defecto): ejecutar aunque la ultima ejecucion fue hace poco (uso manual desde la UI). '
    'force=False: respetar intervalo minimo desde la ultima ejecucion (para llamadas tipo cron).'
)
endpoint_text = endpoint_text.replace(old_run_now, new_run_now)
with open(ENDPOINT_PATH, "w", encoding="utf-8") as f:
    f.write(endpoint_text)
print("OK pagos_gmail endpoint: run_now docstring actualizado")

print("Listo.")
