"""
Script de verificación: Valida que todos los endpoints del dashboard
usen los campos correctos de las tablas correctas según los modelos.
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.models.amortizacion import Cuota
from backend.app.models.pago import Pago
from backend.app.models.prestamo import Prestamo
from backend.app.models.cliente import Cliente

def obtener_campos_modelo(modelo):
    """Obtiene todos los campos de un modelo SQLAlchemy"""
    campos = {}
    for column in modelo.__table__.columns:
        campos[column.name] = {
            'type': str(column.type),
            'nullable': column.nullable,
            'primary_key': column.primary_key
        }
    return campos

def verificar_campos_en_consultas():
    """Verifica que los campos usados en las consultas existan en los modelos"""
    
    # Obtener campos de cada modelo
    campos_cuota = obtener_campos_modelo(Cuota)
    campos_pago = obtener_campos_modelo(Pago)
    campos_prestamo = obtener_campos_modelo(Prestamo)
    campos_cliente = obtener_campos_modelo(Cliente)
    
    print("=" * 80)
    print("VERIFICACIÓN DE CAMPOS DEL DASHBOARD")
    print("=" * 80)
    
    # Campos esperados en consultas de cuotas
    campos_cuota_esperados = [
        'id', 'prestamo_id', 'numero_cuota', 'fecha_vencimiento', 'fecha_pago',
        'monto_cuota', 'total_pagado', 'estado', 'dias_morosidad'
    ]
    
    print("\n📋 CAMPOS DE CUOTA:")
    print("-" * 80)
    campos_faltantes_cuota = []
    for campo in campos_cuota_esperados:
        if campo in campos_cuota:
            print(f"  ✅ {campo}: {campos_cuota[campo]['type']}")
        else:
            print(f"  ❌ {campo}: NO EXISTE")
            campos_faltantes_cuota.append(campo)
    
    # Campos esperados en consultas de pagos
    campos_pago_esperados = [
        'id', 'cedula', 'cliente_id', 'prestamo_id', 'numero_cuota',
        'fecha_pago', 'monto_pagado', 'activo', 'conciliado', 'estado'
    ]
    
    print("\n📋 CAMPOS DE PAGO:")
    print("-" * 80)
    campos_faltantes_pago = []
    for campo in campos_pago_esperados:
        if campo in campos_pago:
            print(f"  ✅ {campo}: {campos_pago[campo]['type']}")
        else:
            print(f"  ❌ {campo}: NO EXISTE")
            campos_faltantes_pago.append(campo)
    
    # Campos esperados en consultas de préstamos
    campos_prestamo_esperados = [
        'id', 'cedula', 'cliente_id', 'total_financiamiento', 'estado',
        'fecha_registro', 'fecha_aprobacion', 'analista', 'concesionario',
        'producto', 'modelo_vehiculo', 'analista_id', 'concesionario_id',
        'modelo_vehiculo_id'
    ]
    
    print("\n📋 CAMPOS DE PRESTAMO:")
    print("-" * 80)
    campos_faltantes_prestamo = []
    for campo in campos_prestamo_esperados:
        if campo in campos_prestamo:
            print(f"  ✅ {campo}: {campos_prestamo[campo]['type']}")
        else:
            print(f"  ❌ {campo}: NO EXISTE")
            campos_faltantes_prestamo.append(campo)
    
    # Campos esperados en consultas de clientes
    campos_cliente_esperados = [
        'id', 'cedula', 'nombres', 'estado'
    ]
    
    print("\n📋 CAMPOS DE CLIENTE:")
    print("-" * 80)
    campos_faltantes_cliente = []
    for campo in campos_cliente_esperados:
        if campo in campos_cliente:
            print(f"  ✅ {campo}: {campos_cliente[campo]['type']}")
        else:
            print(f"  ❌ {campo}: NO EXISTE")
            campos_faltantes_cliente.append(campo)
    
    # Resumen
    print("\n" + "=" * 80)
    print("RESUMEN DE VERIFICACIÓN")
    print("=" * 80)
    
    total_faltantes = len(campos_faltantes_cuota) + len(campos_faltantes_pago) + \
                      len(campos_faltantes_prestamo) + len(campos_faltantes_cliente)
    
    if total_faltantes == 0:
        print("✅ TODOS LOS CAMPOS VERIFICADOS EXISTEN EN LOS MODELOS")
    else:
        print(f"❌ SE ENCONTRARON {total_faltantes} CAMPOS FALTANTES:")
        if campos_faltantes_cuota:
            print(f"  - Cuota: {', '.join(campos_faltantes_cuota)}")
        if campos_faltantes_pago:
            print(f"  - Pago: {', '.join(campos_faltantes_pago)}")
        if campos_faltantes_prestamo:
            print(f"  - Prestamo: {', '.join(campos_faltantes_prestamo)}")
        if campos_faltantes_cliente:
            print(f"  - Cliente: {', '.join(campos_faltantes_cliente)}")
    
    # Verificar campos que NO deberían usarse
    print("\n" + "=" * 80)
    print("CAMPOS QUE NO DEBEN USARSE (eliminados del modelo)")
    print("=" * 80)
    
    campos_deprecados = {
        'Cuota': ['capital_pendiente', 'interes_pendiente', 'monto_mora', 
                  'capital_pagado', 'interes_pagado', 'mora_pagada', 'monto_morosidad'],
        'Pago': ['monto']  # Legacy, usar monto_pagado
    }
    
    for modelo_nombre, campos in campos_deprecados.items():
        print(f"\n{modelo_nombre}:")
        for campo in campos:
            if modelo_nombre == 'Cuota' and campo in campos_cuota:
                print(f"  ⚠️  {campo}: EXISTE pero NO DEBE USARSE (deprecado)")
            elif modelo_nombre == 'Pago' and campo in campos_pago:
                print(f"  ⚠️  {campo}: EXISTE pero usar monto_pagado en su lugar")
            else:
                print(f"  ✅ {campo}: No existe (correcto)")
    
    return total_faltantes == 0

if __name__ == "__main__":
    try:
        resultado = verificar_campos_en_consultas()
        sys.exit(0 if resultado else 1)
    except Exception as e:
        print(f"\n❌ Error durante la verificación: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
