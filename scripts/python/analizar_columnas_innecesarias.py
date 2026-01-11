"""
Análisis de columnas innecesarias o problemáticas
Verifica si hay columnas que causan problemas y pueden eliminarse
"""

import re
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict

PROYECTO_ROOT = Path(__file__).parent.parent.parent
BACKEND_MODELS = PROYECTO_ROOT / "backend" / "app" / "models"
BACKEND_SCHEMAS = PROYECTO_ROOT / "backend" / "app" / "schemas"
BACKEND_ENDPOINTS = PROYECTO_ROOT / "backend" / "app" / "api" / "v1" / "endpoints"

# Columnas que podrían ser problemáticas o innecesarias
COLUMNAS_SOSPECHOSAS = {
    'pagos': {
        'monto': 'Integer en BD pero hay monto_pagado (Numeric) - posible duplicado',
        'documento': 'VARCHAR(50) pero hay documento_nombre, documento_tipo, documento_ruta - posible redundancia',
    },
    'prestamos': {
        'cedula': 'Duplicado de clientes.cedula - posible redundancia',
        'nombres': 'Duplicado de clientes.nombres - posible redundancia',
        'concesionario': 'String pero hay concesionario_id (FK) - posible redundancia',
        'analista': 'String pero hay analista_id (FK) - posible redundancia',
        'modelo_vehiculo': 'String pero hay modelo_vehiculo_id (FK) - posible redundancia',
    },
    'pagos': {
        'cedula': 'Duplicado de clientes.cedula - posible redundancia',
    }
}


def buscar_uso_columna_en_codigo(columna: str, tabla: str) -> Dict[str, List[str]]:
    """Busca uso de una columna en el código"""
    usos = {
        'modelos': [],
        'schemas': [],
        'endpoints': [],
        'servicios': []
    }
    
    modelo_nombre = {
        'pagos': 'pago',
        'cuotas': 'amortizacion',
        'prestamos': 'prestamo',
        'clientes': 'cliente',
        'users': 'user',
        'notificaciones': 'notificacion'
    }.get(tabla, tabla)
    
    # Buscar en modelos
    modelo_file = BACKEND_MODELS / f"{modelo_nombre}.py"
    if modelo_file.exists():
        with open(modelo_file, 'r', encoding='utf-8') as f:
            contenido = f.read()
            if columna in contenido:
                # Buscar contexto
                patron = rf'{columna}\s*='
                if re.search(patron, contenido):
                    usos['modelos'].append(f"{modelo_nombre}.py")
    
    # Buscar en schemas
    schema_file = BACKEND_SCHEMAS / f"{modelo_nombre}.py"
    if schema_file.exists():
        with open(schema_file, 'r', encoding='utf-8') as f:
            contenido = f.read()
            if columna in contenido:
                usos['schemas'].append(f"{modelo_nombre}.py")
    
    # Buscar en endpoints
    if BACKEND_ENDPOINTS.exists():
        for archivo in BACKEND_ENDPOINTS.glob("*.py"):
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                    # Buscar uso como atributo (Pago.columna o pago.columna)
                    patrones = [
                        rf'Pago\.{columna}',
                        rf'pago\.{columna}',
                        rf'Cuota\.{columna}',
                        rf'cuota\.{columna}',
                        rf'Prestamo\.{columna}',
                        rf'prestamo\.{columna}',
                        rf'Cliente\.{columna}',
                        rf'cliente\.{columna}',
                    ]
                    for patron in patrones:
                        if re.search(patron, contenido, re.IGNORECASE):
                            usos['endpoints'].append(archivo.name)
                            break
            except:
                pass
    
    return usos


