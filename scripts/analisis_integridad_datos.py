"""
Script de análisis de integridad de datos
Revisa la coherencia entre Clientes, Préstamos, Pagos y Cuotas
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path para importar módulos
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.models.amortizacion import Cuota
from datetime import datetime
from collections import defaultdict

def print_section(title: str):
    """Imprime un separador de sección"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def print_subsection(title: str):
    """Imprime un separador de subsección"""
    print(f"\n--- {title} ---")

def analizar_clientes(db):
    """Analiza la estructura y coherencia de clientes"""
    print_section("1. ANÁLISIS DE CLIENTES")
    
    # Total de clientes
    total_clientes = db.query(func.count(Cliente.id)).scalar()
    print(f"📊 Total de clientes: {total_clientes}")
    
    # Clientes activos vs inactivos
    clientes_activos = db.query(func.count(Cliente.id)).filter(Cliente.activo == True).scalar()
    clientes_inactivos = total_clientes - clientes_activos
    print(f"✅ Clientes activos: {clientes_activos}")
    print(f"❌ Clientes inactivos: {clientes_inactivos}")
    
    # Clientes con cédulas duplicadas (PROBLEMA: No deberían existir)
    print_subsection("Cédulas duplicadas (PROBLEMA)")
    duplicados = db.execute(text("""
        SELECT cedula, COUNT(*) as cantidad
        FROM clientes
        WHERE activo = TRUE
        GROUP BY cedula
        HAVING COUNT(*) > 1
        ORDER BY cantidad DESC
    """)).fetchall()
    
    if duplicados:
        print(f"❌ PROBLEMA: Se encontraron {len(duplicados)} cédulas duplicadas en clientes:")
        print("   ⚠️  Las cédulas NO deben estar duplicadas en la tabla de clientes")
        for cedula, cantidad in duplicados:
            print(f"   - Cédula {cedula}: {cantidad} registros")
    else:
        print("✅ No hay cédulas duplicadas en clientes (correcto)")
    
    # Clientes sin cédula
    sin_cedula = db.query(func.count(Cliente.id)).filter(
        (Cliente.cedula == None) | (Cliente.cedula == '')
    ).scalar()
    if sin_cedula > 0:
        print(f"⚠️  Clientes sin cédula: {sin_cedula}")
    else:
        print("✅ Todos los clientes tienen cédula")
    
    # Clientes con email duplicado
    print_subsection("Emails duplicados")
    emails_dup = db.execute(text("""
        SELECT email, COUNT(*) as cantidad
        FROM clientes
        WHERE activo = TRUE AND email IS NOT NULL AND email != ''
        GROUP BY email
        HAVING COUNT(*) > 1
        ORDER BY cantidad DESC
        LIMIT 10
    """)).fetchall()
    
    if emails_dup:
        print(f"⚠️  Se encontraron {len(emails_dup)} emails duplicados (mostrando primeros 10):")
        for email, cantidad in emails_dup:
            print(f"   - {email}: {cantidad} registros")
    else:
        print("✅ No hay emails duplicados")
    
    return {
        'total': total_clientes,
        'activos': clientes_activos,
        'inactivos': clientes_inactivos,
        'duplicados_cedula': len(duplicados),
        'sin_cedula': sin_cedula
    }

