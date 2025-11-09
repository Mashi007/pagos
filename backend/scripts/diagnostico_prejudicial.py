"""
Script de diagnóstico para notificaciones prejudiciales
Verifica por qué no hay información en la pestaña de notificaciones prejudiciales
"""

import sys
import os
from datetime import date
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Crear conexión a la base de datos
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def diagnosticar_prejudicial():
    """Diagnostica por qué no hay notificaciones prejudiciales"""
    db = SessionLocal()
    hoy = date.today()

    print("=" * 80)
    print("DIAGNOSTICO: NOTIFICACIONES PREJUDICIALES")
    print("=" * 80)
    print(f"Fecha actual: {hoy}")
    print()

    try:
        # 1. Verificar cuotas atrasadas en general
        print("1. Verificando cuotas atrasadas...")
        query_cuotas_atrasadas = text("""
            SELECT COUNT(*) as total
            FROM cuotas c
            INNER JOIN prestamos p ON p.id = c.prestamo_id
            WHERE c.estado = 'ATRASADO'
              AND c.fecha_vencimiento < :hoy
              AND p.estado = 'APROBADO'
        """)
        result = db.execute(query_cuotas_atrasadas, {"hoy": hoy})
        total_cuotas_atrasadas = result.scalar()
        print(f"   [OK] Total de cuotas atrasadas: {total_cuotas_atrasadas}")
        print()

        # 2. Verificar clientes con cuotas atrasadas
        print("2. Verificando clientes con cuotas atrasadas...")
        query_clientes_atrasados = text("""
            SELECT
                p.cliente_id,
                cl.nombres,
                COUNT(*) as cuotas_atrasadas
            FROM prestamos p
            INNER JOIN cuotas c ON c.prestamo_id = p.id
            INNER JOIN clientes cl ON cl.id = p.cliente_id
            WHERE p.estado = 'APROBADO'
              AND c.estado = 'ATRASADO'
              AND c.fecha_vencimiento < :hoy
              AND cl.estado != 'INACTIVO'
            GROUP BY p.cliente_id, cl.nombres
            ORDER BY cuotas_atrasadas DESC
            LIMIT 10
        """)
        result = db.execute(query_clientes_atrasados, {"hoy": hoy})
        clientes_atrasados = result.fetchall()
        print(f"   [OK] Clientes con cuotas atrasadas: {len(clientes_atrasados)}")
        if clientes_atrasados:
            print("   Top 10 clientes con mas cuotas atrasadas:")
            for row in clientes_atrasados:
                cliente_id, nombre, cuotas = row
                print(f"      - Cliente ID {cliente_id} ({nombre}): {cuotas} cuotas atrasadas")
        print()

        # 3. Verificar clientes con 3+ cuotas atrasadas (criterio prejudicial)
        print("3. Verificando clientes con 3+ cuotas atrasadas (PREJUDICIAL)...")
        query_prejudicial = text("""
            WITH cuotas_atrasadas AS (
                SELECT
                    p.cliente_id,
                    COUNT(*) as total_cuotas
                FROM prestamos p
                INNER JOIN cuotas c ON c.prestamo_id = p.id
                INNER JOIN clientes cl ON cl.id = p.cliente_id
                WHERE p.estado = 'APROBADO'
                  AND c.estado = 'ATRASADO'
                  AND c.fecha_vencimiento < :hoy
                  AND cl.estado != 'INACTIVO'
                GROUP BY p.cliente_id
                HAVING COUNT(*) >= 3
            )
            SELECT
                ca.cliente_id,
                cl.nombres,
                cl.cedula,
                ca.total_cuotas
            FROM cuotas_atrasadas ca
            INNER JOIN clientes cl ON cl.id = ca.cliente_id
            ORDER BY ca.total_cuotas DESC
        """)
        result = db.execute(query_prejudicial, {"hoy": hoy})
        clientes_prejudiciales = result.fetchall()
        print(f"   [OK] Clientes con 3+ cuotas atrasadas: {len(clientes_prejudiciales)}")
        if clientes_prejudiciales:
            print("   Clientes prejudiciales encontrados:")
            for row in clientes_prejudiciales:
                cliente_id, nombre, cedula, total = row
                print(f"      - Cliente ID {cliente_id} ({nombre}, Cédula: {cedula}): {total} cuotas atrasadas")
        else:
            print("   [WARN] No se encontraron clientes con 3+ cuotas atrasadas")
        print()

        # 4. Ejecutar la consulta completa del servicio
        print("4. Ejecutando consulta completa del servicio...")
        query_completa = text("""
            WITH cuotas_atrasadas AS (
                SELECT
                    p.id as prestamo_id,
                    p.cliente_id,
                    cl.nombres as nombre_cliente,
                    p.cedula,
                    COALESCE(p.modelo_vehiculo, p.producto, 'N/A') as modelo_vehiculo,
                    cl.email as correo,
                    cl.telefono,
                    c.fecha_vencimiento,
                    c.numero_cuota,
                    c.monto_cuota,
                    ROW_NUMBER() OVER (PARTITION BY p.cliente_id ORDER BY c.fecha_vencimiento ASC) as rn
                FROM prestamos p
                INNER JOIN cuotas c ON c.prestamo_id = p.id
                INNER JOIN clientes cl ON cl.id = p.cliente_id
                WHERE p.estado = 'APROBADO'
                  AND c.estado = 'ATRASADO'
                  AND c.fecha_vencimiento < :hoy
                  AND cl.estado != 'INACTIVO'
            ),
            clientes_prejudiciales AS (
                SELECT cliente_id
                FROM cuotas_atrasadas
                GROUP BY cliente_id
                HAVING COUNT(*) >= 3
            )
            SELECT
                ca.prestamo_id,
                ca.cliente_id,
                ca.nombre_cliente,
                ca.cedula,
                ca.modelo_vehiculo,
                ca.correo,
                ca.telefono,
                ca.fecha_vencimiento,
                ca.numero_cuota,
                ca.monto_cuota,
                (SELECT COUNT(*)
                 FROM cuotas c2
                 WHERE c2.prestamo_id = ca.prestamo_id
                   AND c2.estado = 'ATRASADO'
                   AND c2.fecha_vencimiento < :hoy) as total_cuotas_atrasadas,
                'PREJUDICIAL' as tipo_notificacion
            FROM cuotas_atrasadas ca
            INNER JOIN clientes_prejudiciales cp ON cp.cliente_id = ca.cliente_id
            ORDER BY ca.fecha_vencimiento ASC, ca.cliente_id, ca.numero_cuota
            LIMIT 20
        """)
        result = db.execute(query_completa.bindparams(hoy=hoy))
        resultados = result.fetchall()
        print(f"   [OK] Resultados de la consulta completa: {len(resultados)} registros")
        if resultados:
            print("   Primeros 20 registros:")
            for i, row in enumerate(resultados, 1):
                prestamo_id, cliente_id, nombre, cedula, modelo, correo, telefono, fecha_venc, num_cuota, monto, total_atrasadas, tipo = row
                print(f"      {i}. Cliente: {nombre} (ID: {cliente_id}) - Cuota #{num_cuota} - Vence: {fecha_venc} - Total atrasadas: {total_atrasadas}")
        else:
            print("   [WARN] La consulta no devolvio resultados")
        print()

        # 5. Verificar estados de préstamos
        print("5. Verificando estados de prestamos...")
        query_estados_prestamos = text("""
            SELECT estado, COUNT(*) as total
            FROM prestamos
            GROUP BY estado
            ORDER BY total DESC
        """)
        result = db.execute(query_estados_prestamos)
        estados_prestamos = result.fetchall()
        print("   Distribucion de estados de prestamos:")
        for estado, total in estados_prestamos:
            print(f"      - {estado}: {total} prestamos")
        print()

        # 6. Verificar estados de cuotas
        print("6. Verificando estados de cuotas...")
        query_estados_cuotas = text("""
            SELECT estado, COUNT(*) as total
            FROM cuotas
            GROUP BY estado
            ORDER BY total DESC
        """)
        result = db.execute(query_estados_cuotas)
        estados_cuotas = result.fetchall()
        print("   Distribucion de estados de cuotas:")
        for estado, total in estados_cuotas:
            print(f"      - {estado}: {total} cuotas")
        print()

        # 7. Verificar estados de clientes
        print("7. Verificando estados de clientes...")
        query_estados_clientes = text("""
            SELECT estado, COUNT(*) as total
            FROM clientes
            GROUP BY estado
            ORDER BY total DESC
        """)
        result = db.execute(query_estados_clientes)
        estados_clientes = result.fetchall()
        print("   Distribucion de estados de clientes:")
        for estado, total in estados_clientes:
            print(f"      - {estado}: {total} clientes")
        print()

        print("=" * 80)
        print("[OK] DIAGNOSTICO COMPLETADO")
        print("=" * 80)

    except Exception as e:
        print(f"[ERROR] Error durante el diagnostico: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    diagnosticar_prejudicial()
