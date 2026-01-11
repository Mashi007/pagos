"""
Auditoría Integral: Coherencia entre Base de Datos, Backend (ORM + Schemas) y Frontend
Analiza todos los modelos, schemas y componentes frontend para detectar discrepancias
"""

import ast
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import json

# Configuración
PROYECTO_ROOT = Path(__file__).parent.parent.parent
BACKEND_MODELS = PROYECTO_ROOT / "backend" / "app" / "models"
BACKEND_SCHEMAS = PROYECTO_ROOT / "backend" / "app" / "schemas"
FRONTEND_SRC = PROYECTO_ROOT / "frontend" / "src"

# Tablas principales a auditar (prioridad)
TABLAS_PRINCIPALES = [
    'pagos', 'cuotas', 'prestamos', 'clientes', 
    'amortizacion', 'notificaciones', 'usuarios'
]

# Mapeo de tipos SQLAlchemy a tipos PostgreSQL
TIPO_SQLALCHEMY_A_POSTGRESQL = {
    'Integer': 'integer',
    'String': 'character varying',
    'Numeric': 'numeric',
    'Boolean': 'boolean',
    'Date': 'date',
    'DateTime': 'timestamp without time zone',
    'Time': 'time without time zone',
    'Text': 'text',
    'ForeignKey': 'integer',  # FK es siempre integer
}

# Mapeo de tipos Pydantic a tipos PostgreSQL
TIPO_PYDANTIC_A_POSTGRESQL = {
    'int': 'integer',
    'str': 'character varying',
    'float': 'numeric',
    'Decimal': 'numeric',
    'bool': 'boolean',
    'date': 'date',
    'datetime': 'timestamp without time zone',
    'Optional': None,  # Se maneja con nullable
}


def obtener_columnas_modelo_orm(archivo_path: Path) -> Dict[str, Dict]:
    """Extrae columnas de un modelo ORM SQLAlchemy"""
    columnas = {}
    
    try:
        with open(archivo_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        tree = ast.parse(contenido)
        
        # Buscar clase que hereda de Base
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Verificar si hereda de Base
                bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
                if 'Base' in bases:
                    # Buscar __tablename__
                    tabla_nombre = None
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name) and target.id == '__tablename__':
                                    if isinstance(item.value, ast.Constant):
                                        tabla_nombre = item.value.value
                                    elif isinstance(item.value, ast.Str):
                                        tabla_nombre = item.value.s
                    
                    # Buscar Column() assignments
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name):
                                    columna_nombre = target.id
                                    
                                    # Buscar Column() en el valor
                                    if isinstance(item.value, ast.Call):
                                        tipo_columna = None
                                        nullable = True
                                        default = None
                                        
                                        # Analizar argumentos de Column()
                                        for keyword in item.value.keywords:
                                            if keyword.arg == 'nullable':
                                                if isinstance(keyword.value, ast.Constant):
                                                    nullable = keyword.value.value
                                                elif isinstance(keyword.value, ast.NameConstant):
                                                    nullable = keyword.value.value
                                            elif keyword.arg == 'default':
                                                default = 'HAS_DEFAULT'
                                        
                                        # Analizar tipo (primer argumento o función)
                                        if item.value.func.id == 'Column':
                                            if item.value.args:
                                                tipo_node = item.value.args[0]
                                                tipo_columna = extraer_tipo_sqlalchemy(tipo_node)
                                        
                                        if tipo_columna:
                                            columnas[columna_nombre] = {
                                                'tipo_orm': tipo_columna,
                                                'nullable': nullable,
                                                'default': default,
                                                'tabla': tabla_nombre
                                            }
    except Exception as e:
        print(f"Error analizando {archivo_path}: {e}")
    
    return columnas


def extraer_tipo_sqlalchemy(node: ast.AST) -> Optional[str]:
    """Extrae el tipo SQLAlchemy de un nodo AST"""
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
    elif isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return node.attr
    return None


