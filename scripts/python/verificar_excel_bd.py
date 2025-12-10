#!/usr/bin/env python3
"""
Script para verificar datos del Excel contra la base de datos PostgreSQL.

INSTRUCCIONES:
1. Coloca tu archivo Excel en: scripts/data/datos_excel.xlsx
   (o cambia la ruta en la variable EXCEL_PATH)
2. Asegúrate de que el Excel tenga estas columnas:
   - CLIENTE (o Cliente)
   - CEDULA IDENTIDAD (o Cédula, CEDULA)
   - TOTAL FINANCIAMIENTO (o Total Financiamiento)
   - ABONOS (o Abonos)
   - SALDO DEUDOR (o Saldo Deudor)
   - CUOTAS (o Cuotas)
   - MODALIDAD FINANCIAMIENTO (o Modalidad)
3. Ejecuta: python scripts/python/verificar_excel_bd.py
4. Revisa el reporte generado en: scripts/data/reporte_verificacion_excel.md
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas no está instalado")
    print("   Instala con: pip install pandas openpyxl")
    sys.exit(1)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ============================================
# CONFIGURACIÓN
# ============================================

# Ruta del archivo Excel
EXCEL_PATH = project_root / "scripts" / "data" / "datos_excel.xlsx"

# Ruta del reporte de salida
REPORTE_PATH = project_root / "scripts" / "data" / "reporte_verificacion_excel.md"

# Obtener DATABASE_URL del entorno
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/pagos_db")

# ============================================
# FUNCIONES AUXILIARES
# ============================================

def normalizar_cedula(cedula: str) -> str:
    """Normaliza la cédula eliminando espacios y convirtiendo a mayúsculas"""
    if pd.isna(cedula):
        return ""
    return str(cedula).strip().upper()

def normalizar_texto(texto: str) -> str:
    """Normaliza texto eliminando espacios extra"""
    if pd.isna(texto):
        return ""
    return str(texto).strip()

def normalizar_numero(valor) -> float:
    """Normaliza números, manejando NaN y strings"""
    if pd.isna(valor):
        return 0.0
    try:
        return float(valor)
    except (ValueError, TypeError):
        return 0.0

def encontrar_columna(df: pd.DataFrame, posibles_nombres: List[str]) -> Optional[str]:
    """Encuentra una columna por posibles nombres"""
    for nombre in posibles_nombres:
        for col in df.columns:
            # Convertir col a string por si es un número (índice de columna)
            col_str = str(col)
            if nombre.upper() in col_str.upper():
                return col
    return None

# ============================================
# LEER EXCEL
# ============================================

def leer_excel(ruta: Path) -> pd.DataFrame:
    """Lee el archivo Excel y normaliza las columnas"""
    print(f"[*] Leyendo Excel: {ruta}")
    
    if not ruta.exists():
        print(f"ERROR: El archivo no existe: {ruta}")
        print(f"   Coloca tu Excel en: {ruta}")
        sys.exit(1)
    
    try:
        df = pd.read_excel(ruta)
        print(f"[OK] Excel leido: {len(df)} registros")
        return df
    except Exception as e:
        print(f"ERROR al leer Excel: {e}")
        sys.exit(1)

def normalizar_columnas_excel(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza las columnas del Excel a nombres estándar"""
    # Mapeo de posibles nombres de columnas
    mapeo = {
        'cliente': encontrar_columna(df, ['CLIENTE', 'Cliente', 'NOMBRE', 'Nombre']),
        'cedula': encontrar_columna(df, ['CEDULA IDENTIDAD', 'CEDULA', 'Cédula', 'Cedula', 'CI']),
        'total_financiamiento': encontrar_columna(df, ['TOTAL FINANCIAMIENTO', 'Total Financiamiento', 'TOTAL', 'Total']),
        'abonos': encontrar_columna(df, ['ABONOS', 'Abonos', 'PAGOS', 'Pagos', 'TOTAL PAGADO']),
        'saldo_deudor': encontrar_columna(df, ['SALDO DEUDOR', 'Saldo Deudor', 'SALDO', 'Saldo', 'PENDIENTE']),
        'cuotas': encontrar_columna(df, ['CUOTAS', 'Cuotas', 'NUMERO CUOTAS', 'Número Cuotas']),
        'monto_cuota': encontrar_columna(df, ['MONTO CANCELADO CUOTA', 'Monto Cancelado Cuota', 'MONTO CUOTA', 'Monto Cuota']),
        'modalidad': encontrar_columna(df, ['MODALIDAD FINANCIAMIENTO', 'Modalidad Financiamiento', 'MODALIDAD', 'Modalidad']),
    }
    
    # Verificar que las columnas críticas existen (cuotas es opcional)
    columnas_criticas = ['cliente', 'cedula', 'total_financiamiento', 'abonos', 'saldo_deudor']
    faltantes = [k for k in columnas_criticas if mapeo[k] is None]
    if faltantes:
        print(f"ERROR: Columnas criticas faltantes en el Excel: {', '.join(faltantes)}")
        print(f"   Columnas disponibles: {', '.join([str(c) for c in df.columns[:30]])}")
        sys.exit(1)
    
    # Crear DataFrame normalizado
    df_normalizado = pd.DataFrame()
    df_normalizado['cliente'] = df[mapeo['cliente']].apply(normalizar_texto)
    df_normalizado['cedula'] = df[mapeo['cedula']].apply(normalizar_cedula)
    df_normalizado['total_financiamiento'] = df[mapeo['total_financiamiento']].apply(normalizar_numero)
    df_normalizado['abonos'] = df[mapeo['abonos']].apply(normalizar_numero)
    df_normalizado['saldo_deudor'] = df[mapeo['saldo_deudor']].apply(normalizar_numero)
    
    # Cuotas: calcular desde diferentes fuentes
    # 1. Si existe columna CUOTAS directa, usarla
    # 2. Si existe MONTO CANCELADO CUOTA, calcular: total_financiamiento / monto_cuota
    # 3. Si no, usar None (se calculará desde BD)
    if mapeo['cuotas'] is not None:
        # Usar columna CUOTAS directa
        df_normalizado['cuotas'] = df[mapeo['cuotas']].apply(lambda x: int(normalizar_numero(x)))
        print("[OK] Usando columna 'CUOTAS' directa")
    elif mapeo['monto_cuota'] is not None:
        # Calcular número de cuotas desde MONTO CANCELADO CUOTA
        monto_cuota = df[mapeo['monto_cuota']].apply(normalizar_numero)
        df_normalizado['cuotas'] = (df_normalizado['total_financiamiento'] / monto_cuota).round(0).astype(int)
        print("[OK] Calculando numero de cuotas desde 'MONTO CANCELADO CUOTA' (Total / Monto Cuota)")
    else:
        # No hay forma de calcular cuotas, usar None
        df_normalizado['cuotas'] = pd.Series([None] * len(df))
        print("[!] ADVERTENCIA: No se encontro columna 'CUOTAS' ni 'MONTO CANCELADO CUOTA'. Se calculara desde la BD.")
    
    # Modalidad: usar columna si existe, sino usar None para todas las filas
    if mapeo['modalidad'] is not None:
        df_normalizado['modalidad'] = df[mapeo['modalidad']].apply(normalizar_texto)
    else:
        df_normalizado['modalidad'] = pd.Series([None] * len(df))
    
    print(f"[OK] Columnas normalizadas correctamente")
    return df_normalizado

