#!/usr/bin/env python3
"""
Generador de Plantilla Excel para Carga Masiva de Clientes
=========================================================

Este script genera una plantilla Excel con:
- Columnas correctas según el modelo Cliente
- Validaciones de datos
- Ejemplos de formato
- Instrucciones de uso
"""

import pandas as pd
from datetime import datetime, date
import os

def crear_plantilla_clientes():
    """Crear plantilla Excel para carga masiva de clientes"""
    
    # Definir columnas según el modelo Cliente
    columnas = [
        # Datos personales (requeridos)
        "cedula",           # String(20), unique, NOT NULL
        "nombres",          # String(100), NOT NULL
        "apellidos",        # String(100), NOT NULL
        
        # Datos personales (opcionales)
        "telefono",         # String(15), nullable
        "email",            # String(100), nullable
        "direccion",        # Text, nullable
        "fecha_nacimiento", # Date, nullable (formato: YYYY-MM-DD)
        "ocupacion",        # String(100), nullable
        
        # Datos de configuración (opcionales)
        "modelo_vehiculo",  # String(100), nullable
        "concesionario",    # String(100), nullable
        "analista",         # String(100), nullable
        
        # Datos de control
        "estado",           # String(20), default 'ACTIVO'
        "notas"             # Text, nullable
    ]
    
    # Crear DataFrame con ejemplos
    ejemplos = [
        {
            "cedula": "1234567890",
            "nombres": "Juan Carlos",
            "apellidos": "Pérez García",
            "telefono": "0987654321",
            "email": "juan.perez@email.com",
            "direccion": "Av. Principal 123, Quito",
            "fecha_nacimiento": "1990-05-15",
            "ocupacion": "Ingeniero",
            "modelo_vehiculo": "Toyota Corolla 2023",
            "concesionario": "AutoMax Quito",
            "analista": "María González",
            "estado": "ACTIVO",
            "notas": "Cliente preferencial"
        },
        {
            "cedula": "0987654321",
            "nombres": "Ana María",
            "apellidos": "López Martínez",
            "telefono": "0998765432",
            "email": "ana.lopez@email.com",
            "direccion": "Calle Secundaria 456, Guayaquil",
            "fecha_nacimiento": "1985-12-20",
            "ocupacion": "Doctora",
            "modelo_vehiculo": "Honda Civic 2024",
            "concesionario": "AutoCenter Guayaquil",
            "analista": "Carlos Rodríguez",
            "estado": "ACTIVO",
            "notas": "Primera compra"
        }
    ]
    
    # Crear DataFrame
    df = pd.DataFrame(ejemplos)
    
    # Crear archivo Excel con múltiples hojas
    nombre_archivo = f"plantilla_clientes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
        # Hoja 1: Plantilla con ejemplos
        df.to_excel(writer, sheet_name='Plantilla_Clientes', index=False)
        
        # Hoja 2: Instrucciones
        instrucciones = [
            ["INSTRUCCIONES PARA CARGA MASIVA DE CLIENTES"],
            [""],
            ["1. FORMATO DE ARCHIVO:"],
            ["   - Archivo Excel (.xlsx)"],
            ["   - Primera fila: encabezados de columnas"],
            ["   - Datos desde la segunda fila"],
            [""],
            ["2. CAMPOS REQUERIDOS:"],
            ["   - cedula: Cédula única (máximo 20 caracteres)"],
            ["   - nombres: Nombres completos (máximo 100 caracteres)"],
            ["   - apellidos: Apellidos completos (máximo 100 caracteres)"],
            [""],
            ["3. CAMPOS OPCIONALES:"],
            ["   - telefono: Número de teléfono (máximo 15 caracteres)"],
            ["   - email: Correo electrónico válido"],
            ["   - direccion: Dirección completa"],
            ["   - fecha_nacimiento: Formato YYYY-MM-DD"],
            ["   - ocupacion: Ocupación del cliente"],
            ["   - modelo_vehiculo: Modelo del vehículo"],
            ["   - concesionario: Nombre del concesionario"],
            ["   - analista: Nombre del analista asignado"],
            ["   - estado: ACTIVO o INACTIVO"],
            ["   - notas: Observaciones adicionales"],
            [""],
            ["4. VALIDACIONES:"],
            ["   - Cédula debe ser única en el sistema"],
            ["   - Email debe tener formato válido"],
            ["   - Fecha de nacimiento en formato YYYY-MM-DD"],
            ["   - Estado debe ser ACTIVO o INACTIVO"],
            [""],
            ["5. CONFIGURACIÓN:"],
            ["   - modelo_vehiculo: Debe existir en /api/v1/modelos-vehiculos"],
            ["   - concesionario: Debe existir en /api/v1/concesionarios"],
            ["   - analista: Debe existir en /api/v1/analistas"],
            [""],
            ["6. EJEMPLOS DE DATOS VÁLIDOS:"],
            ["   - cedula: '1234567890'"],
            ["   - nombres: 'Juan Carlos'"],
            ["   - apellidos: 'Pérez García'"],
            ["   - telefono: '0987654321'"],
            ["   - email: 'juan.perez@email.com'"],
            ["   - fecha_nacimiento: '1990-05-15'"],
            ["   - estado: 'ACTIVO'"],
            [""],
            ["7. NOTAS IMPORTANTES:"],
            ["   - No eliminar las columnas"],
            ["   - No cambiar el orden de las columnas"],
            ["   - Usar solo caracteres ASCII"],
            ["   - Evitar caracteres especiales en nombres"],
            ["   - Verificar que las cédulas no estén duplicadas"]
        ]
        
        df_instrucciones = pd.DataFrame(instrucciones)
        df_instrucciones.to_excel(writer, sheet_name='Instrucciones', index=False, header=False)
        
        # Hoja 3: Plantilla vacía para llenar
        df_vacio = pd.DataFrame(columns=columnas)
        df_vacio.to_excel(writer, sheet_name='Plantilla_Vacia', index=False)
        
        # Hoja 4: Referencias de configuración
        referencias = [
            ["REFERENCIAS DE CONFIGURACIÓN"],
            [""],
            ["MODELOS DE VEHÍCULOS DISPONIBLES:"],
            ["(Obtener desde /api/v1/modelos-vehiculos)"],
            ["- Toyota Corolla 2023"],
            ["- Honda Civic 2024"],
            ["- Nissan Sentra 2023"],
            ["- Hyundai Elantra 2024"],
            [""],
            ["CONCESIONARIOS DISPONIBLES:"],
            ["(Obtener desde /api/v1/concesionarios)"],
            ["- AutoMax Quito"],
            ["- AutoCenter Guayaquil"],
            ["- CarDealer Cuenca"],
            ["- AutoShop Ambato"],
            [""],
            ["ANALISTAS DISPONIBLES:"],
            ["(Obtener desde /api/v1/analistas)"],
            ["- María González"],
            ["- Carlos Rodríguez"],
            ["- Ana Fernández"],
            ["- Luis Martínez"]
        ]
        
        df_referencias = pd.DataFrame(referencias)
        df_referencias.to_excel(writer, sheet_name='Referencias', index=False, header=False)
    
    print(f"✅ Plantilla Excel creada: {nombre_archivo}")
    print(f"📊 Ubicación: {os.path.abspath(nombre_archivo)}")
    print(f"📋 Hojas incluidas:")
    print(f"   - Plantilla_Clientes: Ejemplos de datos")
    print(f"   - Instrucciones: Guía de uso")
    print(f"   - Plantilla_Vacia: Para llenar con datos")
    print(f"   - Referencias: Valores de configuración")
    
    return nombre_archivo

