#!/usr/bin/env python3
"""
Generador de Plantilla Excel MEJORADA para Carga Masiva de Clientes
==================================================================

Plantilla optimizada con:
- Instrucciones en Hoja 1
- Solo 2 hojas: Instrucciones + Plantilla
- Listas desplegables basicas
"""

import pandas as pd
from datetime import datetime
import os

def crear_plantilla_mejorada():
    """Crear plantilla Excel mejorada"""
    
    # Datos de configuracion (valores por defecto)
    modelos_vehiculos = [
        "Toyota Corolla 2023",
        "Honda Civic 2024", 
        "Nissan Sentra 2023",
        "Hyundai Elantra 2024",
        "Mazda 3 2023",
        "Kia Forte 2024"
    ]
    
    concesionarios = [
        "AutoMax Quito",
        "AutoCenter Guayaquil", 
        "CarDealer Cuenca",
        "AutoShop Ambato",
        "MotorCity Manta",
        "AutoPlaza Loja"
    ]
    
    analistas = [
        "Maria Gonzalez",
        "Carlos Rodriguez",
        "Ana Fernandez", 
        "Luis Martinez",
        "Patricia Lopez",
        "Roberto Silva"
    ]
    
    # Definir columnas segun el modelo Cliente
    columnas = [
        "cedula",           # String(20), unique, NOT NULL
        "nombres",          # String(100), NOT NULL
        "apellidos",        # String(100), NOT NULL
        "telefono",         # String(15), nullable
        "email",            # String(100), nullable
        "direccion",        # Text, nullable
        "fecha_nacimiento", # Date, nullable (formato: YYYY-MM-DD)
        "ocupacion",        # String(100), nullable
        "modelo_vehiculo",  # String(100), nullable - LISTA DESPLEGABLE
        "concesionario",    # String(100), nullable - LISTA DESPLEGABLE
        "analista",         # String(100), nullable - LISTA DESPLEGABLE
        "estado",           # String(20), default 'ACTIVO'
        "notas"             # Text, nullable
    ]
    
    # Crear archivo Excel
    nombre_archivo = f"plantilla_clientes_mejorada_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    # HOJA 1: INSTRUCCIONES
    instrucciones = [
        ["INSTRUCCIONES PARA CARGA MASIVA DE CLIENTES"],
        [""],
        ["1. FORMATO DE ARCHIVO:"],
        ["   - Archivo Excel (.xlsx)"],
        ["   - Primera fila: encabezados de columnas"],
        ["   - Datos desde la segunda fila"],
        [""],
        ["2. CAMPOS REQUERIDOS:"],
        ["   - cedula: Cedula unica (maximo 20 caracteres)"],
        ["   - nombres: Nombres completos (maximo 100 caracteres)"],
        ["   - apellidos: Apellidos completos (maximo 100 caracteres)"],
        [""],
        ["3. CAMPOS OPCIONALES:"],
        ["   - telefono: Numero de telefono (maximo 15 caracteres)"],
        ["   - email: Correo electronico valido"],
        ["   - direccion: Direccion completa"],
        ["   - fecha_nacimiento: Formato YYYY-MM-DD"],
        ["   - ocupacion: Ocupacion del cliente"],
        ["   - modelo_vehiculo: Seleccionar de lista desplegable"],
        ["   - concesionario: Seleccionar de lista desplegable"],
        ["   - analista: Seleccionar de lista desplegable"],
        ["   - estado: ACTIVO o INACTIVO"],
        ["   - notas: Observaciones adicionales"],
        [""],
        ["4. LISTAS DESPLEGABLES DISPONIBLES:"],
        [""],
        ["MODELOS DE VEHICULOS:"],
    ]
    
    # Agregar modelos de vehiculos
    for modelo in modelos_vehiculos:
        instrucciones.append([f"   - {modelo}"])
    
    instrucciones.extend([
        [""],
        ["CONCESIONARIOS:"],
    ])
    
    # Agregar concesionarios
    for concesionario in concesionarios:
        instrucciones.append([f"   - {concesionario}"])
    
    instrucciones.extend([
        [""],
        ["ANALISTAS:"],
    ])
    
    # Agregar analistas
    for analista in analistas:
        instrucciones.append([f"   - {analista}"])
    
    instrucciones.extend([
        [""],
        ["5. VALIDACIONES:"],
        ["   - Cedula debe ser unica en el sistema"],
        ["   - Email debe tener formato valido"],
        ["   - Fecha de nacimiento en formato YYYY-MM-DD"],
        ["   - Estado debe ser ACTIVO o INACTIVO"],
        ["   - Usar solo valores de las listas desplegables"],
        [""],
        ["6. EJEMPLOS DE DATOS VALIDOS:"],
        ["   - cedula: '1234567890'"],
        ["   - nombres: 'Juan Carlos'"],
        ["   - apellidos: 'Perez Garcia'"],
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
        ["   - Verificar que las cedulas no esten duplicadas"],
        ["   - Usar valores exactos de las listas desplegables"]
    ])
    
    # HOJA 2: PLANTILLA CON EJEMPLO
    ejemplo = {
        "cedula": "1234567890",
        "nombres": "Juan Carlos",
        "apellidos": "Perez Garcia",
        "telefono": "0987654321",
        "email": "juan.perez@email.com",
        "direccion": "Av. Principal 123, Quito",
        "fecha_nacimiento": "1990-05-15",
        "ocupacion": "Ingeniero",
        "modelo_vehiculo": "Toyota Corolla 2023",
        "concesionario": "AutoMax Quito",
        "analista": "Maria Gonzalez",
        "estado": "ACTIVO",
        "notas": "Cliente preferencial"
    }
    
    # Crear DataFrames
    df_instrucciones = pd.DataFrame(instrucciones)
    df_plantilla = pd.DataFrame([ejemplo])
    
    # Crear archivo Excel
    with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
        df_instrucciones.to_excel(writer, sheet_name='Instrucciones', index=False, header=False)
        df_plantilla.to_excel(writer, sheet_name='Plantilla_Clientes', index=False)
    
    print(f"Plantilla Excel mejorada creada: {nombre_archivo}")
    print(f"Ubicacion: {os.path.abspath(nombre_archivo)}")
    print(f"Hojas incluidas:")
    print(f"   - Instrucciones: Guia completa de uso")
    print(f"   - Plantilla_Clientes: Con ejemplo y referencias")
    print(f"\nReferencias incluidas:")
    print(f"   - modelo_vehiculo: {len(modelos_vehiculos)} opciones")
    print(f"   - concesionario: {len(concesionarios)} opciones")
    print(f"   - analista: {len(analistas)} opciones")
    print(f"   - estado: ACTIVO, INACTIVO")
    
    return nombre_archivo

if __name__ == "__main__":
    print("GENERANDO PLANTILLA EXCEL MEJORADA PARA CLIENTES")
    print("=" * 60)
    
    # Crear plantilla mejorada
    archivo = crear_plantilla_mejorada()
    
    print("\n" + "=" * 60)
    print("RESUMEN DE LA PLANTILLA MEJORADA:")
    print("=" * 60)
    
    # Mostrar columnas
    columnas = [
        "cedula", "nombres", "apellidos", "telefono", "email",
        "direccion", "fecha_nacimiento", "ocupacion", "modelo_vehiculo",
        "concesionario", "analista", "estado", "notas"
    ]
    
    print("COLUMNAS INCLUIDAS:")
    for i, col in enumerate(columnas, 1):
        print(f"   {i:2d}. {col}")
    
    print(f"\nArchivo creado: {archivo}")
    print("Listo para usar con referencias de configuracion")
