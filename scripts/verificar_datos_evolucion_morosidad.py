#!/usr/bin/env python3
"""
Script para verificar los datos del gráfico "Evolución de Morosidad"
Muestra la query SQL exacta y permite ejecutarla directamente en la base de datos
"""

import sys
from datetime import date, timedelta
from pathlib import Path

# Agregar el directorio raíz al path para importar módulos del backend
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

try:
    from sqlalchemy import create_engine, text
    from app.core.config import settings
    from app.db.session import get_db
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("💡 Asegúrate de estar en el directorio raíz del proyecto")
    sys.exit(1)


def construir_query_sql(meses: int = 6, analista: str = None, concesionario: str = None, modelo: str = None):
    """
    Construye la query SQL exacta que usa el endpoint
    """
    hoy = date.today()
    
    # Calcular fecha inicio (hace N meses)
    año_inicio = hoy.year
    mes_inicio = hoy.month - meses + 1
    if mes_inicio <= 0:
        año_inicio -= 1
        mes_inicio += 12
    fecha_inicio_query = date(año_inicio, mes_inicio, 1)
    
    # Construir filtros base
    filtros_base = [
        "p.estado = 'APROBADO'",
        f"c.fecha_vencimiento >= '{fecha_inicio_query}'",
        f"c.fecha_vencimiento < '{hoy}'",
        "c.estado != 'PAGADO'",
    ]
    
    # Aplicar filtros opcionales
    if analista:
        filtros_base.append(f"(p.analista = '{analista}' OR p.producto_financiero = '{analista}')")
    if concesionario:
        filtros_base.append(f"p.concesionario = '{concesionario}'")
    if modelo:
        filtros_base.append(f"(p.producto = '{modelo}' OR p.modelo_vehiculo = '{modelo}')")
    
    where_clause = " AND ".join(filtros_base)
    
    query_sql = f"""
SELECT 
    EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
    EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes,
    COALESCE(SUM(c.monto_cuota), 0) as morosidad,
    COUNT(c.id) as cantidad_cuotas
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE {where_clause}
GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
ORDER BY año, mes;
"""
    
    return query_sql, fecha_inicio_query, hoy


def ejecutar_query(query_sql: str):
    """
    Ejecuta la query en la base de datos
    """
    try:
        # Crear conexión a la base de datos
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as conn:
            result = conn.execute(text(query_sql))
            rows = result.fetchall()
            
            return rows
    except Exception as e:
        print(f"❌ Error ejecutando query: {e}")
        return None


def formatear_resultados(rows, fecha_inicio: date, fecha_fin: date):
    """
    Formatea los resultados igual que el endpoint
    """
    nombres_meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    
    # Crear diccionario con los resultados
    morosidad_por_mes = {(int(row[0]), int(row[1])): float(row[2] or 0) for row in rows}
    
    # Generar datos mensuales (incluyendo meses sin datos)
    meses_data = []
    current_date = fecha_inicio
    
    while current_date <= fecha_fin:
        año_mes = current_date.year
        num_mes = current_date.month
        morosidad_mes = morosidad_por_mes.get((año_mes, num_mes), 0.0)
        
        meses_data.append({
            "mes": f"{nombres_meses[num_mes - 1]} {año_mes}",
            "morosidad": morosidad_mes,
        })
        
        # Avanzar al siguiente mes
        if num_mes == 12:
            año_mes += 1
            num_mes = 1
        else:
            num_mes += 1
        current_date = date(año_mes, num_mes, 1)
    
    return meses_data


def main():
    print("=" * 80)
    print("📊 VERIFICACIÓN DE DATOS - GRÁFICO 'EVOLUCIÓN DE MOROSIDAD'")
    print("=" * 80)
    print()
    
    # Parámetros (puedes modificar estos)
    meses = 6
    analista = None  # Ejemplo: "Juan Pérez"
    concesionario = None  # Ejemplo: "Toyota"
    modelo = None  # Ejemplo: "Corolla"
    
    print(f"🔍 Parámetros de búsqueda:")
    print(f"   - Meses: {meses}")
    print(f"   - Analista: {analista or 'Todos'}")
    print(f"   - Concesionario: {concesionario or 'Todos'}")
    print(f"   - Modelo: {modelo or 'Todos'}")
    print()
    
    # Construir query
    query_sql, fecha_inicio, fecha_fin = construir_query_sql(meses, analista, concesionario, modelo)
    
    print("=" * 80)
    print("📝 QUERY SQL EJECUTADA:")
    print("=" * 80)
    print(query_sql)
    print()
    
    # Ejecutar query
    print("🔄 Ejecutando query en la base de datos...")
    rows = ejecutar_query(query_sql)
    
    if rows is None:
        print("❌ No se pudo ejecutar la query")
        return
    
    print(f"✅ Query ejecutada exitosamente. {len(rows)} meses con datos encontrados.")
    print()
    
    # Mostrar resultados raw
    print("=" * 80)
    print("📊 RESULTADOS RAW (Base de Datos):")
    print("=" * 80)
    print(f"{'Año':<6} {'Mes':<6} {'Morosidad':<15} {'Cantidad Cuotas':<20}")
    print("-" * 80)
    for row in rows:
        año, mes, morosidad, cantidad = row
        print(f"{año:<6} {mes:<6} ${morosidad:>12,.2f} {cantidad:>20}")
    print()
    
    # Formatear resultados como el endpoint
    meses_data = formatear_resultados(rows, fecha_inicio, fecha_fin)
    
    print("=" * 80)
    print("📊 RESULTADOS FORMATEADOS (Como el endpoint):")
    print("=" * 80)
    print(f"{'Mes':<15} {'Morosidad':<15}")
    print("-" * 80)
    for mes_data in meses_data:
        print(f"{mes_data['mes']:<15} ${mes_data['morosidad']:>12,.2f}")
    print()
    
    # Resumen
    total_morosidad = sum(m['morosidad'] for m in meses_data)
    promedio_morosidad = total_morosidad / len(meses_data) if meses_data else 0
    max_morosidad = max(m['morosidad'] for m in meses_data) if meses_data else 0
    min_morosidad = min(m['morosidad'] for m in meses_data) if meses_data else 0
    
    print("=" * 80)
    print("📈 RESUMEN ESTADÍSTICO:")
    print("=" * 80)
    print(f"   - Total de meses analizados: {len(meses_data)}")
    print(f"   - Morosidad total acumulada: ${total_morosidad:,.2f}")
    print(f"   - Promedio mensual: ${promedio_morosidad:,.2f}")
    print(f"   - Máximo mensual: ${max_morosidad:,.2f}")
    print(f"   - Mínimo mensual: ${min_morosidad:,.2f}")
    print()
    
    # JSON Response (como el endpoint)
    print("=" * 80)
    print("📦 JSON RESPONSE (Como el endpoint retorna):")
    print("=" * 80)
    import json
    response_json = {"meses": meses_data}
    print(json.dumps(response_json, indent=2, ensure_ascii=False))
    print()


if __name__ == "__main__":
    main()

