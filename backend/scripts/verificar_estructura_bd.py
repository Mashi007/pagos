#!/usr/bin/env python3
"""
Script para verificar la estructura real de la base de datos
Especialmente la tabla usuarios
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from app.db.session import get_db, engine
from app.models.user import User

def verificar_estructura_bd():
    """Verificar la estructura real de la base de datos"""
    print("VERIFICANDO ESTRUCTURA DE BASE DE DATOS")
    print("=" * 50)
    
    try:
        # Obtener inspector de SQLAlchemy
        inspector = inspect(engine)
        
        # Verificar si existe la tabla usuarios
        tablas = inspector.get_table_names()
        print(f"Tablas encontradas: {tablas}")
        
        if 'usuarios' in tablas:
            print("\nESTRUCTURA DE LA TABLA 'usuarios':")
            print("-" * 40)
            
            # Obtener columnas de la tabla usuarios
            columnas = inspector.get_columns('usuarios')
            
            for columna in columnas:
                print(f"Campo: {columna['name']}")
                print(f"  Tipo: {columna['type']}")
                print(f"  Nullable: {columna['nullable']}")
                print(f"  Default: {columna.get('default', 'None')}")
                print()
            
            # Verificar índices
            indices = inspector.get_indexes('usuarios')
            if indices:
                print("ÍNDICES:")
                for indice in indices:
                    print(f"  {indice['name']}: {indice['column_names']}")
                print()
            
            # Verificar claves foráneas
            fks = inspector.get_foreign_keys('usuarios')
            if fks:
                print("CLAVES FORÁNEAS:")
                for fk in fks:
                    print(f"  {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
                print()
                
        else:
            print("ERROR: Tabla 'usuarios' no encontrada")
            return False
            
        return True
        
    except Exception as e:
        print(f"ERROR verificando estructura: {e}")
        return False

def verificar_datos_existentes():
    """Verificar datos existentes en la tabla usuarios"""
    print("\nVERIFICANDO DATOS EXISTENTES")
    print("=" * 50)
    
    try:
        db = next(get_db())
        
        # Contar usuarios
        total_usuarios = db.query(User).count()
        print(f"Total usuarios en BD: {total_usuarios}")
        
        if total_usuarios > 0:
            # Obtener algunos usuarios de ejemplo
            usuarios = db.query(User).limit(3).all()
            
            print("\nUSUARIOS DE EJEMPLO:")
            for usuario in usuarios:
                print(f"ID: {usuario.id}")
                print(f"Email: {usuario.email}")
                
                # Verificar qué campos existen
                campos_disponibles = []
                if hasattr(usuario, 'nombre'):
                    campos_disponibles.append(f"nombre: {usuario.nombre}")
                if hasattr(usuario, 'apellido'):
                    campos_disponibles.append(f"apellido: {usuario.apellido}")
                if hasattr(usuario, 'full_name'):
                    campos_disponibles.append(f"full_name: {usuario.full_name}")
                if hasattr(usuario, 'cargo'):
                    campos_disponibles.append(f"cargo: {usuario.cargo}")
                if hasattr(usuario, 'rol'):
                    campos_disponibles.append(f"rol: {usuario.rol}")
                if hasattr(usuario, 'is_active'):
                    campos_disponibles.append(f"is_active: {usuario.is_active}")
                
                print(f"Campos disponibles: {', '.join(campos_disponibles)}")
                print()
        
        return True
        
    except Exception as e:
        print(f"ERROR verificando datos: {e}")
        return False

def verificar_modelo_vs_bd():
    """Verificar diferencias entre modelo y BD real"""
    print("\nVERIFICANDO MODELO vs BD REAL")
    print("=" * 50)
    
    try:
        # Obtener campos del modelo User
        print("CAMPOS EN EL MODELO User:")
        campos_modelo = User.__table__.columns.keys()
        for campo in campos_modelo:
            print(f"  - {campo}")
        
        print("\nCAMPOS EN LA BD REAL:")
        inspector = inspect(engine)
        columnas_bd = [col['name'] for col in inspector.get_columns('usuarios')]
        for campo in columnas_bd:
            print(f"  - {campo}")
        
        # Encontrar diferencias
        campos_solo_modelo = set(campos_modelo) - set(columnas_bd)
        campos_solo_bd = set(columnas_bd) - set(campos_modelo)
        
        if campos_solo_modelo:
            print(f"\nCAMPOS SOLO EN MODELO: {campos_solo_modelo}")
        if campos_solo_bd:
            print(f"\nCAMPOS SOLO EN BD: {campos_solo_bd}")
        
        if not campos_solo_modelo and not campos_solo_bd:
            print("\nOK - Modelo y BD están sincronizados")
        
        return True
        
    except Exception as e:
        print(f"ERROR verificando modelo vs BD: {e}")
        return False

def main():
    """Función principal"""
    print("ANALISIS COMPLETO DE BASE DE DATOS")
    print("=" * 60)
    
    # Verificar estructura
    estructura_ok = verificar_estructura_bd()
    
    if estructura_ok:
        # Verificar datos
        datos_ok = verificar_datos_existentes()
        
        # Verificar modelo vs BD
        modelo_ok = verificar_modelo_vs_bd()
        
        print("\n" + "=" * 60)
        print("RESUMEN")
        print("=" * 60)
        print(f"Estructura BD: {'OK' if estructura_ok else 'ERROR'}")
        print(f"Datos existentes: {'OK' if datos_ok else 'ERROR'}")
        print(f"Modelo vs BD: {'OK' if modelo_ok else 'ERROR'}")
        
        if estructura_ok and datos_ok and modelo_ok:
            print("\nBase de datos funcionando correctamente")
        else:
            print("\nHay problemas en la base de datos")
    else:
        print("\nNo se pudo verificar la estructura de la BD")

if __name__ == "__main__":
    main()
