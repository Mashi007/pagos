"""Corregir inconsistencias en cuotas: eliminar duplicadas y completar faltantes"""
import sys
import io
from pathlib import Path
from datetime import date

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from app.db.session import SessionLocal
from app.services.prestamo_amortizacion_service import generar_tabla_amortizacion
from app.models.prestamo import Prestamo
from sqlalchemy import text

db = SessionLocal()

print("=" * 70)
print("CORRECCION: INCONSISTENCIAS EN CUOTAS DE PRESTAMOS")
print("=" * 70)
print("\nEste script corrige:")
print("  1. Elimina cuotas duplicadas/extra (mantiene solo numero_cuotas)")
print("  2. Completa cuotas faltantes (regenera las que faltan)")
print("\n" + "=" * 70)

# ======================================================================
# PARTE 1: ELIMINAR CUOTAS DUPLICADAS/EXTRA
# ======================================================================

print("\n" + "=" * 70)
print("PARTE 1: ELIMINAR CUOTAS DUPLICADAS/EXTRA")
print("=" * 70)

# Verificar préstamos con cuotas de más
resultado = db.execute(
    text("""
        SELECT 
            p.id AS prestamo_id,
            p.cedula,
            c.nombres AS nombre_cliente,
            p.numero_cuotas AS cuotas_planificadas,
            COUNT(cu.id) AS cuotas_actuales,
            COUNT(cu.id) - p.numero_cuotas AS cuotas_extra
        FROM prestamos p
        LEFT JOIN clientes c ON p.cedula = c.cedula
        INNER JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE p.estado = 'APROBADO'
        GROUP BY p.id, p.cedula, c.nombres, p.numero_cuotas
        HAVING COUNT(cu.id) > p.numero_cuotas
        ORDER BY p.id
    """)
)

prestamos_con_extra = resultado.fetchall()

if len(prestamos_con_extra) == 0:
    print("\n[OK] No hay prestamos con cuotas extra")
else:
    print(f"\n[ATENCION] Se encontraron {len(prestamos_con_extra)} prestamos con cuotas extra")
    
    # Verificar si hay pagos en las cuotas extra
    print("\nVerificando si hay pagos asociados a cuotas extra...")
    
    total_cuotas_extra = 0
    cuotas_extra_con_pagos = 0
    
    for prestamo_id, cedula, nombre, planificadas, actuales, extra in prestamos_con_extra:
        total_cuotas_extra += extra
        
        # Verificar pagos en cuotas extra
        resultado_pagos = db.execute(
            text("""
                SELECT COUNT(*)
                FROM cuotas cu
                WHERE cu.prestamo_id = :prestamo_id
                  AND cu.id NOT IN (
                      SELECT cu2.id
                      FROM cuotas cu2
                      WHERE cu2.prestamo_id = :prestamo_id
                      ORDER BY cu2.numero_cuota, cu2.fecha_vencimiento, cu2.id
                      LIMIT :numero_cuotas
                  )
                  AND cu.total_pagado > 0
            """),
            {"prestamo_id": prestamo_id, "numero_cuotas": planificadas}
        )
        pagos_en_extra = resultado_pagos.scalar()
        
        if pagos_en_extra > 0:
            cuotas_extra_con_pagos += pagos_en_extra
            print(f"  [ADVERTENCIA] Prestamo {prestamo_id} tiene {pagos_en_extra} cuotas extra con pagos")
    
    if cuotas_extra_con_pagos > 0:
        print(f"\n[CRITICO] Se encontraron {cuotas_extra_con_pagos} cuotas extra con pagos")
        print("  Estas cuotas NO se pueden eliminar automaticamente")
        print("  Se requiere revision manual")
        respuesta = input("\n¿Desea continuar eliminando solo las cuotas extra SIN pagos? (s/n): ")
        if respuesta.lower() != 's':
            print("Operacion cancelada")
            db.close()
            sys.exit(0)
    else:
        print(f"\n[OK] Ninguna cuota extra tiene pagos. Se pueden eliminar {total_cuotas_extra} cuotas extra")
        respuesta = input("\n¿Desea eliminar las cuotas extra? (s/n): ")
        if respuesta.lower() != 's':
            print("Operacion cancelada")
            db.close()
            sys.exit(0)
    
    # Eliminar cuotas extra
    print("\nEliminando cuotas extra...")
    
    eliminadas = 0
    for prestamo_id, cedula, nombre, planificadas, actuales, extra in prestamos_con_extra:
        # Eliminar cuotas extra (mantener solo las primeras numero_cuotas)
        resultado_delete = db.execute(
            text("""
                DELETE FROM cuotas
                WHERE id IN (
                    SELECT cu.id
                    FROM cuotas cu
                    WHERE cu.prestamo_id = :prestamo_id
                      AND cu.id NOT IN (
                          SELECT cu2.id
                          FROM cuotas cu2
                          WHERE cu2.prestamo_id = :prestamo_id
                          ORDER BY cu2.numero_cuota, cu2.fecha_vencimiento, cu2.id
                          LIMIT :numero_cuotas
                      )
                      AND cu.total_pagado = 0
                )
            """),
            {"prestamo_id": prestamo_id, "numero_cuotas": planificadas}
        )
        eliminadas += resultado_delete.rowcount
    
    db.commit()
    print(f"\n[OK] Se eliminaron {eliminadas} cuotas extra")

# ======================================================================
# PARTE 2: COMPLETAR CUOTAS FALTANTES
# ======================================================================

print("\n" + "=" * 70)
print("PARTE 2: COMPLETAR CUOTAS FALTANTES")
print("=" * 70)

