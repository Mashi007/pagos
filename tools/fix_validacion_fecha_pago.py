from pathlib import Path

p = Path(r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\app\api\v1\endpoints\tasa_cambio_validacion.py")
t = p.read_text(encoding="utf-8")
needle = """    # Caso 2: Tasa no existe y estamos en horario de ingreso obligatorio
    if debe_ingresar:
"""
if "No hay tasa de cambio registrada para la fecha de pago" in t:
    print("already fixed")
    raise SystemExit(0)
insert = """    if fecha_pago is not None:
        return ValidacionTasaResponse(
            puede_procesar_pagos_bs=False,
            tasa_actual=None,
            fecha_tasa=None,
            hora_obligatoria_desde=\"01:00\",
            hora_obligatoria_hasta=\"23:59\",
            mensaje=(
                \"CRITICO: No hay tasa de cambio registrada para la fecha de pago \"
                f\"{fecha_pago.isoformat()}. Registrela en Administracion > Tasas de cambio para esa fecha.\"
            ),
            acciones_recomendadas=[
                \"Registrar la tasa oficial para esa fecha en tasas_cambio_diaria\",
                \"O solicitar al cliente que reporte en USD\",
            ],
        )

"""
if needle not in t:
    raise SystemExit("needle not found")
t = t.replace(needle, insert + needle, 1)
p.write_text(t, encoding="utf-8")
print("ok")