# ============================================
# CONSULTAR BASE DE DATOS
# ============================================

def crear_conexion_bd():
    """Crea conexión a la base de datos"""
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        return engine
    except Exception as e:
        print(f"ERROR al conectar a la base de datos: {e}")
        print(f"   Verifica tu DATABASE_URL")
        sys.exit(1)

def verificar_cliente(engine, cedula: str) -> Optional[Dict]:
    """Verifica si un cliente existe en la BD"""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, cedula, nombres FROM clientes WHERE cedula = :cedula"),
            {"cedula": cedula}
        )
        row = result.fetchone()
        if row:
            return {
                "id": row[0],
                "cedula": row[1],
                "nombres": row[2]
            }
        return None

def verificar_prestamo(engine, cedula: str, total_financiamiento: float) -> Optional[Dict]:
    """Verifica si un préstamo existe y obtiene sus datos"""
    with engine.connect() as conn:
        # Buscar préstamo por cédula y total_financiamiento (con tolerancia)
        result = conn.execute(
            text("""
                SELECT 
                    p.id,
                    p.cedula,
                    p.total_financiamiento,
                    p.numero_cuotas,
                    p.modalidad_pago,
                    p.estado,
                    COALESCE(SUM(c.total_pagado), 0) AS abonos_bd,
                    COALESCE(SUM(c.monto_cuota - c.total_pagado), 0) AS saldo_deudor_bd,
                    COUNT(c.id) AS cuotas_generadas
                FROM prestamos p
                LEFT JOIN cuotas c ON p.id = c.prestamo_id
                WHERE p.cedula = :cedula
                  AND ABS(p.total_financiamiento - :total) < 10
                GROUP BY p.id, p.cedula, p.total_financiamiento, p.numero_cuotas, p.modalidad_pago, p.estado
                ORDER BY ABS(p.total_financiamiento - :total)
                LIMIT 1
            """),
            {"cedula": cedula, "total": total_financiamiento}
        )
        row = result.fetchone()
        if row:
            return {
                "id": row[0],
                "cedula": row[1],
                "total_financiamiento": float(row[2]),
                "numero_cuotas": row[3],
                "modalidad_pago": row[4],
                "estado": row[5],
                "abonos_bd": float(row[6]),
                "saldo_deudor_bd": float(row[7]),
                "cuotas_generadas": row[8]
            }
        return None

