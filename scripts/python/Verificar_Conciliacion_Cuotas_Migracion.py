"""
Script para verificar y corregir la conciliación de cuotas después de la migración.

Este script:
1. Identifica cuotas que tienen total_pagado >= monto_cuota pero sus pagos no están conciliados
2. Marca los pagos relacionados como conciliados (conciliación positiva)
3. Actualiza el estado de las cuotas a "PAGADO" si corresponde

Uso:
    python scripts/python/Verificar_Conciliacion_Cuotas_Migracion.py
    python scripts/python/Verificar_Conciliacion_Cuotas_Migracion.py --aplicar
"""

import os
import sys
import argparse
from datetime import datetime
from decimal import Decimal

# Manejar encoding para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Agregar el directorio del backend al path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend"))
sys.path.insert(0, backend_dir)

from sqlalchemy import text
from app.db.session import SessionLocal
from app.models.pago import Pago
from app.models.amortizacion import Cuota

def verificar_cuotas_sin_conciliar(db):
    """
    Identifica cuotas que tienen total_pagado >= monto_cuota pero sus pagos no están conciliados
    """
    query = text("""
        SELECT DISTINCT
            c.id as cuota_id,
            c.prestamo_id,
            c.numero_cuota,
            c.total_pagado,
            c.monto_cuota,
            c.estado,
            COUNT(p.id) as total_pagos,
            COUNT(CASE WHEN p.conciliado = true THEN 1 END) as pagos_conciliados,
            COUNT(CASE WHEN p.conciliado = false OR p.conciliado IS NULL THEN 1 END) as pagos_sin_conciliar
        FROM cuotas c
        INNER JOIN prestamos pr ON c.prestamo_id = pr.id
        LEFT JOIN pagos p ON p.prestamo_id = c.prestamo_id 
            AND p.activo = true
            AND p.numero_documento IS NOT NULL
            AND p.numero_documento != ''
        WHERE pr.estado = 'APROBADO'
          AND c.total_pagado >= c.monto_cuota
          AND c.total_pagado > 0
        GROUP BY c.id, c.prestamo_id, c.numero_cuota, c.total_pagado, c.monto_cuota, c.estado
        HAVING COUNT(CASE WHEN p.conciliado = false OR p.conciliado IS NULL THEN 1 END) > 0
        ORDER BY c.prestamo_id, c.numero_cuota
    """)
    
    return query


def verificar_cuotas_estado_incorrecto(db):
    """
    Identifica cuotas que tienen total_pagado >= monto_cuota pero estado != 'PAGADO'
    y todos sus pagos están conciliados
    """
    query = text("""
        SELECT DISTINCT
            c.id as cuota_id,
            c.prestamo_id,
            c.numero_cuota,
            c.total_pagado,
            c.monto_cuota,
            c.estado,
            COUNT(p.id) as total_pagos,
            COUNT(CASE WHEN p.conciliado = true THEN 1 END) as pagos_conciliados
        FROM cuotas c
        INNER JOIN prestamos pr ON c.prestamo_id = pr.id
        LEFT JOIN pagos p ON p.prestamo_id = c.prestamo_id 
            AND p.activo = true
            AND p.numero_documento IS NOT NULL
            AND p.numero_documento != ''
        WHERE pr.estado = 'APROBADO'
          AND c.total_pagado >= c.monto_cuota
          AND c.total_pagado > 0
          AND c.estado != 'PAGADO'
        GROUP BY c.id, c.prestamo_id, c.numero_cuota, c.total_pagado, c.monto_cuota, c.estado
        HAVING COUNT(CASE WHEN p.conciliado = false OR p.conciliado IS NULL THEN 1 END) = 0
           OR COUNT(p.id) = 0  -- Cuotas sin pagos pero completamente pagadas (datos migrados)
        ORDER BY c.prestamo_id, c.numero_cuota
    """)
    
    return query
    
    result = db.execute(query)
    cuotas_problema = []
    
    for row in result:
        cuotas_problema.append({
            'cuota_id': row[0],
            'prestamo_id': row[1],
            'numero_cuota': row[2],
            'total_pagado': float(row[3]),
            'monto_cuota': float(row[4]),
            'estado': row[5],
            'total_pagos': row[6],
            'pagos_conciliados': row[7],
            'pagos_sin_conciliar': row[8] if len(row) > 8 else 0
        })
    
    return cuotas_problema


