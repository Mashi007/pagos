# -*- coding: utf-8 -*-
"""Aplica: 1) Prompt Gemini clarificado, 2) Docstring pipeline, 3) Docstring run_now."""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 1) gemini_service.py
path = "app/services/pagos_gmail/gemini_service.py"
with open(path, "r", encoding="utf-8") as f:
    s = f.read()
old = "Si un dato genuinamente NO aparece en la imagen, usa 'NA'. Responde SOLO el JSON.\"\n)"
new = (
    "Si un dato genuinamente NO aparece en la imagen, usa 'NA'. "
    "Si la imagen no es un comprobante de pago (solo logo, firma, publicidad o irrelevante), devuelve los cuatro campos con 'NA'. "
    "No inventes datos. FORMATO: Responde UNICAMENTE con un objeto JSON valido, sin texto antes ni despues, sin markdown (no uses ```json). Responde SOLO el JSON.\"\n)"
)
if old not in s:
    raise SystemExit("gemini: no se encontro el texto a reemplazar")
s = s.replace(old, new, 1)
with open(path, "w", encoding="utf-8") as f:
    f.write(s)
print("gemini_service.py: prompt actualizado")

# 2) pipeline.py
path = "app/services/pagos_gmail/pipeline.py"
with open(path, "r", encoding="utf-8") as f:
    s = f.read()
# Actualizar docstring: "revisión final" -> ciclo de revisión
s = s.replace(
    "7. Al terminar el último del lote: volver a listar no leídos; si hay alguno\n     (re-marcado como no leído), procesarlo en la misma ejecución (revisión final).",
    "7. Al terminar el lote: ciclo de revisión (hasta 10 pasadas): volver a listar no leídos; si hay alguno, procesarlos; repetir hasta que no quede ninguno o 10 pasadas."
)
with open(path, "w", encoding="utf-8") as f:
    f.write(s)
print("pipeline.py: docstring actualizado")

# 3) pagos_gmail endpoint run_now
path = "app/api/v1/endpoints/pagos_gmail.py"
with open(path, "r", encoding="utf-8") as f:
    s = f.read()
s = s.replace(
    "Por defecto force=True (ejecución manual desde la UI); con force=false se respeta el intervalo mínimo.",
    "force=True (por defecto): ejecutar aunque la última ejecución fue hace poco (uso manual desde la UI). force=False: respetar intervalo mínimo (para cron)."
)
with open(path, "w", encoding="utf-8") as f:
    f.write(s)
print("pagos_gmail.py: run_now docstring actualizado")

print("Listo.")
