"""
Script para corregir nullable en modelos ORM según estructura real de BD
FASE 1: Correcciones críticas
"""

import re
from pathlib import Path
from typing import Dict

PROYECTO_ROOT = Path(__file__).parent.parent.parent
BACKEND_MODELS = PROYECTO_ROOT / "backend" / "app" / "models"

# Estructura de BD con nullable correcto
BD_NULLABLE = {
    'clientes': {
        'id': False,
        'cedula': False,
        'nombres': False,
        'telefono': False,
        'email': False,
        'direccion': False,
        'fecha_nacimiento': False,
        'ocupacion': False,
        'estado': False,
        'activo': False,
        'fecha_registro': False,
        'fecha_actualizacion': False,
        'usuario_registro': False,
        'notas': False,
    },
    'cuotas': {
        'id': False,
        'prestamo_id': False,
        'numero_cuota': False,
        'fecha_vencimiento': False,
        'fecha_pago': True,
        'monto_cuota': False,
        'monto_capital': False,
        'monto_interes': False,
        'saldo_capital_inicial': False,
        'saldo_capital_final': False,
        'capital_pagado': True,
        'interes_pagado': True,
        'mora_pagada': True,
        'total_pagado': True,
        'capital_pendiente': False,
        'interes_pendiente': False,
        'dias_mora': True,
        'monto_mora': True,
        'tasa_mora': True,
        'estado': False,
        'observaciones': True,
        'es_cuota_especial': True,
        'creado_en': True,
        'actualizado_en': True,
        'dias_morosidad': True,
        'monto_morosidad': True,
    },
    'pagos': {
        'id': False,
        'prestamo_id': True,
        'numero_cuota': True,
        'codigo_pago': True,
        'monto_cuota_programado': True,
        'monto_pagado': False,
        'monto_capital': True,
        'monto_interes': True,
        'monto_mora': True,
        'descuento': True,
        'monto_total': True,
        'fecha_pago': False,
        'fecha_vencimiento': True,
        'hora_pago': True,
        'dias_mora': True,
        'tasa_mora': True,
        'metodo_pago': True,
        'numero_operacion': True,
        'comprobante': True,
        'banco': True,
        'estado': True,
        'tipo_pago': True,
        'observaciones': True,
        'usuario_registro': True,
        'creado_en': True,
        'cedula': True,
        'fecha_registro': False,
        'institucion_bancaria': True,
        'referencia_pago': False,
        'numero_documento': True,
        'documento_nombre': True,
        'documento_tipo': True,
        'documento_tamaño': True,
        'documento_ruta': True,
        'conciliado': True,
        'fecha_conciliacion': True,
        'activo': True,
        'notas': True,
        'fecha_actualizacion': True,
        'verificado_concordancia': False,
        'monto': True,
        'documento': True,
        'cliente_id': True,
    },
    'prestamos': {
        'id': False,
        'cliente_id': False,
        'cedula': False,
        'nombres': False,
        'total_financiamiento': False,
        'fecha_requerimiento': False,
        'modalidad_pago': False,
        'numero_cuotas': False,
        'cuota_periodo': False,
        'tasa_interes': False,
        'fecha_base_calculo': True,
        'producto': False,
        'producto_financiero': False,
        'estado': False,
        'usuario_proponente': False,
        'usuario_aprobador': True,
        'observaciones': True,
        'informacion_desplegable': False,
        'fecha_registro': False,
        'fecha_aprobacion': True,
        'fecha_actualizacion': False,
        'concesionario': True,
        'analista': True,
        'modelo_vehiculo': True,
        'usuario_autoriza': True,
        'ml_impago_nivel_riesgo_manual': True,
        'ml_impago_probabilidad_manual': True,
        'concesionario_id': True,
        'analista_id': True,
        'modelo_vehiculo_id': True,
        'valor_activo': True,
    },
    'users': {
        'id': False,
        'email': False,
        'nombre': False,
        'apellido': False,
        'hashed_password': False,
        'rol': False,
        'is_active': False,
        'created_at': False,
        'updated_at': True,
        'last_login': True,
        'is_admin': False,
        'cargo': True,
    },
}