def obtener_pagos_sin_conciliar(db, prestamo_id: int):
    """
    Obtiene todos los pagos de un préstamo que no están conciliados
    """
    pagos = db.query(Pago).filter(
        Pago.prestamo_id == prestamo_id,
        Pago.activo == True,
        (Pago.conciliado == False) | (Pago.conciliado.is_(None))
    ).all()
    
    return pagos


def conciliar_pagos_prestamo(db, prestamo_id: int, aplicar: bool = False):
    """
    Marca todos los pagos de un préstamo como conciliados
    """
    pagos = obtener_pagos_sin_conciliar(db, prestamo_id)
    
    if not pagos:
        return 0
    
    if aplicar:
        fecha_conciliacion = datetime.now()
        for pago in pagos:
            pago.conciliado = True
            pago.fecha_conciliacion = fecha_conciliacion
            if hasattr(pago, "verificado_concordancia"):
                pago.verificado_concordancia = "SI"
        
        db.commit()
    
    return len(pagos)


def actualizar_estado_cuota(db, cuota_id: int, prestamo_id: int, aplicar: bool = False):
    """
    Actualiza el estado de una cuota a PAGADO si total_pagado >= monto_cuota
    y todos los pagos están conciliados
    """
    cuota = db.query(Cuota).filter(Cuota.id == cuota_id).first()
    
    if not cuota:
        return False
    
    # Verificar que total_pagado >= monto_cuota
    if cuota.total_pagado < cuota.monto_cuota:
        return False
    
    # Verificar que todos los pagos estén conciliados
    pagos_sin_conciliar = obtener_pagos_sin_conciliar(db, prestamo_id)
    if pagos_sin_conciliar:
        return False  # Aún hay pagos sin conciliar
    
    # Actualizar estado si no está en PAGADO
    if aplicar and cuota.estado != "PAGADO":
        estado_anterior = cuota.estado
        cuota.estado = "PAGADO"
        db.commit()
        return True
    
    return cuota.estado == "PAGADO"


