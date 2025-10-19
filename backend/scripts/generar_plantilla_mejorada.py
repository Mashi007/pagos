#!/usr/bin/env python3
"""
Generador de Plantilla Excel MEJORADA para Carga Masiva de Clientes
==================================================================

Plantilla optimizada con:
- Instrucciones en Hoja 1
- Listas desplegables desde configuracion
- Solo 2 hojas: Instrucciones + Plantilla
"""

import pandas as pd
from datetime import datetime
import os
import requests
import json

def obtener_datos_configuracion():
    """Obtener datos reales de configuracion desde la API"""
    
    # URLs de la API (ajustar segun el entorno)
    base_url = "https://pagos-f2qf.onrender.com"  # URL de produccion
    
    datos = {
        "modelos_vehiculos": [],
        "concesionarios": [],
        "analistas": []
    }
    
    try:
        # Obtener modelos de vehiculos
        try:
            response = requests.get(f"{base_url}/api/v1/modelos-vehiculos?limit=100", timeout=10)
            if response.status_code == 200:
                modelos_data = response.json()
                if isinstance(modelos_data, list):
                    datos["modelos_vehiculos"] = [item.get("nombre", "") for item in modelos_data if item.get("nombre")]
                elif isinstance(modelos_data, dict) and "items" in modelos_data:
                    datos["modelos_vehiculos"] = [item.get("nombre", "") for item in modelos_data["items"] if item.get("nombre")]
        except:
            datos["modelos_vehiculos"] = ["Toyota Corolla 2023", "Honda Civic 2024", "Nissan Sentra 2023"]
        
        # Obtener concesionarios
        try:
            response = requests.get(f"{base_url}/api/v1/concesionarios?limit=100", timeout=10)
            if response.status_code == 200:
                concesionarios_data = response.json()
                if isinstance(concesionarios_data, list):
                    datos["concesionarios"] = [item.get("nombre", "") for item in concesionarios_data if item.get("nombre")]
                elif isinstance(concesionarios_data, dict) and "items" in concesionarios_data:
                    datos["concesionarios"] = [item.get("nombre", "") for item in concesionarios_data["items"] if item.get("nombre")]
        except:
            datos["concesionarios"] = ["AutoMax Quito", "AutoCenter Guayaquil", "CarDealer Cuenca"]
        
        # Obtener analistas
        try:
            response = requests.get(f"{base_url}/api/v1/analistas?limit=100", timeout=10)
            if response.status_code == 200:
                analistas_data = response.json()
                if isinstance(analistas_data, list):
                    datos["analistas"] = [item.get("nombre", "") for item in analistas_data if item.get("nombre")]
                elif isinstance(analistas_data, dict) and "items" in analistas_data:
                    datos["analistas"] = [item.get("nombre", "") for item in analistas_data["items"] if item.get("nombre")]
        except:
            datos["analistas"] = ["Maria Gonzalez", "Carlos Rodriguez", "Ana Fernandez"]
            
    except Exception as e:
        print(f"Error obteniendo datos de configuracion: {e}")
        # Valores por defecto
        datos = {
            "modelos_vehiculos": ["Toyota Corolla 2023", "Honda Civic 2024", "Nissan Sentra 2023"],
            "concesionarios": ["AutoMax Quito", "AutoCenter Guayaquil", "CarDealer Cuenca"],
            "analistas": ["Maria Gonzalez", "Carlos Rodriguez", "Ana Fernandez"]
        }
    
    return datos

