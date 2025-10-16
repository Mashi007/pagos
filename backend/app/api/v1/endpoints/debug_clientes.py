"""
Endpoint de diagnóstico profundo para clientes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.cliente import ClienteCreate
import logging
import traceback

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/debug/cliente-model")
def debug_cliente_model(db: Session = Depends(get_db)):
    """
    Verificar estructura del modelo Cliente
    """
    try:
        inspector = inspect(Cliente)
        
        columns_info = []
        for col in inspector.columns:
            columns_info.append({
                "name": col.name,
                "type": str(col.type),
                "nullable": col.nullable,
                "primary_key": col.primary_key,
                "foreign_keys": [str(fk.column) for fk in col.foreign_keys] if col.foreign_keys else []
            })
        
        return {
            "status": "success",
            "table_name": Cliente.__tablename__,
            "columns": columns_info,
            "total_columns": len(columns_info)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@router.get("/debug/cliente-db-structure")
def debug_cliente_db_structure(db: Session = Depends(get_db)):
    """
    Verificar estructura real de la tabla clientes en la BD
    """
    try:
        # Usar SQL directo para verificar estructura
        query = text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'clientes'
            ORDER BY ordinal_position;
        """)
        
        result = db.execute(query)
        columns = []
        for row in result:
            columns.append({
                "name": row[0],
                "type": row[1],
                "nullable": row[2],
                "default": row[3]
            })
        
        return {
            "status": "success",
            "table": "clientes",
            "columns": columns,
            "total_columns": len(columns)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@router.post("/debug/test-insert")
def debug_test_insert(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Probar inserción con datos mínimos
    """
    try:
        # Datos mínimos para inserción
        cliente = Cliente(
            cedula="999-TEST-999",
            nombres="Test",
            apellidos="Debug",
            estado="ACTIVO",
            activo=True
        )
        
        db.add(cliente)
        db.flush()  # No commit, solo flush para obtener ID
        
        cliente_id = cliente.id
        
        db.rollback()  # Rollback para no guardar datos de prueba
        
        return {
            "status": "success",
            "message": "Inserción de prueba exitosa (rollback aplicado)",
            "test_id": cliente_id
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@router.post("/debug/test-create-schema")
def debug_test_create_schema(
    current_user: User = Depends(get_current_user)
):
    """
    Probar validación del schema ClienteCreate
    """
    try:
        # Datos de prueba
        test_data = {
            "cedula": "001-1234567-8",
            "nombres": "Roberto",
            "apellidos": "Sanchez Garcia",
            "telefono": "809-555-2001",
            "email": "roberto.sanchez@email.com",
            "direccion": "Calle Principal #123",
            "fecha_nacimiento": "1985-06-15",
            "ocupacion": "Ingeniero",
            "modelo_vehiculo": "Toyota Corolla 2023",
            "marca_vehiculo": "Toyota",
            "anio_vehiculo": 2023,
            "color_vehiculo": "Blanco",
            "chasis": "TC2023-001-ABC",
            "motor": "1.8L-001",
            "concesionario": "AutoMax Santo Domingo",
            "vendedor_concesionario": "Pedro Martinez",
            "total_financiamiento": 25000.00,
            "cuota_inicial": 5000.00,
            "fecha_entrega": "2024-01-15",
            "numero_amortizaciones": 36,
            "modalidad_pago": "MENSUAL",
            "asesor_config_id": 1,
            "notas": "Cliente nuevo"
        }
        
        # Validar con Pydantic
        cliente_create = ClienteCreate(**test_data)
        cliente_dict = cliente_create.model_dump()
        
        # Filtrar campos válidos
        campos_validos = {
            'cedula', 'nombres', 'apellidos', 'telefono', 'email', 'direccion',
            'fecha_nacimiento', 'ocupacion', 'modelo_vehiculo', 'marca_vehiculo',
            'anio_vehiculo', 'color_vehiculo', 'chasis', 'motor', 'concesionario',
            'vendedor_concesionario', 'total_financiamiento', 'cuota_inicial',
            'fecha_entrega', 'numero_amortizaciones', 'modalidad_pago',
            'asesor_config_id', 'notas'
        }
        
        cliente_dict_filtrado = {k: v for k, v in cliente_dict.items() if k in campos_validos}
        
        # Calcular monto_financiado
        if 'total_financiamiento' in cliente_dict_filtrado and 'cuota_inicial' in cliente_dict_filtrado:
            total = cliente_dict_filtrado.get('total_financiamiento', 0) or 0
            inicial = cliente_dict_filtrado.get('cuota_inicial', 0) or 0
            cliente_dict_filtrado['monto_financiado'] = total - inicial
        
        return {
            "status": "success",
            "message": "Validación de schema exitosa",
            "original_keys": list(cliente_dict.keys()),
            "filtered_keys": list(cliente_dict_filtrado.keys()),
            "removed_keys": list(set(cliente_dict.keys()) - set(cliente_dict_filtrado.keys())),
            "data": cliente_dict_filtrado
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