def analizar_prestamos(db):
    """Analiza la estructura y coherencia de préstamos"""
    print_section("2. ANÁLISIS DE PRÉSTAMOS")
    
    # Total de préstamos
    total_prestamos = db.query(func.count(Prestamo.id)).scalar()
    print(f"📊 Total de préstamos: {total_prestamos}")
    
    # Préstamos por estado
    print_subsection("Préstamos por estado")
    prestamos_por_estado = db.execute(text("""
        SELECT estado, COUNT(*) as cantidad
        FROM prestamos
        GROUP BY estado
        ORDER BY cantidad DESC
    """)).fetchall()
    
    for estado, cantidad in prestamos_por_estado:
        porcentaje = (cantidad / total_prestamos * 100) if total_prestamos > 0 else 0
        print(f"   - {estado}: {cantidad} ({porcentaje:.1f}%)")
    
    # Préstamos aprobados
    prestamos_aprobados = db.query(func.count(Prestamo.id)).filter(
        Prestamo.estado == 'APROBADO'
    ).scalar()
    print(f"\n✅ Préstamos APROBADOS: {prestamos_aprobados}")
    
    # Préstamos aprobados sin fecha de aprobación
    aprobados_sin_fecha = db.query(func.count(Prestamo.id)).filter(
        Prestamo.estado == 'APROBADO',
        Prestamo.fecha_aprobacion == None
    ).scalar()
    if aprobados_sin_fecha > 0:
        print(f"⚠️  Préstamos aprobados sin fecha_aprobacion: {aprobados_sin_fecha}")
    else:
        print("✅ Todos los préstamos aprobados tienen fecha_aprobacion")
    
    # Préstamos con cédulas que no existen en clientes (PROBLEMA)
    print_subsection("Préstamos con cédulas sin cliente (PROBLEMA)")
    prestamos_sin_cliente = db.execute(text("""
        SELECT DISTINCT p.cedula, COUNT(*) as cantidad_prestamos
        FROM prestamos p
        LEFT JOIN clientes c ON p.cedula = c.cedula AND c.activo = TRUE
        WHERE c.id IS NULL
        GROUP BY p.cedula
        ORDER BY cantidad_prestamos DESC
        LIMIT 20
    """)).fetchall()
    
    if prestamos_sin_cliente:
        print(f"❌ PROBLEMA: Se encontraron {len(prestamos_sin_cliente)} cédulas con préstamos pero sin cliente activo:")
        total_prestamos_sin_cliente = 0
        for cedula, cantidad in prestamos_sin_cliente:
            print(f"   - Cédula {cedula}: {cantidad} préstamos")
            total_prestamos_sin_cliente += cantidad
        print(f"   Total de préstamos afectados: {total_prestamos_sin_cliente}")
        print("   ⚠️  Todos los préstamos deben tener un cliente activo asociado")
    else:
        print("✅ Todos los préstamos tienen cliente asociado")
    
    # NOTA: Es normal que una cédula tenga múltiples préstamos (una persona puede tener varios préstamos)
    print_subsection("Múltiples préstamos por cédula (NORMAL)")
    cedulas_multiples_prestamos = db.execute(text("""
        SELECT cedula, COUNT(*) as cantidad_prestamos
        FROM prestamos
        WHERE estado = 'APROBADO'
        GROUP BY cedula
        HAVING COUNT(*) > 1
        ORDER BY cantidad_prestamos DESC
        LIMIT 10
    """)).fetchall()
    
    if cedulas_multiples_prestamos:
        print(f"ℹ️  Se encontraron {len(cedulas_multiples_prestamos)} cédulas con múltiples préstamos aprobados (esto es normal):")
        for cedula, cantidad in cedulas_multiples_prestamos[:5]:  # Mostrar solo primeros 5
            print(f"   - Cédula {cedula}: {cantidad} préstamos aprobados")
        if len(cedulas_multiples_prestamos) > 5:
            print(f"   ... y {len(cedulas_multiples_prestamos) - 5} más")
    else:
        print("ℹ️  No hay cédulas con múltiples préstamos aprobados")
    
    # Préstamos aprobados sin cuotas
    print_subsection("Préstamos aprobados sin cuotas")
    prestamos_sin_cuotas = db.execute(text("""
        SELECT p.id, p.cedula, p.total_financiamiento, p.numero_cuotas, p.fecha_aprobacion
        FROM prestamos p
        LEFT JOIN cuotas c ON p.id = c.prestamo_id
        WHERE p.estado = 'APROBADO' AND c.id IS NULL
        ORDER BY p.fecha_aprobacion DESC
        LIMIT 20
    """)).fetchall()
    
    if prestamos_sin_cuotas:
        print(f"⚠️  Se encontraron {len(prestamos_sin_cuotas)} préstamos aprobados sin cuotas:")
        for prestamo_id, cedula, total, num_cuotas, fecha_aprob in prestamos_sin_cuotas:
            print(f"   - Préstamo ID {prestamo_id} (Cédula: {cedula}, Cuotas esperadas: {num_cuotas}, Aprobado: {fecha_aprob})")
    else:
        print("✅ Todos los préstamos aprobados tienen cuotas")
    
    # Préstamos con número de cuotas inconsistente
    print_subsection("Préstamos con número de cuotas inconsistente")
    prestamos_cuotas_inconsistentes = db.execute(text("""
        SELECT p.id, p.cedula, p.numero_cuotas, COUNT(c.id) as cuotas_reales
        FROM prestamos p
        LEFT JOIN cuotas c ON p.id = c.prestamo_id
        WHERE p.estado = 'APROBADO'
        GROUP BY p.id, p.cedula, p.numero_cuotas
        HAVING COUNT(c.id) != p.numero_cuotas AND p.numero_cuotas > 0
        ORDER BY ABS(COUNT(c.id) - p.numero_cuotas) DESC
        LIMIT 20
    """)).fetchall()
    
    if prestamos_cuotas_inconsistentes:
        print(f"⚠️  Se encontraron {len(prestamos_cuotas_inconsistentes)} préstamos con número de cuotas inconsistente:")
        for prestamo_id, cedula, esperadas, reales in prestamos_cuotas_inconsistentes:
            diferencia = reales - esperadas
            print(f"   - Préstamo ID {prestamo_id} (Cédula: {cedula}): Esperadas {esperadas}, Reales {reales} (Diferencia: {diferencia:+d})")
    else:
        print("✅ Todos los préstamos tienen el número correcto de cuotas")
    
    return {
        'total': total_prestamos,
        'aprobados': prestamos_aprobados,
        'sin_cuotas': len(prestamos_sin_cuotas),
        'cuotas_inconsistentes': len(prestamos_cuotas_inconsistentes),
        'sin_cliente': len(prestamos_sin_cliente)
    }

