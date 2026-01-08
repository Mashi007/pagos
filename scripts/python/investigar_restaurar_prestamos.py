"""Investigar y restaurar préstamos eliminados desde cuotas huérfanas"""
import sys
import io
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("=" * 70)
print("INVESTIGACION Y RESTAURACION DE PRESTAMOS ELIMINADOS")
print("=" * 70)

# 1. Analizar información disponible en cuotas huérfanas
print("\n1. ANALIZAR INFORMACION DISPONIBLE EN CUOTAS HUERFANAS:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        c.prestamo_id,
        COUNT(*) AS total_cuotas,
        MIN(c.numero_cuota) AS primera_cuota,
        MAX(c.numero_cuota) AS ultima_cuota,
        MIN(c.fecha_vencimiento) AS primera_fecha,
        MAX(c.fecha_vencimiento) AS ultima_fecha,
        SUM(c.monto_cuota) AS total_monto_cuotas,
        SUM(c.monto_capital) AS total_capital,
        SUM(c.monto_interes) AS total_interes,
        SUM(c.total_pagado) AS total_pagado,
        AVG(c.monto_cuota) AS promedio_cuota,
        COUNT(DISTINCT c.monto_cuota) AS montos_diferentes
    FROM cuotas c
    LEFT JOIN prestamos p ON c.prestamo_id = p.id
    WHERE p.id IS NULL
    GROUP BY c.prestamo_id
    ORDER BY c.prestamo_id
    LIMIT 10
"""))

print("\nAnálisis de primeros 10 préstamos inexistentes:")
print(f"{'Prestamo ID':<12} {'Cuotas':<8} {'Rango':<12} {'Total Capital':<15} {'Total Pagado':<15} {'Cuota Prom':<12}")
print("-" * 90)

prestamos_a_restaurar = []
for row in resultado.fetchall():
    prestamo_id, total_cuotas, primera_cuota, ultima_cuota, primera_fecha, ultima_fecha, \
    total_monto, total_capital, total_interes, total_pagado, promedio_cuota, montos_diferentes = row
    
    rango = f"{primera_cuota}-{ultima_cuota}"
    
    print(f"{prestamo_id:<12} {total_cuotas:<8} {rango:<12} ${total_capital:>13,.2f} ${total_pagado:>13,.2f} ${promedio_cuota:>10,.2f}")
    
    # Determinar modalidad de pago basado en fechas
    if primera_fecha and ultima_fecha:
        dias_diferencia = (ultima_fecha - primera_fecha).days
        if total_cuotas > 1:
            dias_entre_cuotas = dias_diferencia / (total_cuotas - 1)
            if 25 <= dias_entre_cuotas <= 35:
                modalidad = "MENSUAL"
            elif 12 <= dias_entre_cuotas <= 18:
                modalidad = "QUINCENAL"
            elif 5 <= dias_entre_cuotas <= 9:
                modalidad = "SEMANAL"
            else:
                modalidad = "MENSUAL"  # Default
        else:
            modalidad = "MENSUAL"
    else:
        modalidad = "MENSUAL"
    
    prestamos_a_restaurar.append({
        'prestamo_id': prestamo_id,
        'numero_cuotas': total_cuotas,
        'total_financiamiento': float(total_capital) if total_capital else 0,
        'cuota_periodo': float(promedio_cuota) if promedio_cuota else 0,
        'modalidad_pago': modalidad,
        'fecha_base_calculo': primera_fecha,
        'total_pagado': float(total_pagado) if total_pagado else 0,
        'montos_diferentes': montos_diferentes
    })

# 2. Verificar si podemos obtener más información de otras tablas
print("\n2. BUSCAR INFORMACION ADICIONAL EN OTRAS TABLAS:")
print("-" * 70)

# Buscar en tabla pagos
resultado = db.execute(text("""
    SELECT 
        COUNT(DISTINCT prestamo_id) AS prestamos_con_info,
        COUNT(*) AS total_pagos
    FROM pagos
    WHERE prestamo_id IN (
        SELECT DISTINCT c.prestamo_id
        FROM cuotas c
        LEFT JOIN prestamos p ON c.prestamo_id = p.id
        WHERE p.id IS NULL
    )
"""))

row = resultado.fetchone()
prestamos_con_info, total_pagos = row
print(f"Prestamos inexistentes con pagos en tabla pagos: {prestamos_con_info}")
print(f"Total pagos encontrados: {total_pagos}")

# Buscar información de clientes por cédula en pagos
resultado = db.execute(text("""
    SELECT DISTINCT
        p.cedula,
        COUNT(DISTINCT p.prestamo_id) AS prestamos_por_cedula
    FROM pagos p
    WHERE p.prestamo_id IN (
        SELECT DISTINCT c.prestamo_id
        FROM cuotas c
        LEFT JOIN prestamos pr ON c.prestamo_id = pr.id
        WHERE pr.id IS NULL
    )
    GROUP BY p.cedula
    LIMIT 10
"""))

cedulas_encontradas = resultado.fetchall()
if cedulas_encontradas:
    print(f"\nCédulas encontradas en pagos para préstamos inexistentes: {len(cedulas_encontradas)}")
    print("Esto puede ayudar a vincular con clientes existentes")

# 3. Verificar si hay información suficiente para restaurar
print("\n3. EVALUAR FACTIBILIDAD DE RESTAURACION:")
print("-" * 70)

total_prestamos_inexistentes = len(prestamos_a_restaurar)
prestamos_con_info_suficiente = 0
prestamos_sin_info = 0

for prestamo in prestamos_a_restaurar:
    tiene_info = (
        prestamo['numero_cuotas'] > 0 and
        prestamo['total_financiamiento'] > 0 and
        prestamo['cuota_periodo'] > 0 and
        prestamo['fecha_base_calculo'] is not None
    )
    
    if tiene_info:
        prestamos_con_info_suficiente += 1
    else:
        prestamos_sin_info += 1

print(f"Prestamos analizados: {total_prestamos_inexistentes}")
print(f"Con información suficiente para restaurar: {prestamos_con_info_suficiente}")
print(f"Sin información suficiente: {prestamos_sin_info}")

# 4. Generar script SQL para restaurar préstamos
print("\n4. GENERAR SCRIPT DE RESTAURACION:")
print("-" * 70)

print("\n⚠️ IMPORTANTE:")
print("   - Este proceso requiere información adicional (cliente_id, cedula, nombres)")
print("   - Necesitamos buscar esta información en otras fuentes")
print("   - Se recomienda hacer backup antes de restaurar")

# 5. Buscar información de clientes desde pagos o cuotas
print("\n5. BUSCAR INFORMACION DE CLIENTES:")
print("-" * 70)

# Intentar obtener información de clientes desde pagos
resultado = db.execute(text("""
    SELECT DISTINCT
        p.prestamo_id,
        p.cedula,
        COUNT(*) AS total_pagos
    FROM pagos p
    WHERE p.prestamo_id IN (
        SELECT DISTINCT c.prestamo_id
        FROM cuotas c
        LEFT JOIN prestamos pr ON c.prestamo_id = pr.id
        WHERE pr.id IS NULL
        LIMIT 100
    )
    GROUP BY p.prestamo_id, p.cedula
    ORDER BY p.prestamo_id
    LIMIT 10
"""))

prestamos_con_cedula = resultado.fetchall()
if prestamos_con_cedula:
    print(f"\nPrestamos con cédula encontrada en tabla pagos: {len(prestamos_con_cedula)}")
    print("\nEjemplos:")
    print(f"{'Prestamo ID':<12} {'Cedula':<15} {'Total Pagos':<12}")
    print("-" * 40)
    for row in prestamos_con_cedula:
        prestamo_id, cedula, total_pagos = row
        print(f"{prestamo_id:<12} {cedula:<15} {total_pagos:<12}")
else:
    print("No se encontraron préstamos con información de cédula en tabla pagos")

# 6. Verificar si hay clientes con esas cédulas
if prestamos_con_cedula:
    print("\n6. VERIFICAR CLIENTES EXISTENTES:")
    print("-" * 70)
    
    cedulas_list = [row[1] for row in prestamos_con_cedula]
    cedulas_str = "', '".join(cedulas_list)
    
    resultado = db.execute(text(f"""
        SELECT 
            cedula,
            id AS cliente_id,
            nombres,
            activo
        FROM clientes
        WHERE cedula IN ('{cedulas_str}')
        ORDER BY cedula
    """))
    
    clientes_encontrados = resultado.fetchall()
    if clientes_encontrados:
        print(f"\nClientes encontrados: {len(clientes_encontrados)}")
        print(f"{'Cedula':<15} {'Cliente ID':<12} {'Nombres':<40} {'Activo':<8}")
        print("-" * 80)
        for row in clientes_encontrados:
            cedula, cliente_id, nombres, activo = row
            nombres_str = nombres[:38] + ".." if len(nombres) > 40 else nombres
            print(f"{cedula:<15} {cliente_id:<12} {nombres_str:<40} {activo}")
    else:
        print("No se encontraron clientes con esas cédulas")

print("\n" + "=" * 70)
print("CONCLUSION:")
print("=" * 70)
print("Para restaurar los préstamos necesitamos:")
print("1. Información de cliente (cliente_id, cedula, nombres)")
print("2. Información del préstamo (total_financiamiento, numero_cuotas, etc.)")
print("3. Fecha base de cálculo")
print("4. Modalidad de pago")
print("\nSe puede obtener esta información desde:")
print("- Tabla pagos (cedula)")
print("- Tabla clientes (cliente_id, nombres)")
print("- Tabla cuotas (información del préstamo)")
print("\n¿Deseas que genere un script SQL completo para restaurar los préstamos?")
print("=" * 70)

db.close()