MAPEO_TABLAS_MODELOS = {
    'clientes': 'cliente',
    'cuotas': 'amortizacion',
    'pagos': 'pago',
    'prestamos': 'prestamo',
    'users': 'user',
}


def corregir_nullable_en_modelo(archivo_path: Path, tabla_bd: str, columnas_bd: Dict[str, bool]):
    """Corrige nullable en un modelo ORM"""
    cambios_realizados = []
    
    try:
        with open(archivo_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        contenido_original = contenido
        
        # Para cada columna en BD, buscar y corregir en el modelo
        for columna_bd, nullable_bd in columnas_bd.items():
            # Buscar patrón: columna = Column(...)
            patron = rf'(\s+)({columna_bd})\s*=\s*Column\s*\(([^)]+)\)'
            
            def reemplazar_nullable(match):
                indentacion = match.group(1)
                nombre_columna = match.group(2)
                args_columna = match.group(3)
                
                # Verificar si ya tiene nullable explícito
                if 'nullable=' in args_columna:
                    # Reemplazar nullable existente
                    nuevo_args = re.sub(
                        r'nullable\s*=\s*(True|False)',
                        f'nullable={nullable_bd}',
                        args_columna
                    )
                    cambios_realizados.append(f"{nombre_columna}: nullable corregido a {nullable_bd}")
                else:
                    # Agregar nullable si no existe
                    # Insertar nullable antes del último paréntesis o después del tipo
                    nuevo_args = args_columna.rstrip()
                    if nuevo_args and not nuevo_args.endswith(','):
                        nuevo_args += ','
                    nuevo_args += f' nullable={nullable_bd}'
                    cambios_realizados.append(f"{nombre_columna}: nullable agregado como {nullable_bd}")
                
                return f"{indentacion}{nombre_columna} = Column({nuevo_args})"
            
            contenido = re.sub(patron, reemplazar_nullable, contenido)
        
        # Guardar solo si hubo cambios
        if contenido != contenido_original:
            with open(archivo_path, 'w', encoding='utf-8') as f:
                f.write(contenido)
            return cambios_realizados
        
    except Exception as e:
        print(f"Error corrigiendo {archivo_path}: {e}")
    
    return cambios_realizados


def main():
    """Función principal"""
    import sys
    import io
    
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 100)
    print("FASE 1: CORRECCIÓN DE NULLABLE EN MODELOS ORM")
    print("=" * 100)
    print("")
    
    total_cambios = 0
    
    for tabla_bd, columnas_bd in BD_NULLABLE.items():
        modelo_nombre = MAPEO_TABLAS_MODELOS.get(tabla_bd, tabla_bd)
        archivo_modelo = BACKEND_MODELS / f"{modelo_nombre}.py"
        
        if not archivo_modelo.exists():
            print(f"[SKIP] Modelo {modelo_nombre}.py no existe")
            continue
        
        print(f"[PROCESANDO] {modelo_nombre}.py (tabla: {tabla_bd})...")
        cambios = corregir_nullable_en_modelo(archivo_modelo, tabla_bd, columnas_bd)
        
        if cambios:
            print(f"  ✅ {len(cambios)} cambios realizados:")
            for cambio in cambios[:10]:  # Mostrar primeros 10
                print(f"    - {cambio}")
            if len(cambios) > 10:
                print(f"    ... y {len(cambios) - 10} más")
            total_cambios += len(cambios)
        else:
            print(f"  ℹ️  Sin cambios necesarios")
        print("")
    
    print("=" * 100)
    print(f"RESUMEN: {total_cambios} correcciones de nullable realizadas")
    print("=" * 100)
    print("")
    print("PRÓXIMOS PASOS:")
    print("1. Verificar que los modelos compilen correctamente")
    print("2. Ejecutar tests si existen")
    print("3. Ejecutar comparar_bd_con_orm.py para verificar correcciones")
    print("")


if __name__ == "__main__":
    main()