def main():
    parser = argparse.ArgumentParser(
        description='Verificar y corregir conciliación de cuotas después de migración'
    )
    parser.add_argument(
        '--aplicar',
        action='store_true',
        help='Aplicar cambios (marcar pagos como conciliados y actualizar estados)'
    )
    args = parser.parse_args()
    
    modo = "APLICACIÓN" if args.aplicar else "VERIFICACIÓN (DRY RUN)"
    
    print("=" * 80)
    print(f"VERIFICACIÓN DE CONCILIACIÓN DE CUOTAS - MODO: {modo}")
    print("=" * 80)
    print()
    
    try:
        db = SessionLocal()
        print("[OK] Conexión a base de datos establecida")
    except Exception as e:
        print(f"[ERROR] Error conectando a base de datos: {str(e)}")
        return
    
    try:
        # 1. Identificar cuotas con problemas de conciliación
        print("\n[INFO] Identificando cuotas con pagos sin conciliar...")
        query1 = verificar_cuotas_sin_conciliar(db)
        result1 = db.execute(query1)
        cuotas_sin_conciliar = []
        for row in result1:
            cuotas_sin_conciliar.append({
                'cuota_id': row[0], 'prestamo_id': row[1], 'numero_cuota': row[2],
                'total_pagado': float(row[3]), 'monto_cuota': float(row[4]), 'estado': row[5],
                'total_pagos': row[6], 'pagos_conciliados': row[7], 'pagos_sin_conciliar': row[8]
            })
        
        # 2. Identificar cuotas con estado incorrecto
        print("\n[INFO] Identificando cuotas con estado incorrecto...")
        query2 = verificar_cuotas_estado_incorrecto(db)
        result2 = db.execute(query2)
        cuotas_estado_incorrecto = []
        for row in result2:
            cuotas_estado_incorrecto.append({
                'cuota_id': row[0], 'prestamo_id': row[1], 'numero_cuota': row[2],
                'total_pagado': float(row[3]), 'monto_cuota': float(row[4]), 'estado': row[5],
                'total_pagos': row[6], 'pagos_conciliados': row[7]
            })
        
        cuotas_problema = cuotas_sin_conciliar + cuotas_estado_incorrecto
        
        print(f"\n[RESULTADO]")
        print(f"  Cuotas con pagos sin conciliar: {len(cuotas_sin_conciliar)}")
        print(f"  Cuotas con estado incorrecto: {len(cuotas_estado_incorrecto)}")
        print(f"  Total cuotas a corregir: {len(cuotas_problema)}")
        
        if not cuotas_problema:
            print("\n✅ Todas las cuotas pagadas tienen sus pagos conciliados y estado correcto")
            return
        
        # 3. Agrupar por préstamo para procesar
        prestamos_afectados = {}
        for cuota in cuotas_problema:
            prestamo_id = cuota['prestamo_id']
            if prestamo_id not in prestamos_afectados:
                prestamos_afectados[prestamo_id] = []
            prestamos_afectados[prestamo_id].append(cuota)
        
        print(f"\n[INFO] Préstamos afectados: {len(prestamos_afectados)}")
        
        # 4. Mostrar resumen
        print("\n" + "=" * 80)
        print("RESUMEN DE CUOTAS CON PROBLEMAS")
        print("=" * 80)
        print(f"Total cuotas: {len(cuotas_problema)}")
        print(f"Total préstamos: {len(prestamos_afectados)}")
        
        # Mostrar primeros 10 ejemplos
        print("\n[EJEMPLOS] Primeras 10 cuotas con problemas:")
        for i, cuota in enumerate(cuotas_problema[:10], 1):
            print(f"  {i}. Préstamo {cuota['prestamo_id']}, Cuota #{cuota['numero_cuota']}: "
                  f"${cuota['total_pagado']:.2f} / ${cuota['monto_cuota']:.2f} - "
                  f"Estado: {cuota['estado']} - "
                  f"Pagos: {cuota['pagos_conciliados']}/{cuota['total_pagos']} conciliados")
        
        if len(cuotas_problema) > 10:
            print(f"  ... y {len(cuotas_problema) - 10} cuotas más")
        
        # 5. Procesar si se solicita aplicar
        if args.aplicar:
            print("\n" + "=" * 80)
            print("APLICANDO CONCILIACIÓN")
            print("=" * 80)
            
            prestamos_procesados = 0
            pagos_conciliados_total = 0
            cuotas_actualizadas = 0
            
            for prestamo_id, cuotas in prestamos_afectados.items():
                # Conciliar pagos del préstamo
                pagos_conciliados = conciliar_pagos_prestamo(db, prestamo_id, aplicar=True)
                pagos_conciliados_total += pagos_conciliados
                
                # Actualizar estado de cuotas
                for cuota in cuotas:
                    if actualizar_estado_cuota(db, cuota['cuota_id'], prestamo_id, aplicar=True):
                        cuotas_actualizadas += 1
                
                prestamos_procesados += 1
                
                if prestamos_procesados % 100 == 0:
                    print(f"  Procesados {prestamos_procesados}/{len(prestamos_afectados)} préstamos...")
            
            print("\n" + "=" * 80)
            print("RESULTADO FINAL")
            print("=" * 80)
            print(f"✅ Préstamos procesados: {prestamos_procesados}")
            print(f"✅ Pagos conciliados: {pagos_conciliados_total}")
            print(f"✅ Cuotas actualizadas a PAGADO: {cuotas_actualizadas}")
            print("\n[OK] Proceso completado exitosamente")
        else:
            print("\n" + "=" * 80)
            print("MODO VERIFICACIÓN (DRY RUN)")
            print("=" * 80)
            print("\nPara aplicar los cambios, ejecuta:")
            print("  python scripts/python/Verificar_Conciliacion_Cuotas_Migracion.py --aplicar")
            
            # Calcular estadísticas
            total_pagos_sin_conciliar = 0
            for prestamo_id in prestamos_afectados:
                pagos = obtener_pagos_sin_conciliar(db, prestamo_id)
                total_pagos_sin_conciliar += len(pagos)
            
            print(f"\n[ESTADÍSTICAS]")
            print(f"  Total pagos sin conciliar: {total_pagos_sin_conciliar}")
            print(f"  Total cuotas que se actualizarían: {len(cuotas_problema)}")
        
    except Exception as e:
        print(f"\n[ERROR] Error general: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()
        print("\n[OK] Sesión cerrada")


if __name__ == "__main__":
    main()