def obtener_campos_schema(archivo_path: Path) -> Dict[str, Dict]:
    """Extrae campos de un schema Pydantic"""
    campos = {}
    
    try:
        with open(archivo_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        tree = ast.parse(contenido)
        
        # Buscar clases que heredan de BaseModel
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
                if 'BaseModel' in bases:
                    # Buscar Field() assignments
                    for item in node.body:
                        if isinstance(item, ast.AnnAssign):
                            if isinstance(item.target, ast.Name):
                                campo_nombre = item.target.id
                                
                                # Extraer tipo de la anotación
                                tipo_campo = None
                                if item.annotation:
                                    tipo_campo = extraer_tipo_pydantic(item.annotation)
                                
                                # Verificar si es Optional
                                nullable = False
                                if tipo_campo and 'Optional' in str(tipo_campo):
                                    nullable = True
                                    # Extraer tipo interno
                                    if isinstance(item.annotation, ast.Subscript):
                                        if item.annotation.slice:
                                            tipo_campo = extraer_tipo_pydantic(item.annotation.slice)
                                
                                # Buscar Field() en el valor
                                default_value = None
                                if item.value:
                                    if isinstance(item.value, ast.Call):
                                        if isinstance(item.value.func, ast.Name) and item.value.func.id == 'Field':
                                            # Buscar default en Field()
                                            for keyword in item.value.keywords:
                                                if keyword.arg == 'default':
                                                    default_value = 'HAS_DEFAULT'
                                                elif keyword.arg == 'default_factory':
                                                    default_value = 'HAS_DEFAULT'
                                    
                                    elif isinstance(item.value, ast.Constant):
                                        default_value = item.value.value
                                    elif isinstance(item.value, ast.NameConstant):
                                        default_value = item.value.value
                                
                                if tipo_campo:
                                    campos[campo_nombre] = {
                                        'tipo_schema': tipo_campo,
                                        'nullable': nullable or (default_value is None),
                                        'default': default_value
                                    }
    except Exception as e:
        print(f"Error analizando schema {archivo_path}: {e}")
    
    return campos


def extraer_tipo_pydantic(node: ast.AST) -> Optional[str]:
    """Extrae el tipo Pydantic de un nodo AST"""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Subscript):
        if isinstance(node.value, ast.Name):
            return node.value.id
    elif isinstance(node, ast.Attribute):
        return node.attr
    return None


