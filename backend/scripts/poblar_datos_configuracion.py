#!/usr/bin/env python3
"""
Script para poblar datos de configuración necesarios
para que el formulario funcione correctamente
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.concesionario import Concesionario
from app.models.asesor import Asesor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def crear_concesionarios(db: Session):
    """Crear concesionarios de ejemplo"""
    logger.info("Creando concesionarios...")
    
    concesionarios_data = [
        {
            "nombre": "AutoCenter Caracas",
            "direccion": "Av. Francisco de Miranda, Caracas",
            "telefono": "+58 212-555-0101",
            "email": "caracas@autocenter.com",
            "responsable": "María González",
            "activo": True
        },
        {
            "nombre": "Motors Valencia",
            "direccion": "Zona Industrial Norte, Valencia",
            "telefono": "+58 241-555-0202",
            "email": "valencia@motors.com",
            "responsable": "Carlos Rodríguez",
            "activo": True
        },
        {
            "nombre": "Vehiculos Maracaibo",
            "direccion": "Av. 5 de Julio, Maracaibo",
            "telefono": "+58 261-555-0303",
            "email": "maracaibo@vehiculos.com",
            "responsable": "Ana Pérez",
            "activo": True
        }
    ]
    
    for data in concesionarios_data:
        # Verificar si ya existe
        existing = db.query(Concesionario).filter(Concesionario.nombre == data["nombre"]).first()
        if not existing:
            concesionario = Concesionario(**data)
            db.add(concesionario)
            logger.info(f"Concesionario creado: {data['nombre']}")
        else:
            logger.info(f"Concesionario ya existe: {data['nombre']}")
    
    db.commit()
    logger.info("Concesionarios creados exitosamente")

def crear_asesores(db: Session):
    """Crear asesores de ejemplo"""
    logger.info("Creando asesores...")
    
    asesores_data = [
        {
            "nombre": "Roberto",
            "apellido": "Martínez",
            "email": "roberto.martinez@rapicredit.com",
            "telefono": "+58 414-555-0404",
            "especialidad": "Vehículos Nuevos",
            "comision_porcentaje": 2.5,
            "activo": True,
            "notas": "Especialista en vehículos de gama alta"
        },
        {
            "nombre": "Sandra",
            "apellido": "López",
            "email": "sandra.lopez@rapicredit.com",
            "telefono": "+58 424-555-0505",
            "especialidad": "Vehículos Usados",
            "comision_porcentaje": 3.0,
            "activo": True,
            "notas": "Experta en financiamiento de vehículos usados"
        },
        {
            "nombre": "Miguel",
            "apellido": "Hernández",
            "email": "miguel.hernandez@rapicredit.com",
            "telefono": "+58 414-555-0606",
            "especialidad": "Motocicletas",
            "comision_porcentaje": 4.0,
            "activo": True,
            "notas": "Especialista en financiamiento de motocicletas"
        }
    ]
    
    for data in asesores_data:
        # Verificar si ya existe
        existing = db.query(Asesor).filter(Asesor.email == data["email"]).first()
        if not existing:
            asesor = Asesor(**data)
            db.add(asesor)
            logger.info(f"Asesor creado: {data['nombre']} {data['apellido']}")
        else:
            logger.info(f"Asesor ya existe: {data['email']}")
    
    db.commit()
    logger.info("Asesores creados exitosamente")

def main():
    """Función principal"""
    logger.info("Iniciando poblamiento de datos de configuración...")
    
    db = SessionLocal()
    try:
        # Crear concesionarios
        crear_concesionarios(db)
        
        # Crear asesores
        crear_asesores(db)
        
        logger.info("✅ Poblamiento completado exitosamente")
        
    except Exception as e:
        logger.error(f"❌ Error durante el poblamiento: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
