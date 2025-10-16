# ============================================================
# GENERADOR DE MOCK DATA PARA SISTEMA DE PRESTAMOS
# ============================================================

import asyncio
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo, EstadoPrestamo, ModalidadPago
from app.models.pago import Pago
from app.models.user import User
from app.models.asesor import Asesor
from app.models.concesionario import Concesionario
from app.models.modelo_vehiculo import ModeloVehiculo
from decimal import Decimal
from datetime import date, datetime, timedelta
import random

def create_mock_data(db_session=None):
    """Crear datos de prueba para el sistema"""
    
    # Obtener sesión de base de datos
    if db_session is None:
        db = next(get_db())
    else:
        db = db_session
    
    try:
        print("🚀 Iniciando creación de mock data...")
        
        # ============================================
        # 1. CREAR ASESORES
        # ============================================
        print("📋 Creando asesores...")
        
        asesores_data = [
            {
                "nombre": "Carlos",
                "apellido": "Mendoza",
                "email": "carlos.mendoza@rapicreditca.com",
                "telefono": "555-0101",
                "especialidad": "Vehiculos Nuevos",
                "activo": True
            },
            {
                "nombre": "Ana",
                "apellido": "Rodriguez",
                "email": "ana.rodriguez@rapicreditca.com", 
                "telefono": "555-0102",
                "especialidad": "Vehiculos Usados",
                "activo": True
            },
            {
                "nombre": "Luis",
                "apellido": "Garcia",
                "email": "luis.garcia@rapicreditca.com",
                "telefono": "555-0103", 
                "especialidad": "Financiamiento Especial",
                "activo": True
            }
        ]
        
        asesores_creados = []
        for asesor_data in asesores_data:
            asesor = Asesor(**asesor_data)
            db.add(asesor)
            db.flush()  # Para obtener el ID
            asesores_creados.append(asesor)
            print(f"   ✅ Asesor: {asesor.nombre_completo}")
        
        # ============================================
        # 2. CREAR CONCESIONARIOS
        # ============================================
        print("🏢 Creando concesionarios...")
        
        concesionarios_data = [
            {
                "nombre": "AutoMax Costa Rica",
                "direccion": "San José, Costa Rica",
                "telefono": "2222-0001",
                "email": "info@automax.cr",
                "responsable": "María González",
                "activo": True
            },
            {
                "nombre": "CarCenter Plus",
                "direccion": "Cartago, Costa Rica", 
                "telefono": "2550-0002",
                "email": "ventas@carcenter.cr",
                "responsable": "Roberto Silva",
                "activo": True
            },
            {
                "nombre": "Vehiculos del Valle",
                "direccion": "Alajuela, Costa Rica",
                "telefono": "2440-0003", 
                "email": "contacto@vehiculosdelvalle.cr",
                "responsable": "Carmen Herrera",
                "activo": True
            }
        ]
        
        concesionarios_creados = []
        for concesionario_data in concesionarios_data:
            concesionario = Concesionario(**concesionario_data)
            db.add(concesionario)
            db.flush()
            concesionarios_creados.append(concesionario)
            print(f"   ✅ Concesionario: {concesionario.nombre}")
        
        # ============================================
        # 3. CREAR MODELOS DE VEHICULOS
        # ============================================
        print("🚗 Creando modelos de vehículos...")
        
        modelos_data = [
            {
                "modelo": "Toyota Corolla 2023",
                "activo": True
            },
            {
                "modelo": "Honda Civic 2023",
                "activo": True
            },
            {
                "modelo": "Nissan Sentra 2023",
                "activo": True
            },
            {
                "modelo": "Toyota RAV4 2023",
                "activo": True
            },
            {
                "modelo": "Hyundai Tucson 2023",
                "activo": True
            }
        ]
        
        modelos_creados = []
        for modelo_data in modelos_data:
            modelo = ModeloVehiculo(**modelo_data)
            db.add(modelo)
            db.flush()
            modelos_creados.append(modelo)
            print(f"   ✅ Modelo: {modelo.modelo}")
        
        # ============================================
        # 4. CREAR CLIENTES
        # ============================================
        print("👥 Creando clientes...")
        
        clientes_data = [
            {
                "cedula": "123456789",
                "nombres": "Juan Carlos",
                "apellidos": "Pérez González",
                "telefono": "8888-1111",
                "email": "juan.perez@email.com",
                "direccion": "San José, Costa Rica",
                "ocupacion": "Ingeniero",
                "modelo_vehiculo": "Corolla",
                "marca_vehiculo": "Toyota",
                "anio_vehiculo": 2023,
                "color_vehiculo": "Blanco",
                "concesionario": "AutoMax Costa Rica",
                "total_financiamiento": Decimal("25000.00"),
                "cuota_inicial": Decimal("5000.00"),
                "monto_financiado": Decimal("20000.00"),
                "modalidad_pago": "MENSUAL",
                "numero_amortizaciones": 36,
                "asesor_config_id": asesores_creados[0].id,
                "concesionario_id": concesionarios_creados[0].id,
                "modelo_vehiculo_id": modelos_creados[0].id,
                "estado": "ACTIVO",
                "estado_financiero": "AL_DIA",
                "activo": True
            },
            {
                "cedula": "987654321",
                "nombres": "María Elena",
                "apellidos": "Rodriguez Silva",
                "telefono": "8888-2222",
                "email": "maria.rodriguez@email.com",
                "direccion": "Cartago, Costa Rica",
                "ocupacion": "Doctora",
                "modelo_vehiculo": "Civic",
                "marca_vehiculo": "Honda",
                "anio_vehiculo": 2023,
                "color_vehiculo": "Azul",
                "concesionario": "CarCenter Plus",
                "total_financiamiento": Decimal("24000.00"),
                "cuota_inicial": Decimal("4000.00"),
                "monto_financiado": Decimal("20000.00"),
                "modalidad_pago": "MENSUAL",
                "numero_amortizaciones": 48,
                "asesor_config_id": asesores_creados[1].id,
                "concesionario_id": concesionarios_creados[1].id,
                "modelo_vehiculo_id": modelos_creados[1].id,
                "estado": "ACTIVO",
                "estado_financiero": "AL_DIA",
                "activo": True
            },
            {
                "cedula": "456789123",
                "nombres": "Roberto",
                "apellidos": "Garcia Morales",
                "telefono": "8888-3333",
                "email": "roberto.garcia@email.com",
                "direccion": "Alajuela, Costa Rica",
                "ocupacion": "Empresario",
                "modelo_vehiculo": "RAV4",
                "marca_vehiculo": "Toyota",
                "anio_vehiculo": 2023,
                "color_vehiculo": "Negro",
                "concesionario": "Vehiculos del Valle",
                "total_financiamiento": Decimal("32000.00"),
                "cuota_inicial": Decimal("8000.00"),
                "monto_financiado": Decimal("24000.00"),
                "modalidad_pago": "MENSUAL",
                "numero_amortizaciones": 60,
                "asesor_config_id": asesores_creados[2].id,
                "concesionario_id": concesionarios_creados[2].id,
                "modelo_vehiculo_id": modelos_creados[3].id,
                "estado": "ACTIVO",
                "estado_financiero": "MORA",
                "dias_mora": 15,
                "activo": True
            }
        ]
        
        clientes_creados = []
        for cliente_data in clientes_data:
            cliente = Cliente(**cliente_data)
            db.add(cliente)
            db.flush()
            clientes_creados.append(cliente)
            print(f"   ✅ Cliente: {cliente.nombre_completo}")
        
        # ============================================
        # 5. CREAR PRESTAMOS
        # ============================================
        print("💰 Creando préstamos...")
        
        prestamos_data = [
            {
                "cliente_id": clientes_creados[0].id,
                "codigo_prestamo": "PREST-001",
                "monto_total": Decimal("20000.00"),
                "monto_financiado": Decimal("20000.00"),
                "monto_inicial": Decimal("5000.00"),
                "tasa_interes": Decimal("12.50"),
                "numero_cuotas": 36,
                "monto_cuota": Decimal("667.00"),
                "cuotas_pagadas": 6,
                "cuotas_pendientes": 30,
                "fecha_aprobacion": date(2023, 1, 15),
                "fecha_desembolso": date(2023, 1, 20),
                "fecha_primer_vencimiento": date(2023, 2, 20),
                "fecha_ultimo_vencimiento": date(2025, 12, 20),
                "saldo_pendiente": Decimal("20000.00"),
                "saldo_capital": Decimal("18000.00"),
                "saldo_interes": Decimal("2000.00"),
                "total_pagado": Decimal("4002.00"),
                "estado": EstadoPrestamo.ACTIVO.value,
                "modalidad": ModalidadPago.MENSUAL.value
            },
            {
                "cliente_id": clientes_creados[1].id,
                "codigo_prestamo": "PREST-002",
                "monto_total": Decimal("20000.00"),
                "monto_financiado": Decimal("20000.00"),
                "monto_inicial": Decimal("4000.00"),
                "tasa_interes": Decimal("11.75"),
                "numero_cuotas": 48,
                "monto_cuota": Decimal("520.00"),
                "cuotas_pagadas": 12,
                "cuotas_pendientes": 36,
                "fecha_aprobacion": date(2023, 3, 10),
                "fecha_desembolso": date(2023, 3, 15),
                "fecha_primer_vencimiento": date(2023, 4, 15),
                "fecha_ultimo_vencimiento": date(2027, 3, 15),
                "saldo_pendiente": Decimal("18720.00"),
                "saldo_capital": Decimal("16000.00"),
                "saldo_interes": Decimal("2720.00"),
                "total_pagado": Decimal("6240.00"),
                "estado": EstadoPrestamo.ACTIVO.value,
                "modalidad": ModalidadPago.MENSUAL.value
            },
            {
                "cliente_id": clientes_creados[2].id,
                "codigo_prestamo": "PREST-003",
                "monto_total": Decimal("24000.00"),
                "monto_financiado": Decimal("24000.00"),
                "monto_inicial": Decimal("8000.00"),
                "tasa_interes": Decimal("13.25"),
                "numero_cuotas": 60,
                "monto_cuota": Decimal("550.00"),
                "cuotas_pagadas": 8,
                "cuotas_pendientes": 52,
                "fecha_aprobacion": date(2023, 6, 5),
                "fecha_desembolso": date(2023, 6, 10),
                "fecha_primer_vencimiento": date(2023, 7, 10),
                "fecha_ultimo_vencimiento": date(2028, 6, 10),
                "saldo_pendiente": Decimal("26400.00"),
                "saldo_capital": Decimal("20000.00"),
                "saldo_interes": Decimal("6400.00"),
                "total_pagado": Decimal("4400.00"),
                "estado": EstadoPrestamo.EN_MORA.value,
                "modalidad": ModalidadPago.MENSUAL.value
            }
        ]
        
        prestamos_creados = []
        for prestamo_data in prestamos_data:
            prestamo = Prestamo(**prestamo_data)
            db.add(prestamo)
            db.flush()
            prestamos_creados.append(prestamo)
            print(f"   ✅ Préstamo: {prestamo.codigo_prestamo}")
        
        # ============================================
        # 6. CREAR PAGOS
        # ============================================
        print("💳 Creando pagos...")
        
        # Pagos para el primer préstamo (6 cuotas pagadas)
        for i in range(1, 7):
            pago_data = {
                "prestamo_id": prestamos_creados[0].id,
                "numero_cuota": i,
                "codigo_pago": f"PAG-001-{i:03d}",
                "monto_cuota_programado": Decimal("667.00"),
                "monto_pagado": Decimal("667.00"),
                "monto_capital": Decimal("500.00"),
                "monto_interes": Decimal("167.00"),
                "monto_mora": Decimal("0.00"),
                "descuento": Decimal("0.00"),
                "monto_total": Decimal("667.00"),
                "fecha_pago": date(2023, 1, 20) + timedelta(days=30*i),
                "fecha_vencimiento": date(2023, 1, 20) + timedelta(days=30*i),
                "dias_mora": 0,
                "tasa_mora": Decimal("0.00"),
                "metodo_pago": "EFECTIVO",
                "estado": "CONFIRMADO",
                "tipo_pago": "NORMAL",
                "estado_conciliacion": "CONCILIADO"
            }
            pago = Pago(**pago_data)
            db.add(pago)
            print(f"   ✅ Pago: {pago.codigo_pago}")
        
        # Pagos para el segundo préstamo (12 cuotas pagadas)
        for i in range(1, 13):
            pago_data = {
                "prestamo_id": prestamos_creados[1].id,
                "numero_cuota": i,
                "codigo_pago": f"PAG-002-{i:03d}",
                "monto_cuota_programado": Decimal("520.00"),
                "monto_pagado": Decimal("520.00"),
                "monto_capital": Decimal("400.00"),
                "monto_interes": Decimal("120.00"),
                "monto_mora": Decimal("0.00"),
                "descuento": Decimal("0.00"),
                "monto_total": Decimal("520.00"),
                "fecha_pago": date(2023, 3, 15) + timedelta(days=30*i),
                "fecha_vencimiento": date(2023, 3, 15) + timedelta(days=30*i),
                "dias_mora": 0,
                "tasa_mora": Decimal("0.00"),
                "metodo_pago": "TRANSFERENCIA",
                "estado": "CONFIRMADO",
                "tipo_pago": "NORMAL",
                "estado_conciliacion": "CONCILIADO"
            }
            pago = Pago(**pago_data)
            db.add(pago)
            print(f"   ✅ Pago: {pago.codigo_pago}")
        
        # Pagos para el tercer préstamo (8 cuotas pagadas, 1 en mora)
        for i in range(1, 9):
            dias_mora = 15 if i == 9 else 0
            monto_mora = Decimal("25.00") if i == 9 else Decimal("0.00")
            
            pago_data = {
                "prestamo_id": prestamos_creados[2].id,
                "numero_cuota": i,
                "codigo_pago": f"PAG-003-{i:03d}",
                "monto_cuota_programado": Decimal("550.00"),
                "monto_pagado": Decimal("550.00") + monto_mora,
                "monto_capital": Decimal("400.00"),
                "monto_interes": Decimal("150.00"),
                "monto_mora": monto_mora,
                "descuento": Decimal("0.00"),
                "monto_total": Decimal("550.00") + monto_mora,
                "fecha_pago": date(2023, 6, 10) + timedelta(days=30*i) + timedelta(days=dias_mora),
                "fecha_vencimiento": date(2023, 6, 10) + timedelta(days=30*i),
                "dias_mora": dias_mora,
                "tasa_mora": Decimal("2.50") if dias_mora > 0 else Decimal("0.00"),
                "metodo_pago": "EFECTIVO",
                "estado": "CONFIRMADO",
                "tipo_pago": "NORMAL",
                "estado_conciliacion": "CONCILIADO"
            }
            pago = Pago(**pago_data)
            db.add(pago)
            print(f"   ✅ Pago: {pago.codigo_pago}")
        
        # ============================================
        # 7. COMMIT DE TODOS LOS DATOS
        # ============================================
        print("💾 Guardando datos en base de datos...")
        db.commit()
        
        print("")
        print("🎉 MOCK DATA CREADO EXITOSAMENTE!")
        print("")
        print("📊 RESUMEN:")
        print(f"   👥 Asesores: {len(asesores_creados)}")
        print(f"   🏢 Concesionarios: {len(concesionarios_creados)}")
        print(f"   🚗 Modelos de vehículos: {len(modelos_creados)}")
        print(f"   👤 Clientes: {len(clientes_creados)}")
        print(f"   💰 Préstamos: {len(prestamos_creados)}")
        print(f"   💳 Pagos: 26")
        print("")
        print("✅ El sistema ahora tiene datos de prueba para testing")
        
    except Exception as e:
        print(f"❌ Error creando mock data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_mock_data()