def analizar_pagos(db):
    """Analiza la estructura y coherencia de pagos"""
    print_section("3. ANÁLISIS DE PAGOS")
    
    # Total de pagos
    total_pagos = db.query(func.count(Pago.id)).scalar()
    print(f"📊 Total de pagos: {total_pagos}")
    
    # Pagos activos vs inactivos
    pagos_activos = db.query(func.count(Pago.id)).filter(Pago.activo == True).scalar()
    pagos_inactivos = total_pagos - pagos_activos
    print(f"✅ Pagos activos: {pagos_activos}")
    print(f"❌ Pagos inactivos: {pagos_inactivos}")
    
    # Pagos por estado
    print_subsection("Pagos por estado")
    pagos_por_estado = db.execute(text("""
        SELECT estado, COUNT(*) as cantidad
        FROM pagos
        WHERE activo = TRUE
        GROUP BY estado
        ORDER BY cantidad DESC
    """)).fetchall()
    
    for estado, cantidad in pagos_por_estado:
        porcentaje = (cantidad / pagos_activos * 100) if pagos_activos > 0 else 0
        print(f"   - {estado}: {cantidad} ({porcentaje:.1f}%)")
    
    # Pagos conciliados vs no conciliados
    print_subsection("Estado de conciliación")
    pagos_conciliados = db.query(func.count(Pago.id)).filter(
        Pago.activo == True,
        Pago.conciliado == True
    ).scalar()
    pagos_no_conciliados = pagos_activos - pagos_conciliados
    
    print(f"✅ Pagos conciliados: {pagos_conciliados}")
    print(f"⚠️  Pagos NO conciliados: {pagos_no_conciliados}")
    
    porcentaje_conciliados = (pagos_conciliados / pagos_activos * 100) if pagos_activos > 0 else 0
    print(f"📈 Porcentaje de conciliación: {porcentaje_conciliados:.1f}%")
    
    # Pagos con cédulas que no tienen préstamos (PROBLEMA)
    print_subsection("Pagos con cédulas sin préstamos (PROBLEMA)")
    pagos_sin_prestamos = db.execute(text("""
        SELECT DISTINCT p.cedula, COUNT(*) as cantidad_pagos, SUM(p.monto_pagado) as total_pagado
        FROM pagos p
        LEFT JOIN prestamos pr ON p.cedula = pr.cedula AND pr.estado = 'APROBADO'
        WHERE p.activo = TRUE AND pr.id IS NULL
        GROUP BY p.cedula
        ORDER BY cantidad_pagos DESC
        LIMIT 20
    """)).fetchall()
    
    if pagos_sin_prestamos:
        print(f"❌ PROBLEMA: Se encontraron {len(pagos_sin_prestamos)} cédulas con pagos pero sin préstamos aprobados:")
        total_pagos_sin_prestamo = 0
        total_monto_sin_prestamo = 0
        for cedula, cantidad, monto in pagos_sin_prestamos:
            print(f"   - Cédula {cedula}: {cantidad} pagos, Total: ${monto:,.2f}")
            total_pagos_sin_prestamo += cantidad
            total_monto_sin_prestamo += float(monto or 0)
        print(f"   Total de pagos afectados: {total_pagos_sin_prestamo}")
        print(f"   Total monto afectado: ${total_monto_sin_prestamo:,.2f}")
        print("   ⚠️  Los pagos deben estar asociados a préstamos aprobados")
    else:
        print("✅ Todos los pagos tienen préstamos asociados")
    
    # NOTA: Es normal que una cédula tenga múltiples pagos (una persona puede realizar varios pagos)
    print_subsection("Múltiples pagos por cédula (NORMAL)")
    cedulas_multiples_pagos = db.execute(text("""
        SELECT cedula, COUNT(*) as cantidad_pagos, SUM(monto_pagado) as total_pagado
        FROM pagos
        WHERE activo = TRUE
        GROUP BY cedula
        HAVING COUNT(*) > 1
        ORDER BY cantidad_pagos DESC
        LIMIT 10
    """)).fetchall()
    
    if cedulas_multiples_pagos:
        print(f"ℹ️  Se encontraron {len(cedulas_multiples_pagos)} cédulas con múltiples pagos (esto es normal):")
        for cedula, cantidad, monto in cedulas_multiples_pagos[:5]:  # Mostrar solo primeros 5
            print(f"   - Cédula {cedula}: {cantidad} pagos, Total: ${monto:,.2f}")
        if len(cedulas_multiples_pagos) > 5:
            print(f"   ... y {len(cedulas_multiples_pagos) - 5} más")
    else:
        print("ℹ️  No hay cédulas con múltiples pagos")
    
    # NOTA: No se verifica número de documento porque tienen nomenclatura científica
    # y se verificarán manualmente
    print_subsection("Nota sobre número de documento")
    print("ℹ️  Los números de documento no se verifican automáticamente")
    print("   (tienen nomenclatura científica y se verificarán manualmente)")
    
    return {
        'total': total_pagos,
        'activos': pagos_activos,
        'conciliados': pagos_conciliados,
        'no_conciliados': pagos_no_conciliados,
        'sin_prestamos': len(pagos_sin_prestamos)
    }

