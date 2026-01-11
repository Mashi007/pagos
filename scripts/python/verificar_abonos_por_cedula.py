#!/usr/bin/env python3
"""
Script para verificar el total de abonos (cantidad total pagada) por cédula comparando:
- Datos de la BD: suma de cuotas.total_pagado agrupado por cédula
- Tabla abono_2026: columna abonos (integer) que contiene el total pagado por cada cédula

INSTRUCCIONES:
1. Ejecuta: python scripts/python/verificar_abonos_por_cedula.py
2. Revisa el reporte generado en: scripts/data/reporte_abonos_por_cedula.md

NOTA: La columna 'abonos' en abono_2026 representa la cantidad total pagada por cada cédula.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.db.session import SessionLocal

# ============================================
# CONFIGURACIÓN
# ============================================

# Ruta del reporte de salida
REPORTE_PATH = project_root / "scripts" / "data" / "reporte_abonos_por_cedula.md"

# ============================================
# FUNCIONES AUXILIARES
# ============================================

def verificar_tabla_existe(db, nombre_tabla: str) -> bool:
    """Verifica si una tabla existe en la base de datos"""
    try:
        resultado = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = :nombre_tabla
            )
        """), {"nombre_tabla": nombre_tabla})
        return resultado.scalar()
    except Exception as e:
        print(f"⚠️ Error al verificar tabla {nombre_tabla}: {e}")
        return False

def obtener_estructura_tabla(db, nombre_tabla: str) -> List[Dict]:
    """Obtiene la estructura de una tabla"""
    try:
        resultado = db.execute(text("""
            SELECT 
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' 
            AND table_name = :nombre_tabla
            ORDER BY ordinal_position
        """), {"nombre_tabla": nombre_tabla})
        
        columnas = []
        for row in resultado:
            columnas.append({
                "nombre": row[0],
                "tipo": row[1],
                "nullable": row[2]
            })
        return columnas
    except Exception as e:
        print(f"⚠️ Error al obtener estructura de {nombre_tabla}: {e}")
        return []

# ============================================
# OBTENER ABONOS DESDE BD
# ============================================

def obtener_abonos_desde_cuotas(db) -> Dict[str, Decimal]:
    """
    Calcula el total de abonos (cantidad total pagada) por cédula desde la tabla cuotas.
    Suma total_pagado agrupado por cédula del préstamo.
    """
    print("[*] Calculando abonos desde tabla cuotas...")
    
    try:
        resultado = db.execute(text("""
            SELECT 
                p.cedula,
                COALESCE(SUM(c.total_pagado), 0) AS total_abonos
            FROM prestamos p
            LEFT JOIN cuotas c ON p.id = c.prestamo_id
            WHERE p.cedula IS NOT NULL
              AND p.cedula != ''
            GROUP BY p.cedula
            ORDER BY p.cedula
        """))
        
        abonos_por_cedula = {}
        total_registros = 0
        
        for row in resultado:
            cedula = str(row[0]).strip().upper()
            total_abonos = Decimal(str(row[1])) if row[1] else Decimal("0")
            
            if cedula:
                abonos_por_cedula[cedula] = total_abonos
                total_registros += 1
        
        print(f"[OK] Abonos calculados desde cuotas: {total_registros} cédulas")
        return abonos_por_cedula
        
    except Exception as e:
        print(f"❌ Error al calcular abonos desde cuotas: {e}")
        import traceback
        traceback.print_exc()
        return {}

def obtener_abonos_desde_pagos(db) -> Dict[str, Decimal]:
    """
    Calcula el total de abonos por cédula desde la tabla pagos.
    Suma monto_pagado agrupado por cédula.
    """
    print("[*] Calculando abonos desde tabla pagos...")
    
    try:
        resultado = db.execute(text("""
            SELECT 
                cedula,
                COALESCE(SUM(monto_pagado), 0) AS total_abonos
            FROM pagos
            WHERE cedula IS NOT NULL
              AND cedula != ''
              AND monto_pagado IS NOT NULL
              AND monto_pagado > 0
              AND activo = TRUE
            GROUP BY cedula
            ORDER BY cedula
        """))
        
        abonos_por_cedula = {}
        total_registros = 0
        
        for row in resultado:
            cedula = str(row[0]).strip().upper()
            total_abonos = Decimal(str(row[1])) if row[1] else Decimal("0")
            
            if cedula:
                abonos_por_cedula[cedula] = total_abonos
                total_registros += 1
        
        print(f"[OK] Abonos calculados desde pagos: {total_registros} cédulas")
        return abonos_por_cedula
        
    except Exception as e:
        print(f"❌ Error al calcular abonos desde pagos: {e}")
        import traceback
        traceback.print_exc()
        return {}

