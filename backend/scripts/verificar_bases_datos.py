#!/usr/bin/env python3
"""
Script para verificar conexiones y sincronización de bases de datos
Analistas, Concesionarios y Modelos de Vehículos
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.db.session import get_db
from app.models.analista import Analista
from app.models.concesionario import Concesionario
from app.models.modelo_vehiculo import ModeloVehiculo
from app.db.session import engine, SessionLocal

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def verificar_conexion_bd():
    """Verificar conexión a la base de datos"""
    print("\n" + "="*60)
    print("1. VERIFICANDO CONEXIÓN A BASE DE DATOS")
    print("="*60)
    
    try:
        # Intentar conectar
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print_success("Conexión a base de datos: EXITOSA")
            return True
    except Exception as e:
        print_error(f"Conexión fallida: {str(e)}")
        return False

def verificar_tablas():
    """Verificar existencia de tablas"""
    print("\n" + "="*60)
    print("2. VERIFICANDO EXISTENCIA DE TABLAS")
    print("="*60)
    
    inspector = inspect(engine)
    tablas_requeridas = [
        ('analistas', 'Analistas'),
        ('concesionarios', 'Concesionarios'),
        ('modelos_vehiculos', 'Modelos de Vehículos'),
        ('clientes', 'Clientes'),
        ('users', 'Usuarios')
    ]
    
    tablas_existentes = inspector.get_table_names()
    
    for tabla, nombre in tablas_requeridas:
        if tabla in tablas_existentes:
            print_success(f"Tabla '{tabla}' ({nombre}): EXISTE")
        else:
            print_error(f"Tabla '{tabla}' ({nombre}): NO EXISTE")

def verificar_estructura_tabla(tabla, columnas_requeridas):
    """Verificar estructura de una tabla específica"""
    inspector = inspect(engine)
    columnas = [col['name'] for col in inspector.get_columns(tabla)]
    
    for columna in columnas_requeridas:
        if columna in columnas:
            print_success(f"  ✓ Columna '{columna}': presente")
        else:
            print_error(f"  ✗ Columna '{columna}': FALTANTE")

def verificar_analistas():
    """Verificar tabla de analistas"""
    print("\n" + "="*60)
    print("3. VERIFICANDO TABLA ANALISTAS")
    print("="*60)
    
    db = SessionLocal()
    try:
        analistas = db.query(Analista).all()
        print_success(f"Total de analistas en BD: {len(analistas)}")
        
        activos = len([a for a in analistas if a.activo])
        inactivos = len([a for a in analistas if not a.activo])
        
        print_info(f"  - Activos: {activos}")
        print_info(f"  - Inactivos: {inactivos}")
        
        if len(analistas) > 0:
            print("\nPrimeros 3 analistas:")
            for i, analista in enumerate(analistas[:3], 1):
                print(f"  {i}. ID: {analista.id} - Nombre: {analista.nombre} - Activo: {analista.activo}")
    except Exception as e:
        print_error(f"Error al leer analistas: {str(e)}")
    finally:
        db.close()

def verificar_concesionarios():
    """Verificar tabla de concesionarios"""
    print("\n" + "="*60)
    print("4. VERIFICANDO TABLA CONCESIONARIOS")
    print("="*60)
    
    try:
        from app.models.concesionario import Concesionario
        db = SessionLocal()
        concesionarios = db.query(Concesionario).all()
        print_success(f"Total de concesionarios en BD: {len(concesionarios)}")
        
        activos = len([c for c in concesionarios if c.activo])
        inactivos = len([c for c in concesionarios if not c.activo])
        
        print_info(f"  - Activos: {activos}")
        print_info(f"  - Inactivos: {inactivos}")
        
        if len(concesionarios) > 0:
            print("\nPrimeros 3 concesionarios:")
            for i, concesionario in enumerate(concesionarios[:3], 1):
                print(f"  {i}. ID: {concesionario.id} - Nombre: {concesionario.nombre} - Activo: {concesionario.activo}")
    except Exception as e:
        print_error(f"Error al leer concesionarios: {str(e)}")
        print_warning(f"Detalle: {type(e).__name__}")
    finally:
        db.close()

def verificar_modelos_vehiculos():
    """Verificar tabla de modelos de vehículos"""
    print("\n" + "="*60)
    print("5. VERIFICANDO TABLA MODELOS_VEHICULOS")
    print("="*60)
    
    try:
        from app.models.modelo_vehiculo import ModeloVehiculo
        db = SessionLocal()
        modelos = db.query(ModeloVehiculo).all()
        print_success(f"Total de modelos en BD: {len(modelos)}")
        
        activos = len([m for m in modelos if m.activo])
        inactivos = len([m for m in modelos if not m.activo])
        
        print_info(f"  - Activos: {activos}")
        print_info(f"  - Inactivos: {inactivos}")
        
        if len(modelos) > 0:
            print("\nPrimeros 3 modelos:")
            for i, modelo in enumerate(modelos[:3], 1):
                print(f"  {i}. ID: {modelo.id} - Modelo: {modelo.modelo} - Activo: {modelo.activo}")
    except Exception as e:
        print_error(f"Error al leer modelos: {str(e)}")
        print_warning(f"Detalle: {type(e).__name__}")
    finally:
        db.close()

def verificar_sincronizacion_clientes():
    """Verificar sincronización con tabla clientes"""
    print("\n" + "="*60)
    print("6. VERIFICANDO SINCRONIZACIÓN CON TABLA CLIENTES")
    print("="*60)
    
    try:
        from app.models.cliente import Cliente
        db = SessionLocal()
        
        # Verificar que los clientes tengan analistas válidos
        clientes = db.query(Cliente).all()
        print_success(f"Total de clientes en BD: {len(clientes)}")
        
        # Contar por analista
        analistas_unicos = set([c.analista for c in clientes if c.analista])
        print_info(f"Analistas únicos en clientes: {len(analistas_unicos)}")
        
        # Contar por concesionario
        concesionarios_unicos = set([c.concesionario for c in clientes if c.concesionario])
        print_info(f"Concesionarios únicos en clientes: {len(concesionarios_unicos)}")
        
        # Contar por modelo
        modelos_unicos = set([c.modelo_vehiculo for c in clientes if c.modelo_vehiculo])
        print_info(f"Modelos únicos en clientes: {len(modelos_unicos)}")
        
    except Exception as e:
        print_error(f"Error al leer clientes: {str(e)}")
    finally:
        db.close()

def main():
    """Función principal"""
    print("\n" + "="*60)
    print("VERIFICACIÓN DE BASES DE DATOS")
    print("Analistas, Concesionarios y Modelos de Vehículos")
    print("="*60)
    
    # 1. Verificar conexión
    if not verificar_conexion_bd():
        print_error("\n❌ No se puede continuar sin conexión a BD")
        return
    
    # 2. Verificar tablas
    verificar_tablas()
    
    # 3. Verificar datos
    verificar_analistas()
    verificar_concesionarios()
    verificar_modelos_vehiculos()
    verificar_sincronizacion_clientes()
    
    print("\n" + "="*60)
    print("VERIFICACIÓN COMPLETADA")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()

