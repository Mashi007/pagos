"""
Comparación de estructura real de BD con modelos ORM y schemas
Usa la salida del script SQL AUDITORIA_INTEGRAL_ESTRUCTURA_BD.sql
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

# Estructura real de BD proporcionada por el usuario
ESTRUCTURA_BD = {
    'clientes': {
        'id': {'tipo': 'integer', 'nullable': False},
        'cedula': {'tipo': 'character varying', 'longitud': 20, 'nullable': False},
        'nombres': {'tipo': 'character varying', 'longitud': 100, 'nullable': False},
        'telefono': {'tipo': 'character varying', 'longitud': 50, 'nullable': False},
        'email': {'tipo': 'character varying', 'longitud': 100, 'nullable': False},
        'direccion': {'tipo': 'text', 'nullable': False},
        'fecha_nacimiento': {'tipo': 'date', 'nullable': False},
        'ocupacion': {'tipo': 'character varying', 'longitud': 100, 'nullable': False},
        'estado': {'tipo': 'character varying', 'longitud': 20, 'nullable': False},
        'activo': {'tipo': 'boolean', 'nullable': False},
        'fecha_registro': {'tipo': 'timestamp without time zone', 'nullable': False},
        'fecha_actualizacion': {'tipo': 'timestamp without time zone', 'nullable': False},
        'usuario_registro': {'tipo': 'character varying', 'longitud': 50, 'nullable': False},
        'notas': {'tipo': 'text', 'nullable': False},
    },
    'cuotas': {
        'id': {'tipo': 'integer', 'nullable': False},
        'prestamo_id': {'tipo': 'integer', 'nullable': False},
        'numero_cuota': {'tipo': 'integer', 'nullable': False},
        'fecha_vencimiento': {'tipo': 'date', 'nullable': False},
        'fecha_pago': {'tipo': 'date', 'nullable': True},
        'monto_cuota': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': False},
        'monto_capital': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': False},
        'monto_interes': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': False},
        'saldo_capital_inicial': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': False},
        'saldo_capital_final': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': False},
        'capital_pagado': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': True},
        'interes_pagado': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': True},
        'mora_pagada': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': True},
        'total_pagado': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': True},
        'capital_pendiente': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': False},
        'interes_pendiente': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': False},
        'dias_mora': {'tipo': 'integer', 'nullable': True},
        'monto_mora': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': True},
        'tasa_mora': {'tipo': 'numeric', 'precision': 5, 'scale': 2, 'nullable': True},
        'estado': {'tipo': 'character varying', 'longitud': 20, 'nullable': False},
        'observaciones': {'tipo': 'character varying', 'longitud': 500, 'nullable': True},
        'es_cuota_especial': {'tipo': 'boolean', 'nullable': True},
        'creado_en': {'tipo': 'timestamp with time zone', 'nullable': True},
        'actualizado_en': {'tipo': 'timestamp with time zone', 'nullable': True},
        'dias_morosidad': {'tipo': 'integer', 'nullable': True},
        'monto_morosidad': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': True},
    },
    'pagos': {
        'id': {'tipo': 'integer', 'nullable': False},
        'prestamo_id': {'tipo': 'integer', 'nullable': True},
        'numero_cuota': {'tipo': 'integer', 'nullable': True},
        'codigo_pago': {'tipo': 'character varying', 'longitud': 30, 'nullable': True},
        'monto_cuota_programado': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': True},
        'monto_pagado': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': False},
        'monto_capital': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': True},
        'monto_interes': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': True},
        'monto_mora': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': True},
        'descuento': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': True},
        'monto_total': {'tipo': 'numeric', 'precision': 12, 'scale': 2, 'nullable': True},
        'fecha_pago': {'tipo': 'timestamp without time zone', 'nullable': False},
        'fecha_vencimiento': {'tipo': 'date', 'nullable': True},
        'hora_pago': {'tipo': 'time without time zone', 'nullable': True},
        'dias_mora': {'tipo': 'integer', 'nullable': True},
        'tasa_mora': {'tipo': 'numeric', 'precision': 5, 'scale': 2, 'nullable': True},
        'metodo_pago': {'tipo': 'character varying', 'longitud': 20, 'nullable': True},
        'numero_operacion': {'tipo': 'character varying', 'longitud': 50, 'nullable': True},
        'comprobante': {'tipo': 'character varying', 'longitud': 50, 'nullable': True},
        'banco': {'tipo': 'character varying', 'longitud': 50, 'nullable': True},
        'estado': {'tipo': 'character varying', 'longitud': 20, 'nullable': True},
        'tipo_pago': {'tipo': 'character varying', 'longitud': 20, 'nullable': True},
        'observaciones': {'tipo': 'text', 'nullable': True},
        'usuario_registro': {'tipo': 'character varying', 'longitud': 50, 'nullable': True},
        'creado_en': {'tipo': 'timestamp without time zone', 'nullable': True},
        'cedula': {'tipo': 'character varying', 'longitud': 20, 'nullable': True},
        'fecha_registro': {'tipo': 'timestamp without time zone', 'nullable': False},
        'institucion_bancaria': {'tipo': 'character varying', 'longitud': 100, 'nullable': True},
        'referencia_pago': {'tipo': 'character varying', 'longitud': 100, 'nullable': False},
        'numero_documento': {'tipo': 'character varying', 'nullable': True},
        'documento_nombre': {'tipo': 'character varying', 'longitud': 255, 'nullable': True},
        'documento_tipo': {'tipo': 'character varying', 'longitud': 10, 'nullable': True},
        'documento_tamaño': {'tipo': 'integer', 'nullable': True},
        'documento_ruta': {'tipo': 'character varying', 'longitud': 500, 'nullable': True},
        'conciliado': {'tipo': 'boolean', 'nullable': True},
        'fecha_conciliacion': {'tipo': 'timestamp without time zone', 'nullable': True},
        'activo': {'tipo': 'boolean', 'nullable': True},
        'notas': {'tipo': 'text', 'nullable': True},
        'fecha_actualizacion': {'tipo': 'timestamp without time zone', 'nullable': True},
        'verificado_concordancia': {'tipo': 'character varying', 'longitud': 2, 'nullable': False},
        'monto': {'tipo': 'integer', 'nullable': True},
        'documento': {'tipo': 'character varying', 'longitud': 50, 'nullable': True},
        'cliente_id': {'tipo': 'integer', 'nullable': True},
    },
    'prestamos': {
        'id': {'tipo': 'integer', 'nullable': False},
        'cliente_id': {'tipo': 'integer', 'nullable': False},
        'cedula': {'tipo': 'character varying', 'longitud': 20, 'nullable': False},
        'nombres': {'tipo': 'character varying', 'longitud': 100, 'nullable': False},
        'total_financiamiento': {'tipo': 'numeric', 'precision': 15, 'scale': 2, 'nullable': False},
        'fecha_requerimiento': {'tipo': 'date', 'nullable': False},
        'modalidad_pago': {'tipo': 'character varying', 'longitud': 20, 'nullable': False},
        'numero_cuotas': {'tipo': 'integer', 'nullable': False},
        'cuota_periodo': {'tipo': 'numeric', 'precision': 15, 'scale': 2, 'nullable': False},
        'tasa_interes': {'tipo': 'numeric', 'precision': 5, 'scale': 2, 'nullable': False},
        'fecha_base_calculo': {'tipo': 'date', 'nullable': True},
        'producto': {'tipo': 'character varying', 'longitud': 100, 'nullable': False},
        'producto_financiero': {'tipo': 'character varying', 'longitud': 100, 'nullable': False},
        'estado': {'tipo': 'character varying', 'longitud': 20, 'nullable': False},
        'usuario_proponente': {'tipo': 'character varying', 'longitud': 100, 'nullable': False},
        'usuario_aprobador': {'tipo': 'character varying', 'longitud': 100, 'nullable': True},
        'observaciones': {'tipo': 'text', 'nullable': True},
        'informacion_desplegable': {'tipo': 'boolean', 'nullable': False},
        'fecha_registro': {'tipo': 'timestamp without time zone', 'nullable': False},
        'fecha_aprobacion': {'tipo': 'timestamp without time zone', 'nullable': True},
        'fecha_actualizacion': {'tipo': 'timestamp without time zone', 'nullable': False},
        'concesionario': {'tipo': 'character varying', 'longitud': 100, 'nullable': True},
        'analista': {'tipo': 'character varying', 'longitud': 100, 'nullable': True},
        'modelo_vehiculo': {'tipo': 'character varying', 'longitud': 100, 'nullable': True},
        'usuario_autoriza': {'tipo': 'character varying', 'longitud': 100, 'nullable': True},
        'ml_impago_nivel_riesgo_manual': {'tipo': 'character varying', 'longitud': 20, 'nullable': True},
        'ml_impago_probabilidad_manual': {'tipo': 'numeric', 'precision': 5, 'scale': 3, 'nullable': True},
        'concesionario_id': {'tipo': 'integer', 'nullable': True},
        'analista_id': {'tipo': 'integer', 'nullable': True},
        'modelo_vehiculo_id': {'tipo': 'integer', 'nullable': True},
        'valor_activo': {'tipo': 'numeric', 'precision': 15, 'scale': 2, 'nullable': True},
    },
    'users': {
        'id': {'tipo': 'integer', 'nullable': False},
        'email': {'tipo': 'character varying', 'longitud': 255, 'nullable': False},
        'nombre': {'tipo': 'character varying', 'longitud': 100, 'nullable': False},
        'apellido': {'tipo': 'character varying', 'longitud': 100, 'nullable': False},
        'hashed_password': {'tipo': 'character varying', 'longitud': 255, 'nullable': False},
        'rol': {'tipo': 'USER-DEFINED', 'nullable': False},
        'is_active': {'tipo': 'boolean', 'nullable': False},
        'created_at': {'tipo': 'timestamp with time zone', 'nullable': False},
        'updated_at': {'tipo': 'timestamp with time zone', 'nullable': True},
        'last_login': {'tipo': 'timestamp with time zone', 'nullable': True},
        'is_admin': {'tipo': 'boolean', 'nullable': False},
        'cargo': {'tipo': 'character varying', 'longitud': 100, 'nullable': True},
    },
    'notificaciones': {
        'id': {'tipo': 'integer', 'nullable': False},
        'user_id': {'tipo': 'integer', 'nullable': True},
        'cliente_id': {'tipo': 'integer', 'nullable': True},
        'destinatario_email': {'tipo': 'character varying', 'longitud': 255, 'nullable': True},
        'destinatario_telefono': {'tipo': 'character varying', 'longitud': 20, 'nullable': True},
        'destinatario_nombre': {'tipo': 'character varying', 'longitud': 255, 'nullable': True},
        'tipo': {'tipo': 'USER-DEFINED', 'nullable': False},
        'categoria': {'tipo': 'USER-DEFINED', 'nullable': False},
        'asunto': {'tipo': 'character varying', 'longitud': 255, 'nullable': True},
        'mensaje': {'tipo': 'text', 'nullable': False},
        'extra_data': {'tipo': 'json', 'nullable': True},
        'estado': {'tipo': 'USER-DEFINED', 'nullable': False},
        'intentos': {'tipo': 'integer', 'nullable': True},
        'max_intentos': {'tipo': 'integer', 'nullable': True},
        'programada_para': {'tipo': 'timestamp with time zone', 'nullable': True},
        'enviada_en': {'tipo': 'timestamp with time zone', 'nullable': True},
        'leida_en': {'tipo': 'timestamp with time zone', 'nullable': True},
        'respuesta_servicio': {'tipo': 'text', 'nullable': True},
        'error_mensaje': {'tipo': 'text', 'nullable': True},
        'prioridad': {'tipo': 'USER-DEFINED', 'nullable': False},
        'creado_en': {'tipo': 'timestamp with time zone', 'nullable': True},
        'actualizado_en': {'tipo': 'timestamp with time zone', 'nullable': True},
    }
}

# Mapeo de nombres de tablas BD a modelos ORM
MAPEO_TABLAS_MODELOS = {
    'clientes': 'cliente',
    'cuotas': 'amortizacion',  # La tabla se llama cuotas pero el modelo es amortizacion
    'pagos': 'pago',
    'prestamos': 'prestamo',
    'users': 'user',
    'notificaciones': 'notificacion',
}

# Mapeo de tipos PostgreSQL a SQLAlchemy
MAPEO_TIPOS_POSTGRESQL_A_SQLALCHEMY = {
    'integer': 'Integer',
    'character varying': 'String',
    'numeric': 'Numeric',
    'boolean': 'Boolean',
    'date': 'Date',
    'timestamp without time zone': 'DateTime',
    'timestamp with time zone': 'DateTime(timezone=True)',
    'time without time zone': 'Time',
    'text': 'Text',
    'json': 'JSON',
    'USER-DEFINED': 'Enum',  # Para tipos enum personalizados
}


def leer_modelo_orm(archivo_path: Path) -> Dict[str, Dict]:
    """Lee un modelo ORM y extrae sus columnas"""
    columnas = {}
    
    try:
        with open(archivo_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Buscar Column() assignments usando regex
        # Patrón: nombre_columna = Column(Tipo(...), ...)
        patron = r'(\w+)\s*=\s*Column\s*\(([^)]+)\)'
        
        for match in re.finditer(patron, contenido):
            nombre_columna = match.group(1)
            args_columna = match.group(2)
            
            # Extraer tipo
            tipo_match = re.search(r'(Integer|String|Numeric|Boolean|Date|DateTime|Time|Text|JSON|ForeignKey)', args_columna)
            tipo_columna = tipo_match.group(1) if tipo_match else None
            
            # Extraer nullable
            nullable_match = re.search(r'nullable\s*=\s*(True|False)', args_columna)
            nullable = nullable_match.group(1) == 'True' if nullable_match else True
            
            # Extraer longitud para String
            longitud_match = re.search(r'String\s*\((\d+)\)', args_columna)
            longitud = int(longitud_match.group(1)) if longitud_match else None
            
            # Extraer precisión para Numeric
            precision_match = re.search(r'Numeric\s*\((\d+)\s*,\s*(\d+)\)', args_columna)
            precision = int(precision_match.group(1)) if precision_match else None
            scale = int(precision_match.group(2)) if precision_match else None
            
            columnas[nombre_columna] = {
                'tipo': tipo_columna,
                'nullable': nullable,
                'longitud': longitud,
                'precision': precision,
                'scale': scale,
            }
    except Exception as e:
        print(f"Error leyendo modelo {archivo_path}: {e}")
    
    return columnas


def comparar_bd_con_orm():
    """Compara estructura de BD con modelos ORM"""
    discrepancias = []
    
    proyecto_root = Path(__file__).parent.parent.parent
    modelos_dir = proyecto_root / "backend" / "app" / "models"
    
    for tabla_bd, columnas_bd in ESTRUCTURA_BD.items():
        modelo_nombre = MAPEO_TABLAS_MODELOS.get(tabla_bd, tabla_bd)
        archivo_modelo = modelos_dir / f"{modelo_nombre}.py"
        
        if not archivo_modelo.exists():
            discrepancias.append({
                'tipo': 'MODELO_NO_EXISTE',
                'tabla_bd': tabla_bd,
                'modelo': modelo_nombre,
                'severidad': 'ALTA',
                'descripcion': f'Tabla {tabla_bd} existe en BD pero modelo {modelo_nombre} no existe'
            })
            continue
        
        columnas_orm = leer_modelo_orm(archivo_modelo)
        
        # Comparar columnas BD vs ORM
        for columna_bd, info_bd in columnas_bd.items():
            if columna_bd not in columnas_orm:
                discrepancias.append({
                    'tipo': 'BD_SIN_ORM',
                    'tabla': tabla_bd,
                    'columna': columna_bd,
                    'severidad': 'ALTA',
                    'descripcion': f'Columna {columna_bd} existe en BD pero no en modelo ORM {modelo_nombre}',
                    'tipo_bd': info_bd['tipo'],
                    'nullable_bd': info_bd['nullable']
                })
            else:
                # Verificar tipos y nullable
                info_orm = columnas_orm[columna_bd]
                
                # Comparar nullable
                if info_bd['nullable'] != info_orm['nullable']:
                    discrepancias.append({
                        'tipo': 'NULLABLE_DIFERENTE',
                        'tabla': tabla_bd,
                        'columna': columna_bd,
                        'severidad': 'MEDIA',
                        'descripcion': f'Columna {columna_bd}: nullable en BD={info_bd["nullable"]}, en ORM={info_orm["nullable"]}',
                        'nullable_bd': info_bd['nullable'],
                        'nullable_orm': info_orm['nullable']
                    })
                
                # Comparar longitudes para String
                if info_bd['tipo'] == 'character varying' and 'longitud' in info_bd:
                    if info_orm.get('longitud') and info_bd['longitud'] != info_orm['longitud']:
                        discrepancias.append({
                            'tipo': 'LONGITUD_DIFERENTE',
                            'tabla': tabla_bd,
                            'columna': columna_bd,
                            'severidad': 'MEDIA',
                            'descripcion': f'Columna {columna_bd}: longitud en BD={info_bd["longitud"]}, en ORM={info_orm["longitud"]}',
                            'longitud_bd': info_bd['longitud'],
                            'longitud_orm': info_orm['longitud']
                        })
        
        # Columnas en ORM pero no en BD
        for columna_orm in columnas_orm.keys():
            if columna_orm not in columnas_bd:
                discrepancias.append({
                    'tipo': 'ORM_SIN_BD',
                    'tabla': tabla_bd,
                    'columna': columna_orm,
                    'severidad': 'ALTA',
                    'descripcion': f'Columna {columna_orm} existe en modelo ORM pero no en BD {tabla_bd}'
                })
    
    return discrepancias


def generar_reporte_discrepancias(discrepancias: List[Dict]) -> str:
    """Genera reporte de discrepancias"""
    reporte = []
    reporte.append("=" * 100)
    reporte.append("REPORTE DE DISCREPANCIAS: BASE DE DATOS vs MODELOS ORM")
    reporte.append("=" * 100)
    reporte.append("")
    reporte.append(f"Fecha: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    reporte.append("")
    
    # Resumen
    alta = [d for d in discrepancias if d['severidad'] == 'ALTA']
    media = [d for d in discrepancias if d['severidad'] == 'MEDIA']
    
    reporte.append("RESUMEN EJECUTIVO")
    reporte.append("-" * 100)
    reporte.append(f"Total discrepancias: {len(discrepancias)}")
    reporte.append(f"  - ALTA (Críticas): {len(alta)}")
    reporte.append(f"  - MEDIA (Importantes): {len(media)}")
    reporte.append("")
    
    # Agrupar por tipo
    por_tipo = defaultdict(list)
    for disc in discrepancias:
        por_tipo[disc['tipo']].append(disc)
    
    reporte.append("DISCREPANCIAS POR TIPO")
    reporte.append("=" * 100)
    
    for tipo, lista_disc in por_tipo.items():
        reporte.append("")
        reporte.append(f"[{tipo}] {len(lista_disc)} casos")
        reporte.append("-" * 100)
        
        for disc in lista_disc:
            reporte.append(f"  Tabla: {disc['tabla']}")
            reporte.append(f"  Columna: {disc['columna']}")
            reporte.append(f"  Severidad: {disc['severidad']}")
            reporte.append(f"  Descripción: {disc['descripcion']}")
            if 'tipo_bd' in disc:
                reporte.append(f"  Tipo en BD: {disc['tipo_bd']}")
            if 'nullable_bd' in disc and 'nullable_orm' in disc:
                reporte.append(f"  Nullable BD: {disc['nullable_bd']}, ORM: {disc['nullable_orm']}")
            reporte.append("")
    
    # Recomendaciones
    reporte.append("=" * 100)
    reporte.append("RECOMENDACIONES PARA CORRECCIÓN")
    reporte.append("=" * 100)
    reporte.append("")
    
    if por_tipo.get('BD_SIN_ORM'):
        reporte.append("1. COLUMNAS EN BD SIN MODELO ORM (ALTA PRIORIDAD)")
        reporte.append("-" * 100)
        reporte.append("  Estas columnas existen en BD pero no están en los modelos ORM.")
        reporte.append("  ACCIÓN: Agregar estas columnas a los modelos ORM correspondientes.")
        reporte.append("")
        for disc in por_tipo['BD_SIN_ORM'][:10]:  # Primeros 10
            reporte.append(f"  - {disc['tabla']}.{disc['columna']} ({disc['tipo_bd']}, nullable={disc['nullable_bd']})")
        reporte.append("")
    
    if por_tipo.get('ORM_SIN_BD'):
        reporte.append("2. COLUMNAS EN MODELO ORM SIN BD (ALTA PRIORIDAD)")
        reporte.append("-" * 100)
        reporte.append("  Estas columnas están en modelos ORM pero no existen en BD.")
        reporte.append("  ACCIÓN: Verificar si deben agregarse a BD o removerse del modelo.")
        reporte.append("")
        for disc in por_tipo['ORM_SIN_BD'][:10]:
            reporte.append(f"  - {disc['tabla']}.{disc['columna']}")
        reporte.append("")
    
    if por_tipo.get('NULLABLE_DIFERENTE'):
        reporte.append("3. DIFERENCIAS EN NULLABLE (MEDIA PRIORIDAD)")
        reporte.append("-" * 100)
        reporte.append("  Estas columnas tienen diferente configuración de nullable.")
        reporte.append("  ACCIÓN: Sincronizar nullable entre BD y ORM.")
        reporte.append("")
        for disc in por_tipo['NULLABLE_DIFERENTE'][:10]:
            reporte.append(f"  - {disc['tabla']}.{disc['columna']}: BD={disc['nullable_bd']}, ORM={disc['nullable_orm']}")
        reporte.append("")
    
    if por_tipo.get('LONGITUD_DIFERENTE'):
        reporte.append("4. DIFERENCIAS EN LONGITUD (MEDIA PRIORIDAD)")
        reporte.append("-" * 100)
        reporte.append("  Estas columnas VARCHAR tienen diferentes longitudes.")
        reporte.append("  ACCIÓN: Sincronizar longitudes entre BD y ORM.")
        reporte.append("")
        for disc in por_tipo['LONGITUD_DIFERENTE'][:10]:
            reporte.append(f"  - {disc['tabla']}.{disc['columna']}: BD={disc['longitud_bd']}, ORM={disc['longitud_orm']}")
        reporte.append("")
    
    reporte.append("=" * 100)
    reporte.append("PLAN DE ACCIÓN")
    reporte.append("=" * 100)
    reporte.append("")
    reporte.append("1. PRIORIDAD ALTA - Corregir discrepancias críticas:")
    reporte.append("   - Agregar columnas faltantes en modelos ORM")
    reporte.append("   - Verificar columnas en ORM que no existen en BD")
    reporte.append("")
    reporte.append("2. PRIORIDAD MEDIA - Sincronizar configuración:")
    reporte.append("   - Corregir diferencias en nullable")
    reporte.append("   - Corregir diferencias en longitudes")
    reporte.append("")
    reporte.append("3. VERIFICACIÓN:")
    reporte.append("   - Ejecutar este script nuevamente después de correcciones")
    reporte.append("   - Verificar que no haya errores en aplicación")
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
    print("COMPARACIÓN: BASE DE DATOS vs MODELOS ORM")
    print("=" * 100)
    print("")
    
    print("[ANALISIS] Comparando estructura de BD con modelos ORM...")
    discrepancias = comparar_bd_con_orm()
    
    print(f"[RESULTADOS] {len(discrepancias)} discrepancias encontradas")
    
    # Generar reporte
    reporte = generar_reporte_discrepancias(discrepancias)
    
    # Guardar reporte
    proyecto_root = Path(__file__).parent.parent.parent
    ruta_reporte = proyecto_root / "Documentos" / "Auditorias" / "2025-01" / "DISCREPANCIAS_BD_VS_ORM.md"
    ruta_reporte.parent.mkdir(parents=True, exist_ok=True)
    
    with open(ruta_reporte, 'w', encoding='utf-8') as f:
        f.write(reporte)
    
    print(f"\n[REPORTE] Reporte guardado en: {ruta_reporte}")
    print("\n" + "=" * 100)
    print(reporte[:3000])  # Mostrar primeros 3000 caracteres
    print("\n... (reporte completo en archivo)")
    print("=" * 100)


if __name__ == "__main__":
    main()