def buscar_campos_frontend(archivo_path: Path, modelo_nombre: str) -> Set[str]:
    """Busca campos usados en componentes frontend relacionados con un modelo"""
    campos_encontrados = set()
    
    try:
        with open(archivo_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Buscar patrones comunes de campos
        # 1. Objetos con propiedades (modelo.campo)
        patron_objeto = rf'\b{modelo_nombre.lower()}\.(\w+)'
        for match in re.finditer(patron_objeto, contenido, re.IGNORECASE):
            campos_encontrados.add(match.group(1))
        
        # 2. Destructuring ({ campo })
        patron_destructuring = r'\{[\s\S]*?(\w+)[\s\S]*?\}'
        for match in re.finditer(patron_destructuring, contenido, re.IGNORECASE):
            campos_encontrados.add(match.group(1))
        
        # 3. Form fields (name="campo")
        patron_form = r'name=["\'](\w+)["\']'
        for match in re.finditer(patron_form, contenido):
            campos_encontrados.add(match.group(1))
        
        # 4. API responses (response.campo)
        patron_response = r'response\.(\w+)'
        for match in re.finditer(patron_response, contenido):
            campos_encontrados.add(match.group(1))
        
        # 5. TypeScript interfaces
        modelo_pattern = modelo_nombre.lower()
        patron_interface = f'interface\\s+\\w*{modelo_pattern}\\w*\\s*\\{{([\\s\\S]*?)\\}}'
        for match in re.finditer(patron_interface, contenido, re.IGNORECASE):
            interface_content = match.group(1)
            for campo_match in re.finditer(r'(\w+)\s*[:?]', interface_content):
                campos_encontrados.add(campo_match.group(1))
    
    except Exception as e:
        print(f"Error buscando campos frontend en {archivo_path}: {e}")
    
    return campos_encontrados


def generar_script_sql_auditoria() -> str:
    """Genera script SQL para obtener estructura real de BD"""
    script = """
-- ============================================================================
-- Script SQL generado para auditoría de coherencia
-- Ejecutar este script para obtener estructura real de la base de datos
-- ============================================================================

-- Obtener todas las columnas de las tablas principales
SELECT 
    table_name AS tabla,
    column_name AS columna,
    data_type AS tipo_dato,
    character_maximum_length AS longitud_maxima,
    numeric_precision AS precision_numerica,
    numeric_scale AS escala_numerica,
    is_nullable AS nullable,
    column_default AS valor_por_defecto
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name IN ('pagos', 'cuotas', 'prestamos', 'clientes', 'amortizacion', 'notificaciones', 'users')
ORDER BY table_name, ordinal_position;
"""
    return script


def analizar_coherencia_completa():
    """Realiza análisis completo de coherencia"""
    resultados = {
        'modelos_orm': {},
        'schemas': {},
        'frontend': {},
        'discrepancias': [],
        'recomendaciones': []
    }
    
    print("[AUDITORIA] Analizando modelos ORM...")
    # Analizar modelos ORM
    if BACKEND_MODELS.exists():
        for archivo in BACKEND_MODELS.glob("*.py"):
            if archivo.name == "__init__.py":
                continue
            
            modelo_nombre = archivo.stem
            columnas = obtener_columnas_modelo_orm(archivo)
            if columnas:
                resultados['modelos_orm'][modelo_nombre] = columnas
                print(f"  - {modelo_nombre}: {len(columnas)} columnas")
    
    print("\n[AUDITORIA] Analizando schemas Pydantic...")
    # Analizar schemas
    if BACKEND_SCHEMAS.exists():
        for archivo in BACKEND_SCHEMAS.glob("*.py"):
            if archivo.name == "__init__.py":
                continue
            
            schema_nombre = archivo.stem
            campos = obtener_campos_schema(archivo)
            if campos:
                resultados['schemas'][schema_nombre] = campos
                print(f"  - {schema_nombre}: {len(campos)} campos")
    
    print("\n[AUDITORIA] Analizando componentes frontend...")
    # Analizar frontend
    if FRONTEND_SRC.exists():
        modelos_buscar = ['pago', 'cuota', 'prestamo', 'cliente', 'notificacion', 'usuario']
        for modelo in modelos_buscar:
            campos_encontrados = set()
            for archivo in FRONTEND_SRC.rglob("*.{tsx,ts,jsx,js}"):
                try:
                    campos = buscar_campos_frontend(archivo, modelo)
                    campos_encontrados.update(campos)
                except:
                    pass
            if campos_encontrados:
                resultados['frontend'][modelo] = campos_encontrados
                print(f"  - {modelo}: {len(campos_encontrados)} campos encontrados")
    
    return resultados


def detectar_discrepancias(resultados: Dict) -> List[Dict]:
    """Detecta discrepancias entre ORM, Schemas y Frontend"""
    discrepancias = []
    
    # Comparar modelos ORM con schemas
    for modelo_nombre, columnas_orm in resultados['modelos_orm'].items():
        schema_nombre = modelo_nombre.lower()
        
        # Buscar schema correspondiente
        schema_encontrado = None
        for schema_key in resultados['schemas'].keys():
            if schema_key.lower() == schema_nombre or schema_key.lower().startswith(schema_nombre):
                schema_encontrado = resultados['schemas'][schema_key]
                break
        
        if schema_encontrado:
            campos_schema = set(schema_encontrado.keys())
            columnas_orm_set = set(columnas_orm.keys())
            
            # Columnas en ORM pero no en Schema
            faltantes_en_schema = columnas_orm_set - campos_schema
            for columna in faltantes_en_schema:
                discrepancias.append({
                    'tipo': 'ORM_SIN_SCHEMA',
                    'tabla': modelo_nombre,
                    'campo': columna,
                    'severidad': 'MEDIA',
                    'descripcion': f'Columna {columna} existe en modelo ORM pero no en schema Pydantic'
                })
            
            # Campos en Schema pero no en ORM
            faltantes_en_orm = campos_schema - columnas_orm_set
            for campo in faltantes_en_orm:
                discrepancias.append({
                    'tipo': 'SCHEMA_SIN_ORM',
                    'tabla': modelo_nombre,
                    'campo': campo,
                    'severidad': 'ALTA',
                    'descripcion': f'Campo {campo} existe en schema pero no en modelo ORM'
                })
    
    # Comparar con frontend
    for modelo_nombre, columnas_orm in resultados['modelos_orm'].items():
        modelo_frontend = modelo_nombre.lower().replace('_', '')
        
        if modelo_frontend in resultados['frontend']:
            campos_frontend = resultados['frontend'][modelo_frontend]
            columnas_orm_set = set(columnas_orm.keys())
            
            # Campos en Frontend pero no en ORM
            faltantes_en_orm = campos_frontend - columnas_orm_set
            for campo in faltantes_en_orm:
                discrepancias.append({
                    'tipo': 'FRONTEND_SIN_ORM',
                    'tabla': modelo_nombre,
                    'campo': campo,
                    'severidad': 'ALTA',
                    'descripcion': f'Campo {campo} usado en frontend pero no existe en modelo ORM'
                })
            
            # Columnas en ORM pero no usadas en Frontend (solo advertencia)
            no_usadas = columnas_orm_set - campos_frontend
            for columna in no_usadas:
                if columna not in ['id', 'created_at', 'updated_at']:  # Ignorar campos comunes
                    discrepancias.append({
                        'tipo': 'ORM_SIN_FRONTEND',
                        'tabla': modelo_nombre,
                        'campo': columna,
                        'severidad': 'BAJA',
                        'descripcion': f'Columna {columna} existe en ORM pero no se usa en frontend'
                    })
    
    return discrepancias


def generar_reporte(resultados: Dict, discrepancias: List[Dict]) -> str:
    """Genera reporte completo de auditoría"""
    reporte = []
    reporte.append("=" * 100)
    reporte.append("AUDITORÍA INTEGRAL: COHERENCIA BD - BACKEND - FRONTEND")
    reporte.append("=" * 100)
    reporte.append("")
    reporte.append(f"Fecha: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    reporte.append("")
    
    # Resumen ejecutivo
    reporte.append("RESUMEN EJECUTIVO")
    reporte.append("-" * 100)
    reporte.append(f"Modelos ORM analizados: {len(resultados['modelos_orm'])}")
    reporte.append(f"Schemas analizados: {len(resultados['schemas'])}")
    reporte.append(f"Modelos en frontend: {len(resultados['frontend'])}")
    reporte.append(f"Discrepancias encontradas: {len(discrepancias)}")
    reporte.append("")
    
    # Discrepancias por severidad
    alta = [d for d in discrepancias if d['severidad'] == 'ALTA']
    media = [d for d in discrepancias if d['severidad'] == 'MEDIA']
    baja = [d for d in discrepancias if d['severidad'] == 'BAJA']
    
    reporte.append("DISCREPANCIAS POR SEVERIDAD")
    reporte.append("-" * 100)
    reporte.append(f"ALTA (Críticas): {len(alta)}")
    reporte.append(f"MEDIA (Importantes): {len(media)}")
    reporte.append(f"BAJA (Advertencias): {len(baja)}")
    reporte.append("")
    
    # Detalle de discrepancias
    reporte.append("DETALLE DE DISCREPANCIAS")
    reporte.append("=" * 100)
    
    for severidad in ['ALTA', 'MEDIA', 'BAJA']:
        discrepancias_severidad = [d for d in discrepancias if d['severidad'] == severidad]
        if discrepancias_severidad:
            reporte.append("")
            reporte.append(f"[{severidad}] {len(discrepancias_severidad)} discrepancias")
            reporte.append("-" * 100)
            
            for disc in discrepancias_severidad:
                reporte.append(f"  Tipo: {disc['tipo']}")
                reporte.append(f"  Tabla/Modelo: {disc['tabla']}")
                reporte.append(f"  Campo: {disc['campo']}")
                reporte.append(f"  Descripción: {disc['descripcion']}")
                reporte.append("")
    
    # Recomendaciones
    reporte.append("=" * 100)
    reporte.append("RECOMENDACIONES PARA CORRECCIÓN")
    reporte.append("=" * 100)
    reporte.append("")
    
    # Agrupar recomendaciones por tipo
    tipos_discrepancias = defaultdict(list)
    for disc in discrepancias:
        tipos_discrepancias[disc['tipo']].append(disc)
    
    for tipo, lista_disc in tipos_discrepancias.items():
        reporte.append(f"[{tipo}] {len(lista_disc)} casos")
        reporte.append("-" * 100)
        
        if tipo == 'ORM_SIN_SCHEMA':
            reporte.append("  ACCIÓN: Agregar campos faltantes a los schemas Pydantic")
            reporte.append("  IMPACTO: Los endpoints no pueden recibir/enviar estos campos")
            reporte.append("  EJEMPLO:")
            for disc in lista_disc[:3]:  # Mostrar primeros 3
                reporte.append(f"    - Agregar campo '{disc['campo']}' al schema {disc['tabla']}")
            reporte.append("")
        
        elif tipo == 'SCHEMA_SIN_ORM':
            reporte.append("  ACCIÓN: Agregar columnas faltantes a los modelos ORM o remover del schema")
            reporte.append("  IMPACTO: CRÍTICO - Los schemas esperan campos que no existen en BD")
            reporte.append("  EJEMPLO:")
            for disc in lista_disc[:3]:
                reporte.append(f"    - Verificar campo '{disc['campo']}' en modelo {disc['tabla']}")
            reporte.append("")
        
        elif tipo == 'FRONTEND_SIN_ORM':
            reporte.append("  ACCIÓN: Verificar si el campo debe existir en ORM o remover del frontend")
            reporte.append("  IMPACTO: CRÍTICO - El frontend intenta usar campos inexistentes")
            reporte.append("  EJEMPLO:")
            for disc in lista_disc[:3]:
                reporte.append(f"    - Verificar uso de '{disc['campo']}' en frontend para {disc['tabla']}")
            reporte.append("")
        
        elif tipo == 'ORM_SIN_FRONTEND':
            reporte.append("  ACCIÓN: Considerar usar estos campos en frontend o documentar por qué no se usan")
            reporte.append("  IMPACTO: BAJO - Campos disponibles pero no aprovechados")
            reporte.append("  EJEMPLO:")
            for disc in lista_disc[:5]:  # Mostrar más ejemplos
                reporte.append(f"    - Campo '{disc['campo']}' disponible en {disc['tabla']} pero no usado")
            reporte.append("")
    
    # Script SQL para verificación
    reporte.append("=" * 100)
    reporte.append("SCRIPT SQL PARA VERIFICACIÓN EN BD")
    reporte.append("=" * 100)
    reporte.append("")
    reporte.append("Ejecutar el siguiente script SQL para obtener estructura real de la BD:")
    reporte.append("")
    reporte.append(generar_script_sql_auditoria())
    reporte.append("")
    
    # Plan de acción
    reporte.append("=" * 100)
    reporte.append("PLAN DE ACCIÓN RECOMENDADO")
    reporte.append("=" * 100)
    reporte.append("")
    reporte.append("1. PRIORIDAD ALTA - Corregir discrepancias críticas:")
    reporte.append("   - Verificar campos en schemas que no existen en ORM")
    reporte.append("   - Verificar campos en frontend que no existen en ORM")
    reporte.append("   - Ejecutar script SQL para comparar con BD real")
    reporte.append("")
    reporte.append("2. PRIORIDAD MEDIA - Sincronizar schemas con ORM:")
    reporte.append("   - Agregar campos faltantes a schemas")
    reporte.append("   - Verificar tipos de datos coinciden")
    reporte.append("")
    reporte.append("3. PRIORIDAD BAJA - Optimizar uso de campos:")
    reporte.append("   - Evaluar si campos no usados deben usarse")
    reporte.append("   - Documentar campos disponibles pero no usados")
    reporte.append("")
    reporte.append("4. VERIFICACIÓN FINAL:")
    reporte.append("   - Ejecutar este script nuevamente después de correcciones")
    reporte.append("   - Comparar resultados con estructura real de BD")
    reporte.append("   - Documentar decisiones sobre campos no usados")
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
    print("AUDITORÍA INTEGRAL: COHERENCIA BD - BACKEND - FRONTEND")
    print("=" * 100)
    print("")
    
    # Realizar análisis
    resultados = analizar_coherencia_completa()
    
    print("\n[AUDITORIA] Detectando discrepancias...")
    discrepancias = detectar_discrepancias(resultados)
    
    print(f"\n[RESULTADOS] {len(discrepancias)} discrepancias encontradas")
    
    # Generar reporte
    reporte = generar_reporte(resultados, discrepancias)
    
    # Guardar reporte
    ruta_reporte = PROYECTO_ROOT / "Documentos" / "Auditorias" / "2025-01" / "AUDITORIA_INTEGRAL_COHERENCIA.md"
    ruta_reporte.parent.mkdir(parents=True, exist_ok=True)
    
    with open(ruta_reporte, 'w', encoding='utf-8') as f:
        f.write(reporte)
    
    # Guardar script SQL
    ruta_sql = PROYECTO_ROOT / "scripts" / "sql" / "AUDITORIA_INTEGRAL_ESTRUCTURA_BD.sql"
    with open(ruta_sql, 'w', encoding='utf-8') as f:
        f.write(generar_script_sql_auditoria())
    
    print(f"\n[REPORTE] Reporte guardado en: {ruta_reporte}")
    print(f"[SQL] Script SQL guardado en: {ruta_sql}")
    print("\n" + "=" * 100)
    print(reporte[:5000])  # Mostrar primeros 5000 caracteres
    print("\n... (reporte completo en archivo)")
    print("=" * 100)


if __name__ == "__main__":
    main()
