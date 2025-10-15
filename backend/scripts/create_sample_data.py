#!/usr/bin/env python3
"""
🎲 SCRIPT DE GENERACIÓN DE DATOS DE PRUEBA
Crea datos simulados para todos los módulos del sistema
"""
import sys
import os
from pathlib import Path

# Agregar backend al PYTHONPATH
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from datetime import datetime, timedelta, date
from decimal import Decimal
import random

from app.db.session import SessionLocal
from app.models.cliente import Cliente
from app.models.user import User
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.models.amortizacion import Cuota
from app.models.concesionario import Concesionario
from app.models.asesor import Asesor
from app.core.security import get_password_hash


def crear_usuarios_ejemplo(db: SessionLocal):
    """Crear usuarios de ejemplo con diferentes roles"""
    print("\n👥 Creando usuarios de ejemplo...")
    
    usuarios = [
        {
            "email": "itmaster@rapicreditca.com",
            "nombre": "Administrador",
            "apellido": "Sistema",
            "rol": "ADMIN",
            "password": "Admin2025!"
        },
        {
            "email": "gerente@financiamiento.com",
            "nombre": "Carlos",
            "apellido": "Gerente",
            "rol": "GERENTE",
            "password": "Gerente2025!"
        },
        {
            "email": "asesor1@financiamiento.com",
            "nombre": "María",
            "apellido": "López",
            "rol": "ASESOR_COMERCIAL",
            "password": "Asesor2025!"
        },
        {
            "email": "asesor2@financiamiento.com",
            "nombre": "Juan",
            "apellido": "Pérez",
            "rol": "ASESOR_COMERCIAL",
            "password": "Asesor2025!"
        },
        {
            "email": "cobrador@financiamiento.com",
            "nombre": "Pedro",
            "apellido": "Cobrador",
            "rol": "COBRADOR",
            "password": "Cobrador2025!"
        }
    ]
    
    usuarios_creados = []
    for u_data in usuarios:
        existing = db.query(User).filter(User.email == u_data["email"]).first()
        if existing:
            print(f"  ⏭️  Usuario ya existe: {u_data['email']}")
            usuarios_creados.append(existing)
            continue
        
        usuario = User(
            email=u_data["email"],
            nombre=u_data["nombre"],
            apellido=u_data["apellido"],
            rol=u_data["rol"],
            hashed_password=get_password_hash(u_data["password"]),
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(usuario)
        usuarios_creados.append(usuario)
        print(f"  ✅ Creado: {u_data['email']} ({u_data['rol']})")
    
    db.commit()
    print(f"\n✅ {len(usuarios_creados)} usuarios disponibles")
    return usuarios_creados


def crear_concesionarios_ejemplo(db: SessionLocal):
    """Crear concesionarios de ejemplo"""
    print("\n🏢 Creando concesionarios de ejemplo...")
    
    concesionarios_data = [
        {"nombre": "AutoStar Motors", "ciudad": "Caracas", "telefono": "02121234567"},
        {"nombre": "VehiPlus C.A.", "ciudad": "Valencia", "telefono": "02411234567"},
        {"nombre": "Autos Premium", "ciudad": "Maracaibo", "telefono": "02611234567"},
    ]
    
    concesionarios_creados = []
    for c_data in concesionarios_data:
        existing = db.query(Concesionario).filter(Concesionario.nombre == c_data["nombre"]).first()
        if existing:
            print(f"  ⏭️  Concesionario ya existe: {c_data['nombre']}")
            concesionarios_creados.append(existing)
            continue
        
        concesionario = Concesionario(
            nombre=c_data["nombre"],
            ciudad=c_data["ciudad"],
            telefono=c_data["telefono"],
            activo=True
        )
        db.add(concesionario)
        concesionarios_creados.append(concesionario)
        print(f"  ✅ Creado: {c_data['nombre']}")
    
    db.commit()
    print(f"\n✅ {len(concesionarios_creados)} concesionarios disponibles")
    return concesionarios_creados


def crear_asesores_ejemplo(db: SessionLocal, usuarios: list):
    """Crear asesores de ejemplo"""
    print("\n👨‍💼 Creando asesores de ejemplo...")
    
    asesores_comerciales = [u for u in usuarios if u.rol == "ASESOR_COMERCIAL"]
    asesores_creados = []
    
    for usuario in asesores_comerciales:
        existing = db.query(Asesor).filter(Asesor.usuario_id == usuario.id).first()
        if existing:
            print(f"  ⏭️  Asesor ya existe: {usuario.nombre}")
            asesores_creados.append(existing)
            continue
        
        asesor = Asesor(
            usuario_id=usuario.id,
            codigo=f"AS{usuario.id:03d}",
            activo=True
        )
        db.add(asesor)
        asesores_creados.append(asesor)
        print(f"  ✅ Creado: {usuario.nombre} {usuario.apellido}")
    
    db.commit()
    print(f"\n✅ {len(asesores_creados)} asesores disponibles")
    return asesores_creados


def crear_clientes_ejemplo(db: SessionLocal, asesores: list, concesionarios: list):
    """Crear clientes de ejemplo con financiamiento"""
    print("\n👥 Creando clientes de ejemplo...")
    
    nombres = ["Juan", "María", "Carlos", "Ana", "Luis", "Carmen", "Pedro", "Laura", "José", "Sofia"]
    apellidos = ["García", "Rodríguez", "Martínez", "Hernández", "López", "González", "Pérez", "Sánchez", "Ramírez", "Torres"]
    modelos = ["Toyota Corolla", "Nissan Versa", "Hyundai Accent", "Chevrolet Aveo", "Ford Fiesta", "Kia Rio", "Mazda 2", "Honda Civic"]
    
    clientes_creados = []
    for i in range(20):
        cedula = f"V{random.randint(10000000, 30000000)}"
        
        existing = db.query(Cliente).filter(Cliente.cedula == cedula).first()
        if existing:
            continue
        
        cliente = Cliente(
            cedula=cedula,
            nombres=random.choice(nombres),
            apellidos=random.choice(apellidos),
            telefono=f"0424{random.randint(1000000, 9999999)}",
            email=f"cliente{i+1}@email.com",
            modelo_vehiculo=random.choice(modelos),
            marca_vehiculo=random.choice(modelos).split()[0],
            anio_vehiculo=random.randint(2018, 2024),
            concesionario=random.choice(concesionarios).nombre if concesionarios else None,
            total_financiamiento=Decimal(random.randint(15000, 45000)),
            cuota_inicial=Decimal(random.randint(3000, 10000)),
            fecha_entrega=date.today() - timedelta(days=random.randint(30, 365)),
            numero_amortizaciones=random.choice([12, 18, 24, 36]),
            modalidad_pago="MENSUAL",
            asesor_id=random.choice(asesores).usuario_id if asesores else None,
            estado="ACTIVO",
            activo=True,
            estado_financiero=random.choice(["AL_DIA", "AL_DIA", "AL_DIA", "MORA"]),  # 75% al día
            dias_mora=0 if random.random() < 0.75 else random.randint(5, 30),
            fecha_registro=datetime.utcnow() - timedelta(days=random.randint(30, 365))
        )
        db.add(cliente)
        clientes_creados.append(cliente)
        print(f"  ✅ Cliente {i+1}: {cliente.nombres} {cliente.apellidos} - {cliente.modelo_vehiculo}")
    
    db.commit()
    print(f"\n✅ {len(clientes_creados)} clientes creados")
    return clientes_creados


def main():
    """Función principal"""
    print("\n" + "="*60)
    print("🎲 GENERADOR DE DATOS DE PRUEBA")
    print("="*60)
    
    db = SessionLocal()
    
    try:
        # 1. Crear usuarios
        usuarios = crear_usuarios_ejemplo(db)
        
        # 2. Crear concesionarios
        concesionarios = crear_concesionarios_ejemplo(db)
        
        # 3. Crear asesores
        asesores = crear_asesores_ejemplo(db, usuarios)
        
        # 4. Crear clientes
        clientes = crear_clientes_ejemplo(db, asesores, concesionarios)
        
        print("\n" + "="*60)
        print("✅ DATOS DE PRUEBA CREADOS EXITOSAMENTE")
        print("="*60)
        print(f"\n📊 Resumen:")
        print(f"  👥 Usuarios: {len(usuarios)}")
        print(f"  🏢 Concesionarios: {len(concesionarios)}")
        print(f"  👨‍💼 Asesores: {len(asesores)}")
        print(f"  👤 Clientes: {len(clientes)}")
        
        print(f"\n🔐 Credenciales de prueba:")
        print(f"  Admin: itmaster@rapicreditca.com / R@pi_2025**")
        print(f"  Gerente: gerente@financiamiento.com / Gerente2025!")
        print(f"  Asesor: asesor1@financiamiento.com / Asesor2025!")
        
        print("\n" + "="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()