def analizar_cuotas(db):
    """Analiza la estructura y coherencia de cuotas"""
    print_section("4. ANÁLISIS DE CUOTAS")
    
    # Total de cuotas
    total_cuotas = db.query(func.count(Cuota.id)).scalar()
    print(f"📊 Total de cuotas: {total_cuotas}")
    
    # Cuotas por estado
    print_subsection("Cuotas por estado")
    cuotas_por_estado = db.execute(text("""
        SELECT estado, COUNT(*) as cantidad
        FROM cuotas
        GROUP BY estado
        ORDER BY cantidad DESC
    """)).fetchall()
    
    for estado, cantidad in cuotas_por_estado:
        porcentaje = (cantidad / total_cuotas * 100) if total_cuotas > 0 else 0
        print(f"   - {estado}: {cantidad} ({porcentaje:.1f}%)")
    
    # Cuotas sin préstamo asociado
    print_subsection("Cuotas sin préstamo asociado")
    cuotas_sin_prestamo = db.execute(text("""
        SELECT c.id, c.prestamo_id, c.numero_cuota
        FROM cuotas c
        LEFT JOIN prestamos p ON c.prestamo_id = p.id
        WHERE p.id IS NULL
        LIMIT 20
    """)).fetchall()
    
    if cuotas_sin_prestamo:
        print(f"⚠️  Se encontraron {len(cuotas_sin_prestamo)} cuotas sin préstamo asociado:")
        for cuota_id, prestamo_id, numero in cuotas_sin_prestamo:
            print(f"   - Cuota ID {cuota_id} (Préstamo ID: {prestamo_id}, Cuota #: {numero})")
    else:
        print("✅ Todas las cuotas tienen préstamo asociado")
    
    # Cuotas con pagos pero sin relación directa
    print_subsection("Análisis de relación cuotas-pagos")
    
    # NOTA: No se verifica relación por número de documento porque tienen nomenclatura científica
    # La relación se verifica por cédula y fecha, que es más confiable
    print("ℹ️  La relación entre cuotas y pagos se verifica por cédula y fecha")
    print("   (no se usa número de documento debido a nomenclatura científica)")
    
    # Verificar cuotas pagadas que podrían tener pagos asociados por cédula
    cuotas_con_pagos_potenciales = db.execute(text("""
        SELECT 
            c.id as cuota_id,
            c.prestamo_id,
            c.numero_cuota,
            c.estado,
            c.total_pagado,
            pr.cedula,
            COUNT(p.id) as pagos_potenciales
        FROM cuotas c
        LEFT JOIN prestamos pr ON c.prestamo_id = pr.id
        LEFT JOIN pagos p ON pr.cedula = p.cedula 
            AND p.activo = TRUE
            AND p.fecha_pago <= COALESCE(c.fecha_pago, CURRENT_DATE)
        WHERE c.total_pagado > 0
        GROUP BY c.id, c.prestamo_id, c.numero_cuota, c.estado, c.total_pagado, pr.cedula
        HAVING COUNT(p.id) = 0
        ORDER BY c.total_pagado DESC
        LIMIT 20
    """)).fetchall()
    
    if cuotas_con_pagos_potenciales:
        print(f"ℹ️  Se encontraron {len(cuotas_con_pagos_potenciales)} cuotas con pagos registrados pero sin pagos potenciales por cédula:")
        print("   (Esto puede ser normal si los pagos se registraron manualmente o tienen fechas diferentes)")
        for cuota_id, prestamo_id, numero, estado, total_pagado, cedula, pagos_rel in cuotas_con_pagos_potenciales:
            print(f"   - Cuota ID {cuota_id} (Préstamo: {prestamo_id}, Cédula: {cedula}, Cuota #: {numero}, Estado: {estado}, Pagado: ${total_pagado:,.2f})")
    else:
        print("✅ Todas las cuotas con pagos tienen pagos potenciales relacionados por cédula")
    
    return {
        'total': total_cuotas,
        'sin_prestamo': len(cuotas_sin_prestamo),
        'con_pagos_sin_relacion': len(cuotas_con_pagos_manuales)
    }