# ============================================
# COMPARAR DATOS
# ============================================

def comparar_registro(registro_excel: Dict, cliente_bd: Optional[Dict], prestamo_bd: Optional[Dict]) -> Dict:
    """Compara un registro del Excel con los datos de la BD"""
    resultado = {
        "cedula": registro_excel["cedula"],
        "cliente_excel": registro_excel["cliente"],
        "cliente_existe": cliente_bd is not None,
        "cliente_id": cliente_bd["id"] if cliente_bd else None,
        "cliente_nombres_bd": cliente_bd["nombres"] if cliente_bd else None,
        "prestamo_existe": prestamo_bd is not None,
        "prestamo_id": prestamo_bd["id"] if prestamo_bd else None,
        "problemas": []
    }
    
    # Verificar cliente
    if not cliente_bd:
        resultado["problemas"].append("CLIENTE NO EXISTE")
    
    # Verificar préstamo
    if not prestamo_bd:
        resultado["problemas"].append("PRESTAMO NO EXISTE")
        return resultado
    
    # Comparar total financiamiento
    if abs(prestamo_bd["total_financiamiento"] - registro_excel["total_financiamiento"]) > 0.01:
        resultado["problemas"].append(
            f"TOTAL FINANCIAMIENTO DIFERENTE: Excel={registro_excel['total_financiamiento']}, BD={prestamo_bd['total_financiamiento']}"
        )
    
    # Comparar abonos
    if abs(prestamo_bd["abonos_bd"] - registro_excel["abonos"]) > 0.01:
        resultado["problemas"].append(
            f"ABONOS DIFERENTES: Excel={registro_excel['abonos']}, BD={prestamo_bd['abonos_bd']}"
        )
    
    # Comparar saldo deudor (tolerancia de 5.00)
    if abs(prestamo_bd["saldo_deudor_bd"] - registro_excel["saldo_deudor"]) > 5.00:
        resultado["problemas"].append(
            f"SALDO DEUDOR DIFERENTE: Excel={registro_excel['saldo_deudor']}, BD={prestamo_bd['saldo_deudor_bd']}"
        )
    
    # Comparar número de cuotas (solo si está en el Excel)
    if registro_excel["cuotas"] is not None and prestamo_bd["numero_cuotas"] != registro_excel["cuotas"]:
        resultado["problemas"].append(
            f"NUMERO CUOTAS DIFERENTE: Excel={registro_excel['cuotas']}, BD={prestamo_bd['numero_cuotas']}"
        )
    
    # Comparar modalidad (solo si está en el Excel)
    if prestamo_bd["modalidad_pago"] and registro_excel["modalidad"]:
        if prestamo_bd["modalidad_pago"].upper() != registro_excel["modalidad"].upper():
            resultado["problemas"].append(
                f"MODALIDAD DIFERENTE: Excel={registro_excel['modalidad']}, BD={prestamo_bd['modalidad_pago']}"
            )
    
    # Agregar datos de BD al resultado
    resultado.update({
        "total_financiamiento_bd": prestamo_bd["total_financiamiento"],
        "abonos_bd": prestamo_bd["abonos_bd"],
        "saldo_deudor_bd": prestamo_bd["saldo_deudor_bd"],
        "cuotas_bd": prestamo_bd["numero_cuotas"],
        "cuotas_excel": registro_excel.get("cuotas"),
        "modalidad_bd": prestamo_bd["modalidad_pago"],
        "modalidad_excel": registro_excel.get("modalidad"),
        "estado_prestamo": prestamo_bd["estado"]
    })
    
    return resultado

# ============================================
# GENERAR REPORTE
# ============================================

