"""
Script para sincronizar schemas Pydantic con modelos ORM
FASE 2.2: Actualizar schemas Pydantic
"""

import re
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict

PROYECTO_ROOT = Path(__file__).parent.parent.parent
BACKEND_MODELS = PROYECTO_ROOT / "backend" / "app" / "models"
BACKEND_SCHEMAS = PROYECTO_ROOT / "backend" / "app" / "schemas"

# Campos calculados conocidos (no deben estar en ORM)
CAMPOS_CALCULADOS = {
    'amortizacion': {
        'fecha_inicio', 'tasa_mora_diaria', 'monto_financiado', 'numero_cuotas',
        'cuotas_pendientes', 'cuotas', 'total_mora', 'fecha_calculo', 'cuotas_actualizadas',
        'cuotas_vencidas', 'monto_pago', 'total_mora_calculada', 'proximas_cuotas',
        'mensaje', 'resumen', 'cuotas_pagadas', 'tasa_interes', 'nuevo_saldo_pendiente',
        'cuotas_afectadas', 'tipo_amortizacion', 'esta_vencida', 'monto_pendiente_total',
        'porcentaje_pagado'
    },
    'analista': {'total', 'pages', 'page', 'size', 'items'},  # Paginación
    'aprobacion': {'monto', 'tipo', 'descripcion'},  # Campos calculados
    'cliente': {'total_prestamos', 'total_pagos', 'saldo_pendiente', 'monto_total_prestamos'},
    'pago': {'cuotas'},  # Relación serializada
    'prestamo': {'cuotas', 'total_pagado', 'saldo_pendiente', 'proxima_cuota'},
    'user': {'total', 'pages', 'page', 'size', 'items'},  # Paginación
}

# Mapeo de tablas a modelos
MAPEO_TABLAS_MODELOS = {
    'clientes': 'cliente',
    'cuotas': 'amortizacion',
    'pagos': 'pago',
    'prestamos': 'prestamo',
    'users': 'user',
    'notificaciones': 'notificacion',
}