def crear_endpoint_descarga():
    """Crear endpoint para descargar plantilla"""
    
    endpoint_code = '''
@router.get("/plantilla-clientes")
async def descargar_plantilla_clientes(
    response: Response,
    current_user: User = Depends(get_current_user)
):
    """
    📊 Descargar plantilla Excel para carga masiva de clientes
    
    Características:
    - Plantilla con columnas correctas
    - Ejemplos de datos válidos
    - Instrucciones de uso
    - Referencias de configuración
    """
    try:
        logger.info(f"Descargando plantilla clientes - Usuario: {current_user.email}")
        
        # Crear plantilla temporal
        plantilla_path = crear_plantilla_clientes()
        
        # Configurar respuesta para descarga
        response.headers["Content-Disposition"] = "attachment; filename=plantilla_clientes.xlsx"
        response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        # Leer y enviar archivo
        with open(plantilla_path, "rb") as file:
            content = file.read()
        
        # Eliminar archivo temporal
        os.remove(plantilla_path)
        
        return Response(content=content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
    except Exception as e:
        logger.error(f"Error descargando plantilla: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error generando plantilla Excel"
        )
'''
    
    print("✅ Código de endpoint generado:")
    print(endpoint_code)
    
    return endpoint_code

if __name__ == "__main__":
    print("🚀 GENERANDO PLANTILLA EXCEL PARA CLIENTES")
    print("=" * 50)
    
    # Crear plantilla
    archivo = crear_plantilla_clientes()
    
    print("\n" + "=" * 50)
    print("📋 RESUMEN DE LA PLANTILLA:")
    print("=" * 50)
    
    # Mostrar columnas
    columnas = [
        "cedula", "nombres", "apellidos", "telefono", "email",
        "direccion", "fecha_nacimiento", "ocupacion", "modelo_vehiculo",
        "concesionario", "analista", "estado", "notas"
    ]
    
    print("📊 COLUMNAS INCLUIDAS:")
    for i, col in enumerate(columnas, 1):
        print(f"   {i:2d}. {col}")
    
    print(f"\n✅ Archivo creado: {archivo}")
    print("🎯 Listo para usar en carga masiva de clientes")