def crear_plantilla_mejorada():
    """Crear plantilla Excel mejorada con listas desplegables"""
    
    # Obtener datos reales de configuracion
    datos_config = obtener_datos_configuracion()
    
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
    
    with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
        
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
            ["4. LISTAS DESPLEGABLES:"],
            ["   - modelo_vehiculo: Valores validos desde configuracion"],
            ["   - concesionario: Valores validos desde configuracion"],
            ["   - analista: Valores validos desde configuracion"],
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
        ]
        
        df_instrucciones = pd.DataFrame(instrucciones)
        df_instrucciones.to_excel(writer, sheet_name='Instrucciones', index=False, header=False)
        
        # HOJA 2: PLANTILLA CON LISTAS DESPLEGABLES
        # Crear DataFrame vacio con las columnas
        df_plantilla = pd.DataFrame(columns=columnas)
        
        # Agregar fila de ejemplo
        ejemplo = {
            "cedula": "1234567890",
            "nombres": "Juan Carlos",
            "apellidos": "Perez Garcia",
            "telefono": "0987654321",
            "email": "juan.perez@email.com",
            "direccion": "Av. Principal 123, Quito",
            "fecha_nacimiento": "1990-05-15",
            "ocupacion": "Ingeniero",
            "modelo_vehiculo": "",  # Se llenara con lista desplegable
            "concesionario": "",    # Se llenara con lista desplegable
            "analista": "",         # Se llenara con lista desplegable
            "estado": "ACTIVO",
            "notas": "Cliente preferencial"
        }
        
        df_plantilla = pd.concat([df_plantilla, pd.DataFrame([ejemplo])], ignore_index=True)
        df_plantilla.to_excel(writer, sheet_name='Plantilla_Clientes', index=False)
        
        # Configurar listas desplegables usando openpyxl
        from openpyxl import load_workbook
        from openpyxl.worksheet.datavalidation import DataValidation
        
        # Cargar el workbook para agregar validaciones
        writer.close()
        
        # Reabrir para agregar validaciones
        wb = load_workbook(nombre_archivo)
        ws = wb['Plantilla_Clientes']
        
        # Lista desplegable para modelo_vehiculo (columna I)
        modelos_list = ",".join(datos_config["modelos_vehiculos"])
        dv_modelos = DataValidation(type="list", formula1=f'"{modelos_list}"', allow_blank=True)
        dv_modelos.add(f'I2:I1000')  # Aplicar a todas las filas de datos
        ws.add_data_validation(dv_modelos)
        
        # Lista desplegable para concesionario (columna J)
        concesionarios_list = ",".join(datos_config["concesionarios"])
        dv_concesionarios = DataValidation(type="list", formula1=f'"{concesionarios_list}"', allow_blank=True)
        dv_concesionarios.add(f'J2:J1000')  # Aplicar a todas las filas de datos
        ws.add_data_validation(dv_concesionarios)
        
        # Lista desplegable para analista (columna K)
        analistas_list = ",".join(datos_config["analistas"])
        dv_analistas = DataValidation(type="list", formula1=f'"{analistas_list}"', allow_blank=True)
        dv_analistas.add(f'K2:K1000')  # Aplicar a todas las filas de datos
        ws.add_data_validation(dv_analistas)
        
        # Lista desplegable para estado (columna L)
        dv_estado = DataValidation(type="list", formula1='"ACTIVO,INACTIVO"', allow_blank=True)
        dv_estado.add(f'L2:L1000')  # Aplicar a todas las filas de datos
        ws.add_data_validation(dv_estado)
        
        # Guardar archivo final
        wb.save(nombre_archivo)
    
    print(f"Plantilla Excel mejorada creada: {nombre_archivo}")
    print(f"Ubicacion: {os.path.abspath(nombre_archivo)}")
    print(f"Hojas incluidas:")
    print(f"   - Instrucciones: Guia completa de uso")
    print(f"   - Plantilla_Clientes: Con listas desplegables")
    print(f"\nListas desplegables configuradas:")
    print(f"   - modelo_vehiculo: {len(datos_config['modelos_vehiculos'])} opciones")
    print(f"   - concesionario: {len(datos_config['concesionarios'])} opciones")
    print(f"   - analista: {len(datos_config['analistas'])} opciones")
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
    print("Listo para usar con listas desplegables desde configuracion")