def analizar_relaciones(db):
    """Analiza las relaciones entre todas las entidades"""
    print_section("5. ANÁLISIS DE RELACIONES ENTRE ENTIDADES")
    
    # Clientes con préstamos
    print_subsection("Clientes con préstamos")
    clientes_con_prestamos = db.execute(text("""
        SELECT COUNT(DISTINCT c.id) as clientes_con_prestamos
        FROM clientes c
        INNER JOIN prestamos p ON c.cedula = p.cedula
        WHERE c.activo = TRUE
    """)).scalar()
    
    total_clientes_activos = db.query(func.count(Cliente.id)).filter(Cliente.activo == True).scalar()
    clientes_sin_prestamos = total_clientes_activos - clientes_con_prestamos
    
    print(f"✅ Clientes activos con préstamos: {clientes_con_prestamos}")
    print(f"⚠️  Clientes activos sin préstamos: {clientes_sin_prestamos}")
    
    # Préstamos con pagos
    print_subsection("Préstamos con pagos")
    prestamos_con_pagos = db.execute(text("""
        SELECT COUNT(DISTINCT p.id) as prestamos_con_pagos
        FROM prestamos p
        INNER JOIN pagos pa ON p.cedula = pa.cedula AND pa.activo = TRUE
        WHERE p.estado = 'APROBADO'
    """)).scalar()
    
    total_prestamos_aprobados = db.query(func.count(Prestamo.id)).filter(Prestamo.estado == 'APROBADO').scalar()
    prestamos_sin_pagos = total_prestamos_aprobados - prestamos_con_pagos
    
    print(f"✅ Préstamos aprobados con pagos: {prestamos_con_pagos}")
    print(f"⚠️  Préstamos aprobados sin pagos: {prestamos_sin_pagos}")
    
    # Préstamos con cuotas pagadas
    print_subsection("Préstamos con cuotas pagadas")
    prestamos_con_cuotas_pagadas = db.execute(text("""
        SELECT COUNT(DISTINCT p.id) as prestamos_con_cuotas_pagadas
        FROM prestamos p
        INNER JOIN cuotas c ON p.id = c.prestamo_id
        WHERE p.estado = 'APROBADO' AND c.total_pagado > 0
    """)).scalar()
    
    print(f"✅ Préstamos aprobados con cuotas pagadas: {prestamos_con_cuotas_pagadas}")
    
    # Resumen de integridad
    print_subsection("Resumen de integridad")
    
    # Cédulas con pagos pero sin préstamos
    cedulas_pagos_sin_prestamos = db.execute(text("""
        SELECT COUNT(DISTINCT p.cedula) as cantidad
        FROM pagos p
        LEFT JOIN prestamos pr ON p.cedula = pr.cedula AND pr.estado = 'APROBADO'
        WHERE p.activo = TRUE AND pr.id IS NULL
    """)).scalar()
    
    # Préstamos aprobados sin cuotas
    prestamos_aprobados_sin_cuotas = db.execute(text("""
        SELECT COUNT(DISTINCT p.id) as cantidad
        FROM prestamos p
        LEFT JOIN cuotas c ON p.id = c.prestamo_id
        WHERE p.estado = 'APROBADO' AND c.id IS NULL
    """)).scalar()
    
    # Cuotas sin préstamo
    cuotas_sin_prestamo_count = db.execute(text("""
        SELECT COUNT(*) as cantidad
        FROM cuotas c
        LEFT JOIN prestamos p ON c.prestamo_id = p.id
        WHERE p.id IS NULL
    """)).scalar()
    
    print(f"\n📋 Resumen de problemas encontrados:")
    print(f"   - Cédulas con pagos pero sin préstamos: {cedulas_pagos_sin_prestamos}")
    print(f"   - Préstamos aprobados sin cuotas: {prestamos_aprobados_sin_cuotas}")
    print(f"   - Cuotas sin préstamo asociado: {cuotas_sin_prestamo_count}")
    
    return {
        'clientes_con_prestamos': clientes_con_prestamos,
        'clientes_sin_prestamos': clientes_sin_prestamos,
        'prestamos_con_pagos': prestamos_con_pagos,
        'prestamos_sin_pagos': prestamos_sin_pagos,
        'cedulas_pagos_sin_prestamos': cedulas_pagos_sin_prestamos,
        'prestamos_aprobados_sin_cuotas': prestamos_aprobados_sin_cuotas,
        'cuotas_sin_prestamo': cuotas_sin_prestamo_count
    }

