"""
🧪 TEST DE INTEGRACIÓN COMPLETA - MÓDULO CLIENTES
Verifica conexión entre Cliente y Asesor, Concesionario, ModeloVehiculo
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from app.models.cliente import Cliente
from app.models.asesor import Asesor
from app.models.concesionario import Concesionario
from app.models.modelo_vehiculo import ModeloVehiculo
from app.core.config import settings

print("=" * 80)
print("🧪 TEST DE INTEGRACIÓN COMPLETA - MÓDULO CLIENTES")
print("=" * 80)

# 1. VERIFICAR CONEXIÓN A BASE DE DATOS
print("\n📊 1. VERIFICANDO CONEXIÓN A BASE DE DATOS...")
try:
    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)
    print(f"✅ Conexión exitosa a: {settings.DATABASE_URL[:50]}...")
except Exception as e:
    print(f"❌ Error de conexión: {e}")
    sys.exit(1)

# 2. VERIFICAR TABLAS EXISTEN
print("\n📋 2. VERIFICANDO TABLAS EN BASE DE DATOS...")
tablas_requeridas = ['clientes', 'asesores', 'concesionarios', 'modelos_vehiculos']
tablas_existentes = inspector.get_table_names()

for tabla in tablas_requeridas:
    if tabla in tablas_existentes:
        print(f"✅ Tabla '{tabla}' existe")
    else:
        print(f"❌ Tabla '{tabla}' NO existe")

# 3. VERIFICAR COLUMNAS EN TABLA CLIENTES
print("\n🔍 3. VERIFICANDO COLUMNAS EN TABLA 'clientes'...")
columnas_clientes = inspector.get_columns('clientes')
columnas_dict = {col['name']: col['type'] for col in columnas_clientes}

columnas_requeridas = {
    'id': 'INTEGER',
    'cedula': 'VARCHAR',
    'nombres': 'VARCHAR',
    'apellidos': 'VARCHAR',
    'telefono': 'VARCHAR',
    'email': 'VARCHAR',
    'modelo_vehiculo_id': 'INTEGER',
    'concesionario_id': 'INTEGER',
    'asesor_config_id': 'INTEGER',
    'total_financiamiento': 'NUMERIC',
    'cuota_inicial': 'NUMERIC',
    'estado': 'VARCHAR',
    'activo': 'BOOLEAN'
}

for columna, tipo in columnas_requeridas.items():
    if columna in columnas_dict:
        print(f"✅ Columna '{columna}': {columnas_dict[columna]}")
    else:
        print(f"❌ Columna '{columna}' NO existe")

# 4. VERIFICAR FOREIGN KEYS
print("\n🔗 4. VERIFICANDO FOREIGN KEYS EN TABLA 'clientes'...")
foreign_keys = inspector.get_foreign_keys('clientes')

fks_requeridas = {
    'modelo_vehiculo_id': 'modelos_vehiculos',
    'concesionario_id': 'concesionarios',
    'asesor_config_id': 'asesores'
}

fks_encontradas = {}
for fk in foreign_keys:
    for col in fk['constrained_columns']:
        fks_encontradas[col] = fk['referred_table']

for col, tabla_ref in fks_requeridas.items():
    if col in fks_encontradas:
        if fks_encontradas[col] == tabla_ref:
            print(f"✅ FK '{col}' → '{tabla_ref}'")
        else:
            print(f"⚠️  FK '{col}' apunta a '{fks_encontradas[col]}', debería ser '{tabla_ref}'")
    else:
        print(f"❌ FK '{col}' NO existe")

# 5. VERIFICAR MODELOS SQLALCHEMY
print("\n🏗️  5. VERIFICANDO MODELOS SQLALCHEMY...")
try:
    # Verificar Cliente
    cliente_cols = [col.name for col in Cliente.__table__.columns]
    print(f"✅ Modelo Cliente: {len(cliente_cols)} columnas")
    
    # Verificar relaciones en Cliente
    relaciones_cliente = ['concesionario_rel', 'modelo_vehiculo_rel', 'asesor_config_rel']
    for rel in relaciones_cliente:
        if hasattr(Cliente, rel):
            print(f"✅ Relación '{rel}' existe en Cliente")
        else:
            print(f"❌ Relación '{rel}' NO existe en Cliente")
    
    # Verificar Asesor
    asesor_cols = [col.name for col in Asesor.__table__.columns]
    print(f"✅ Modelo Asesor: {len(asesor_cols)} columnas")
    
    # Verificar Concesionario
    concesionario_cols = [col.name for col in Concesionario.__table__.columns]
    print(f"✅ Modelo Concesionario: {len(concesionario_cols)} columnas")
    
    # Verificar ModeloVehiculo
    vehiculo_cols = [col.name for col in ModeloVehiculo.__table__.columns]
    print(f"✅ Modelo ModeloVehiculo: {len(vehiculo_cols)} columnas")
    
except Exception as e:
    print(f"❌ Error verificando modelos: {e}")

# 6. VERIFICAR PROPIEDADES DEL MODELO CLIENTE
print("\n🎯 6. VERIFICANDO PROPIEDADES DEL MODELO CLIENTE...")
propiedades_requeridas = [
    'nombre_completo',
    'tiene_financiamiento',
    'vehiculo_completo',
    'esta_en_mora',
    'concesionario_nombre',
    'modelo_vehiculo_nombre',
    'asesor_config_nombre'
]

for prop in propiedades_requeridas:
    if hasattr(Cliente, prop):
        print(f"✅ Propiedad '{prop}' existe")
    else:
        print(f"❌ Propiedad '{prop}' NO existe")

# 7. TEST DE QUERY SIMPLE
print("\n💾 7. TEST DE QUERY SIMPLE...")
try:
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Contar registros
    count_clientes = session.query(Cliente).count()
    count_asesores = session.query(Asesor).count()
    count_concesionarios = session.query(Concesionario).count()
    count_vehiculos = session.query(ModeloVehiculo).count()
    
    print(f"✅ Clientes en BD: {count_clientes}")
    print(f"✅ Asesores en BD: {count_asesores}")
    print(f"✅ Concesionarios en BD: {count_concesionarios}")
    print(f"✅ Modelos de vehículos en BD: {count_vehiculos}")
    
    # Test de relación si hay datos
    if count_clientes > 0:
        cliente = session.query(Cliente).first()
        print(f"\n🧪 TEST DE RELACIONES CON CLIENTE ID {cliente.id}:")
        print(f"   - Cédula: {cliente.cedula}")
        print(f"   - Nombre: {cliente.nombre_completo}")
        print(f"   - Asesor Config ID: {cliente.asesor_config_id}")
        print(f"   - Asesor Config Nombre: {cliente.asesor_config_nombre}")
        print(f"   - Concesionario ID: {cliente.concesionario_id}")
        print(f"   - Concesionario Nombre: {cliente.concesionario_nombre}")
        print(f"   - Modelo Vehículo ID: {cliente.modelo_vehiculo_id}")
        print(f"   - Modelo Vehículo Nombre: {cliente.modelo_vehiculo_nombre}")
    
    session.close()
    
except Exception as e:
    print(f"❌ Error en queries: {e}")
    import traceback
    traceback.print_exc()

# 8. VERIFICAR MÉTODOS TO_DICT
print("\n📦 8. VERIFICANDO MÉTODOS TO_DICT()...")
try:
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Test Asesor.to_dict()
    if session.query(Asesor).count() > 0:
        asesor = session.query(Asesor).first()
        asesor_dict = asesor.to_dict()
        campos_esperados = ['id', 'nombre', 'activo', 'created_at', 'updated_at']
        for campo in campos_esperados:
            if campo in asesor_dict:
                print(f"✅ Asesor.to_dict() contiene '{campo}'")
            else:
                print(f"❌ Asesor.to_dict() NO contiene '{campo}'")
    
    # Test Concesionario.to_dict()
    if session.query(Concesionario).count() > 0:
        concesionario = session.query(Concesionario).first()
        concesionario_dict = concesionario.to_dict()
        campos_esperados = ['id', 'nombre', 'activo', 'created_at', 'updated_at']
        for campo in campos_esperados:
            if campo in concesionario_dict:
                print(f"✅ Concesionario.to_dict() contiene '{campo}'")
            else:
                print(f"❌ Concesionario.to_dict() NO contiene '{campo}'")
    
    # Test ModeloVehiculo.to_dict()
    if session.query(ModeloVehiculo).count() > 0:
        vehiculo = session.query(ModeloVehiculo).first()
        vehiculo_dict = vehiculo.to_dict()
        campos_esperados = ['id', 'modelo', 'activo', 'created_at', 'updated_at']
        for campo in campos_esperados:
            if campo in vehiculo_dict:
                print(f"✅ ModeloVehiculo.to_dict() contiene '{campo}'")
            else:
                print(f"❌ ModeloVehiculo.to_dict() NO contiene '{campo}'")
    
    session.close()
    
except Exception as e:
    print(f"❌ Error verificando to_dict(): {e}")

# RESUMEN FINAL
print("\n" + "=" * 80)
print("📊 RESUMEN DE VERIFICACIÓN")
print("=" * 80)
print("✅ Todos los tests completados")
print("🎯 Si todos los checks son ✅, la integración es correcta")
print("⚠️  Si hay ❌, revisar y corregir antes de deployment")
print("=" * 80)