def obtener_columnas_orm(archivo_path: Path) -> Set[str]:
    """Obtiene columnas de un modelo ORM"""
    columnas = set()
    
    try:
        with open(archivo_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Buscar patrones: nombre_columna = Column(...)
        patron = r'(\w+)\s*=\s*Column\s*\('
        matches = re.findall(patron, contenido)
        columnas.update(matches)
        
    except Exception as e:
        print(f"Error leyendo modelo {archivo_path}: {e}")
    
    return columnas


def obtener_campos_schema(archivo_path: Path) -> Set[str]:
    """Obtiene campos de un schema Pydantic"""
    campos = set()
    
    try:
        with open(archivo_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Buscar patrones: nombre_campo: tipo = Field(...) o nombre_campo: tipo
        patrones = [
            r'(\w+)\s*:\s*\w+.*?=.*?Field',  # Con Field
            r'(\w+)\s*:\s*\w+[^=]*$',  # Sin Field (en líneas simples)
        ]
        
        for patron in patrones:
            matches = re.findall(patron, contenido, re.MULTILINE)
            campos.update(matches)
        
        # También buscar en class definitions
        clases = re.findall(r'class\s+(\w+)\(.*?\):', contenido)
        
    except Exception as e:
        print(f"Error leyendo schema {archivo_path}: {e}")
    
    return campos


def analizar_discrepancias_schemas():
    """Analiza discrepancias entre ORM y Schemas"""
    resultados = {
        'campos_faltantes_en_schemas': [],
        'campos_calculados_documentados': [],
        'campos_orm_sin_schema': [],
    }
    
    for tabla_bd, modelo_nombre in MAPEO_TABLAS_MODELOS.items():
        archivo_modelo = BACKEND_MODELS / f"{modelo_nombre}.py"
        archivo_schema = BACKEND_SCHEMAS / f"{modelo_nombre}.py"
        
        if not archivo_modelo.exists():
            continue
        
        columnas_orm = obtener_columnas_orm(archivo_modelo)
        campos_calculados = CAMPOS_CALCULADOS.get(modelo_nombre, set())
        
        if archivo_schema.exists():
            campos_schema = obtener_campos_schema(archivo_schema)
            
            # Campos en ORM pero no en schema (deben agregarse)
            campos_faltantes = columnas_orm - campos_schema - campos_calculados
            if campos_faltantes:
                resultados['campos_faltantes_en_schemas'].append({
                    'modelo': modelo_nombre,
                    'tabla': tabla_bd,
                    'campos': campos_faltantes
                })
            
            # Campos calculados encontrados (documentar)
            campos_calc_encontrados = campos_schema & campos_calculados
            if campos_calc_encontrados:
                resultados['campos_calculados_documentados'].append({
                    'modelo': modelo_nombre,
                    'campos': campos_calc_encontrados
                })
        else:
            # Schema no existe, todos los campos ORM faltan
            resultados['campos_orm_sin_schema'].append({
                'modelo': modelo_nombre,
                'tabla': tabla_bd,
                'campos': columnas_orm - campos_calculados
            })
    
    return resultados


def generar_reporte_sincronizacion(resultados: Dict) -> str:
    """Genera reporte de sincronización"""
    reporte = []
    reporte.append("=" * 100)
    reporte.append("REPORTE: SINCRONIZACIÓN SCHEMAS PYDANTIC CON MODELOS ORM")
    reporte.append("=" * 100)
    reporte.append("")
    reporte.append(f"Fecha: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    reporte.append("")
    
    # Resumen
    total_faltantes = sum(len(item['campos']) for item in resultados['campos_faltantes_en_schemas'])
    total_calculados = sum(len(item['campos']) for item in resultados['campos_calculados_documentados'])
    
    reporte.append("RESUMEN EJECUTIVO")
    reporte.append("-" * 100)
    reporte.append(f"Campos faltantes en schemas: {total_faltantes}")
    reporte.append(f"Campos calculados documentados: {total_calculados}")
    reporte.append(f"Schemas sin archivo: {len(resultados['campos_orm_sin_schema'])}")
    reporte.append("")
    
    # Campos faltantes
    if resultados['campos_faltantes_en_schemas']:
        reporte.append("CAMPOS FALTANTES EN SCHEMAS (Agregar)")
        reporte.append("-" * 100)
        for item in resultados['campos_faltantes_en_schemas']:
            reporte.append(f"  Modelo: {item['modelo']} (tabla: {item['tabla']})")
            reporte.append(f"  Campos a agregar ({len(item['campos'])}):")
            for campo in sorted(item['campos']):
                reporte.append(f"    - {campo}")
            reporte.append("")
    
    # Campos calculados
    if resultados['campos_calculados_documentados']:
        reporte.append("CAMPOS CALCULADOS (OK - Mantener solo en schemas)")
        reporte.append("-" * 100)
        for item in resultados['campos_calculados_documentados']:
            reporte.append(f"  Modelo: {item['modelo']}")
            reporte.append(f"  Campos calculados ({len(item['campos'])}):")
            for campo in sorted(item['campos']):
                reporte.append(f"    - {campo}")
            reporte.append("")
    
    # Schemas faltantes
    if resultados['campos_orm_sin_schema']:
        reporte.append("SCHEMAS FALTANTES (Crear archivo)")
        reporte.append("-" * 100)
        for item in resultados['campos_orm_sin_schema']:
            reporte.append(f"  Modelo: {item['modelo']} (tabla: {item['tabla']})")
            reporte.append(f"  Archivo a crear: backend/app/schemas/{item['modelo']}.py")
            reporte.append(f"  Campos a incluir ({len(item['campos'])}):")
            for campo in sorted(list(item['campos'])[:10]):
                reporte.append(f"    - {campo}")
            if len(item['campos']) > 10:
                reporte.append(f"    ... y {len(item['campos']) - 10} más")
            reporte.append("")
    
    reporte.append("=" * 100)
    reporte.append("RECOMENDACIONES")
    reporte.append("=" * 100)
    reporte.append("")
    reporte.append("1. Agregar campos faltantes a schemas Response")
    reporte.append("2. Documentar campos calculados en comentarios")
    reporte.append("3. Verificar tipos de datos coinciden")
    reporte.append("")
    
    return "\n".join(reporte)


def main():
    """Función principal"""
    import sys
    import io
    
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 100)
    print("FASE 2.2: SINCRONIZACIÓN SCHEMAS PYDANTIC CON MODELOS ORM")
    print("=" * 100)
    print("")
    
    print("[ANALISIS] Analizando discrepancias entre ORM y Schemas...")
    resultados = analizar_discrepancias_schemas()
    
    # Generar reporte
    reporte = generar_reporte_sincronizacion(resultados)
    
    # Guardar reporte
    ruta_reporte = PROYECTO_ROOT / "Documentos" / "Auditorias" / "2025-01" / "SINCRONIZACION_SCHEMAS_FASE2.md"
    ruta_reporte.parent.mkdir(parents=True, exist_ok=True)
    
    with open(ruta_reporte, 'w', encoding='utf-8') as f:
        f.write(reporte)
    
    print(f"\n[REPORTE] Reporte guardado en: {ruta_reporte}")
    print("\n" + "=" * 100)
    print(reporte[:2000])  # Mostrar primeros 2000 caracteres
    print("\n... (reporte completo en archivo)")
    print("=" * 100)


if __name__ == "__main__":
    main()
