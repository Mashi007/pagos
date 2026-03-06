"""
Endpoints de clientes: CONECTADOS A LA TABLA REAL `clientes` (public.clientes).
- Conexión: engine/sesión desde app.core.database (DATABASE_URL en .env).
- Modelo: app.models.cliente.Cliente con __tablename__ = "clientes".
- Todos los datos son REALES: listado, stats, get, create, update, delete y cambio de estado
  usan Depends(get_db) y consultas contra la tabla clientes. No hay stubs ni datos demo.
"""
import calendar
import logging
import re
from datetime import date
from typing import Optional, Any

from fastapi import APIRouter, Query, Depends, HTTPException, Body

from app.core.deps import get_current_user
from pydantic import BaseModel, ValidationError
from sqlalchemy import select, func, or_, delete
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError, OperationalError, IntegrityError

from app.core.database import get_db
from app.models.cliente import Cliente
from app.models.estado_cliente import EstadoCliente
from app.models.prestamo import Prestamo
from app.schemas.cliente import ClienteResponse, ClienteCreate, ClienteUpdate

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


def _row_to_cliente_response(row: Any) -> ClienteResponse:
    """Convierte una fila ORM a ClienteResponse tolerando NULLs y tipos de BD."""
    date_keys = {"fecha_nacimiento", "fecha_registro", "fecha_actualizacion"}
    d: dict[str, Any] = {}
    for key in ("id", "cedula", "nombres", "telefono", "email", "direccion", "fecha_nacimiento",
                "ocupacion", "estado", "fecha_registro", "fecha_actualizacion", "usuario_registro", "notas"):
        try:
            v = getattr(row, key, None)
            if v is None:
                if key == "id":
                    v = 0
                elif key in date_keys:
                    pass
                else:
                    v = ""
            d[key] = v
        except Exception:
            d[key] = None if key in date_keys else ("" if key != "id" else 0)
    return ClienteResponse.model_validate(d)


# Estados de cliente desde BD (tabla estados_cliente) - usado en formularios
ESTADOS_CLIENTE_FALLBACK = [
    {"valor": "ACTIVO", "etiqueta": "Activo", "orden": 1},
    {"valor": "INACTIVO", "etiqueta": "Inactivo", "orden": 2},
    {"valor": "FINALIZADO", "etiqueta": "Finalizado", "orden": 3},
    {"valor": "LEGACY", "etiqueta": "Legacy", "orden": 4},
]


@router.get("/estados", summary="Lista de estados de cliente para dropdowns")
def get_estados_cliente(db: Session = Depends(get_db)):
    """
    Obtiene lista de estados de cliente desde la tabla estados_cliente.
    Si la tabla no existe, retorna lista por defecto.
    """
    try:
        rows = db.execute(
            select(EstadoCliente.valor, EstadoCliente.etiqueta, EstadoCliente.orden)
            .order_by(EstadoCliente.orden)
        ).all()
        if rows:
            return {"estados": [{"valor": r[0], "etiqueta": r[1], "orden": r[2]} for r in rows]}
    except Exception:
        pass
    return {"estados": ESTADOS_CLIENTE_FALLBACK}


