"""
Script para calcular cuántos días representa el gráfico de Cobranzas Mensuales
"""

from datetime import date

hoy = date.today()
print(f"Fecha actual: {hoy}")

# Calcular fecha inicio (hace 12 meses) - igual que en el endpoint
año_inicio = hoy.year
mes_inicio = hoy.month - 11
if mes_inicio <= 0:
    año_inicio -= 1
    mes_inicio += 12

fecha_inicio_query = date(año_inicio, mes_inicio, 1)

# Calcular días
dias = (hoy - fecha_inicio_query).days

print(f"\nFecha inicio: {fecha_inicio_query}")
print(f"Fecha fin: {hoy}")
print(f"\nDías representados: {dias} días")
print(f"Meses completos: {round(dias/30, 1)} meses aproximadamente")
print(f"Años: {round(dias/365, 2)} años aproximadamente")

# Calcular meses exactos
from calendar import monthrange
meses_completos = 0
fecha_temp = fecha_inicio_query
while fecha_temp <= hoy:
    meses_completos += 1
    if fecha_temp.month == 12:
        fecha_temp = date(fecha_temp.year + 1, 1, 1)
    else:
        fecha_temp = date(fecha_temp.year, fecha_temp.month + 1, 1)

print(f"\nMeses incluidos en el gráfico: {meses_completos} meses")
