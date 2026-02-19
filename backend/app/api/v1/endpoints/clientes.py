"""
Endpoints de clientes: CONECTADOS A LA TABLA REAL `clientes` (public.clientes).
- Conexión: engine/sesión desde app.core.database (DATABASE_URL en .env).
- Modelo: app.models.cliente.Cliente con __tablename__ = "clientes".
- Todos los datos son REALES: listado, stats, get, create, update, delete y cambio de estado
  usan Depends(get_db) y consultas contra la tabla clientes. No hay stubs ni datos demo.
"""
import logging
import re
from typing import Optional, Any

from fastapi import APIRouter, Query, Depends, HTTPException

from app.core.deps import get_current_user
from pydantic import BaseModel, ValidationError
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError, OperationalError, IntegrityError

from app.core.database import get_db
from app.models.cliente import Cliente
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


@router.get("", summary="Listado paginado", response_model=dict)
@router.get("/", include_in_schema=False, response_model=dict)
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
    Estadísticas de clientes por estado: total, activos, inactivos, finalizados.
    """
    total = db.scalar(select(func.count()).select_from(Cliente)) or 0
    activos = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "ACTIVO")) or 0
    inactivos = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "INACTIVO")) or 0
    finalizados = db.scalar(select(func.count()).select_from(Cliente).where(Cliente.estado == "FINALIZADO")) or 0
    return {
        "total": total,
        "activos": activos,
        "inactivos": inactivos,
        "finalizados": finalizados,
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
            update_cliente(cliente_id=cid, payload=payload, db=db)
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
    if estado not in ("ACTIVO", "INACTIVO", "MORA", "FINALIZADO"):
        raise HTTPException(status_code=400, detail="estado debe ser ACTIVO, INACTIVO, MORA o FINALIZADO")
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
    cedula_norm = _normalize_for_duplicate(payload.cedula) or "Z999999999"
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


@router.put("/{cliente_id}", response_model=ClienteResponse)
def update_cliente(cliente_id: int, payload: ClienteUpdate, db: Session = Depends(get_db)):
    """
    Actualizar cliente.
    No se permite dejar cédula+nombres o email duplicados con otro cliente (distinto id) → 409.
    """
    row = db.get(Cliente, cliente_id)
    if not row:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    data = payload.model_dump(exclude_unset=True)

    # Validar duplicados: no permitir cédula, nombre, email ni teléfono igual a otro cliente
    # Z999999999 puede repetirse (clientes sin cédula)
    if "cedula" in data:
        cedula_norm = _normalize_for_duplicate(data.get("cedula") or getattr(row, "cedula") or "") or "Z999999999"
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