@router.get("", summary="Listado paginado", response_model=dict)
def get_clientes(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Listado paginado de clientes desde la BD.
    Filtros: search (cedula, nombres, email, telefono), estado (ACTIVO, INACTIVO, MORA, FINALIZADO).
    """
    # Columnas que existen en la tabla clientes (sin total_financiamiento ni dias_mora).
    _cols = (
        Cliente.id,
        Cliente.cedula,
        Cliente.nombres,
        Cliente.telefono,
        Cliente.email,
        Cliente.direccion,
        Cliente.fecha_nacimiento,
        Cliente.ocupacion,
        Cliente.estado,
        Cliente.fecha_registro,
        Cliente.fecha_actualizacion,
        Cliente.usuario_registro,
        Cliente.notas,
    )
    try:
        q = select(*_cols)
        count_q = select(func.count()).select_from(Cliente)

        if search and search.strip():
            t = f"%{search.strip()}%"
            filtro = or_(
                Cliente.cedula.ilike(t),
                Cliente.nombres.ilike(t),
                Cliente.email.ilike(t),
                Cliente.telefono.ilike(t),
            )
            q = q.select_from(Cliente).where(filtro)
            count_q = count_q.where(filtro)
        else:
            q = q.select_from(Cliente)
        if estado and estado.strip():
            est = estado.strip().upper()
            q = q.where(Cliente.estado == est)
            count_q = count_q.where(Cliente.estado == est)

        total = db.scalar(count_q) or 0
        q = q.order_by(Cliente.id.desc()).offset((page - 1) * per_page).limit(per_page)
        result = db.execute(q)
        rows = result.all()

        total_pages = (total + per_page - 1) // per_page if total else 0

        clientes_list = []
        for r in rows:
            try:
                clientes_list.append(_row_to_cliente_response(r))
            except (ValidationError, TypeError, AttributeError) as ve:
                logger.warning("Fila cliente id=%s omitida por validación: %s", getattr(r, "id", "?"), ve)
                continue
        if rows and not clientes_list:
            logger.error("Ninguna fila pudo serializarse; revisar esquema de tabla clientes.")
            raise HTTPException(
                status_code=500,
                detail="Error al cargar el listado de clientes: datos no compatibles con el esquema.",
            )
        return {
            "clientes": clientes_list,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }
    except (ProgrammingError, OperationalError) as e:
        logger.exception("Error de BD en listado de clientes: %s", e)
        hint = " Revisa que la tabla clientes tenga las columnas: id, cedula, nombres, telefono, email, direccion, fecha_nacimiento, ocupacion, estado, fecha_registro, fecha_actualizacion, usuario_registro, notas."
        raise HTTPException(
            status_code=500,
            detail=f"Error al cargar el listado de clientes: {e!s}.{hint}",
        ) from e
    except ValidationError as ve:
        logger.exception("Error de validación en listado de clientes: %s", ve)
        raise HTTPException(status_code=500, detail=f"Error al cargar el listado de clientes: {ve!s}") from ve
    except Exception as e:
        logger.exception("Error en listado de clientes: %s", e)
        err_msg = str(e)
        raise HTTPException(
            status_code=500,
            detail=f"Error al cargar el listado de clientes: {err_msg}",
        ) from e


@router.get("/stats")
def get_clientes_stats(db: Session = Depends(get_db)):
    """
    Estadísticas de clientes: total, activos, inactivos, finalizados, nuevos_este_mes.
    nuevos_este_mes = clientes con fecha_registro en el mes actual (calendario).
    """
    total = db.scalar(select(func.count()).select_from(Cliente)) or 0
    activos = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "ACTIVO")) or 0
    inactivos = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "INACTIVO")) or 0
    finalizados = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "FINALIZADO")) or 0
    # Nuevos clientes registrados en el mes actual
    hoy = date.today()
    primer_dia_mes = hoy.replace(day=1)
    _, ultimo_dia_num = calendar.monthrange(hoy.year, hoy.month)
    ultimo_dia_mes = hoy.replace(day=ultimo_dia_num)
    nuevos_este_mes = (
        db.scalar(
            select(func.count()).select_from(Cliente).where(
                func.date(Cliente.fecha_registro) >= primer_dia_mes,
                func.date(Cliente.fecha_registro) <= ultimo_dia_mes,
            )
        )
        or 0
    )
    return {
        "total": total,
        "activos": activos,
        "inactivos": inactivos,
        "finalizados": finalizados,
        "nuevos_este_mes": nuevos_este_mes,
    }


class EstadoPayload(BaseModel):
    estado: str


class CheckCedulasRequest(BaseModel):
    """Lista de cédulas a comprobar (p. ej. desde carga masiva)."""
    cedulas: list[str] = []


class CheckCedulasResponse(BaseModel):
    """Cédulas que ya existen en la tabla clientes."""
    existing_cedulas: list[str] = []


@router.get("/casos-a-revisar", response_model=dict)
def get_casos_a_revisar(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Clientes que no cumplen validadores: tienen valores placeholder
    (cedula=Z999999999, nombres=Revisar Nombres, telefono=+589999999999, email=revisar@email.com).
    """
    _cols = (
        Cliente.id,
        Cliente.cedula,
        Cliente.nombres,
        Cliente.telefono,
        Cliente.email,
        Cliente.direccion,
        Cliente.fecha_nacimiento,
        Cliente.ocupacion,
        Cliente.estado,
        Cliente.fecha_registro,
        Cliente.fecha_actualizacion,
        Cliente.usuario_registro,
        Cliente.notas,
    )
    filtro = or_(
        Cliente.cedula == "Z999999999",
        Cliente.nombres == "Revisar Nombres",
        Cliente.telefono == "+589999999999",
        Cliente.email == "revisar@email.com",
    )
    count_q = select(func.count()).select_from(Cliente).where(filtro)
    total = db.scalar(count_q) or 0
    q = (
        select(*_cols)
        .select_from(Cliente)
        .where(filtro)
        .order_by(Cliente.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    rows = db.execute(q).all()
    clientes_list = []
    for r in rows:
        try:
            clientes_list.append(_row_to_cliente_response(r))
        except (ValidationError, TypeError, AttributeError) as ve:
            logger.warning("Fila cliente id=%s omitida: %s", getattr(r, "id", "?"), ve)
    total_pages = (total + per_page - 1) // per_page if total else 0
    return {
        "clientes": clientes_list,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


class ActualizarLoteItem(BaseModel):
    """Item para actualización en lote."""
    id: int
    cedula: Optional[str] = None
    nombres: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    ocupacion: Optional[str] = None
    notas: Optional[str] = None


class ActualizarLoteResponse(BaseModel):
    """Respuesta de actualización en lote."""
    actualizados: int = 0
    errores: list[dict] = []
    total_procesados: int = 0


@router.post("/actualizar-lote", response_model=ActualizarLoteResponse)
def actualizar_clientes_lote(
    items: list[ActualizarLoteItem],
    db: Session = Depends(get_db),
):
    """
    Actualizar múltiples clientes. Cada item debe tener id y los campos a actualizar.
    Usa las mismas validaciones que update_cliente (duplicados → 409).
    """
    actualizados = 0
    errores: list[dict] = []
    for item in items:
        data = item.model_dump(exclude_unset=True)
        if "id" not in data:
            errores.append({"id": item.id, "error": "Falta id"})
            continue
        cid = data.pop("id")
        if not data:
            continue
        try:
            payload = ClienteUpdate(**{k: v for k, v in data.items() if v is not None})
            _perform_update_cliente(cid, payload, db)
            actualizados += 1
        except HTTPException as e:
            detail = e.detail
            if isinstance(detail, (list, dict)):
                detail = str(detail)
            errores.append({"id": cid, "error": str(detail)})
        except (ValidationError, TypeError) as e:
            errores.append({"id": cid, "error": str(e)})
    return ActualizarLoteResponse(
        actualizados=actualizados,
        errores=errores,
        total_procesados=len(items),
    )


@router.post("/check-cedulas", response_model=CheckCedulasResponse)
def check_cedulas(payload: CheckCedulasRequest, db: Session = Depends(get_db)):
    """
    Comprobar qué cédulas ya están registradas (para advertir en carga masiva antes de guardar).
    Recibe una lista de cédulas y devuelve las que ya existen en la BD.
    """
    if not payload.cedulas:
        return CheckCedulasResponse(existing_cedulas=[])
    cedulas_norm = [c.strip() for c in payload.cedulas if (c or "").strip()]
    if not cedulas_norm:
        return CheckCedulasResponse(existing_cedulas=[])
    # Consultar solo las que existen (sin duplicar en respuesta)
    # Z999999999 no se considera "existente" para bloquear: puede repetirse (clientes sin cédula)
    seen: set[str] = set()
    existing: list[str] = []
    for ced in cedulas_norm:
        if ced in seen or ced == "Z999999999":
            continue
        seen.add(ced)
        row = db.execute(select(Cliente.cedula).where(Cliente.cedula == ced)).first()
        if row:
            existing.append(ced)
    return CheckCedulasResponse(existing_cedulas=existing)


@router.patch("/{cliente_id}/estado", response_model=ClienteResponse)
def cambiar_estado_cliente(
    cliente_id: int,
    payload: EstadoPayload,
    db: Session = Depends(get_db),
):
    """Cambiar estado del cliente (PATCH /clientes/{id}/estado)."""
    row = db.get(Cliente, cliente_id)
    if not row:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    estado = payload.estado
    if estado not in ("ACTIVO", "INACTIVO", "MORA", "FINALIZADO", "LEGACY"):
        raise HTTPException(status_code=400, detail="estado debe ser ACTIVO, INACTIVO, MORA, FINALIZADO o LEGACY")
    row.estado = estado
    db.commit()
    db.refresh(row)
    return ClienteResponse.model_validate(row)


@router.get("/{cliente_id}", response_model=ClienteResponse)
def get_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Obtener un cliente por ID."""
    row = db.get(Cliente, cliente_id)
    if not row:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return ClienteResponse.model_validate(row)


def _normalize_for_duplicate(s: str) -> str:
    """Normaliza string para comparación de duplicados (strip, case)."""
    return (s or "").strip()


def _digits_telefono(s: str) -> str:
    """Solo dígitos del teléfono para comparar duplicados."""
    return re.sub(r"\D", "", (s or "").strip())


@router.post("", response_model=ClienteResponse, status_code=201)
def create_cliente(payload: ClienteCreate, db: Session = Depends(get_db)):
    """
    Crear cliente en la BD.
    No permitido duplicados: misma cédula, mismo nombre, mismo email o mismo teléfono → 409.
    Aplica a Nuevo Cliente y Carga masiva.
    """
    cedula_norm = (_normalize_for_duplicate(payload.cedula) or "Z999999999").upper()  # Uppercase para consistency
    nombres_norm = _normalize_for_duplicate(payload.nombres)
    email_norm = _normalize_for_duplicate(payload.email)
    telefono_dig = _digits_telefono(payload.telefono)

    # Prohibir duplicado por cédula (Z999999999 puede repetirse: clientes sin cédula)
    if cedula_norm != "Z999999999":
        existing_cedula = db.execute(
            select(Cliente.id).where(Cliente.cedula == cedula_norm)
        ).first()
        if existing_cedula:
            raise HTTPException(
                status_code=409,
                detail=f"Ya existe un cliente con la misma cédula. Cliente existente ID: {existing_cedula[0]}",
            )

    # Prohibir duplicado por nombre completo
    if nombres_norm:
        existing_nombres = db.execute(
            select(Cliente.id).where(Cliente.nombres == nombres_norm)
        ).first()
        if existing_nombres:
            raise HTTPException(
                status_code=409,
                detail=f"Ya existe un cliente con el mismo nombre completo. Cliente existente ID: {existing_nombres[0]}",
            )

    # Prohibir duplicado por email (si no vacío)
    if email_norm:
        existing_email = db.execute(
            select(Cliente.id).where(Cliente.email == email_norm)
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=409,
                detail=f"Ya existe un cliente con el mismo email. Cliente existente ID: {existing_email[0]}",
            )

    # Si teléfono duplicado (2 números exactamente iguales) → reemplazar por +589999999999
    telefono_final = payload.telefono
    if len(telefono_dig) >= 8:
        rows_telefono = db.execute(
            select(Cliente.id, Cliente.telefono).where(Cliente.telefono.isnot(None))
        ).all()
        for r in rows_telefono:
            if r.telefono and _digits_telefono(r.telefono) == telefono_dig:
                telefono_final = "+589999999999"
                break

    row = Cliente(
        cedula=cedula_norm,
        nombres=payload.nombres,
        telefono=telefono_final,
        email=payload.email,
        direccion=payload.direccion,
        fecha_nacimiento=payload.fecha_nacimiento,
        ocupacion=payload.ocupacion,
        estado=payload.estado,
        usuario_registro=payload.usuario_registro,
        notas=payload.notas,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ClienteResponse.model_validate(row)


def _perform_update_cliente(cliente_id: int, payload: ClienteUpdate, db: Session) -> ClienteResponse:
    """
    Lógica interna de actualización de cliente (reutilizable desde rutas y otros métodos).
    No se permite dejar cédula+nombres o email duplicados con otro cliente (distinto id) → 409.
    Retorna ClienteResponse tras guardar en BD.
    """
    row = db.get(Cliente, cliente_id)
    if not row:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    data = payload.model_dump(exclude_unset=True)

    # Validar duplicados: no permitir cédula, nombre, email ni teléfono igual a otro cliente
    # Z999999999 puede repetirse (clientes sin cédula)
    if "cedula" in data:
        cedula_norm = (_normalize_for_duplicate(data.get("cedula") or getattr(row, "cedula") or "") or "Z999999999").upper()  # Uppercase para consistency
        data["cedula"] = cedula_norm
        if cedula_norm and cedula_norm != "Z999999999":
            existing = db.execute(
                select(Cliente.id).where(Cliente.cedula == cedula_norm, Cliente.id != cliente_id)
            ).first()
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"Ya existe otro cliente con la misma cédula. Cliente existente ID: {existing[0]}",
                )
    if "nombres" in data:
        nombres_norm = _normalize_for_duplicate(data.get("nombres") or getattr(row, "nombres") or "")
        if nombres_norm:
            existing = db.execute(
                select(Cliente.id).where(Cliente.nombres == nombres_norm, Cliente.id != cliente_id)
            ).first()
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"Ya existe otro cliente con el mismo nombre completo. Cliente existente ID: {existing[0]}",
                )
    if "email" in data:
        email_norm = _normalize_for_duplicate(data.get("email") or "")
        if email_norm:
            existing = db.execute(
                select(Cliente.id).where(Cliente.email == email_norm, Cliente.id != cliente_id)
            ).first()
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"Ya existe otro cliente con el mismo email. Cliente existente ID: {existing[0]}",
                )
    if "telefono" in data:
        telefono_dig = _digits_telefono(data.get("telefono") or getattr(row, "telefono") or "")
        if len(telefono_dig) >= 8:
            rows_telefono = db.execute(
                select(Cliente.id, Cliente.telefono).where(
                    Cliente.telefono.isnot(None),
                    Cliente.id != cliente_id,
                )
            ).all()
            for r in rows_telefono:
                if r.telefono and _digits_telefono(r.telefono) == telefono_dig:
                    data["telefono"] = "+589999999999"
                    break

    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return ClienteResponse.model_validate(row)


@router.put("/{cliente_id}", response_model=ClienteResponse)
def update_cliente(cliente_id: int, payload: ClienteUpdate, db: Session = Depends(get_db)):
    """
    Actualizar cliente (endpoint HTTP).
    No se permite dejar cédula+nombres o email duplicados con otro cliente (distinto id) → 409.
    """
    return _perform_update_cliente(cliente_id, payload, db)


@router.delete("/{cliente_id}", status_code=204)
def delete_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Eliminar cliente. No se puede si tiene préstamos asociados."""
    row = db.get(Cliente, cliente_id)
    if not row:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Verificar si tiene préstamos (FK bloquea el delete)
    count_prestamos = db.scalar(
        select(func.count()).select_from(Prestamo).where(Prestamo.cliente_id == cliente_id)
    ) or 0
    if count_prestamos > 0:
        raise HTTPException(
            status_code=409,
            detail=f"No se puede eliminar: el cliente tiene {count_prestamos} préstamo(s) asociado(s). "
            "Elimine o reasigne los préstamos antes de eliminar al cliente.",
        )

    try:
        db.delete(row)
        db.commit()
        return None
    except IntegrityError as e:
        db.rollback()
        logger.warning("IntegrityError al eliminar cliente %s: %s", cliente_id, e)
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar: el cliente tiene registros asociados (préstamos, cuotas, tickets, etc.).",
        ) from e


# ============================================================================
# CARGA MASIVA DE CLIENTES DESDE EXCEL
# ============================================================================

from datetime import date, datetime
from fastapi import UploadFile, File
import io
from decimal import Decimal

try:
    import openpyxl
except ImportError:
    openpyxl = None

from app.models.cliente_con_error import ClienteConError


def _normalize_cedula_excel(cedula_str: str) -> str:
    """Normaliza cédula desde Excel: uppercase, sin espacios."""
    if not cedula_str:
        return ""
    return str(cedula_str).strip().upper()


def _validate_email(email: str) -> bool:
    """Valida formato básico de email."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def _parse_fecha(fecha_val: any) -> date:
    """Intenta parsear fecha en múltiples formatos."""
    if isinstance(fecha_val, date):
        return fecha_val
    if isinstance(fecha_val, datetime):
        return fecha_val.date()
    if not fecha_val:
        return None
    
    s = str(fecha_val).strip()
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


@router.post("/upload-excel", response_model=dict)
async def upload_clientes_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Carga masiva de clientes desde Excel.
    Formato esperado: Cédula | Nombres | Dirección | Fecha Nacimiento | Ocupación | Correo | Teléfono
    
    Validaciones:
    - Cédula: V|E|J|Z + 6-11 dígitos, única en BD
    - Email: formato válido, único en BD
    - Teléfono: requerido
    - Nombres: requerido
    
    Respuesta: {registros_creados, registros_con_error, clientes_con_errores}
    """
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Debe subir un archivo Excel (.xlsx o .xls)")
    
    if not openpyxl:
        raise HTTPException(status_code=500, detail="Excel library not available")
    
    try:
        content = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        
        if not ws:
            return {
                "registros_creados": 0,
                "registros_con_error": 0,
                "clientes_con_errores": []
            }
        
        registros_creados = 0
        registros_con_error = 0
        clientes_con_errores = []
        
        # Cargar emails y cédulas existentes para validación rápida
        cedulas_existentes = set(
            db.execute(select(Cliente.cedula)).scalars().all()
        )
        emails_existentes = set(
            db.execute(select(Cliente.email)).scalars().all()
        )
        cedulas_en_lote = set()
        emails_en_lote = set()
        
        usuario_email = current_user.email if hasattr(current_user, 'email') else "sistema@rapicredit.com"
        
        # Procesar filas (saltar header)
        for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or all(cell is None for cell in row):
                continue
            
            try:
                cedula_raw = row[0] if len(row) > 0 else None
                nombres_raw = row[1] if len(row) > 1 else None
                direccion_raw = row[2] if len(row) > 2 else None
                fecha_nac_raw = row[3] if len(row) > 3 else None
                ocupacion_raw = row[4] if len(row) > 4 else None
                email_raw = row[5] if len(row) > 5 else None
                telefono_raw = row[6] if len(row) > 6 else None
                
                errores = []
                
                # Validar cédula
                cedula = _normalize_cedula_excel(str(cedula_raw or ""))
                if not cedula:
                    errores.append("Cédula es requerida")
                elif not re.match(r"^[VEJZ]\d{6,11}$", cedula):
                    errores.append("Cédula debe ser V|E|J|Z + 6-11 dígitos")
                elif cedula in cedulas_existentes or cedula in cedulas_en_lote:
                    errores.append("Cédula duplicada (existe en BD o en este lote)")
                else:
                    cedulas_en_lote.add(cedula)
                
                # Validar nombres
                nombres = str(nombres_raw or "").strip()
                if not nombres:
                    errores.append("Nombres es requerido")
                
                # Validar dirección
                direccion = str(direccion_raw or "").strip()
                if not direccion:
                    errores.append("Dirección es requerida")
                
                # Validar fecha nacimiento
                fecha_nac = _parse_fecha(fecha_nac_raw)
                if not fecha_nac:
                    errores.append("Fecha de nacimiento inválida")
                
                # Validar ocupación
                ocupacion = str(ocupacion_raw or "").strip()
                if not ocupacion:
                    errores.append("Ocupación es requerida")
                
                # Validar email
                email = str(email_raw or "").strip()
                if not email:
                    errores.append("Email es requerido")
                elif not _validate_email(email):
                    errores.append("Email no tiene formato válido")
                elif email in emails_existentes or email in emails_en_lote:
                    errores.append("Email duplicado (existe en BD o en este lote)")
                else:
                    emails_en_lote.add(email)
                
                # Validar teléfono
                telefono = str(telefono_raw or "").strip()
                if not telefono:
                    errores.append("Teléfono es requerido")
                
                # Si hay errores, agregar a lista de revisión
                if errores:
                    cliente_error = ClienteConError(
                        cedula=cedula or None,
                        nombres=nombres,
                        telefono=telefono or None,
                        email=email or None,
                        direccion=direccion,
                        fecha_nacimiento=str(fecha_nac_raw) if fecha_nac_raw else None,
                        ocupacion=ocupacion or None,
                        estado="PENDIENTE",
                        errores_descripcion="; ".join(errores),
                        fila_origen=idx,
                        usuario_registro=usuario_email
                    )
                    db.add(cliente_error)
                    registros_con_error += 1
                    continue
                
                # Crear cliente
                cliente = Cliente(
                    cedula=cedula,
                    nombres=nombres,
                    telefono=telefono,
                    email=email,
                    direccion=direccion,
                    fecha_nacimiento=fecha_nac,
                    ocupacion=ocupacion,
                    estado="ACTIVO",
                    usuario_registro=usuario_email,
                    notas="Cargado desde Excel"
                )
                db.add(cliente)
                registros_creados += 1
                
            except Exception as e:
                logger.error(f"Error procesando fila {idx}: {e}")
                cliente_error = ClienteConError(
                    cedula=str(row[0]) if len(row) > 0 else None,
                    nombres=str(row[1]) if len(row) > 1 else None,
                    telefono=str(row[6]) if len(row) > 6 else None,
                    email=str(row[5]) if len(row) > 5 else None,
                    errores_descripcion=f"Error general: {str(e)[:200]}",
                    fila_origen=idx,
                    usuario_registro=usuario_email
                )
                db.add(cliente_error)
                registros_con_error += 1
        
        db.commit()
        
        return {
            "registros_creados": registros_creados,
            "registros_con_error": registros_con_error,
            "mensaje": f"Se crearon {registros_creados} cliente(s) y {registros_con_error} con error(es)"
        }
        
    except Exception as e:
        db.rollback()
        logger.exception("Error cargando Excel de clientes: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando archivo: {str(e)[:200]}"
        )


@router.get("/revisar/lista", response_model=dict)
def get_clientes_con_errores(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Listado de clientes con errores de validación (pendientes de revisión).
    Paginado para facilitar corrección manual.
    """
    total = db.scalar(select(func.count()).select_from(ClienteConError)) or 0
    rows = db.execute(
        select(ClienteConError)
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).scalars().all()
    
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": [
            {
                "id": r.id,
                "cedula": r.cedula,
                "nombres": r.nombres,
                "email": r.email,
                "telefono": r.telefono,
                "errores": r.errores_descripcion,
                "fila_origen": r.fila_origen,
                "estado": r.estado,
                "fecha_registro": r.fecha_registro.isoformat() if r.fecha_registro else None,
            }
            for r in rows
        ]
    }


class RevisarClienteAgregarBody(BaseModel):
    """Datos de una fila para enviar a revisión manual (clientes_con_errores)."""
    cedula: Optional[str] = None
    nombres: Optional[str] = None
    direccion: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    ocupacion: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    errores_descripcion: Optional[str] = None
    fila_origen: Optional[int] = None


@router.post("/revisar/agregar", response_model=dict)
def agregar_cliente_a_revisar(
    body: RevisarClienteAgregarBody,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Envía una fila a la tabla clientes_con_errores (revisar clientes).
    Usado desde la carga masiva cuando el usuario pulsa "Enviar a Revisar Clientes".
    """
    usuario_email = current_user.email if hasattr(current_user, "email") else "sistema@rapicredit.com"
    row = ClienteConError(
        cedula=body.cedula,
        nombres=body.nombres,
        direccion=body.direccion,
        fecha_nacimiento=body.fecha_nacimiento,
        ocupacion=body.ocupacion,
        email=body.email,
        telefono=body.telefono,
        estado="PENDIENTE",
        errores_descripcion=body.errores_descripcion or "Enviado a revisión desde carga masiva",
        fila_origen=body.fila_origen,
        usuario_registro=usuario_email,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "mensaje": "Cliente enviado a Revisar Clientes"}


@router.delete("/revisar/{error_id}", status_code=204)
def resolver_cliente_error(error_id: int, db: Session = Depends(get_db)):
    """Marcar cliente con error como resuelto (eliminar de la lista)."""
    row = db.get(ClienteConError, error_id)
    if not row:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    
    db.delete(row)
    db.commit()
    return None

@router.post("/revisar/eliminar-por-descarga")
def eliminar_clientes_por_descarga(
    ids: list[int] = Body(...),
    db: Session = Depends(get_db),
):
    """Elimina registros de clientes_con_errores tras su descarga en Excel."""
    if not ids:
        return {"deleted": 0}
    
    result = db.execute(
        delete(ClienteConError).where(ClienteConError.id.in_(ids))
    )
    db.commit()
    return {"deleted": result.rowcount}