# ============================================
# OBTENER ABONOS DESDE TABLA abono_2026
# ============================================

def obtener_abonos_desde_tabla_referencia(db, nombre_tabla: str) -> Dict[str, Decimal]:
    """
    Obtiene los abonos (cantidad total pagada) desde la tabla de referencia (abono_2026).
    Usa la columna 'abonos' (integer) que contiene el total pagado por cada cédula.
    """
    print(f"[*] Obteniendo abonos desde tabla {nombre_tabla}...")
    
    # Primero obtener la estructura de la tabla
    columnas = obtener_estructura_tabla(db, nombre_tabla)
    
    if not columnas:
        print(f"⚠️ No se pudo obtener estructura de {nombre_tabla}")
        return {}
    
    print(f"[OK] Estructura de {nombre_tabla}:")
    for col in columnas:
        print(f"   - {col['nombre']} ({col['tipo']})")
    
    # Buscar columna de cédula
    columna_cedula = None
    for col in columnas:
        if 'cedula' in col['nombre'].lower() or 'ci' in col['nombre'].lower():
            columna_cedula = col['nombre']
            break
    
    if not columna_cedula:
        print(f"⚠️ No se encontró columna de cédula en {nombre_tabla}")
        return {}
    
    # Buscar columna de abonos - usar específicamente 'abonos' (integer)
    # Esta columna contiene la cantidad total pagada por cada cédula
    columna_abonos = None
    
    # Buscar primero la columna 'abonos' específicamente (total pagado por cédula)
    for col in columnas:
        if col['nombre'].lower() == 'abonos':
            columna_abonos = col['nombre']
            break
    
    # Si no se encuentra 'abonos', buscar otras opciones
    if not columna_abonos:
        posibles_nombres = ['abono', 'total', 'total_pagado', 'monto']
        for col in columnas:
            nombre_lower = col['nombre'].lower()
            if any(nombre in nombre_lower for nombre in posibles_nombres):
                columna_abonos = col['nombre']
                break
    
    if not columna_abonos:
        print(f"[!] No se encontro columna de abonos en {nombre_tabla}")
        print(f"   Columnas disponibles: {[c['nombre'] for c in columnas]}")
        return {}
    
    print(f"[OK] Usando columnas: cedula={columna_cedula}, abonos={columna_abonos} (total pagado por cedula)")
    
    # Obtener datos
    try:
        # Verificar si hay datos no nulos en la columna de abonos
        check_query = f"""
            SELECT COUNT(*) 
            FROM {nombre_tabla}
            WHERE {columna_cedula} IS NOT NULL
              AND {columna_cedula} != ''
              AND {columna_abonos} IS NOT NULL
              AND {columna_abonos} != 0
        """
        resultado_check = db.execute(text(check_query))
        registros_con_abonos = resultado_check.scalar()
        
        print(f"[*] Registros con abonos no nulos: {registros_con_abonos}")
        
        # Convertir integer a numeric para la suma si es necesario
        # Si la columna es integer, convertirla a numeric para mantener precisión
        tipo_columna = next((c['tipo'] for c in columnas if c['nombre'] == columna_abonos), None)
        
        if tipo_columna == 'integer':
            # Convertir integer a numeric para la suma
            columna_abonos_cast = f"{columna_abonos}::numeric"
        else:
            columna_abonos_cast = columna_abonos
        
        query = f"""
            SELECT 
                {columna_cedula} AS cedula,
                COALESCE(SUM({columna_abonos_cast}), 0) AS total_abonos
            FROM {nombre_tabla}
            WHERE {columna_cedula} IS NOT NULL
              AND {columna_cedula} != ''
            GROUP BY {columna_cedula}
            ORDER BY {columna_cedula}
        """
        
        resultado = db.execute(text(query))
        
        abonos_por_cedula = {}
        total_registros = 0
        
        for row in resultado:
            cedula = str(row[0]).strip().upper()
            total_abonos = Decimal(str(row[1])) if row[1] else Decimal("0")
            
            if cedula:
                abonos_por_cedula[cedula] = total_abonos
                total_registros += 1
        
        print(f"[OK] Abonos obtenidos desde {nombre_tabla}: {total_registros} cédulas")
        return abonos_por_cedula
        
    except Exception as e:
        print(f"❌ Error al obtener abonos desde {nombre_tabla}: {e}")
        import traceback
        traceback.print_exc()
        return {}

