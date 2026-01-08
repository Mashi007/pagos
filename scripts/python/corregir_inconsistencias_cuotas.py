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
from sqlalchemy import text
from datetime import date, timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta

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
        # Ejecutar automáticamente sin confirmación interactiva
        print("\n[INFO] Ejecutando eliminacion automatica de cuotas extra...")
    
    # Eliminar cuotas extra
    print("\nEliminando cuotas extra...")
    
    eliminadas = 0
    for prestamo_id, cedula, nombre, planificadas, actuales, extra in prestamos_con_extra:
        # Primero identificar las cuotas a mantener (primeras numero_cuotas)
        # Mantener las primeras N cuotas ordenadas, sin importar si tienen pagos
        resultado_mantener = db.execute(
            text("""
                SELECT id
                FROM cuotas
                WHERE prestamo_id = :prestamo_id
                ORDER BY numero_cuota, fecha_vencimiento, id
                LIMIT :numero_cuotas
            """),
            {"prestamo_id": prestamo_id, "numero_cuotas": planificadas}
        )
        ids_a_mantener = [row[0] for row in resultado_mantener.fetchall()]
        
        if len(ids_a_mantener) == 0:
            print(f"  [ADVERTENCIA] Prestamo {prestamo_id}: No se encontraron cuotas para mantener")
            continue
        
        # Verificar si alguna cuota a mantener tiene pagos
        resultado_pagos = db.execute(
            text("""
                SELECT COUNT(*) 
                FROM cuotas 
                WHERE prestamo_id = :prestamo_id 
                  AND id IN :ids_mantener
                  AND total_pagado > 0
            """),
            {"prestamo_id": prestamo_id, "ids_mantener": tuple(ids_a_mantener)}
        )
        cuotas_con_pagos = resultado_pagos.scalar()
        
        if cuotas_con_pagos > 0:
            print(f"  [ADVERTENCIA] Prestamo {prestamo_id}: {cuotas_con_pagos} cuotas a mantener tienen pagos - NO se eliminan cuotas extra")
            continue
        
        # Eliminar cuotas extra (todas excepto las que se mantienen)
        # Solo eliminar cuotas sin pagos
        ids_str = ','.join(str(id_val) for id_val in ids_a_mantener)
        resultado_delete = db.execute(
            text(f"""
                DELETE FROM cuotas
                WHERE prestamo_id = :prestamo_id
                  AND id NOT IN ({ids_str})
                  AND total_pagado = 0
            """),
            {"prestamo_id": prestamo_id}
        )
        eliminadas += resultado_delete.rowcount
        print(f"  [OK] Prestamo {prestamo_id}: Eliminadas {resultado_delete.rowcount} cuotas extra")
    
    db.commit()
    print(f"\n[OK] Se eliminaron {eliminadas} cuotas extra en total")

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
        # Ejecutar automáticamente sin confirmación interactiva
        print(f"\n[INFO] Regenerando cuotas para {len(prestamos_pueden_regenerar)} prestamos automaticamente...")
        
        print("\nRegenerando cuotas faltantes...")
        
        regenerados = 0
        errores = 0
        
        for prestamo_id, cedula, nombre, planificadas, generadas, faltantes, fecha_base in prestamos_pueden_regenerar:
            try:
                # Obtener datos del préstamo usando SQL directo (evita problema con ORM)
                resultado_prestamo = db.execute(
                    text("""
                        SELECT 
                            id, numero_cuotas, total_financiamiento, cuota_periodo,
                            modalidad_pago, COALESCE(tasa_interes, 0.00) as tasa_interes,
                            fecha_base_calculo
                        FROM prestamos
                        WHERE id = :prestamo_id
                    """),
                    {"prestamo_id": prestamo_id}
                )
                prestamo_data = resultado_prestamo.fetchone()
                
                if not prestamo_data:
                    print(f"  [ERROR] Prestamo {prestamo_id} no encontrado")
                    errores += 1
                    continue
                
                p_id, num_cuotas, total_fin, cuota_per, modalidad, tasa, fecha_base_calc = prestamo_data
                
                # Eliminar cuotas existentes
                db.execute(text("DELETE FROM cuotas WHERE prestamo_id = :prestamo_id"), 
                          {"prestamo_id": prestamo_id})
                
                # Generar cuotas usando SQL directo
                saldo_capital = Decimal(str(total_fin))
                intervalo_dias = 30 if modalidad == "MENSUAL" else (15 if modalidad == "QUINCENAL" else 7)
                tasa_mensual = Decimal(str(tasa)) / Decimal(100) / Decimal(12) if Decimal(str(tasa)) > 0 else Decimal("0.00")
                
                cuotas_insertadas = 0
                for numero_cuota in range(1, num_cuotas + 1):
                    # Calcular fecha de vencimiento
                    if modalidad == "MENSUAL":
                        fecha_vencimiento = fecha_base_calc + relativedelta(months=numero_cuota)
                    else:
                        fecha_vencimiento = fecha_base_calc + timedelta(days=intervalo_dias * numero_cuota)
                    
                    # Método Francés (cuota fija)
                    monto_cuota = Decimal(str(cuota_per))
                    
                    # Calcular interés y capital
                    if tasa_mensual == Decimal("0.00"):
                        monto_interes = Decimal("0.00")
                        monto_capital = monto_cuota
                    else:
                        monto_interes = saldo_capital * tasa_mensual
                        monto_capital = monto_cuota - monto_interes
                    
                    # Actualizar saldo
                    saldo_capital_inicial = saldo_capital
                    saldo_capital = saldo_capital - monto_capital
                    saldo_capital_final = saldo_capital
                    
                    # Insertar cuota
                    db.execute(
                        text("""
                            INSERT INTO cuotas (
                                prestamo_id, numero_cuota, fecha_vencimiento,
                                monto_cuota, monto_capital, monto_interes,
                                saldo_capital_inicial, saldo_capital_final,
                                capital_pagado, interes_pagado, mora_pagada,
                                total_pagado, capital_pendiente, interes_pendiente,
                                estado
                            ) VALUES (
                                :prestamo_id, :numero_cuota, :fecha_vencimiento,
                                :monto_cuota, :monto_capital, :monto_interes,
                                :saldo_capital_inicial, :saldo_capital_final,
                                0.00, 0.00, 0.00,
                                0.00, :capital_pendiente, :interes_pendiente,
                                'PENDIENTE'
                            )
                        """),
                        {
                            "prestamo_id": prestamo_id,
                            "numero_cuota": numero_cuota,
                            "fecha_vencimiento": fecha_vencimiento,
                            "monto_cuota": float(monto_cuota),
                            "monto_capital": float(monto_capital),
                            "monto_interes": float(monto_interes),
                            "saldo_capital_inicial": float(saldo_capital_inicial),
                            "saldo_capital_final": float(saldo_capital_final),
                            "capital_pendiente": float(monto_capital),
                            "interes_pendiente": float(monto_interes)
                        }
                    )
                    cuotas_insertadas += 1
                
                db.commit()
                regenerados += 1
                print(f"  [OK] Prestamo {prestamo_id}: Regeneradas {cuotas_insertadas} cuotas")
                
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