def analizar_columnas_innecesarias():
    """Analiza columnas que podrían ser innecesarias"""
    resultados = {
        'columnas_duplicadas': [],
        'columnas_redundantes': [],
        'columnas_no_usadas': [],
        'recomendaciones': []
    }
    
    # Analizar columnas duplicadas
    print("[ANALISIS] Analizando columnas duplicadas...")
    
    # prestamos.cedula y prestamos.nombres (duplicados de clientes)
    usos_cedula_prestamos = buscar_uso_columna_en_codigo('cedula', 'prestamos')
    usos_nombres_prestamos = buscar_uso_columna_en_codigo('nombres', 'prestamos')
    
    if usos_cedula_prestamos['endpoints'] or usos_cedula_prestamos['schemas']:
        resultados['columnas_duplicadas'].append({
            'tabla': 'prestamos',
            'columna': 'cedula',
            'razon': 'Duplicado de clientes.cedula',
            'usos_encontrados': usos_cedula_prestamos,
            'puede_eliminarse': False,
            'recomendacion': 'Mantener por ahora - se usa en código. Considerar migrar a usar cliente_id y relación'
        })
    else:
        resultados['columnas_duplicadas'].append({
            'tabla': 'prestamos',
            'columna': 'cedula',
            'razon': 'Duplicado de clientes.cedula',
            'usos_encontrados': usos_cedula_prestamos,
            'puede_eliminarse': True,
            'recomendacion': 'Puede eliminarse - no se usa en código. Usar cliente_id y relación'
        })
    
    # prestamos.concesionario vs concesionario_id
    usos_concesionario = buscar_uso_columna_en_codigo('concesionario', 'prestamos')
    usos_concesionario_id = buscar_uso_columna_en_codigo('concesionario_id', 'prestamos')
    
    if usos_concesionario['endpoints'] and not usos_concesionario_id['endpoints']:
        resultados['columnas_redundantes'].append({
            'tabla': 'prestamos',
            'columna': 'concesionario',
            'razon': 'String redundante cuando existe concesionario_id (FK)',
            'usos_encontrados': usos_concesionario,
            'puede_eliminarse': False,
            'recomendacion': 'Migrar código a usar concesionario_id y relación antes de eliminar'
        })
    elif not usos_concesionario['endpoints'] and usos_concesionario_id['endpoints']:
        resultados['columnas_redundantes'].append({
            'tabla': 'prestamos',
            'columna': 'concesionario',
            'razon': 'String redundante cuando existe concesionario_id (FK)',
            'usos_encontrados': usos_concesionario,
            'puede_eliminarse': True,
            'recomendacion': 'Puede eliminarse - código ya usa concesionario_id'
        })
    
    # pagos.monto vs monto_pagado
    usos_monto = buscar_uso_columna_en_codigo('monto', 'pagos')
    usos_monto_pagado = buscar_uso_columna_en_codigo('monto_pagado', 'pagos')
    
    if usos_monto['endpoints'] and usos_monto_pagado['endpoints']:
        resultados['columnas_redundantes'].append({
            'tabla': 'pagos',
            'columna': 'monto',
            'razon': 'Integer redundante cuando existe monto_pagado (Numeric más preciso)',
            'usos_encontrados': usos_monto,
            'puede_eliminarse': False,
            'recomendacion': 'Migrar código de monto a monto_pagado antes de eliminar'
        })
    elif not usos_monto['endpoints'] and usos_monto_pagado['endpoints']:
        resultados['columnas_redundantes'].append({
            'tabla': 'pagos',
            'columna': 'monto',
            'razon': 'Integer redundante cuando existe monto_pagado (Numeric más preciso)',
            'usos_encontrados': usos_monto,
            'puede_eliminarse': True,
            'recomendacion': 'Puede eliminarse - código ya usa monto_pagado'
        })
    
    # pagos.cedula (duplicado de clientes)
    usos_cedula_pagos = buscar_uso_columna_en_codigo('cedula', 'pagos')
    
    if usos_cedula_pagos['endpoints']:
        resultados['columnas_duplicadas'].append({
            'tabla': 'pagos',
            'columna': 'cedula',
            'razon': 'Duplicado de clientes.cedula',
            'usos_encontrados': usos_cedula_pagos,
            'puede_eliminarse': False,
            'recomendacion': 'Mantener por ahora - se usa en código. Considerar migrar a usar cliente_id'
        })
    
    return resultados


