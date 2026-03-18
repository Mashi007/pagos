# Script para corregir vencimientos MENSUAL: mismo dia cada mes.
# Ejecutar desde backend: python patch_amortizacion_mensual.py

from pathlib import Path

path = Path(__file__).resolve().parent / "app" / "api" / "v1" / "endpoints" / "prestamos.py"
text = path.read_text(encoding="utf-8", errors="replace")

# 1) Insertar helper antes de _resolver_monto_cuota (calendar ya esta importado arriba)
marker = 'def _resolver_monto_cuota(prestamo: "Prestamo", total: float, numero_cuotas: int) -> float:'
helper = '''def _fecha_base_mas_meses(fecha_base: date, meses: int) -> date:
    """
    Suma `meses` meses a `fecha_base` manteniendo el mismo dia del mes.
    Si el dia no existe en el mes resultante (ej. 31 en febrero), usa el ultimo dia del mes.
    Ejemplo: 17 julio 2025 + 1 mes = 17 agosto 2025; + 2 meses = 17 septiembre 2025.
    """
    if meses <= 0:
        return fecha_base
    year = fecha_base.year + (fecha_base.month + meses - 1) // 12
    month = (fecha_base.month + meses - 1) % 12 + 1
    _, ultimo_dia = calendar.monthrange(year, month)
    day = min(fecha_base.day, ultimo_dia)
    return date(year, month, day)


'''

if marker not in text:
    print("No se encontro _resolver_monto_cuota")
    exit(1)

if "def _fecha_base_mas_meses" in text:
    print("Helper ya existe, no se aplica parche.")
    exit(0)

text = text.replace(marker, helper + marker, 1)

# 2) En _generar_cuotas_amortizacion: para MENSUAL usar mismo dia cada mes
old_loop = """    for n in range(1, numero_cuotas + 1):
        next_date = fecha_base + timedelta(days=delta_dias * n - 1)"""

new_loop = """    for n in range(1, numero_cuotas + 1):
        if modalidad == "MENSUAL":
            next_date = _fecha_base_mas_meses(fecha_base, n)
        else:
            next_date = fecha_base + timedelta(days=delta_dias * n - 1)"""

if old_loop not in text:
    print("No se encontro el bucle de next_date (puede estar ya parcheado o con otro formato).")
    exit(1)

text = text.replace(old_loop, new_loop, 1)

path.write_text(text, encoding="utf-8")
print("Parche aplicado: MENSUAL usa mismo dia cada mes (ej. 17 jul -> 17 ago, 17 sep, 17 oct).")