def main():
    """Función principal"""
    print("\n" + "="*80)
    print("  ANÁLISIS DE INTEGRIDAD DE DATOS")
    print("  Sistema de Préstamos y Pagos")
    print("="*80)
    print(f"\nFecha de análisis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base de datos: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'N/A'}")
    
    # Crear conexión a la base de datos
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Ejecutar análisis
        resultados_clientes = analizar_clientes(db)
        resultados_prestamos = analizar_prestamos(db)
        resultados_pagos = analizar_pagos(db)
        resultados_cuotas = analizar_cuotas(db)
        resultados_relaciones = analizar_relaciones(db)
        
        # Resumen final
        print_section("RESUMEN FINAL")
        
        print("📊 Estadísticas generales:")
        print(f"   - Total clientes: {resultados_clientes['total']}")
        print(f"   - Total préstamos: {resultados_prestamos['total']}")
        print(f"   - Total pagos: {resultados_pagos['total']}")
        print(f"   - Total cuotas: {resultados_cuotas['total']}")
        
        print("\n✅ Aspectos correctos:")
        if resultados_clientes['duplicados_cedula'] == 0:
            print("   ✓ No hay cédulas duplicadas en clientes (correcto)")
        if resultados_prestamos['sin_cuotas'] == 0:
            print("   ✓ Todos los préstamos aprobados tienen cuotas")
        if resultados_prestamos['sin_cliente'] == 0:
            print("   ✓ Todos los préstamos tienen cliente activo asociado")
        if resultados_pagos['no_conciliados'] == 0:
            print("   ✓ Todos los pagos están conciliados")
        if resultados_pagos['sin_prestamos'] == 0:
            print("   ✓ Todos los pagos tienen préstamos aprobados asociados")
        if resultados_cuotas['sin_prestamo'] == 0:
            print("   ✓ Todas las cuotas tienen préstamo asociado")
        
        print("\nℹ️  Notas importantes:")
        print("   - Es NORMAL que una cédula tenga múltiples préstamos (una persona puede tener varios préstamos)")
        print("   - Es NORMAL que una cédula tenga múltiples pagos (una persona puede realizar varios pagos)")
        print("   - NO es normal que haya cédulas duplicadas en la tabla de clientes")
        
        print("\n⚠️  Problemas encontrados:")
        problemas = []
        if resultados_clientes['duplicados_cedula'] > 0:
            problemas.append(f"   ❌ {resultados_clientes['duplicados_cedula']} cédulas duplicadas en clientes (NO deberían existir)")
        if resultados_prestamos['sin_cuotas'] > 0:
            problemas.append(f"   ❌ {resultados_prestamos['sin_cuotas']} préstamos aprobados sin cuotas")
        if resultados_prestamos['cuotas_inconsistentes'] > 0:
            problemas.append(f"   ❌ {resultados_prestamos['cuotas_inconsistentes']} préstamos con número de cuotas inconsistente")
        if resultados_prestamos['sin_cliente'] > 0:
            problemas.append(f"   ❌ {resultados_prestamos['sin_cliente']} préstamos con cédulas sin cliente activo")
        if resultados_pagos['no_conciliados'] > 0:
            problemas.append(f"   ⚠️  {resultados_pagos['no_conciliados']} pagos no conciliados (revisar)")
        if resultados_pagos['sin_prestamos'] > 0:
            problemas.append(f"   ❌ {resultados_pagos['sin_prestamos']} cédulas con pagos pero sin préstamos aprobados")
        if resultados_cuotas['sin_prestamo'] > 0:
            problemas.append(f"   ❌ {resultados_cuotas['sin_prestamo']} cuotas sin préstamo asociado")
        if resultados_cuotas['con_pagos_sin_relacion'] > 0:
            problemas.append(f"   ⚠️  {resultados_cuotas['con_pagos_sin_relacion']} cuotas con pagos pero sin relación directa (revisar)")
        
        if problemas:
            for problema in problemas:
                print(problema)
        else:
            print("   ✓ No se encontraron problemas")
        
        print("\n" + "="*80)
        print("  Análisis completado")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error durante el análisis: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
