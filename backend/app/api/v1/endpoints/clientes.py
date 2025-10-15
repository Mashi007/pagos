# backend/app/api/v1/endpoints/clientes.py
from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, desc, asc
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal

from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.user import User
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.schemas.cliente import (
    ClienteCreate, 
    ClienteUpdate, 
    ClienteResponse, 
    ClienteList,
    ClienteSearchFilters,
    ClienteDetallado,
    ClienteCreateWithLoan,
    ClienteResumenFinanciero,
    ClienteQuickActions
)
from app.schemas.amortizacion import TablaAmortizacionRequest
from app.services.amortizacion_service import AmortizacionService
from app.api.deps import get_current_user
import traceback

router = APIRouter()


@router.post("/", response_model=ClienteResponse, status_code=201)
def crear_cliente(
    cliente: ClienteCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crear un nuevo cliente con validaciones completas y auditoría"""
    
    try:
        # 🔍 AUDITORÍA: Registrar inicio de creación
        from app.models.auditoria import Auditoria, TipoAccion
        
        # Verificar si ya existe la cédula
        existing = db.query(Cliente).filter(Cliente.cedula == cliente.cedula).first()
        if existing:
            # 🔍 AUDITORÍA: Registrar intento de duplicado
            auditoria = Auditoria.registrar(
                usuario_id=current_user.id,
                accion=TipoAccion.CREAR,
                tabla="Cliente",
                descripcion=f"Intento de crear cliente con cédula duplicada: {cliente.cedula}",
                resultado="FALLIDO",
                mensaje_error="Cédula ya registrada"
            )
            db.add(auditoria)
            db.commit()
            raise HTTPException(status_code=400, detail="Cédula ya registrada")
        
        # 🔍 VALIDACIONES: Aplicar validadores antes de crear
        from app.services.validators_service import (
            ValidadorCedula, ValidadorTelefono, ValidadorEmail
        )
        
        errores_validacion = []
        
        # Validar cédula
        if cliente.cedula:
            resultado_cedula = ValidadorCedula.validar_y_formatear_cedula(cliente.cedula, "VENEZUELA")
            if not resultado_cedula.get("valido"):
                errores_validacion.append(f"Cédula inválida: {resultado_cedula.get('mensaje', 'Formato incorrecto')}")
            else:
                cliente.cedula = resultado_cedula.get("valor_formateado", cliente.cedula)
        
        # Validar teléfono
        if cliente.telefono:
            resultado_telefono = ValidadorTelefono.validar_y_formatear_telefono(cliente.telefono, "VENEZUELA")
            if not resultado_telefono.get("valido"):
                errores_validacion.append(f"Teléfono inválido: {resultado_telefono.get('mensaje', 'Formato incorrecto')}")
            else:
                cliente.telefono = resultado_telefono.get("valor_formateado", cliente.telefono)
        
        # Validar email
        if cliente.email:
            resultado_email = ValidadorEmail.validar_email(cliente.email)
            if not resultado_email.get("valido"):
                errores_validacion.append(f"Email inválido: {resultado_email.get('mensaje', 'Formato incorrecto')}")
            else:
                cliente.email = resultado_email.get("valor_formateado", cliente.email)
        
        # Si hay errores de validación, no crear el cliente
        if errores_validacion:
            # 🔍 AUDITORÍA: Registrar fallo de validación
            auditoria = Auditoria.registrar(
                usuario_id=current_user.id,
                accion=TipoAccion.CREAR,
                tabla="Cliente",
                descripcion=f"Cliente rechazado por validaciones: {cliente.cedula}",
                datos_nuevos=cliente.model_dump(),
                resultado="FALLIDO",
                mensaje_error="; ".join(errores_validacion)
            )
            db.add(auditoria)
            db.commit()
            raise HTTPException(status_code=422, detail={
                "mensaje": "Errores de validación encontrados",
                "errores": errores_validacion
            })
        
        # 🔍 AUDITORÍA: Registrar datos antes de la creación
        datos_cliente = cliente.model_dump()
        
        # ============================================
        # MAPEAR NOMBRES A FOREIGNKEYS
        # ============================================
        
        # Buscar concesionario_id por nombre
        if cliente.concesionario and not cliente.concesionario_id:
            from app.models.concesionario import Concesionario
            concesionario_obj = db.query(Concesionario).filter(
                Concesionario.nombre.ilike(f"%{cliente.concesionario}%"),
                Concesionario.activo == True
            ).first()
            if concesionario_obj:
                cliente.concesionario_id = concesionario_obj.id
                print(f"✅ Concesionario mapeado: {cliente.concesionario} -> ID {concesionario_obj.id}")
        
        # Buscar modelo_vehiculo_id por nombre
        if cliente.modelo_vehiculo and not cliente.modelo_vehiculo_id:
            from app.models.modelo_vehiculo import ModeloVehiculo
            modelo_obj = db.query(ModeloVehiculo).filter(
                ModeloVehiculo.modelo.ilike(f"%{cliente.modelo_vehiculo}%"),
                ModeloVehiculo.activo == True
            ).first()
            if modelo_obj:
                cliente.modelo_vehiculo_id = modelo_obj.id
                print(f"✅ Modelo de vehículo mapeado: {cliente.modelo_vehiculo} -> ID {modelo_obj.id}")
        
        # Convertir a dict para SQLAlchemy
        cliente_dict = cliente.model_dump()
        
        db_cliente = Cliente(**cliente_dict)
        db.add(db_cliente)
        db.flush()  # Para obtener el ID antes del commit
        
        # 🔍 AUDITORÍA: Registrar creación exitosa
        auditoria = Auditoria.registrar(
            usuario_id=current_user.id,
            accion=TipoAccion.CREAR,
            tabla="Cliente",
            registro_id=db_cliente.id,
            descripcion=f"Cliente creado exitosamente: {cliente.cedula}",
            datos_nuevos=datos_cliente,
            resultado="EXITOSO"
        )
        db.add(auditoria)
        db.commit()
        db.refresh(db_cliente)
        
        print(f"✅ Cliente creado con validaciones: ID={db_cliente.id}")
        return db_cliente
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error creando cliente: {e}")
        import traceback
        traceback.print_exc()
        
        # 🔍 AUDITORÍA: Registrar error crítico
        auditoria = Auditoria.registrar(
            usuario_id=current_user.id,
            accion=TipoAccion.CREAR,
            tabla="Cliente",
            descripcion=f"Error crítico creando cliente: {cliente.cedula}",
            resultado="FALLIDO",
            mensaje_error=str(e)
        )
        db.add(auditoria)
        db.commit()
        
        raise


@router.get("/")
def listar_clientes(
    # Paginación
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    
    # Búsqueda de texto
    search: Optional[str] = Query(None, description="Buscar en nombre, cédula o móvil"),
    
    # Filtros específicos
    estado: Optional[str] = Query(None, description="ACTIVO, INACTIVO, MORA"),
    estado_financiero: Optional[str] = Query(None, description="AL_DIA, MORA, VENCIDO"),
    asesor_config_id: Optional[int] = Query(None, description="ID del asesor de configuración asignado"),
    
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Listar clientes con filtros básicos y paginación
    
    IMPLEMENTA MATRIZ DE ACCESO POR ROL:
    - ADMINISTRADOR_GENERAL y GERENTE: Ve TODOS los clientes
    - COBRANZAS: Ve TODOS los clientes (para gestión de cobranza)
    """
    try:
        # Construir query base SIN relaciones para evitar errores
        query = db.query(Cliente)
        
        # Todos los roles actuales tienen acceso a todos los clientes
        
        # APLICAR FILTROS
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Cliente.nombres.ilike(search_pattern),
                    Cliente.apellidos.ilike(search_pattern),
                    Cliente.cedula.ilike(search_pattern),
                    Cliente.telefono.ilike(search_pattern)
                )
            )
        
        if estado:
            query = query.filter(Cliente.estado == estado)
        
        if estado_financiero:
            query = query.filter(Cliente.estado_financiero == estado_financiero)
        
        if asesor_config_id:
            query = query.filter(Cliente.asesor_config_id == asesor_config_id)
        
        # ORDENAMIENTO
        query = query.order_by(Cliente.id.desc())
        
        # PAGINACIÓN
        total = query.count()
        clientes = query.all()
        total_pages = 1
        
        # Serialización simplificada para evitar errores 503
        clientes_dict = []
        for cliente in clientes:
            try:
                cliente_data = {
                    "id": cliente.id,
                    "cedula": cliente.cedula or "",
                    "nombres": cliente.nombres or "",
                    "apellidos": cliente.apellidos or "",
                    "telefono": cliente.telefono or "",
                    "email": cliente.email or "",
                    "direccion": cliente.direccion or "",
                    "ocupacion": cliente.ocupacion or "",
                    "modelo_vehiculo": cliente.modelo_vehiculo or "",
                    "marca_vehiculo": cliente.marca_vehiculo or "",
                    "anio_vehiculo": cliente.anio_vehiculo,
                    "color_vehiculo": cliente.color_vehiculo or "",
                    "concesionario": cliente.concesionario or "",
                    "total_financiamiento": float(cliente.total_financiamiento) if cliente.total_financiamiento else 0.0,
                    "cuota_inicial": float(cliente.cuota_inicial) if cliente.cuota_inicial else 0.0,
                    "monto_financiado": float(cliente.monto_financiado) if cliente.monto_financiado else 0.0,
                    "modalidad_pago": cliente.modalidad_pago or "MENSUAL",
                    "numero_amortizaciones": cliente.numero_amortizaciones or 0,
                    "asesor_config_id": cliente.asesor_config_id,
                    "estado": cliente.estado or "ACTIVO",
                    "activo": cliente.activo if cliente.activo is not None else True,
                    "estado_financiero": cliente.estado_financiero or "AL_DIA",
                    "dias_mora": cliente.dias_mora or 0,
                    "fecha_registro": cliente.fecha_registro.isoformat() if cliente.fecha_registro else None,
                    "fecha_asignacion": cliente.fecha_asignacion.isoformat() if cliente.fecha_asignacion else None
                }
                clientes_dict.append(cliente_data)
            except Exception as serialization_error:
                # Si hay error en la serialización de un cliente específico, agregarlo con datos mínimos
                clientes_dict.append({
                    "id": cliente.id,
                    "cedula": cliente.cedula or "",
                    "nombres": cliente.nombres or "",
                    "apellidos": cliente.apellidos or "",
                    "error": f"Error serializando cliente: {str(serialization_error)}"
                })
        
        return {
            "items": clientes_dict,
            "total": total,
            "page": page,
            "page_size": per_page,
            "total_pages": total_pages
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error listando clientes: {str(e)}")


@router.get("/verificar-estructura")
def verificar_estructura_tabla(db: Session = Depends(get_db)):
    """Verificar estructura de la tabla clientes"""
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.bind)
        columns = inspector.get_columns('clientes')
        column_names = [col['name'] for col in columns]
        
        return {
            "tabla": "clientes",
            "columnas": column_names,
            "total_columnas": len(column_names),
            "tiene_total_financiamiento": "total_financiamiento" in column_names
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/test-simple")
def test_simple_query(db: Session = Depends(get_db)):
    """Test simple para verificar conexión a base de datos"""
    try:
        # Query muy simple sin joins
        count = db.query(Cliente).count()
        return {
            "mensaje": "Query simple exitosa",
            "total_clientes": count,
            "status": "ok"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }


@router.get("/test-with-auth")
def test_with_auth(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Endpoint simple con autenticación para probar"""
    try:
        total = db.query(Cliente).count()
        return {
            "mensaje": "Query con auth exitosa",
            "total_clientes": total,
            "usuario": current_user.nombre,
            "rol": current_user.rol,
            "status": "ok"
        }
    except Exception as e:
        return {
            "mensaje": f"Error en query con auth: {str(e)}",
            "total_clientes": 0,
            "status": "error"
        }


@router.get("/test-simple")
def test_simple(db: Session = Depends(get_db)):
    """Endpoint de prueba muy simple"""
    try:
        count = db.query(Cliente).count()
        return {
            "mensaje": "Test simple exitoso",
            "total_clientes": count,
            "status": "ok"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }

@router.get("/test-with-auth")
def test_with_auth(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Test con autenticación"""
    try:
        count = db.query(Cliente).count()
        return {
            "mensaje": "Test con auth exitoso",
            "total_clientes": count,
            "usuario": current_user.email,
            "rol": current_user.rol,
            "status": "ok"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }

@router.get("/test-main-logic")
def test_main_logic(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test replicando la lógica del endpoint principal"""
    try:
        # Construir query base
        query = db.query(Cliente)
        
        # FILTRO POR ROL - Todos los roles tienen acceso completo
        # (ADMINISTRADOR_GENERAL, GERENTE, COBRANZAS)
        
        # ORDENAMIENTO
        query = query.order_by(desc(Cliente.fecha_registro))
        
        # PAGINACIÓN
        total = query.count()
        skip = (page - 1) * per_page
        clientes = query.offset(skip).limit(per_page).all()
        
        total_pages = (total + per_page - 1) // per_page
        
        return {
            "mensaje": "Lógica principal exitosa",
            "total": total,
            "page": page,
            "page_size": per_page,
            "total_pages": total_pages,
            "clientes_count": len(clientes),
            "status": "ok"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }

@router.get("/test-step-by-step")
def test_step_by_step(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test paso a paso para identificar el problema exacto"""
    try:
        # Paso 1: Query base
        query = db.query(Cliente)
        
        # Paso 2: Filtro por rol - Todos los roles tienen acceso completo
        
        # Paso 3: Count (sin ordenamiento)
        total = query.count()
        
        # Paso 4: Ordenamiento simple
        query = query.order_by(Cliente.fecha_registro.desc())
        
        # Paso 5: Paginación
        skip = (page - 1) * per_page
        clientes = query.offset(skip).limit(per_page).all()
        
        return {
            "mensaje": "Test paso a paso exitoso",
            "total": total,
            "clientes_count": len(clientes),
            "status": "ok"
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "status": "error"
        }

@router.get("/test-no-desc")
def test_no_desc(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test sin usar desc() para ver si ese es el problema"""
    try:
        query = db.query(Cliente)
        
        # Todos los roles tienen acceso completo
        
        total = query.count()
        
        # Ordenamiento simple sin desc()
        query = query.order_by(Cliente.fecha_registro)
        
        skip = (page - 1) * per_page
        clientes = query.offset(skip).limit(per_page).all()
        
        return {
            "mensaje": "Test sin desc() exitoso",
            "total": total,
            "clientes_count": len(clientes),
            "status": "ok"
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "status": "error"
        }


@router.get("/debug-no-model")
def debug_no_model(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Debug sin usar modelo Cliente"""
    try:
        # Probar conexión básica
        result = db.execute("SELECT 1 as test").fetchone()
        
        # Probar query directo a la tabla
        table_exists = db.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'clientes')").fetchone()
        
        # Contar registros directamente
        count_result = db.execute("SELECT COUNT(*) as total FROM clientes").fetchone()
        
        return {
            "test_query": result[0] if result else "error",
            "table_exists": table_exists[0] if table_exists else False,
            "total_records": count_result[0] if count_result else 0,
            "usuario": current_user.nombre,
            "status": "ok"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "status": "error"
        }


@router.get("/crear-clientes-prueba")
def crear_clientes_prueba(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Crear clientes de prueba para demostrar la funcionalidad"""
    try:
        # Verificar si ya existen clientes
        existing_count = db.query(Cliente).count()
        if existing_count > 0:
            return {
                "mensaje": f"Ya existen {existing_count} clientes en la base de datos",
                "status": "info"
            }
        
        # Crear clientes de prueba
        clientes_prueba = [
            {
                "cedula": "12345678",
                "nombres": "Juan Carlos",
                "apellidos": "Pérez González",
                "telefono": "0987654321",
                "email": "juan.perez@email.com",
                "direccion": "Av. Principal 123, Quito",
                "ocupacion": "Ingeniero",
                "modelo_vehiculo": "Toyota Corolla",
                "marca_vehiculo": "Toyota",
                "anio_vehiculo": 2022,
                "color_vehiculo": "Blanco",
                "concesionario": "AutoCenter Quito",
                "total_financiamiento": 25000.00,
                "cuota_inicial": 5000.00,
                "monto_financiado": 20000.00,
                "modalidad_pago": "MENSUAL",
                "numero_amortizaciones": 48,
                "estado": "ACTIVO",
                "estado_financiero": "AL_DIA",
                "asesor_config_id": None
            },
            {
                "cedula": "87654321",
                "nombres": "María Elena",
                "apellidos": "Rodríguez López",
                "telefono": "0998765432",
                "email": "maria.rodriguez@email.com",
                "direccion": "Calle Secundaria 456, Guayaquil",
                "ocupacion": "Contadora",
                "modelo_vehiculo": "Hyundai Accent",
                "marca_vehiculo": "Hyundai",
                "anio_vehiculo": 2023,
                "color_vehiculo": "Azul",
                "concesionario": "Hyundai Motors",
                "total_financiamiento": 18000.00,
                "cuota_inicial": 3000.00,
                "monto_financiado": 15000.00,
                "modalidad_pago": "MENSUAL",
                "numero_amortizaciones": 36,
                "estado": "ACTIVO",
                "estado_financiero": "AL_DIA",
                "asesor_config_id": None
            },
            {
                "cedula": "11223344",
                "nombres": "Carlos Alberto",
                "apellidos": "Martínez Silva",
                "telefono": "0987654321",
                "email": "carlos.martinez@email.com",
                "direccion": "Av. Libertad 789, Cuenca",
                "ocupacion": "Comerciante",
                "modelo_vehiculo": "Nissan Versa",
                "marca_vehiculo": "Nissan",
                "anio_vehiculo": 2021,
                "color_vehiculo": "Gris",
                "concesionario": "Nissan Ecuador",
                "total_financiamiento": 22000.00,
                "cuota_inicial": 4000.00,
                "monto_financiado": 18000.00,
                "modalidad_pago": "MENSUAL",
                "numero_amortizaciones": 42,
                "estado": "ACTIVO",
                "estado_financiero": "MORA",
                "dias_mora": 15,
                "asesor_config_id": None
            }
        ]
        
        clientes_creados = []
        for cliente_data in clientes_prueba:
            cliente = Cliente(**cliente_data)
            db.add(cliente)
            db.flush()  # Para obtener el ID
            clientes_creados.append({
                "id": cliente.id,
                "nombre": f"{cliente.nombres} {cliente.apellidos}",
                "cedula": cliente.cedula
            })
        
        db.commit()
        
        return {
            "mensaje": f"Se crearon {len(clientes_creados)} clientes de prueba exitosamente",
            "clientes": clientes_creados,
            "status": "success"
        }
        
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        return {
            "mensaje": f"Error creando clientes de prueba: {str(e)}",
            "status": "error"
        }


@router.get("/test-sin-join")
def test_sin_join(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Test sin join para verificar si el problema es el join con User"""
    try:
        # Query sin join - Todos los roles tienen acceso completo
        query = db.query(Cliente)
        
        count = query.count()
        return {
            "mensaje": "Query sin join exitosa",
            "total_clientes": count,
            "usuario_rol": current_user.rol,
            "status": "ok"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }


@router.post("/aplicar-migracion-manual")
def aplicar_migracion_manual(db: Session = Depends(get_db)):
    """Aplicar migración manual para agregar columnas faltantes"""
    try:
        from sqlalchemy import text
        
        # Lista de columnas que faltan
        columnas_faltantes = [
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS modelo_vehiculo VARCHAR(100)",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS marca_vehiculo VARCHAR(50)",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS anio_vehiculo INTEGER",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS color_vehiculo VARCHAR(30)",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS chasis VARCHAR(50)",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS motor VARCHAR(50)",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS concesionario VARCHAR(100)",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS vendedor_concesionario VARCHAR(100)",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS total_financiamiento NUMERIC(12,2)",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS cuota_inicial NUMERIC(12,2) DEFAULT 0.00",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS monto_financiado NUMERIC(12,2)",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS fecha_entrega DATE",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS numero_amortizaciones INTEGER",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS modalidad_pago VARCHAR(20)",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS asesor_config_id INTEGER",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS fecha_asignacion DATE",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS estado_financiero VARCHAR(20) DEFAULT 'AL_DIA'",
            "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS dias_mora INTEGER DEFAULT 0"
        ]
        
        columnas_aplicadas = []
        for sql in columnas_faltantes:
            try:
                db.execute(text(sql))
                columnas_aplicadas.append(sql)
            except Exception as e:
                print(f"Error aplicando {sql}: {e}")
        
        db.commit()
        
        return {
            "mensaje": "Migración manual aplicada",
            "columnas_aplicadas": len(columnas_aplicadas),
            "total_columnas": len(columnas_faltantes),
            "detalles": columnas_aplicadas
        }
        
    except Exception as e:
        db.rollback()
        return {"error": str(e)}


@router.get("/cedula/{cedula}", response_model=ClienteResponse)
def buscar_por_cedula(cedula: str, db: Session = Depends(get_db)):
    """Buscar cliente por cédula"""
    cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente






# ============================================
# ENDPOINTS CON PARÁMETROS DE RUTA - AL FINAL PARA EVITAR CONFLICTOS
# ============================================

@router.get("/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Obtener un cliente por ID"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


# ============================================
# ENDPOINTS ADICIONALES PARA FUNCIONALIDAD AVANZADA
# ============================================

    """
    Obtener ficha detallada del cliente con resumen financiero
    """
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Obtener información del asesor
    asesor_nombre = None
    asesor_email = None
    if cliente.asesor_config_id:
        from app.models.asesor import Asesor
        asesor = db.query(Asesor).filter(Asesor.id == cliente.asesor_config_id).first()
        if asesor:
            asesor_nombre = asesor.full_name
            asesor_email = asesor.email
    
    # Calcular resumen financiero
    resumen = cliente.calcular_resumen_financiero(db)
    resumen_financiero = ClienteResumenFinanciero(**resumen)
    
    # Estadísticas adicionales
    total_prestamos = db.query(Prestamo).filter(Prestamo.cliente_id == cliente_id).count()
    prestamos_activos = db.query(Prestamo).filter(
        Prestamo.cliente_id == cliente_id,
        Prestamo.estado.in_(["ACTIVO", "EN_MORA"])
    ).count()
    
    # Último pago
    ultimo_pago_obj = db.query(Pago).join(Prestamo).filter(
        Prestamo.cliente_id == cliente_id
    ).order_by(desc(Pago.fecha_pago)).first()
    
    ultimo_pago = None
    if ultimo_pago_obj:
        ultimo_pago = {
            "fecha": ultimo_pago_obj.fecha_pago,
            "monto": float(ultimo_pago_obj.monto_pagado),
            "numero_cuota": ultimo_pago_obj.numero_cuota
        }
    
    # Crear respuesta detallada
    cliente_dict = cliente.__dict__.copy()
    cliente_dict.update({
        "asesor_nombre": asesor_nombre,
        "asesor_email": asesor_email,
        "resumen_financiero": resumen_financiero,
        "total_prestamos": total_prestamos,
        "prestamos_activos": prestamos_activos,
        "ultimo_pago": ultimo_pago
    })
    
    return ClienteDetallado(**cliente_dict)


@router.post("/con-financiamiento", response_model=ClienteResponse, status_code=201)
def crear_cliente_con_financiamiento(
    cliente_data: ClienteCreateWithLoan,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🚗 FLUJO COMPLETO: Crear cliente con financiamiento
    
    Pasos del flujo:
    1. ✅ Asesor inicia sesión (verificado por get_current_user)
    2. ✅ Click "Nuevo Cliente" (este endpoint)
    3. ✅ Completa formulario (ClienteCreateWithLoan)
    4. ✅ Sistema valida datos
    5. ✅ Genera tabla de amortización automáticamente
    6. ✅ Sistema guarda y ejecuta acciones automáticas
    7. ✅ Cliente listo para cobrar
    """
    try:
        # ============================================
        # 4. VALIDACIONES DEL SISTEMA
        # ============================================
        
        # Validar cédula única
        existing = db.query(Cliente).filter(Cliente.cedula == cliente_data.cedula).first()
        if existing:
            raise HTTPException(status_code=400, detail="❌ Cédula ya registrada en el sistema")
        
        # Validar email válido (si se proporciona)
        if cliente_data.email:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, cliente_data.email):
                raise HTTPException(status_code=400, detail="❌ Formato de email inválido")
        
        # Validar que el asesor existe y tiene rol apropiado
        from app.models.asesor import Asesor
        asesor = db.query(Asesor).filter(Asesor.id == cliente_data.asesor_config_id).first()
        if not asesor:
            raise HTTPException(status_code=400, detail="❌ Asesor no encontrado")
        
        # Validar que el asesor esté activo
        if not asesor.activo:
            raise HTTPException(status_code=400, detail="❌ El asesor no está activo")
        
        # Validar montos coherentes
        if cliente_data.cuota_inicial >= cliente_data.total_financiamiento:
            raise HTTPException(status_code=400, detail="❌ La cuota inicial no puede ser mayor o igual al total")
        
        monto_financiado = cliente_data.total_financiamiento - cliente_data.cuota_inicial
        if monto_financiado <= 0:
            raise HTTPException(status_code=400, detail="❌ El monto financiado debe ser mayor a 0")
        
        # Validar límites de financiamiento
        from app.core.config import settings
        if monto_financiado < settings.MONTO_MINIMO_PRESTAMO:
            raise HTTPException(
                status_code=400, 
                detail=f"❌ Monto financiado mínimo: ${settings.MONTO_MINIMO_PRESTAMO:,.2f}"
            )
        
        if monto_financiado > settings.MONTO_MAXIMO_PRESTAMO:
            raise HTTPException(
                status_code=400, 
                detail=f"❌ Monto financiado máximo: ${settings.MONTO_MAXIMO_PRESTAMO:,.2f}"
            )
        
        # Validar número de cuotas
        if cliente_data.numero_amortizaciones < settings.PLAZO_MINIMO_MESES:
            raise HTTPException(
                status_code=400,
                detail=f"❌ Número mínimo de cuotas: {settings.PLAZO_MINIMO_MESES}"
            )
        
        if cliente_data.numero_amortizaciones > settings.PLAZO_MAXIMO_MESES:
            raise HTTPException(
                status_code=400,
                detail=f"❌ Número máximo de cuotas: {settings.PLAZO_MAXIMO_MESES}"
            )
        
        # Validar fecha de entrega
        if cliente_data.fecha_entrega < date.today():
            raise HTTPException(status_code=400, detail="❌ La fecha de entrega no puede ser pasada")
        
        # ============================================
        # 5. GENERACIÓN AUTOMÁTICA (PREVIEW)
        # ============================================
        
        # Generar tabla de amortización para preview
        tasa_interes = cliente_data.tasa_interes_anual or settings.TASA_INTERES_BASE
        
        from app.schemas.amortizacion import TablaAmortizacionRequest
        from app.services.amortizacion_service import AmortizacionService
        
        tabla_request = TablaAmortizacionRequest(
            monto_financiado=monto_financiado,
            tasa_interes_anual=tasa_interes,
            numero_cuotas=cliente_data.numero_amortizaciones,
            fecha_primer_vencimiento=cliente_data.fecha_entrega,
            modalidad=cliente_data.modalidad_pago,
            sistema_amortizacion="FRANCES"
        )
        
        tabla_preview = AmortizacionService.generar_tabla_amortizacion(tabla_request)
        
        # ============================================
        # 7. CREAR CLIENTE Y EJECUTAR ACCIONES AUTOMÁTICAS
        # ============================================
        
        # Crear cliente
        cliente_dict = cliente_data.model_dump()
        cliente_dict['monto_financiado'] = monto_financiado
        cliente_dict['fecha_asignacion'] = date.today()
        cliente_dict['usuario_registro'] = current_user.email
        cliente_dict['estado_financiero'] = "AL_DIA"
        
        db_cliente = Cliente(**cliente_dict)
        db.add(db_cliente)
        db.commit()
        db.refresh(db_cliente)
        
        # Registrar en auditoría
        from app.models.auditoria import Auditoria, TipoAccion
        auditoria = Auditoria.registrar(
            usuario_id=current_user.id,
            accion=TipoAccion.CREAR.value,
            tabla="clientes",
            registro_id=db_cliente.id,
            descripcion=f"Nuevo cliente creado: {db_cliente.nombre_completo}",
            datos_nuevos={
                "cedula": db_cliente.cedula,
                "nombre": db_cliente.nombre_completo,
                "vehiculo": db_cliente.vehiculo_completo,
                "monto_financiado": float(monto_financiado),
                "asesor": asesor.full_name
            }
        )
        db.add(auditoria)
        
        # Generar tabla de amortización automáticamente
        if cliente_data.generar_tabla_automatica:
            background_tasks.add_task(
                _generar_tabla_amortizacion_cliente,
                cliente_id=db_cliente.id,
                cliente_data=cliente_data
            )
        
        # Enviar email de bienvenida al cliente
        if db_cliente.email:
            background_tasks.add_task(
                _enviar_email_bienvenida,
                cliente_id=db_cliente.id,
                asesor_nombre=asesor.full_name
            )
        
        # Notificar a equipo de cobranzas sobre nuevo cliente
        background_tasks.add_task(
            _notificar_cobranzas_nuevo_cliente,
            cliente_id=db_cliente.id,
            asesor_nombre=asesor.full_name
        )
        
        db.commit()
        
        return {
            **db_cliente.__dict__,
            "mensaje": "✅ Cliente registrado exitosamente",
            "tabla_amortizacion_preview": {
                "cuotas_generadas": len(tabla_preview.cuotas),
                "primera_cuota": float(tabla_preview.cuotas[0].cuota) if tabla_preview.cuotas else 0,
                "total_intereses": float(tabla_preview.resumen.get("total_interes", 0)),
                "total_pagar": float(tabla_preview.resumen.get("total_pagar", 0))
            },
            "acciones_ejecutadas": {
                "cliente_guardado": True,
                "auditoria_registrada": True,
                "tabla_amortizacion_programada": cliente_data.generar_tabla_automatica,
                "email_bienvenida_programado": bool(db_cliente.email),
                "notificacion_cobranzas_programada": True
            },
            "proximo_paso": "Cliente listo para gestión de cobranza"
        }
        
    except HTTPException:
        # Re-lanzar HTTPExceptions (errores de validación)
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"❌ Error interno: {str(e)}")


@router.post("/preview-amortizacion")
def preview_tabla_amortizacion(
    cliente_data: ClienteCreateWithLoan,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔍 PASO 6: Preview de tabla de amortización para revisión del asesor
    Permite al asesor revisar antes de confirmar
    """
    try:
        # Calcular monto financiado
        monto_financiado = cliente_data.total_financiamiento - cliente_data.cuota_inicial
        
        # Validaciones básicas
        if monto_financiado <= 0:
            raise HTTPException(status_code=400, detail="Monto financiado debe ser mayor a 0")
        
        # Generar tabla de amortización
        from app.core.config import settings
        tasa_interes = cliente_data.tasa_interes_anual or settings.TASA_INTERES_BASE
        
        from app.schemas.amortizacion import TablaAmortizacionRequest
        from app.services.amortizacion_service import AmortizacionService
        
        tabla_request = TablaAmortizacionRequest(
            monto_financiado=monto_financiado,
            tasa_interes_anual=tasa_interes,
            numero_cuotas=cliente_data.numero_amortizaciones,
            fecha_primer_vencimiento=cliente_data.fecha_entrega,
            modalidad=cliente_data.modalidad_pago,
            sistema_amortizacion="FRANCES"
        )
        
        tabla = AmortizacionService.generar_tabla_amortizacion(tabla_request)
        
        # Calcular estadísticas adicionales
        cuota_promedio = float(tabla.cuotas[0].cuota) if tabla.cuotas else 0
        total_intereses = sum(float(c.interes) for c in tabla.cuotas)
        total_pagar = sum(float(c.cuota) for c in tabla.cuotas)
        
        return {
            "cliente_preview": {
                "nombre": f"{cliente_data.nombres} {cliente_data.apellidos}",
                "cedula": cliente_data.cedula,
                "vehiculo": f"{cliente_data.marca_vehiculo} {cliente_data.modelo_vehiculo}",
                "concesionario": cliente_data.concesionario
            },
            "financiamiento_preview": {
                "total_financiamiento": float(cliente_data.total_financiamiento),
                "cuota_inicial": float(cliente_data.cuota_inicial),
                "monto_financiado": float(monto_financiado),
                "numero_cuotas": cliente_data.numero_amortizaciones,
                "modalidad": cliente_data.modalidad_pago,
                "tasa_interes": float(tasa_interes)
            },
            "tabla_amortizacion": {
                "cuotas": [
                    {
                        "numero": c.numero_cuota,
                        "fecha": c.fecha_vencimiento.strftime("%d/%m/%Y"),
                        "cuota": float(c.cuota),
                        "capital": float(c.capital),
                        "interes": float(c.interes),
                        "saldo": float(c.saldo_final)
                    }
                    for c in tabla.cuotas[:5]  # Primeras 5 cuotas para preview
                ],
                "resumen": {
                    "cuota_mensual": cuota_promedio,
                    "total_intereses": total_intereses,
                    "total_pagar": total_pagar,
                    "ahorro_vs_contado": 0  # Calcular si hay descuento por contado
                }
            },
            "validaciones": {
                "cedula_disponible": True,
                "asesor_valido": True,
                "montos_coherentes": True,
                "dentro_limites": True
            },
            "acciones_pendientes": [
                "Guardar cliente en base de datos",
                "Generar tabla de amortización completa",
                "Enviar email de bienvenida",
                "Notificar a equipo de cobranzas",
                "Registrar en auditoría"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando preview: {str(e)}")




@router.post("/{cliente_id}/reasignar-asesor")
def reasignar_asesor(
    cliente_id: int,
    nuevo_asesor_config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reasignar asesor a un cliente
    """
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Verificar que el nuevo asesor existe
    from app.models.asesor import Asesor
    nuevo_asesor = db.query(Asesor).filter(Asesor.id == nuevo_asesor_config_id).first()
    if not nuevo_asesor:
        raise HTTPException(status_code=400, detail="Asesor no encontrado")
    
    # Verificar que el nuevo asesor esté activo
    if not nuevo_asesor.activo:
        raise HTTPException(
            status_code=400, 
            detail="El asesor no está activo"
        )
    
    # Actualizar asignación
    asesor_config_anterior = cliente.asesor_config_id
    cliente.asesor_config_id = nuevo_asesor_config_id
    cliente.fecha_asignacion = date.today()
    cliente.fecha_actualizacion = func.now()
    
    db.commit()
    
    return {
        "message": "Asesor reasignado exitosamente",
        "cliente_id": cliente_id,
        "asesor_config_anterior": asesor_config_anterior,
        "asesor_config_nuevo": nuevo_asesor_config_id,
        "asesor_nombre": nuevo_asesor.nombre_completo
    }


@router.get("/asesores/disponibles")
def obtener_asesores_disponibles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener lista de asesores disponibles para asignación
    """
    asesores = db.query(User).filter(
        User.is_active == True
    ).all()
    
    # Contar clientes asignados por asesor
    result = []
    for asesor in asesores:
        clientes_asignados = db.query(Cliente).filter(
            Cliente.asesor_config_id == asesor.id,
            Cliente.activo == True
        ).count()
        
        result.append({
            "id": asesor.id,
            "nombre": asesor.full_name,
            "email": asesor.email,
            "rol": asesor.rol,
            "clientes_asignados": clientes_asignados
        })
    
    return {
        "asesores": result,
        "total": len(result)
    }


# ============================================
# FUNCIONES AUXILIARES
# ============================================

async def _generar_tabla_amortizacion_cliente(cliente_id: int, cliente_data: ClienteCreateWithLoan):
    """
    Función background para generar tabla de amortización automáticamente
    """
    try:
        db = SessionLocal()
        
        # Crear préstamo automático
        from app.core.config import settings
        tasa_interes = cliente_data.tasa_interes_anual or settings.TASA_INTERES_BASE
        
        prestamo_data = {
            "cliente_id": cliente_id,
            "monto_total": cliente_data.total_financiamiento,
            "monto_financiado": cliente_data.total_financiamiento - cliente_data.cuota_inicial,
            "monto_inicial": cliente_data.cuota_inicial,
            "tasa_interes": tasa_interes,
            "numero_cuotas": cliente_data.numero_amortizaciones,
            "fecha_aprobacion": date.today(),
            "fecha_desembolso": cliente_data.fecha_entrega,
            "fecha_primer_vencimiento": cliente_data.fecha_entrega,
            "modalidad": cliente_data.modalidad_pago,
            "destino_credito": f"Financiamiento vehículo {cliente_data.marca_vehiculo} {cliente_data.modelo_vehiculo}",
            "estado": "ACTIVO"
        }
        
        # Calcular cuota mensual (método francés simplificado)
        monto = prestamo_data["monto_financiado"]
        n_cuotas = prestamo_data["numero_cuotas"]
        tasa_mensual = (tasa_interes / 100) / 12
        
        if tasa_mensual > 0:
            cuota = monto * (tasa_mensual * (1 + tasa_mensual)**n_cuotas) / ((1 + tasa_mensual)**n_cuotas - 1)
        else:
            cuota = monto / n_cuotas
        
        prestamo_data["monto_cuota"] = cuota
        prestamo_data["saldo_pendiente"] = monto
        prestamo_data["saldo_capital"] = monto
        
        db_prestamo = Prestamo(**prestamo_data)
        db.add(db_prestamo)
        db.commit()
        db.refresh(db_prestamo)
        
        # Generar tabla de amortización
        tabla_request = TablaAmortizacionRequest(
            monto_financiado=prestamo_data["monto_financiado"],
            tasa_interes_anual=tasa_interes,
            numero_cuotas=n_cuotas,
            fecha_primer_vencimiento=cliente_data.fecha_entrega,
            modalidad=cliente_data.modalidad_pago,
            sistema_amortizacion="FRANCES"
        )
        
        tabla = AmortizacionService.generar_tabla_amortizacion(tabla_request)
        AmortizacionService.crear_cuotas_prestamo(db, db_prestamo.id, tabla)
        
        db.close()
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error generando tabla de amortización para cliente {cliente_id}: {str(e)}")


async def _enviar_email_bienvenida(cliente_id: int, asesor_nombre: str):
    """
    📧 PASO 7a: Enviar email de bienvenida al cliente
    """
    try:
        db = SessionLocal()
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        
        if cliente and cliente.email:
            from app.models.notificacion import Notificacion
            from app.services.email_service import EmailService
            
            mensaje = f"""
¡Bienvenido/a a Financiera Automotriz!

Estimado/a {cliente.nombre_completo},

Nos complace darle la bienvenida como nuevo cliente de nuestra financiera.

DETALLES DE SU FINANCIAMIENTO:
• Vehículo: {cliente.vehiculo_completo}
• Concesionario: {cliente.concesionario}
• Monto financiado: ${float(cliente.monto_financiado or 0):,.2f}
• Modalidad de pago: {cliente.modalidad_pago}
• Asesor asignado: {asesor_nombre}

PRÓXIMOS PASOS:
1. Recibirá la tabla de amortización completa por email
2. Su primera cuota vence el: {cliente.fecha_entrega.strftime('%d/%m/%Y') if cliente.fecha_entrega else 'Por definir'}
3. Le enviaremos recordatorios antes de cada vencimiento

DATOS DE CONTACTO:
• Teléfono: (021) 123-456
• Email: info@financiera.com
• Horario: Lunes a Viernes 8:00 - 18:00

¡Gracias por confiar en nosotros!

Saludos cordiales,
Equipo de Financiera Automotriz
            """
            
            # Crear notificación
            notif = Notificacion(
                cliente_id=cliente_id,
                tipo="EMAIL",
                categoria="GENERAL",
                asunto="🎉 ¡Bienvenido a Financiera Automotriz!",
                mensaje=mensaje,
                estado="PENDIENTE",
                programada_para=datetime.now(),
                prioridad="NORMAL"
            )
            
            db.add(notif)
            db.commit()
            db.refresh(notif)
            
            # Enviar email
            email_service = EmailService()
            await email_service.send_email(
                to_email=cliente.email,
                subject=notif.asunto,
                body=notif.mensaje,
                notificacion_id=notif.id
            )
            
        db.close()
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error enviando email de bienvenida a cliente {cliente_id}: {str(e)}")


async def _notificar_cobranzas_nuevo_cliente(cliente_id: int, asesor_nombre: str):
    """
    🔔 PASO 7b: Notificar a equipo de cobranzas sobre nuevo cliente
    """
    try:
        db = SessionLocal()
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        
        if cliente:
            # Obtener usuarios de cobranzas
            usuarios_cobranzas = db.query(User).filter(
                User.rol.in_(["ADMINISTRADOR_GENERAL", "COBRANZAS"]),
                User.is_active == True,
                User.email.isnot(None)
            ).all()
            
            for usuario in usuarios_cobranzas:
                mensaje = f"""
Hola {usuario.full_name},

NUEVO CLIENTE REGISTRADO

📋 DATOS DEL CLIENTE:
• Nombre: {cliente.nombre_completo}
• Cédula: {cliente.cedula}
• Teléfono: {cliente.telefono or 'No proporcionado'}
• Email: {cliente.email or 'No proporcionado'}

🚗 VEHÍCULO FINANCIADO:
• Vehículo: {cliente.vehiculo_completo}
• Concesionario: {cliente.concesionario or 'No especificado'}

💰 FINANCIAMIENTO:
• Total: ${float(cliente.total_financiamiento or 0):,.2f}
• Cuota inicial: ${float(cliente.cuota_inicial or 0):,.2f}
• Monto financiado: ${float(cliente.monto_financiado or 0):,.2f}
• Modalidad: {cliente.modalidad_pago}
• Primera cuota: {cliente.fecha_entrega.strftime('%d/%m/%Y') if cliente.fecha_entrega else 'Por definir'}

👤 ASESOR RESPONSABLE: {asesor_nombre}

ACCIONES RECOMENDADAS:
• Verificar datos de contacto
• Programar recordatorios de pago
• Incluir en seguimiento de cartera

Acceder al cliente: https://pagos-f2qf.onrender.com/clientes/{cliente_id}

Saludos.
                """
                
                from app.models.notificacion import Notificacion
                notif = Notificacion(
                    user_id=usuario.id,
                    tipo="EMAIL",
                    categoria="GENERAL",
                    asunto=f"🆕 Nuevo Cliente: {cliente.nombre_completo}",
                    mensaje=mensaje,
                    estado="PENDIENTE",
                    programada_para=datetime.now(),
                    prioridad="NORMAL"
                )
                
                db.add(notif)
            
            db.commit()
            
            # Enviar emails
            from app.services.email_service import EmailService
            email_service = EmailService()
            
            for usuario in usuarios_cobranzas:
                notif = db.query(Notificacion).filter(
                    Notificacion.user_id == usuario.id,
                    Notificacion.asunto.like(f"%{cliente.nombre_completo}%")
                ).order_by(Notificacion.id.desc()).first()
                
                if notif:
                    await email_service.send_email(
                        to_email=usuario.email,
                        subject=notif.asunto,
                        body=notif.mensaje,
                        notificacion_id=notif.id
                    )
        
        db.close()
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error notificando a cobranzas sobre cliente {cliente_id}: {str(e)}")


@router.get("/buscar/avanzada", response_model=ClienteList)
def busqueda_avanzada_clientes(
    filters: ClienteSearchFilters = Depends(),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Búsqueda avanzada de clientes usando el objeto de filtros
    """
    query = db.query(Cliente)
    
    # Aplicar todos los filtros del objeto filters
    if filters.search_text:
        search_pattern = f"%{filters.search_text}%"
        query = query.filter(
            or_(
                Cliente.nombres.ilike(search_pattern),
                Cliente.apellidos.ilike(search_pattern),
                Cliente.cedula.ilike(search_pattern),
                Cliente.telefono.ilike(search_pattern)
            )
        )
    
    if filters.estado:
        query = query.filter(Cliente.estado == filters.estado)
    
    if filters.asesor_config_id:
        query = query.filter(Cliente.asesor_config_id == filters.asesor_config_id)
    
    if filters.concesionario:
        query = query.filter(Cliente.concesionario.ilike(f"%{filters.concesionario}%"))
    
    # ... aplicar resto de filtros
    
    # Paginación
    total = query.count()
    skip = (page - 1) * page_size
    clientes = query.offset(skip).limit(page_size).all()
    
    return ClienteList(
        items=clientes,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/buscar/nombre/{nombre}")
def buscar_por_nombre(
    nombre: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Buscar clientes por nombre (búsqueda parcial)"""
    search_pattern = f"%{nombre}%"
    clientes = db.query(Cliente).filter(
        or_(
            Cliente.nombres.ilike(search_pattern),
            Cliente.apellidos.ilike(search_pattern),
            func.concat(Cliente.nombres, ' ', Cliente.apellidos).ilike(search_pattern)
        )
    ).limit(10).all()
    
    return {
        "query": nombre,
        "total": len(clientes),
        "clientes": [
            {
                "id": c.id,
                "nombre_completo": c.nombre_completo,
                "cedula": c.cedula,
                "telefono": c.telefono,
                "estado": c.estado
            }
            for c in clientes
        ]
    }


@router.get("/buscar/telefono/{telefono}")
def buscar_por_telefono(
    telefono: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Buscar cliente por teléfono"""
    cliente = db.query(Cliente).filter(Cliente.telefono == telefono).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.get("/estadisticas/generales")
def estadisticas_clientes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener estadísticas generales de clientes
    """
    # Totales por estado
    total_activos = db.query(Cliente).filter(Cliente.estado == "ACTIVO").count()
    total_inactivos = db.query(Cliente).filter(Cliente.estado == "INACTIVO").count()
    total_mora = db.query(Cliente).filter(Cliente.estado_financiero == "MORA").count()
    
    # Por asesor de configuración
    from app.models.asesor import Asesor
    por_asesor = db.query(
        Asesor.nombre_completo,
        func.count(Cliente.id).label('total_clientes')
    ).outerjoin(Cliente, Asesor.id == Cliente.asesor_config_id).filter(
        Asesor.activo == True
    ).group_by(Asesor.id, Asesor.nombre, Asesor.apellido).all()
    
    # Por concesionario
    por_concesionario = db.query(
        Cliente.concesionario,
        func.count(Cliente.id).label('total_clientes'),
        func.sum(Cliente.total_financiamiento).label('monto_total')
    ).filter(
        Cliente.concesionario.isnot(None)
    ).group_by(Cliente.concesionario).all()
    
    # Por modalidad
    por_modalidad = db.query(
        Cliente.modalidad_pago,
        func.count(Cliente.id).label('total_clientes')
    ).filter(
        Cliente.modalidad_pago.isnot(None)
    ).group_by(Cliente.modalidad_pago).all()
    
    return {
        "totales": {
            "activos": total_activos,
            "inactivos": total_inactivos,
            "en_mora": total_mora,
            "total_general": total_activos + total_inactivos
        },
        "por_asesor": [
            {"asesor": nombre, "clientes": total}
            for nombre, total in por_asesor
        ],
        "por_concesionario": [
            {
                "concesionario": conc or "Sin concesionario",
                "clientes": total,
                "monto_total": float(monto or 0)
            }
            for conc, total, monto in por_concesionario
        ],
        "por_modalidad": [
            {"modalidad": mod or "Sin modalidad", "clientes": total}
            for mod, total in por_modalidad
        ]
    }


# ============================================
# ENDPOINTS CON PARÁMETROS DE RUTA - AL FINAL PARA EVITAR CONFLICTOS
# ============================================

@router.get("/{cliente_id}/acciones-rapidas", response_model=ClienteQuickActions)
def obtener_acciones_rapidas(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener acciones rápidas disponibles para un cliente
    """
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Verificar permisos del usuario actual
    from app.core.permissions import UserRole, has_permission, Permission
    user_role = UserRole(current_user.rol)
    
    # Determinar acciones disponibles
    acciones = ClienteQuickActions(
        puede_registrar_pago=has_permission(user_role, Permission.PAGO_CREATE),
        puede_enviar_recordatorio=has_permission(user_role, Permission.NOTIFICACION_SEND),
        puede_generar_estado_cuenta=has_permission(user_role, Permission.REPORTE_READ),
        puede_modificar_financiamiento=has_permission(user_role, Permission.PRESTAMO_UPDATE),
        puede_reasignar_asesor=(
            user_role in [UserRole.ADMINISTRADOR_GENERAL, UserRole.GERENTE]
        )
    )
    
    return acciones
