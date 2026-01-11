"""
Script de Auditoría: Endpoints que dependen de Base de Datos
Analiza todos los endpoints y verifica el uso de columnas sincronizadas en FASE 3
"""

import ast
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Columnas sincronizadas en FASE 3
COLUMNAS_PAGOS_SINCRONIZADAS = {
    'banco', 'codigo_pago', 'comprobante', 'creado_en', 'descuento',
    'dias_mora', 'documento', 'fecha_vencimiento', 'hora_pago', 'metodo_pago',
    'monto', 'monto_capital', 'monto_cuota_programado', 'monto_interes',
    'monto_mora', 'monto_total', 'numero_operacion', 'observaciones',
    'referencia_pago', 'tasa_mora', 'tipo_pago'
}

COLUMNAS_CUOTAS_SINCRONIZADAS = {
    'creado_en', 'actualizado_en'
}

COLUMNAS_PRESTAMOS_ML = {
    'ml_impago_nivel_riesgo_manual',
    'ml_impago_probabilidad_manual',
    'ml_impago_nivel_riesgo_calculado',
    'ml_impago_probabilidad_calculada',
    'ml_impago_calculado_en',
    'ml_impago_modelo_id'
}


def obtener_ruta_endpoints():
    """Obtiene la ruta del directorio de endpoints"""
    script_dir = Path(__file__).parent
    proyecto_root = script_dir.parent.parent
    return proyecto_root / "backend" / "app" / "api" / "v1" / "endpoints"