def generar_reporte(resultados: List[Dict], ruta: Path):
    """Genera un reporte markdown con los resultados"""
    total = len(resultados)
    clientes_existentes = sum(1 for r in resultados if r["cliente_existe"])
    prestamos_existentes = sum(1 for r in resultados if r["prestamo_existe"])
    sin_problemas = sum(1 for r in resultados if len(r["problemas"]) == 0)
    con_problemas = total - sin_problemas
    
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write("# Reporte de Verificacion: Excel vs Base de Datos\n\n")
        f.write(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Resumen
        f.write("## Resumen General\n\n")
        f.write(f"- **Total de registros en Excel:** {total}\n")
        f.write(f"- **Clientes existentes en BD:** {clientes_existentes} ({clientes_existentes*100/total:.1f}%)\n")
        f.write(f"- **Préstamos existentes en BD:** {prestamos_existentes} ({prestamos_existentes*100/total:.1f}%)\n")
        f.write(f"- **Registros sin problemas:** {sin_problemas} ({sin_problemas*100/total:.1f}%)\n")
        f.write(f"- **Registros con problemas:** {con_problemas} ({con_problemas*100/total:.1f}%)\n\n")
        
        # Registros con problemas
        if con_problemas > 0:
            f.write("## [!] Registros con Problemas\n\n")
            f.write("| Cédula | Cliente (Excel) | Problemas |\n")
            f.write("|--------|-----------------|-----------|\n")
            for r in resultados:
                if len(r["problemas"]) > 0:
                    problemas_str = "; ".join(r["problemas"])
                    f.write(f"| {r['cedula']} | {r['cliente_excel']} | {problemas_str} |\n")
            f.write("\n")
        
        # Detalle completo
        f.write("## Detalle Completo\n\n")
        f.write("| Cédula | Cliente | Cliente BD | Préstamo BD | Total Excel | Total BD | Abonos Excel | Abonos BD | Saldo Excel | Saldo BD | Estado |\n")
        f.write("|--------|---------|------------|-------------|-------------|----------|--------------|-----------|-------------|----------|--------|\n")
        
        for r in resultados:
            cliente_bd = "[OK]" if r["cliente_existe"] else "[NO]"
            prestamo_bd = f"[OK] ID:{r['prestamo_id']}" if r["prestamo_existe"] else "[NO]"
            estado = "[OK] OK" if len(r["problemas"]) == 0 else "[!] PROBLEMAS"
            
            f.write(f"| {r['cedula']} | {r['cliente_excel']} | {cliente_bd} | {prestamo_bd} | "
                   f"{r.get('total_financiamiento', 'N/A')} | {r.get('total_financiamiento_bd', 'N/A')} | "
                   f"{r.get('abonos', 'N/A')} | {r.get('abonos_bd', 'N/A')} | "
                   f"{r.get('saldo_deudor', 'N/A')} | {r.get('saldo_deudor_bd', 'N/A')} | {estado} |\n")
    
    print(f"[OK] Reporte generado: {ruta}")

# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

def main():
    """Función principal"""
    print("=" * 70)
    print("VERIFICACIÓN: Excel vs Base de Datos")
    print("=" * 70)
    print()
    
    # Leer Excel
    df = leer_excel(EXCEL_PATH)
    df_normalizado = normalizar_columnas_excel(df)
    
    # Conectar a BD
    print("[*] Conectando a la base de datos...")
    engine = crear_conexion_bd()
    print("[OK] Conexion establecida")
    print()
    
    # Verificar cada registro
    print("[*] Verificando registros...")
    resultados = []
    
    for idx, row in df_normalizado.iterrows():
        if idx % 100 == 0:
            print(f"   Procesando registro {idx + 1}/{len(df_normalizado)}...")
        
        registro = row.to_dict()
        
        # Verificar cliente
        cliente_bd = verificar_cliente(engine, registro["cedula"])
        
        # Verificar préstamo
        prestamo_bd = verificar_prestamo(engine, registro["cedula"], registro["total_financiamiento"])
        
        # Comparar
        resultado = comparar_registro(registro, cliente_bd, prestamo_bd)
        resultados.append(resultado)
    
    print(f"[OK] Verificacion completada: {len(resultados)} registros procesados")
    print()
    
    # Generar reporte
    print("[*] Generando reporte...")
    generar_reporte(resultados, REPORTE_PATH)
    
    # Resumen en consola
    total = len(resultados)
    sin_problemas = sum(1 for r in resultados if len(r["problemas"]) == 0)
    con_problemas = total - sin_problemas
    
    print()
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"Total registros: {total}")
    print(f"[OK] Sin problemas: {sin_problemas} ({sin_problemas*100/total:.1f}%)")
    print(f"[!] Con problemas: {con_problemas} ({con_problemas*100/total:.1f}%)")
    print()
    print(f"📄 Reporte completo: {REPORTE_PATH}")
    print("=" * 70)

if __name__ == "__main__":
    main()