# ============================================
# COMPARAR DATOS
# ============================================

def comparar_abonos(
    abonos_bd: Dict[str, Decimal],
    abonos_tabla: Dict[str, Decimal],
    tolerancia: Decimal = Decimal("0.01")
) -> List[Dict]:
    """
    Compara los abonos de la BD con los de la tabla de referencia.
    Retorna lista de discrepancias.
    """
    print("[*] Comparando abonos...")
    
    todas_cedulas = set(abonos_bd.keys()) | set(abonos_tabla.keys())
    discrepancias = []
    coincidencias = 0
    
    for cedula in todas_cedulas:
        abono_bd = abonos_bd.get(cedula, Decimal("0"))
        abono_tabla = abonos_tabla.get(cedula, Decimal("0"))
        
        diferencia = abs(abono_bd - abono_tabla)
        
        if diferencia > tolerancia:
            discrepancias.append({
                "cedula": cedula,
                "abono_bd": float(abono_bd),
                "abono_tabla": float(abono_tabla),
                "diferencia": float(diferencia),
                "solo_en_bd": cedula not in abonos_tabla,
                "solo_en_tabla": cedula not in abonos_bd
            })
        else:
            coincidencias += 1
    
    print(f"[OK] Comparación completada:")
    print(f"   - Coincidencias: {coincidencias}")
    print(f"   - Discrepancias: {len(discrepancias)}")
    
    return discrepancias

# ============================================
# GENERAR REPORTE
# ============================================

