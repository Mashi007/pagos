#!/usr/bin/env python3
"""
Script para crear clientes de ejemplo con datos reales
"""
import sys
import os
from datetime import datetime, date

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.cliente import Cliente
from app.models.concesionario import Concesionario
from app.models.analista import Analista

def create_sample_clients():
    """Crear 2 clientes de ejemplo con datos reales"""
    
    db = SessionLocal()
    
    try:
        # Obtener un concesionario y asesor existentes
        concesionario = db.query(Concesionario).filter(Concesionario.activo == True).first()
        asesor = db.query(Analista).filter(Analista.activo == True).first()
        
        if not concesionario or not asesor:
            print("❌ Error: No hay concesionarios o asesores activos en la base de datos")
            return
        
        # Datos de clientes de ejemplo
        sample_clients = [
            {
                "nombre": "María Elena Rodríguez",
                "cedula": "V12345678",
                "telefono": "+58 424 1234567",
                "email": "maria.rodriguez@email.com",
                "direccion": "Av. Principal, Residencias El Paraíso, Torre A, Apt 4B, Caracas",
                "saldo_pendiente": 15750.00,
                "fecha_ultimo_pago": date(2024, 1, 15),
                "estado": "ACTIVO",
                "modelo_vehiculo": "Toyota Corolla 2023",
                "total_financiamiento": 25000.00,
                "cuota_inicial": 5000.00,
                "numero_amortizaciones": 24,
                "modalidad_financiamiento": "mensual",
                "fecha_entrega": date(2024, 1, 10),
                "concesionario_id": concesionario.id,
                "asesor_id": asesor.id,
                "notas": "Cliente puntual en pagos, excelente historial crediticio"
            },
            {
                "nombre": "Carlos Alberto Mendoza",
                "cedula": "E87654321",
                "telefono": "+58 414 9876543",
                "email": "carlos.mendoza@hotmail.com",
                "direccion": "Urbanización Los Palos Grandes, Calle Principal, Casa 123, Caracas",
                "saldo_pendiente": 8230.50,
                "fecha_ultimo_pago": date(2024, 1, 20),
                "estado": "ACTIVO",
                "modelo_vehiculo": "Nissan Versa 2022",
                "total_financiamiento": 18000.00,
                "cuota_inicial": 3000.00,
                "numero_amortizaciones": 18,
                "modalidad_financiamiento": "quincenal",
                "fecha_entrega": date(2024, 1, 5),
                "concesionario_id": concesionario.id,
                "asesor_id": asesor.id,
                "notas": "Cliente preferencial, referido por otro cliente satisfecho"
            }
        ]
        
        # Crear los clientes
        created_count = 0
        for client_data in sample_clients:
            # Verificar si ya existe un cliente con esta cédula
            existing_client = db.query(Cliente).filter(Cliente.cedula == client_data["cedula"]).first()
            
            if existing_client:
                print(f"⚠️ Cliente con cédula {client_data['cedula']} ya existe, omitiendo...")
                continue
            
            # Crear nuevo cliente
            cliente = Cliente(**client_data)
            db.add(cliente)
            created_count += 1
            
            print(f"✅ Cliente creado: {client_data['nombre']} - {client_data['cedula']}")
        
        # Confirmar cambios
        db.commit()
        
        print(f"\n🎉 Se crearon {created_count} clientes de ejemplo exitosamente")
        print(f"📊 Total de clientes en la base de datos: {db.query(Cliente).count()}")
        
    except Exception as e:
        print(f"❌ Error al crear clientes de ejemplo: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Creando clientes de ejemplo...")
    create_sample_clients()
