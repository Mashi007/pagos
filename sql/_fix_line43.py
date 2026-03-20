# -*- coding: utf-8 -*-
path = r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\sql\regenerar_y_verificar_cuotas_fecha_aprobacion.sql"
with open(path, encoding="utf-8") as f:
    lines = f.readlines()
lines[42] = "-- - Generación de cuotas: `prestamos.py` → `_generar_cuotas_amortizacion`,\n"
lines[43] = "--   `_resolver_monto_cuota` (cuota plana si tasa 0 % por defecto; sistema francés\n"
with open(path, "w", encoding="utf-8", newline="\n") as f:
    f.writelines(lines)
print("ok")