def generar_reporte(
    abonos_bd: Dict[str, Decimal],
    abonos_tabla: Dict[str, Decimal],
    discrepancias: List[Dict],
    nombre_tabla: str,
    ruta: Path
):
    """Genera un reporte markdown con los resultados"""
    
    total_cedulas_bd = len(abonos_bd)
    total_cedulas_tabla = len(abonos_tabla)
    total_coincidencias = len(abonos_bd) - len(discrepancias)
    
    total_abonos_bd = sum(abonos_bd.values())
    total_abonos_tabla = sum(abonos_tabla.values())
    
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write("# Reporte de Verificación: Abonos por Cédula\n\n")
        f.write(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Resumen
        f.write("## Resumen General\n\n")
        f.write(f"- **Total cédulas en BD:** {total_cedulas_bd:,}\n")
        f.write(f"- **Total cédulas en {nombre_tabla}:** {total_cedulas_tabla:,}\n")
        f.write(f"- **Total abonos en BD:** ${total_abonos_bd:,.2f}\n")
        f.write(f"- **Total abonos en {nombre_tabla}:** ${total_abonos_tabla:,.2f}\n")
        f.write(f"- **Cédulas con coincidencias:** {total_coincidencias:,}\n")
        f.write(f"- **Cédulas con discrepancias:** {len(discrepancias):,}\n\n")
        
        # Discrepancias
        if discrepancias:
            f.write("## [!] Discrepancias Encontradas\n\n")
            f.write("| Cédula | Abono BD | Abono Tabla | Diferencia | Observación |\n")
            f.write("|--------|----------|-------------|------------|-------------|\n")
            
            for disc in discrepancias:
                observacion = ""
                if disc["solo_en_bd"]:
                    observacion = "Solo en BD"
                elif disc["solo_en_tabla"]:
                    observacion = f"Solo en {nombre_tabla}"
                else:
                    observacion = "Valores diferentes"
                
                f.write(f"| {disc['cedula']} | ${disc['abono_bd']:,.2f} | "
                       f"${disc['abono_tabla']:,.2f} | ${disc['diferencia']:,.2f} | {observacion} |\n")
            f.write("\n")
        else:
            f.write("## ✅ Sin Discrepancias\n\n")
            f.write("Todos los abonos coinciden entre la BD y la tabla de referencia.\n\n")
        
        # Estadísticas adicionales
        f.write("## Estadísticas Adicionales\n\n")
        
        if discrepancias:
            diferencias = [d["diferencia"] for d in discrepancias]
            max_diferencia = max(diferencias)
            min_diferencia = min(diferencias)
            promedio_diferencia = sum(diferencias) / len(diferencias)
            
            f.write(f"- **Diferencia máxima:** ${max_diferencia:,.2f}\n")
            f.write(f"- **Diferencia mínima:** ${min_diferencia:,.2f}\n")
            f.write(f"- **Diferencia promedio:** ${promedio_diferencia:,.2f}\n\n")
    
    print(f"[OK] Reporte generado: {ruta}")

# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

def main():
    """Función principal"""
    print("=" * 70)
    print("VERIFICACIÓN: Abonos por Cédula")
    print("=" * 70)
    print()
    
    # Conectar a BD
    print("[*] Conectando a la base de datos...")
    db = SessionLocal()
    
    try:
        # Verificar si existe la tabla abono_2026
        nombre_tabla = "abono_2026"
        tabla_existe = verificar_tabla_existe(db, nombre_tabla)
        
        if not tabla_existe:
            print(f"⚠️ La tabla {nombre_tabla} no existe en la base de datos")
            print(f"   Buscando tablas similares...")
            
            # Buscar tablas que contengan 'abono' o '2026'
            resultado = db.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND (table_name ILIKE '%abono%' OR table_name ILIKE '%2026%')
                ORDER BY table_name
            """))
            
            tablas_similares = [row[0] for row in resultado]
            
            if tablas_similares:
                print(f"   Tablas encontradas: {', '.join(tablas_similares)}")
                if len(tablas_similares) == 1:
                    nombre_tabla = tablas_similares[0]
                    print(f"   Usando tabla: {nombre_tabla}")
                else:
                    print(f"   Por favor, especifica qué tabla usar")
                    db.close()
                    return
            else:
                print(f"   No se encontraron tablas similares")
                print(f"   Continuando solo con verificación de BD...")
                nombre_tabla = None
        
        # Obtener abonos desde BD (cuotas)
        abonos_bd_cuotas = obtener_abonos_desde_cuotas(db)
        
        # Obtener abonos desde BD (pagos) - como referencia alternativa
        abonos_bd_pagos = obtener_abonos_desde_pagos(db)
        
        # Usar abonos desde cuotas como principal
        abonos_bd = abonos_bd_cuotas
        
        # Obtener abonos desde tabla de referencia si existe
        abonos_tabla = {}
        if nombre_tabla:
            abonos_tabla = obtener_abonos_desde_tabla_referencia(db, nombre_tabla)
        
        # Comparar si hay tabla de referencia
        discrepancias = []
        if abonos_tabla:
            discrepancias = comparar_abonos(abonos_bd, abonos_tabla)
            
            # Generar reporte
            print("[*] Generando reporte...")
            generar_reporte(abonos_bd, abonos_tabla, discrepancias, nombre_tabla, REPORTE_PATH)
        else:
            # Solo generar reporte con datos de BD
            print("[*] Generando reporte solo con datos de BD...")
            with open(REPORTE_PATH, 'w', encoding='utf-8') as f:
                f.write("# Reporte de Verificación: Abonos por Cédula\n\n")
                f.write(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("## Resumen\n\n")
                f.write(f"- **Total cédulas:** {len(abonos_bd):,}\n")
                f.write(f"- **Total abonos:** ${sum(abonos_bd.values()):,.2f}\n\n")
                f.write("## Abonos por Cédula (desde cuotas.total_pagado)\n\n")
                f.write("| Cédula | Total Abonos |\n")
                f.write("|--------|-------------|\n")
                
                for cedula, abono in sorted(abonos_bd.items()):
                    f.write(f"| {cedula} | ${float(abono):,.2f} |\n")
        
        # Resumen en consola
        print()
        print("=" * 70)
        print("RESUMEN")
        print("=" * 70)
        print(f"Total cédulas en BD: {len(abonos_bd):,}")
        print(f"Total abonos en BD: ${sum(abonos_bd.values()):,.2f}")
        
        if abonos_tabla:
            print(f"Total cédulas en {nombre_tabla}: {len(abonos_tabla):,}")
            print(f"Total abonos en {nombre_tabla}: ${sum(abonos_tabla.values()):,.2f}")
            print(f"Discrepancias encontradas: {len(discrepancias)}")
        
        print()
        print(f"Reporte completo: {REPORTE_PATH}")
        print("=" * 70)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
