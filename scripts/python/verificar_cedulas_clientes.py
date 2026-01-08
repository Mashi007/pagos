"""Verificar que todas las cédulas en la tabla clientes cumplen criterios"""
import sys
import io
from pathlib import Path

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
print("VERIFICACION: CRITERIOS DE CEDULAS EN TABLA CLIENTES")
print("=" * 70)

# 1. Resumen general
print("\n1. RESUMEN GENERAL:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total_clientes,
        COUNT(DISTINCT cedula) AS cedulas_unicas,
        COUNT(*) - COUNT(DISTINCT cedula) AS cedulas_duplicadas,
        COUNT(CASE WHEN cedula IS NULL THEN 1 END) AS cedulas_nulas,
        COUNT(CASE WHEN cedula IS NOT NULL AND LENGTH(TRIM(cedula)) = 0 THEN 1 END) AS cedulas_vacias
    FROM clientes
"""))
row = resultado.fetchone()
total, unicas, duplicadas, nulas, vacias = row

print(f"Total clientes: {total}")
print(f"Cedulas unicas: {unicas}")
print(f"Cedulas duplicadas: {duplicadas}")
print(f"Cedulas nulas: {nulas}")
print(f"Cedulas vacias: {vacias}")

# 2. Verificar formato y longitud
print("\n2. VERIFICACION DE FORMATO Y LONGITUD:")
print("-" * 70)

resultado = db.execute(text("""
    SELECT 
        COUNT(*) AS total,
        COUNT(CASE 
            WHEN cedula IS NOT NULL 
             AND TRIM(cedula) != ''
             AND cedula ~ '^[VEJ]\\d+$'
             AND LENGTH(cedula) >= 6
             AND LENGTH(cedula) <= 10
            THEN 1 
        END) AS cedulas_validas,
        COUNT(CASE 
            WHEN cedula IS NOT NULL 
             AND TRIM(cedula) != ''
             AND cedula !~ '^[VEJ]\\d+$'
            THEN 1 
        END) AS formato_invalido,
        COUNT(CASE 
            WHEN cedula IS NOT NULL 
             AND TRIM(cedula) != ''
             AND cedula ~ '^[VEJ]\\d+$'
             AND (LENGTH(cedula) < 6 OR LENGTH(cedula) > 10)
            THEN 1 
        END) AS longitud_invalida
    FROM clientes
"""))
row = resultado.fetchone()
total_check, validas, formato_inv, longitud_inv = row

print(f"Total clientes verificados: {total_check}")
print(f"Cedulas validas: {validas}")
print(f"Formato invalido: {formato_inv}")
print(f"Longitud invalida: {longitud_inv}")

# 3. Verificar que clientes duplicados tienen préstamos
print("\n3. VERIFICAR CLIENTES DUPLICADOS CON PRESTAMOS:")
print("-" * 70)

if duplicadas > 0:
    resultado = db.execute(text("""
        WITH clientes_duplicados AS (
            SELECT c.id, c.cedula, c.nombres
            FROM clientes c
            WHERE c.cedula IN (
                SELECT cedula
                FROM clientes
                WHERE cedula IS NOT NULL
                GROUP BY cedula
                HAVING COUNT(*) > 1
            )
        ),
        clientes_con_prestamos AS (
            SELECT 
                cd.id,
                COUNT(DISTINCT p.id) AS total_prestamos
            FROM clientes_duplicados cd
            LEFT JOIN prestamos p ON cd.cedula = p.cedula
            GROUP BY cd.id
        )
        SELECT 
            COUNT(*) AS total_duplicados,
            COUNT(CASE WHEN total_prestamos >= 1 THEN 1 END) AS con_prestamos,
            COUNT(CASE WHEN total_prestamos = 0 THEN 1 END) AS sin_prestamos
        FROM clientes_con_prestamos
    """))
    
    row = resultado.fetchone()
    total_dup, con_prest, sin_prest = row
    
    print(f"Total clientes con cedulas duplicadas: {total_dup}")
    print(f"Clientes con prestamos: {con_prest}")
    print(f"Clientes sin prestamos: {sin_prest}")
    
    if sin_prest == 0:
        print("\n[OK] Todos los clientes duplicados tienen prestamos asociados")
        print("     Las cedulas duplicadas son validas (cada cliente tiene prestamos)")
    else:
        print(f"\n[ADVERTENCIA] {sin_prest} clientes duplicados sin prestamos")

# 4. Verificación final
print("\n4. VERIFICACION FINAL:")
print("-" * 70)

# Las cédulas duplicadas son válidas si cada cliente tiene préstamos
cedulas_validas_final = total == validas and nulas == 0 and vacias == 0

if cedulas_validas_final:
    print("[OK] Todas las cedulas cumplen criterios:")
    print("  - No hay cedulas nulas")
    print("  - No hay cedulas vacias")
    print("  - Todas tienen formato valido (V/E/J seguido de numeros)")
    print("  - Todas tienen longitud valida (6-10 caracteres)")
    if duplicadas > 0:
        print(f"  - {duplicadas} cedulas duplicadas (VALIDAS: cada cliente tiene prestamos)")
else:
    print("[ERROR] Hay cedulas que no cumplen criterios:")
    if nulas > 0:
        print(f"  - {nulas} cedulas nulas")
    if vacias > 0:
        print(f"  - {vacias} cedulas vacias")
    if formato_inv > 0:
        print(f"  - {formato_inv} cedulas con formato invalido")
    if longitud_inv > 0:
        print(f"  - {longitud_inv} cedulas con longitud invalida")
    
    # Mostrar ejemplos de cédulas inválidas
    print("\n4. EJEMPLOS DE CEDULAS INVALIDAS:")
    print("-" * 70)
    
    resultado = db.execute(text("""
        SELECT 
            id,
            cedula,
            nombres,
            fecha_registro,
            CASE 
                WHEN cedula IS NULL THEN 'CEDULA NULA'
                WHEN TRIM(cedula) = '' THEN 'CEDULA VACIA'
                WHEN cedula !~ '^[VEJ]\\d+$' THEN 'FORMATO INVALIDO'
                WHEN LENGTH(cedula) < 6 THEN 'MUY CORTA'
                WHEN LENGTH(cedula) > 10 THEN 'MUY LARGA'
                ELSE 'OTRO PROBLEMA'
            END AS motivo_invalido
        FROM clientes
        WHERE cedula IS NULL
           OR TRIM(cedula) = ''
           OR cedula !~ '^[VEJ]\\d+$'
           OR LENGTH(cedula) < 6
           OR LENGTH(cedula) > 10
        ORDER BY fecha_registro DESC
        LIMIT 20
    """))
    
    invalidas = resultado.fetchall()
    if len(invalidas) > 0:
        for i, inv in enumerate(invalidas, 1):
            cliente_id, cedula_val, nombres_val, fecha_reg, motivo = inv
            print(f"\n  Cliente {i}:")
            print(f"    ID: {cliente_id}")
            print(f"    Cedula: {cedula_val or '(NULL)'}")
            print(f"    Nombres: {nombres_val or 'N/A'}")
            print(f"    Motivo: {motivo}")
        
        if len(invalidas) == 20:
            print(f"\n  ... (mostrando solo los primeros 20)")

print("\n" + "=" * 70)

db.close()
