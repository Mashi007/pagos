"""
Script para auditar el proceso de aprobación automática
Verifica el estado completo del préstamo y detecta errores
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Agregar el directorio backend al path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Importar módulos del backend
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Crear engine y sesión
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def verificar_prestamo(prestamo_id=9):
    """Verifica el estado completo del préstamo"""
    
    db = SessionLocal()
    
    try:
        print("=" * 70)
        print("AUDITORÍA: PROCESO DE APROBACIÓN AUTOMÁTICA")
        print("=" * 70)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Préstamo ID: {prestamo_id}")
        print("=" * 70)
        
        # 1. Verificar préstamo
        print("\n📋 1. ESTADO DEL PRÉSTAMO")
        print("-" * 70)
        
        prestamo_query = text("""
            SELECT 
                id, cedula, nombres, estado, total_financiamiento,
                numero_cuotas, cuota_periodo, tasa_interes,
                fecha_aprobacion, fecha_base_calculo,
                usuario_proponente, usuario_aprobador, observaciones,
                created_at, updated_at
            FROM prestamos
            WHERE id = :prestamo_id
        """)
        
        result = db.execute(prestamo_query, {"prestamo_id": prestamo_id})
        prestamo = result.fetchone()
        
        if not prestamo:
            print("❌ ERROR: Préstamo no encontrado")
            return
        
        print(f"ID: {prestamo.id}")
        print(f"Cédula: {prestamo.cedula}")
        print(f"Nombres: {prestamo.nombres}")
        print(f"Estado: {prestamo.estado}")
        print(f"Monto: ${prestamo.total_financiamiento}")
        print(f"Cuotas: {prestamo.numero_cuotas}")
        print(f"Cuota período: ${prestamo.cuota_periodo}")
        print(f"Tasa interés: {prestamo.tasa_interes}%")
        print(f"Fecha aprobación: {prestamo.fecha_aprobacion}")
        print(f"Fecha base cálculo: {prestamo.fecha_base_calculo}")
        print(f"Usuario proponente: {prestamo.usuario_proponente}")
        print(f"Usuario aprobador: {prestamo.usuario_aprobador}")
        print(f"Observaciones: {prestamo.observaciones}")
        print(f"Created at: {prestamo.created_at}")
        print(f"Updated at: {prestamo.updated_at}")
        
        # Diagnóstico
        if prestamo.estado == 'APROBADO':
            print("\n✅ OK: Préstamo aprobado correctamente")
        else:
            print(f"\n❌ ERROR: Estado incorrecto - Esperado: APROBADO, Actual: {prestamo.estado}")
        
        if prestamo.fecha_aprobacion:
            print("✅ OK: Fecha de aprobación establecida")
        else:
            print("❌ ERROR: No hay fecha de aprobación")
        
        if prestamo.fecha_base_calculo:
            print("✅ OK: Fecha base de cálculo establecida")
        else:
            print("⚠️  ADVERTENCIA: No hay fecha base de cálculo")
        
        if prestamo.usuario_aprobador:
            print("✅ OK: Usuario aprobador asignado")
        else:
            print("❌ ERROR: No hay usuario aprobador")
        
        # 2. Verificar evaluación
        print("\n📊 2. EVALUACIÓN DE RIESGO")
        print("-" * 70)
        
        eval_query = text("""
            SELECT 
                id, prestamo_id, puntuacion_total, clasificacion_riesgo,
                decision_final, tasa_interes_aplicada, plazo_maximo,
                requisitos_adicionales, created_at
            FROM prestamos_evaluacion
            WHERE prestamo_id = :prestamo_id
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        result = db.execute(eval_query, {"prestamo_id": prestamo_id})
        evaluacion = result.fetchone()
        
        if evaluacion:
            print(f"ID: {evaluacion.id}")
            print(f"Préstamo ID: {evaluacion.prestamo_id}")
            print(f"Puntuación: {evaluacion.puntuacion_total}/100")
            print(f"Clasificación: {evaluacion.clasificacion_riesgo}")
            print(f"Decisión: {evaluacion.decision_final}")
            print(f"Tasa interés: {evaluacion.tasa_interes_aplicada}%")
            print(f"Plazo máximo: {evaluacion.plazo_maximo} meses")
            print(f"Requisitos: {evaluacion.requisitos_adicionales}")
            print(f"Created at: {evaluacion.created_at}")
            
            # Diagnóstico
            if evaluacion.decision_final == 'APROBADO_AUTOMATICO':
                print("\n✅ OK: Evaluación con aprobación automática")
            else:
                print(f"\n⚠️  ADVERTENCIA: Decisión: {evaluacion.decision_final}")
        else:
            print("❌ ERROR: No existe evaluación para este préstamo")
        
        # 3. Verificar cuotas
        print("\n💰 3. TABLA DE AMORTIZACIÓN")
        print("-" * 70)
        
        cuotas_query = text("""
            SELECT 
                id, numero_cuota, fecha_vencimiento, 
                monto_capital, monto_interes, monto_cuota,
                saldo_capital_inicial, saldo_capital_final, estado
            FROM cuotas
            WHERE prestamo_id = :prestamo_id
            ORDER BY numero_cuota
        """)
        
        result = db.execute(cuotas_query, {"prestamo_id": prestamo_id})
        cuotas = result.fetchall()
        
        print(f"Total cuotas encontradas: {len(cuotas)}")
        
        if cuotas:
            print(f"\nPrimeras 3 cuotas:")
            for cuota in cuotas[:3]:
                print(f"  Cuota {cuota.numero_cuota}: ${cuota.monto_cuota} - Vence: {cuota.fecha_vencimiento}")
            
            if len(cuotas) == prestamo.numero_cuotas:
                print(f"\n✅ OK: Todas las cuotas generadas ({len(cuotas)})")
            else:
                print(f"\n❌ ERROR: Se esperaban {prestamo.numero_cuotas} cuotas, se encontraron {len(cuotas)}")
        else:
            print("❌ ERROR: No se generaron cuotas")
        
        # 4. Verificar auditoría
        print("\n📝 4. HISTORIAL DE AUDITORÍA")
        print("-" * 70)
        
        audit_query = text("""
            SELECT 
                id, usuario, accion, campo_modificado,
                valor_anterior, valor_nuevo, estado_anterior, estado_nuevo,
                created_at
            FROM prestamo_auditoria
            WHERE prestamo_id = :prestamo_id
            ORDER BY created_at DESC
        """)
        
        result = db.execute(audit_query, {"prestamo_id": prestamo_id})
        auditorias = result.fetchall()
        
        print(f"Total registros: {len(auditorias)}")
        
        if auditorias:
            print(f"\nÚltimos cambios:")
            for audit in auditorias[:3]:
                print(f"  - {audit.accion}: {audit.estado_anterior} → {audit.estado_nuevo} ({audit.created_at})")
            
            # Verificar si hay cambio a APROBADO
            if any(a.estado_nuevo == 'APROBADO' for a in auditorias):
                print("\n✅ OK: Existe registro de cambio a APROBADO")
            else:
                print("\n❌ ERROR: No hay registro de cambio a APROBADO")
        else:
            print("⚠️  ADVERTENCIA: No hay registros de auditoría")
        
        # Resumen final
        print("\n" + "=" * 70)
        print("RESUMEN DE VERIFICACIÓN")
        print("=" * 70)
        
        errores = []
        advertencias = []
        
        if prestamo.estado != 'APROBADO':
            errores.append("Estado no es APROBADO")
        
        if not prestamo.fecha_aprobacion:
            errores.append("No hay fecha de aprobación")
        
        if not evaluacion:
            errores.append("No existe evaluación")
        
        if not cuotas:
            errores.append("No se generaron cuotas")
        elif len(cuotas) != prestamo.numero_cuotas:
            advertencias.append(f"Cuotas incompletas ({len(cuotas)}/{prestamo.numero_cuotas})")
        
        if not prestamo.fecha_base_calculo:
            advertencias.append("No hay fecha base de cálculo")
        
        if errores:
            print("❌ ERRORES DETECTADOS:")
            for error in errores:
                print(f"  - {error}")
        
        if advertencias:
            print("\n⚠️  ADVERTENCIAS:")
            for advertencia in advertencias:
                print(f"  - {advertencia}")
        
        if not errores and not advertencias:
            print("✅ TODO CORRECTO: El proceso de aprobación automática funcionó correctamente")
        elif not errores:
            print("✅ PROCESO CORRECTO: Todo funcionó, solo hay advertencias menores")
        
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR al ejecutar auditoría: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    # Puedes cambiar el ID del préstamo si es necesario
    prestamo_id = 9
    verificar_prestamo(prestamo_id)