def analizar_archivo_python(archivo_path: Path) -> Dict:
    """Analiza un archivo Python y extrae información sobre endpoints y uso de modelos"""
    resultados = {
        'archivo': str(archivo_path.relative_to(archivo_path.parent.parent.parent.parent)),
        'endpoints': [],
        'modelos_usados': set(),
        'columnas_pagos_usadas': set(),
        'columnas_cuotas_usadas': set(),
        'columnas_prestamos_ml_usadas': set(),
        'importaciones': [],
        'errores': []
    }
    
    try:
        with open(archivo_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Parsear el AST
        try:
            tree = ast.parse(contenido)
        except SyntaxError as e:
            resultados['errores'].append(f"Error de sintaxis: {e}")
            return resultados
        
        # Analizar importaciones
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    resultados['importaciones'].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    resultados['importaciones'].append(node.module)
                    for alias in node.names:
                        resultados['importaciones'].append(f"{node.module}.{alias.name}")
        
        # Buscar decoradores @router
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Verificar si tiene decorador router
                tiene_router = False
                metodo_http = None
                ruta = None
                
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            if decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch']:
                                tiene_router = True
                                metodo_http = decorator.func.attr.upper()
                                if decorator.args:
                                    if isinstance(decorator.args[0], ast.Constant):
                                        ruta = decorator.args[0].value
                                    elif isinstance(decorator.args[0], ast.Str):
                                        ruta = decorator.args[0].s
                
                if tiene_router:
                    endpoint_info = {
                        'nombre': node.name,
                        'metodo': metodo_http,
                        'ruta': ruta or '/',
                        'usa_db': False,
                        'modelos': set(),
                        'columnas_pagos': set(),
                        'columnas_cuotas': set(),
                        'columnas_prestamos_ml': set()
                    }
                    
                    # Buscar parámetro db: Session
                    for arg in node.args.args:
                        if arg.annotation:
                            if isinstance(arg.annotation, ast.Name):
                                if arg.annotation.id == 'Session':
                                    endpoint_info['usa_db'] = True
                    
                    # Analizar cuerpo de la función
                    analizar_cuerpo_funcion(node, endpoint_info, resultados)
                    
                    if endpoint_info['usa_db']:
                        resultados['endpoints'].append(endpoint_info)
        
        # Buscar uso de modelos en el código completo
        analizar_uso_modelos(contenido, resultados)
        
    except Exception as e:
        resultados['errores'].append(f"Error al analizar archivo: {e}")
    
    return resultados


def analizar_cuerpo_funcion(func_node: ast.FunctionDef, endpoint_info: Dict, resultados: Dict):
    """Analiza el cuerpo de una función para encontrar uso de modelos y columnas"""
    for node in ast.walk(func_node):
        # Buscar db.query(Modelo)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == 'query':
                    if node.args:
                        if isinstance(node.args[0], ast.Name):
                            modelo = node.args[0].id
                            endpoint_info['modelos'].add(modelo)
                            resultados['modelos_usados'].add(modelo)
        
        # Buscar acceso a atributos de modelos (Pago.columna, Cuota.columna, etc.)
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                modelo = node.value.id
                columna = node.attr
                
                if modelo == 'Pago' and columna in COLUMNAS_PAGOS_SINCRONIZADAS:
                    endpoint_info['columnas_pagos'].add(columna)
                    resultados['columnas_pagos_usadas'].add(columna)
                elif modelo == 'Cuota' and columna in COLUMNAS_CUOTAS_SINCRONIZADAS:
                    endpoint_info['columnas_cuotas'].add(columna)
                    resultados['columnas_cuotas_usadas'].add(columna)
                elif modelo == 'Prestamo' and columna in COLUMNAS_PRESTAMOS_ML:
                    endpoint_info['columnas_prestamos_ml'].add(columna)
                    resultados['columnas_prestamos_ml_usadas'].add(columna)


def analizar_uso_modelos(contenido: str, resultados: Dict):
    """Analiza el contenido del archivo buscando uso de modelos y columnas usando regex"""
    # Buscar Pago.columna
    patron_pago = r'Pago\.(\w+)'
    for match in re.finditer(patron_pago, contenido):
        columna = match.group(1)
        if columna in COLUMNAS_PAGOS_SINCRONIZADAS:
            resultados['columnas_pagos_usadas'].add(columna)
    
    # Buscar Cuota.columna
    patron_cuota = r'Cuota\.(\w+)'
    for match in re.finditer(patron_cuota, contenido):
        columna = match.group(1)
        if columna in COLUMNAS_CUOTAS_SINCRONIZADAS:
            resultados['columnas_cuotas_usadas'].add(columna)
    
    # Buscar Prestamo.columna (ML)
    patron_prestamo = r'Prestamo\.(\w+)'
    for match in re.finditer(patron_prestamo, contenido):
        columna = match.group(1)
        if columna in COLUMNAS_PRESTAMOS_ML:
            resultados['columnas_prestamos_ml_usadas'].add(columna)
    
    # Buscar acceso a atributos de instancias (pago.columna, cuota.columna)
    patron_instancia_pago = r'(?:pago|pagos|pago_obj|pago_item)\.(\w+)'
    for match in re.finditer(patron_instancia_pago, contenido, re.IGNORECASE):
        columna = match.group(1)
        if columna in COLUMNAS_PAGOS_SINCRONIZADAS:
            resultados['columnas_pagos_usadas'].add(columna)
    
    patron_instancia_cuota = r'(?:cuota|cuotas|cuota_obj|cuota_item)\.(\w+)'
    for match in re.finditer(patron_instancia_cuota, contenido, re.IGNORECASE):
        columna = match.group(1)
        if columna in COLUMNAS_CUOTAS_SINCRONIZADAS:
            resultados['columnas_cuotas_usadas'].add(columna)
    
    patron_instancia_prestamo = r'(?:prestamo|prestamos|prestamo_obj)\.(\w+)'
    for match in re.finditer(patron_instancia_prestamo, contenido, re.IGNORECASE):
        columna = match.group(1)
        if columna in COLUMNAS_PRESTAMOS_ML:
            resultados['columnas_prestamos_ml_usadas'].add(columna)


def generar_reporte(auditoria_completa: List[Dict]) -> str:
    """Genera un reporte completo de la auditoría"""
    reporte = []
    reporte.append("=" * 80)
    reporte.append("AUDITORÍA DE ENDPOINTS QUE DEPENDEN DE BASE DE DATOS")
    reporte.append("=" * 80)
    reporte.append("")
    reporte.append(f"Fecha: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    reporte.append("")
    
    # Estadísticas generales
    total_endpoints = sum(len(r['endpoints']) for r in auditoria_completa)
    total_archivos = len(auditoria_completa)
    archivos_con_endpoints = len([r for r in auditoria_completa if r['endpoints']])
    
    reporte.append("ESTADISTICAS GENERALES")
    reporte.append("-" * 80)
    reporte.append(f"Total de archivos analizados: {total_archivos}")
    reporte.append(f"Archivos con endpoints: {archivos_con_endpoints}")
    reporte.append(f"Total de endpoints con DB: {total_endpoints}")
    reporte.append("")
    
    # Modelos más usados
    modelos_count = defaultdict(int)
    for resultado in auditoria_completa:
        for modelo in resultado['modelos_usados']:
            modelos_count[modelo] += 1
    
    reporte.append("MODELOS MAS USADOS")
    reporte.append("-" * 80)
    for modelo, count in sorted(modelos_count.items(), key=lambda x: x[1], reverse=True):
        reporte.append(f"  {modelo}: {count} archivo(s)")
    reporte.append("")
    
    # Columnas sincronizadas usadas
    todas_columnas_pagos = set()
    todas_columnas_cuotas = set()
    todas_columnas_prestamos_ml = set()
    
    for resultado in auditoria_completa:
        todas_columnas_pagos.update(resultado['columnas_pagos_usadas'])
        todas_columnas_cuotas.update(resultado['columnas_cuotas_usadas'])
        todas_columnas_prestamos_ml.update(resultado['columnas_prestamos_ml_usadas'])
    
    reporte.append("COLUMNAS SINCRONIZADAS EN USO")
    reporte.append("-" * 80)
    reporte.append(f"Columnas Pago usadas: {len(todas_columnas_pagos)} de {len(COLUMNAS_PAGOS_SINCRONIZADAS)}")
    if todas_columnas_pagos:
        reporte.append(f"  {', '.join(sorted(todas_columnas_pagos))}")
    else:
        reporte.append("  [ADVERTENCIA] Ninguna columna sincronizada esta siendo usada")
    reporte.append("")
    
    reporte.append(f"Columnas Cuota usadas: {len(todas_columnas_cuotas)} de {len(COLUMNAS_CUOTAS_SINCRONIZADAS)}")
    if todas_columnas_cuotas:
        reporte.append(f"  {', '.join(sorted(todas_columnas_cuotas))}")
    else:
        reporte.append("  [ADVERTENCIA] Ninguna columna sincronizada esta siendo usada")
    reporte.append("")
    
    reporte.append(f"Columnas Prestamo ML usadas: {len(todas_columnas_prestamos_ml)} de {len(COLUMNAS_PRESTAMOS_ML)}")
    if todas_columnas_prestamos_ml:
        reporte.append(f"  {', '.join(sorted(todas_columnas_prestamos_ml))}")
    else:
        reporte.append("  [ADVERTENCIA] Ninguna columna ML esta siendo usada")
    reporte.append("")
    
    # Columnas no usadas
    columnas_pagos_no_usadas = COLUMNAS_PAGOS_SINCRONIZADAS - todas_columnas_pagos
    columnas_cuotas_no_usadas = COLUMNAS_CUOTAS_SINCRONIZADAS - todas_columnas_cuotas
    columnas_prestamos_ml_no_usadas = COLUMNAS_PRESTAMOS_ML - todas_columnas_prestamos_ml
    
    reporte.append("[ADVERTENCIA] COLUMNAS SINCRONIZADAS NO USADAS")
    reporte.append("-" * 80)
    reporte.append(f"Columnas Pago no usadas ({len(columnas_pagos_no_usadas)}):")
    if columnas_pagos_no_usadas:
        reporte.append(f"  {', '.join(sorted(columnas_pagos_no_usadas))}")
    else:
        reporte.append("  ✅ Todas las columnas están en uso")
    reporte.append("")
    
    reporte.append(f"Columnas Cuota no usadas ({len(columnas_cuotas_no_usadas)}):")
    if columnas_cuotas_no_usadas:
        reporte.append(f"  {', '.join(sorted(columnas_cuotas_no_usadas))}")
    else:
        reporte.append("  ✅ Todas las columnas están en uso")
    reporte.append("")
    
    reporte.append(f"Columnas Prestamo ML no usadas ({len(columnas_prestamos_ml_no_usadas)}):")
    if columnas_prestamos_ml_no_usadas:
        reporte.append(f"  {', '.join(sorted(columnas_prestamos_ml_no_usadas))}")
    else:
        reporte.append("  ✅ Todas las columnas están en uso")
    reporte.append("")
    
    # Detalle por archivo
    reporte.append("DETALLE POR ARCHIVO")
    reporte.append("=" * 80)
    
    for resultado in sorted(auditoria_completa, key=lambda x: len(x['endpoints']), reverse=True):
        if resultado['endpoints']:
            reporte.append("")
            reporte.append(f"[ARCHIVO] {resultado['archivo']}")
            reporte.append("-" * 80)
            reporte.append(f"  Endpoints con DB: {len(resultado['endpoints'])}")
            reporte.append(f"  Modelos usados: {', '.join(sorted(resultado['modelos_usados'])) if resultado['modelos_usados'] else 'Ninguno'}")
            
            if resultado['columnas_pagos_usadas']:
                reporte.append(f"  Columnas Pago usadas: {', '.join(sorted(resultado['columnas_pagos_usadas']))}")
            if resultado['columnas_cuotas_usadas']:
                reporte.append(f"  Columnas Cuota usadas: {', '.join(sorted(resultado['columnas_cuotas_usadas']))}")
            if resultado['columnas_prestamos_ml_usadas']:
                reporte.append(f"  Columnas Prestamo ML usadas: {', '.join(sorted(resultado['columnas_prestamos_ml_usadas']))}")
            
            if resultado['errores']:
                reporte.append(f"  [ERROR] Errores: {', '.join(resultado['errores'])}")
            
            # Listar endpoints
            reporte.append("  Endpoints:")
            for endpoint in resultado['endpoints']:
                reporte.append(f"    - {endpoint['metodo']} {endpoint['ruta']} ({endpoint['nombre']})")
                if endpoint['modelos']:
                    reporte.append(f"      Modelos: {', '.join(sorted(endpoint['modelos']))}")
                if endpoint['columnas_pagos']:
                    reporte.append(f"      Columnas Pago: {', '.join(sorted(endpoint['columnas_pagos']))}")
                if endpoint['columnas_cuotas']:
                    reporte.append(f"      Columnas Cuota: {', '.join(sorted(endpoint['columnas_cuotas']))}")
                if endpoint['columnas_prestamos_ml']:
                    reporte.append(f"      Columnas Prestamo ML: {', '.join(sorted(endpoint['columnas_prestamos_ml']))}")
    
    # Recomendaciones
    reporte.append("")
    reporte.append("=" * 80)
    reporte.append("RECOMENDACIONES")
    reporte.append("=" * 80)
    
    if columnas_pagos_no_usadas:
        reporte.append("")
        reporte.append("[INFO] Columnas de Pago disponibles pero no usadas:")
        reporte.append("   Considera usar estas columnas para mejorar funcionalidades:")
        for col in sorted(columnas_pagos_no_usadas):
            reporte.append(f"   - {col}")
    
    if columnas_cuotas_no_usadas:
        reporte.append("")
        reporte.append("[INFO] Columnas de Cuota disponibles pero no usadas:")
        for col in sorted(columnas_cuotas_no_usadas):
            reporte.append(f"   - {col}")
    
    if columnas_prestamos_ml_no_usadas:
        reporte.append("")
        reporte.append("[INFO] Columnas ML de Prestamo disponibles pero no usadas:")
        for col in sorted(columnas_prestamos_ml_no_usadas):
            reporte.append(f"   - {col}")
    
    reporte.append("")
    reporte.append("=" * 80)
    reporte.append("FIN DEL REPORTE")
    reporte.append("=" * 80)
    
    return "\n".join(reporte)


def main():
    """Función principal"""
    import sys
    import io
    
    # Configurar stdout para UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("[AUDITORIA] Iniciando auditoria de endpoints...")
    
    ruta_endpoints = obtener_ruta_endpoints()
    
    if not ruta_endpoints.exists():
        print(f"[ERROR] No se encontro el directorio {ruta_endpoints}")
        return
    
    auditoria_completa = []
    archivos_procesados = 0
    
    # Analizar todos los archivos Python en el directorio de endpoints
    for archivo in sorted(ruta_endpoints.glob("*.py")):
        if archivo.name == "__init__.py":
            continue
        
        print(f"  Analizando: {archivo.name}...")
        resultado = analizar_archivo_python(archivo)
        auditoria_completa.append(resultado)
        archivos_procesados += 1
    
    print(f"\n[OK] Procesados {archivos_procesados} archivos")
    
    # Generar reporte
    reporte = generar_reporte(auditoria_completa)
    
    # Guardar reporte
    script_dir = Path(__file__).parent
    proyecto_root = script_dir.parent.parent
    ruta_reporte = proyecto_root / "Documentos" / "Auditorias" / "2025-01" / "AUDITORIA_ENDPOINTS_BD.md"
    
    ruta_reporte.parent.mkdir(parents=True, exist_ok=True)
    
    with open(ruta_reporte, 'w', encoding='utf-8') as f:
        f.write(reporte)
    
    print(f"\n[REPORTE] Reporte guardado en: {ruta_reporte}")
    print("\n" + "=" * 80)
    print(reporte)
    print("=" * 80)


if __name__ == "__main__":
    main()