# Verificar préstamos con cuotas faltantes
resultado = db.execute(
    text("""
        SELECT 
            p.id AS prestamo_id,
            p.cedula,
            c.nombres AS nombre_cliente,
            p.numero_cuotas AS cuotas_planificadas,
            COUNT(cu.id) AS cuotas_generadas,
            p.numero_cuotas - COUNT(cu.id) AS cuotas_faltantes,
            p.fecha_base_calculo
        FROM prestamos p
        LEFT JOIN clientes c ON p.cedula = c.cedula
        LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE p.estado = 'APROBADO'
        GROUP BY p.id, p.cedula, c.nombres, p.numero_cuotas, p.fecha_base_calculo
        HAVING COUNT(cu.id) < p.numero_cuotas
        ORDER BY p.id
    """)
)

prestamos_con_faltantes = resultado.fetchall()

if len(prestamos_con_faltantes) == 0:
    print("\n[OK] No hay prestamos con cuotas faltantes")
else:
    print(f"\n[ATENCION] Se encontraron {len(prestamos_con_faltantes)} prestamos con cuotas faltantes")
    
    # Separar por si tienen fecha_base_calculo
    prestamos_pueden_regenerar = []
    prestamos_sin_fecha = []
    
    for prestamo_data in prestamos_con_faltantes:
        prestamo_id, cedula, nombre, planificadas, generadas, faltantes, fecha_base = prestamo_data
        if fecha_base:
            prestamos_pueden_regenerar.append(prestamo_data)
        else:
            prestamos_sin_fecha.append(prestamo_data)
    
    print(f"\n  Prestamos que pueden regenerar: {len(prestamos_pueden_regenerar)}")
    print(f"  Prestamos sin fecha_base_calculo: {len(prestamos_sin_fecha)}")
    
    if len(prestamos_sin_fecha) > 0:
        print("\n[ADVERTENCIA] Los siguientes prestamos NO pueden regenerar (falta fecha_base_calculo):")
        for prestamo_id, cedula, nombre, planificadas, generadas, faltantes, fecha_base in prestamos_sin_fecha[:10]:
            print(f"  Prestamo {prestamo_id}: {cedula} - {nombre or 'N/A'}")
        if len(prestamos_sin_fecha) > 10:
            print(f"  ... y {len(prestamos_sin_fecha) - 10} prestamos mas")
    
    if len(prestamos_pueden_regenerar) > 0:
        respuesta = input(f"\n¿Desea regenerar cuotas para {len(prestamos_pueden_regenerar)} prestamos? (s/n): ")
        if respuesta.lower() != 's':
            print("Operacion cancelada")
            db.close()
            sys.exit(0)
        
        print("\nRegenerando cuotas faltantes...")
        
        regenerados = 0
        errores = 0
        
        for prestamo_id, cedula, nombre, planificadas, generadas, faltantes, fecha_base in prestamos_pueden_regenerar:
            try:
                # Obtener préstamo
                prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
                if not prestamo:
                    print(f"  [ERROR] Prestamo {prestamo_id} no encontrado")
                    errores += 1
                    continue
                
                # Regenerar tabla de amortización (elimina existentes y crea todas)
                cuotas_generadas = generar_tabla_amortizacion(
                    prestamo,
                    prestamo.fecha_base_calculo,
                    db
                )
                
                regenerados += 1
                print(f"  [OK] Prestamo {prestamo_id}: Regeneradas {len(cuotas_generadas)} cuotas")
                
            except Exception as e:
                print(f"  [ERROR] Prestamo {prestamo_id}: {str(e)}")
                errores += 1
                db.rollback()
        
        print(f"\n[OK] Se regeneraron cuotas para {regenerados} prestamos")
        if errores > 0:
            print(f"[ADVERTENCIA] Hubo {errores} errores durante la regeneracion")

# ======================================================================
# VERIFICACION FINAL
# ======================================================================

print("\n" + "=" * 70)
print("VERIFICACION FINAL")
print("=" * 70)

# Verificar cuotas extra
resultado = db.execute(
    text("""
        SELECT COUNT(DISTINCT p.id)
        FROM prestamos p
        INNER JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE p.estado = 'APROBADO'
        GROUP BY p.id, p.numero_cuotas
        HAVING COUNT(cu.id) > p.numero_cuotas
    """)
)
prestamos_con_extra_restantes = len(resultado.fetchall())

# Verificar cuotas faltantes
resultado = db.execute(
    text("""
        SELECT COUNT(DISTINCT p.id)
        FROM prestamos p
        LEFT JOIN cuotas cu ON p.id = cu.prestamo_id
        WHERE p.estado = 'APROBADO'
        GROUP BY p.id, p.numero_cuotas
        HAVING COUNT(cu.id) < p.numero_cuotas
    """)
)
prestamos_con_faltantes_restantes = len(resultado.fetchall())

print(f"\nPrestamos con cuotas extra restantes: {prestamos_con_extra_restantes}")
print(f"Prestamos con cuotas faltantes restantes: {prestamos_con_faltantes_restantes}")

if prestamos_con_extra_restantes == 0 and prestamos_con_faltantes_restantes == 0:
    print("\n[OK] VERIFICACION EXITOSA: Todas las inconsistencias fueron corregidas")
else:
    print("\n[ATENCION] Aun quedan inconsistencias:")
    if prestamos_con_extra_restantes > 0:
        print(f"  - {prestamos_con_extra_restantes} prestamos con cuotas extra (pueden tener pagos)")
    if prestamos_con_faltantes_restantes > 0:
        print(f"  - {prestamos_con_faltantes_restantes} prestamos con cuotas faltantes (pueden faltar fecha_base_calculo)")

print("\n" + "=" * 70)

db.close()