def generar_reporte_columnas_innecesarias(resultados: Dict) -> str:
    """Genera reporte de columnas innecesarias"""
    reporte = []
    reporte.append("=" * 100)
    reporte.append("ANÁLISIS DE COLUMNAS INNECESARIAS O PROBLEMÁTICAS")
    reporte.append("=" * 100)
    reporte.append("")
    reporte.append(f"Fecha: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    reporte.append("")
    
    total_analizadas = (
        len(resultados['columnas_duplicadas']) +
        len(resultados['columnas_redundantes']) +
        len(resultados['columnas_no_usadas'])
    )
    
    reporte.append("RESUMEN")
    reporte.append("-" * 100)
    reporte.append(f"Total columnas analizadas: {total_analizadas}")
    reporte.append(f"  - Duplicadas: {len(resultados['columnas_duplicadas'])}")
    reporte.append(f"  - Redundantes: {len(resultados['columnas_redundantes'])}")
    reporte.append(f"  - No usadas: {len(resultados['columnas_no_usadas'])}")
    reporte.append("")
    
    # Columnas que pueden eliminarse
    pueden_eliminarse = [
        d for d in resultados['columnas_duplicadas'] + 
        resultados['columnas_redundantes'] + 
        resultados['columnas_no_usadas']
        if d.get('puede_eliminarse', False)
    ]
    
    no_pueden_eliminarse = [
        d for d in resultados['columnas_duplicadas'] + 
        resultados['columnas_redundantes'] + 
        resultados['columnas_no_usadas']
        if not d.get('puede_eliminarse', False)
    ]
    
    reporte.append("COLUMNAS QUE PUEDEN ELIMINARSE (SEGURO)")
    reporte.append("-" * 100)
    if pueden_eliminarse:
        for col in pueden_eliminarse:
            reporte.append(f"  - {col['tabla']}.{col['columna']}")
            reporte.append(f"    Razón: {col['razon']}")
            reporte.append(f"    Recomendación: {col['recomendacion']}")
            reporte.append("")
    else:
        reporte.append("  No se encontraron columnas que puedan eliminarse de forma segura.")
        reporte.append("")
    
    reporte.append("COLUMNAS QUE REQUIEREN MIGRACIÓN ANTES DE ELIMINAR")
    reporte.append("-" * 100)
    if no_pueden_eliminarse:
        for col in no_pueden_eliminarse:
            reporte.append(f"  - {col['tabla']}.{col['columna']}")
            reporte.append(f"    Razón: {col['razon']}")
            reporte.append(f"    Usos encontrados:")
            for tipo, archivos in col['usos_encontrados'].items():
                if archivos:
                    reporte.append(f"      {tipo}: {', '.join(archivos[:3])}")
            reporte.append(f"    Recomendación: {col['recomendacion']}")
            reporte.append("")
    else:
        reporte.append("  No se encontraron columnas que requieran migración.")
        reporte.append("")
    
    # Recomendaciones finales
    reporte.append("=" * 100)
    reporte.append("RECOMENDACIONES FINALES")
    reporte.append("=" * 100)
    reporte.append("")
    
    if pueden_eliminarse:
        reporte.append("1. COLUMNAS PARA ELIMINAR (Prioridad BAJA)")
        reporte.append("   Estas columnas pueden eliminarse de forma segura:")
        for col in pueden_eliminarse:
            reporte.append(f"   - {col['tabla']}.{col['columna']}")
        reporte.append("")
        reporte.append("   ACCIÓN: Crear migración Alembic para eliminar estas columnas")
        reporte.append("")
    
    if no_pueden_eliminarse:
        reporte.append("2. COLUMNAS QUE REQUIEREN MIGRACIÓN (Prioridad MEDIA)")
        reporte.append("   Estas columnas se usan en código y requieren migración:")
        for col in no_pueden_eliminarse:
            reporte.append(f"   - {col['tabla']}.{col['columna']}")
        reporte.append("")
        reporte.append("   ACCIÓN: Migrar código a usar columnas alternativas antes de eliminar")
        reporte.append("")
    
    reporte.append("3. CONCLUSIÓN")
    reporte.append("   - No se encontraron columnas críticas que deban eliminarse inmediatamente")
    reporte.append("   - Las columnas duplicadas/redundantes pueden mantenerse por ahora")
    reporte.append("   - Priorizar correcciones de FASE 1 (nullable, tipos, etc.)")
    reporte.append("   - Revisar eliminación de columnas en futuras refactorizaciones")
    reporte.append("")
    
    reporte.append("=" * 100)
    reporte.append("FIN DEL REPORTE")
    reporte.append("=" * 100)
    
    return "\n".join(reporte)


def main():
    """Función principal"""
    import sys
    import io
    
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 100)
    print("ANÁLISIS DE COLUMNAS INNECESARIAS O PROBLEMÁTICAS")
    print("=" * 100)
    print("")
    
    print("[ANALISIS] Buscando columnas innecesarias...")
    resultados = analizar_columnas_innecesarias()
    
    print(f"[RESULTADOS] {len(resultados['columnas_duplicadas']) + len(resultados['columnas_redundantes'])} columnas analizadas")
    
    # Generar reporte
    reporte = generar_reporte_columnas_innecesarias(resultados)
    
    # Guardar reporte
    ruta_reporte = PROYECTO_ROOT / "Documentos" / "Auditorias" / "2025-01" / "ANALISIS_COLUMNAS_INNECESARIAS.md"
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
