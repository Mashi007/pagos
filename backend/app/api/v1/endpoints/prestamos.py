"""
Endpoints de préstamos. Datos reales desde BD (tabla prestamos).
Todos los endpoints usan Depends(get_db). No hay stubs ni datos demo.
"""
import calendar
import io
import logging
from datetime import date, datetime, timedelta, time
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, field_validator
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.auth import UserResponse
from app.models.auditoria import Auditoria
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.models.user import User
from app.models.revision_manual_prestamo import RevisionManualPrestamo
from app.schemas.prestamo import PrestamoCreate, PrestamoResponse, PrestamoUpdate, PrestamoListResponse

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


def _audit_user_id(db: Session, current_user: UserResponse) -> int:
    """
    Devuelve un usuario_id que exista en la tabla usuarios (la que referencia la FK de auditoria).
    Usa consultas explícitas a public.usuarios para no depender del mapeo del modelo User.
    Verifica que el id exista antes de devolverlo (evita FK violation si hay desincronización).
    """
    def _verify_exists(uid: int) -> bool:
        """Comprueba que el id exista en usuarios (misma tabla que la FK de auditoria)."""
        r = db.execute(text("SELECT 1 FROM public.usuarios WHERE id = :id"), {"id": uid}).first()
        return r is not None

    # 1) Probar current_user.id si viene de BD (evita usar id de tabla users u otra fuente)
    uid = getattr(current_user, "id", None)
    if uid is not None and _verify_exists(uid):
        return uid

    # 2) Buscar por email (case-insensitive)
    email = (getattr(current_user, "email", None) or "").strip().lower()
    if email:
        r = db.execute(
            text("SELECT id FROM public.usuarios WHERE LOWER(email) = :e AND is_active = true LIMIT 1"),
            {"e": email},
        ).first()
        if r and _verify_exists(r[0]):
            return r[0]

    # 3) Cualquier administrador activo
    r = db.execute(
        text("SELECT id FROM public.usuarios WHERE rol = 'administrador' AND is_active = true LIMIT 1"),
    ).first()
    if r and _verify_exists(r[0]):
        return r[0]

    # 4) Cualquier usuario activo
    r = db.execute(
        text("SELECT id FROM public.usuarios WHERE is_active = true ORDER BY id LIMIT 1"),
    ).first()
    if r and _verify_exists(r[0]):
        return r[0]

    # 5) Cualquier usuario
    r = db.execute(text("SELECT id FROM public.usuarios ORDER BY id LIMIT 1")).first()
    if r and _verify_exists(r[0]):
        return r[0]

    raise HTTPException(
        status_code=503,
        detail=(
            "No hay usuarios en la tabla usuarios; no se puede registrar la aprobación. "
            "Cree al menos un usuario activo en la aplicación."
        ),
    )


def _registrar_en_revision_manual(db: Session, prestamo_id: int) -> None:
    """
    Registra el préstamo en Revisión Manual (estado pendiente) si no existe.
    Se llama al aprobar un crédito para que aparezca automáticamente en la lista.
    """
    existente = db.execute(
        select(RevisionManualPrestamo).where(RevisionManualPrestamo.prestamo_id == prestamo_id)
    ).scalars().first()
    if not existente:
        rev = RevisionManualPrestamo(prestamo_id=prestamo_id, estado_revision="pendiente")
        db.add(rev)


# --- Schemas para body de endpoints adicionales ---
class AplicarCondicionesBody(BaseModel):
    tasa_interes: Optional[float] = 0.0  # Siempre 0% por defecto
    plazo_maximo: Optional[int] = None
    fecha_base_calculo: Optional[date] = None
    observaciones: Optional[str] = None


class EvaluarRiesgoBody(BaseModel):
    ml_impago_nivel_riesgo_manual: Optional[str] = None
    ml_impago_probabilidad_manual: Optional[float] = None
    requiere_revision: Optional[bool] = None
    estado: Optional[str] = None


class AsignarFechaAprobacionBody(BaseModel):
    fecha_aprobacion: date


class AprobarManualBody(BaseModel):
    """Body para aprobación manual de riesgo: una fecha, confirmaciones y datos editables."""
    fecha_aprobacion: date
    acepta_declaracion: bool  # Declaración políticas RapiCredit y riesgo
    documentos_analizados: bool  # Confirmación de que se analizaron documentos
    total_financiamiento: Optional[float] = None
    numero_cuotas: Optional[int] = None
    modalidad_pago: Optional[str] = None

    cuota_periodo: Optional[float] = None
    tasa_interes: Optional[float] = 0.0  # Siempre 0% por defecto
    observaciones: Optional[str] = None

    @field_validator("numero_cuotas")
    @classmethod
    def numero_cuotas_rango(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 12):
            raise ValueError("numero_cuotas debe estar entre 1 y 12")
        return v


@router.get("", response_model=dict)
def listar_prestamos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    cliente_id: Optional[int] = Query(None),
    estado: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    cedula: Optional[str] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    requiere_revision: Optional[bool] = Query(None),
    modelo: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Listado paginado de préstamos desde BD con nombres y cédula del cliente (join)."""
    q = select(Prestamo, Cliente.nombres, Cliente.cedula).select_from(Prestamo).join(
        Cliente, Prestamo.cliente_id == Cliente.id
    )
    count_q = select(func.count()).select_from(Prestamo).join(Cliente, Prestamo.cliente_id == Cliente.id)

    if cliente_id is not None:
        q = q.where(Prestamo.cliente_id == cliente_id)
        count_q = count_q.where(Prestamo.cliente_id == cliente_id)
    if estado and estado.strip():
        est = estado.strip().upper()
        q = q.where(Prestamo.estado == est)
        count_q = count_q.where(Prestamo.estado == est)
    if analista and analista.strip():
        q = q.where(Prestamo.analista == analista.strip())
        count_q = count_q.where(Prestamo.analista == analista.strip())
    if concesionario and concesionario.strip():
        q = q.where(Prestamo.concesionario == concesionario.strip())
        count_q = count_q.where(Prestamo.concesionario == concesionario.strip())
    if cedula and cedula.strip():
        ced_clean = cedula.strip()
        q = q.where(Cliente.cedula == ced_clean)
        count_q = count_q.where(Cliente.cedula == ced_clean)
    if search and search.strip():
        search_clean = search.strip()
        q = q.where(Cliente.cedula.ilike(f"%{search_clean}%") | Cliente.nombres.ilike(f"%{search_clean}%"))
        count_q = count_q.where(Cliente.cedula.ilike(f"%{search_clean}%") | Cliente.nombres.ilike(f"%{search_clean}%"))
    if modelo and modelo.strip():
        q = q.where(Prestamo.modelo_vehiculo == modelo.strip())
        count_q = count_q.where(Prestamo.modelo_vehiculo == modelo.strip())
    if requiere_revision is not None:
        q = q.where(Prestamo.requiere_revision == requiere_revision)
        count_q = count_q.where(Prestamo.requiere_revision == requiere_revision)
    if fecha_inicio:
        try:
            fd = datetime.fromisoformat(fecha_inicio.replace("Z", "+00:00")).date()
            q = q.where(func.date(Prestamo.fecha_registro) >= fd)
            count_q = count_q.where(func.date(Prestamo.fecha_registro) >= fd)
        except ValueError:
            pass
    if fecha_fin:
        try:
            fh = datetime.fromisoformat(fecha_fin.replace("Z", "+00:00")).date()
            q = q.where(func.date(Prestamo.fecha_registro) <= fh)
            count_q = count_q.where(func.date(Prestamo.fecha_registro) <= fh)
        except ValueError:
            pass

    total = db.scalar(count_q) or 0
    q = q.order_by(Prestamo.id.desc()).offset((page - 1) * per_page).limit(per_page)
    rows = db.execute(q).all()
    prestamo_ids = [row[0].id for row in rows]
    # Conteo de cuotas por préstamo (para mostrar en columna Cuotas)
    cuotas_por_prestamo = {}
    if prestamo_ids:
        cuenta = select(Cuota.prestamo_id, func.count()).select_from(Cuota).where(
            Cuota.prestamo_id.in_(prestamo_ids)
        ).group_by(Cuota.prestamo_id)
        for pid, cnt in db.execute(cuenta).all():
            cuotas_por_prestamo[pid] = cnt
    
    # Estados de revisión manual
    revision_manual_estados = {}
    if prestamo_ids:
        rev_q = select(RevisionManualPrestamo.prestamo_id, RevisionManualPrestamo.estado_revision).where(
            RevisionManualPrestamo.prestamo_id.in_(prestamo_ids)
        )
        for pid, estado in db.execute(rev_q).all():
            revision_manual_estados[pid] = estado
    
    items = []
    for row in rows:
        p, nombres_cliente, cedula_cliente = row[0], row[1], row[2]
        # Cuotas: preferir conteo desde tabla cuotas; si no hay, usar columna numero_cuotas
        numero_cuotas = cuotas_por_prestamo.get(p.id) if cuotas_por_prestamo.get(p.id) is not None else p.numero_cuotas
        item = PrestamoListResponse(
            id=p.id,
            cliente_id=p.cliente_id,
            total_financiamiento=p.total_financiamiento,
            estado=p.estado,
            concesionario=p.concesionario,
            modelo=p.modelo,
            analista=p.analista,
            fecha_creacion=p.fecha_creacion,
            fecha_actualizacion=p.fecha_actualizacion,
            fecha_registro=p.fecha_registro,
            fecha_aprobacion=p.fecha_aprobacion,
            nombres=nombres_cliente or p.nombres,
            cedula=cedula_cliente or p.cedula,
            numero_cuotas=numero_cuotas,
            modalidad_pago=p.modalidad_pago,
            revision_manual_estado=revision_manual_estados.get(p.id),  # None si no existe
        )
        items.append(item)
    total_pages = (total + per_page - 1) // per_page if total else 0
    return {
        "prestamos": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


@router.get("/stats", response_model=dict)
def get_prestamos_stats(
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    mes: Optional[int] = Query(None),
    año: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Estadísticas de préstamos mensuales desde BD (solo clientes ACTIVOS).
    a) total_financiamiento: suma de total_financiamiento de préstamos APROBADOS en el mes.
    b) total: cantidad de préstamos APROBADOS en el mes.
    c) cartera_vigente: suma de monto de cuotas con vencimiento en el mes no cobradas.
    d) Usa COALESCE(fecha_aprobacion, fecha_registro) para determinar 'aprobados en el mes'."""
    hoy = date.today()
    mes_u = mes if mes is not None and 1 <= mes <= 12 else hoy.month
    año_u = año if año is not None and año >= 2000 else hoy.year
    import calendar
    _, ultimo_dia = calendar.monthrange(año_u, mes_u)
    inicio_mes = date(año_u, mes_u, 1)
    fin_mes = date(año_u, mes_u, ultimo_dia)

    # Fecha de referencia: aprobación o registro (para "aprobados en el mes")
    # Solo clientes ACTIVOS (consistente con dashboard, pagos, reportes)
    fecha_ref = func.coalesce(func.date(Prestamo.fecha_aprobacion), func.date(Prestamo.fecha_registro))
    q_base = (
        select(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
            fecha_ref >= inicio_mes,
            fecha_ref <= fin_mes,
        )
    )
    if analista and analista.strip():
        q_base = q_base.where(Prestamo.analista == analista.strip())
    if concesionario and concesionario.strip():
        q_base = q_base.where(Prestamo.concesionario == concesionario.strip())
    if modelo and modelo.strip():
        q_base = q_base.where(Prestamo.modelo_vehiculo == modelo.strip())
    subq = q_base.subquery()
    total = db.scalar(select(func.count()).select_from(subq)) or 0
    q_estado = (
        select(Prestamo.estado, func.count())
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            Cliente.estado == "ACTIVO",
            fecha_ref >= inicio_mes,
            fecha_ref <= fin_mes,
        )
    )
    if analista and analista.strip():
        q_estado = q_estado.where(Prestamo.analista == analista.strip())
    if concesionario and concesionario.strip():
        q_estado = q_estado.where(Prestamo.concesionario == concesionario.strip())
    if modelo and modelo.strip():
        q_estado = q_estado.where(Prestamo.modelo_vehiculo == modelo.strip())
    q_estado = q_estado.group_by(Prestamo.estado)
    rows = db.execute(q_estado).all()
    por_estado = {r[0]: r[1] for r in rows}
    total_fin = db.scalar(select(func.coalesce(func.sum(subq.c.total_financiamiento), 0)).select_from(subq)) or 0
    total_fin = float(total_fin)
    promedio_monto = (total_fin / total) if total else 0
    # Cartera por cobrar: suma monto de cuotas con vencimiento en el mes, no cobradas (solo clientes ACTIVOS)
    conds_cartera = [
        Cliente.estado == "ACTIVO",
        Prestamo.estado == "APROBADO",
        Cuota.fecha_vencimiento >= inicio_mes,
        Cuota.fecha_vencimiento <= fin_mes,
        Cuota.fecha_pago.is_(None),
    ]
    if analista and analista.strip():
        conds_cartera.append(Prestamo.analista == analista.strip())
    if concesionario and concesionario.strip():
        conds_cartera.append(Prestamo.concesionario == concesionario.strip())
    if modelo and modelo.strip():
        conds_cartera.append(Prestamo.modelo_vehiculo == modelo.strip())
    cartera_vigente = float(
        db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(*conds_cartera)
        ) or 0
    )
    return {
        "total": total,
        "por_estado": por_estado,
        "total_financiamiento": total_fin,
        "promedio_monto": promedio_monto,
        "cartera_vigente": cartera_vigente,
        "mes": mes_u,
        "año": año_u,
    }


def _normalizar_cedula_para_busqueda(cedula: str) -> str:
    """Normaliza cédula para búsqueda: sin guiones, sin espacios, mayúsculas."""
    if not cedula:
        return ""
    return (cedula or "").strip().upper().replace("-", "").replace(" ", "")


class PrestamosPorCedulasBatchBody(BaseModel):
    """Body para consulta batch de préstamos por múltiples cédulas."""

    cedulas: list[str] = []


@router.post("/cedula/batch", response_model=dict)
def listar_prestamos_por_cedulas_batch(
    body: PrestamosPorCedulasBatchBody,
    db: Session = Depends(get_db),
):
    """Consulta batch OPTIMIZADA: búsqueda rápida con normalización.
    
    Estrategia:
    1. Búsqueda exacta primero (si cédula en request = cédula en BD) - muy rápido
    2. Si no encuentra, busca todos los préstamos (sin WHERE) y filtra por normalización en Python
       (más rápido que SQL con func.upper/replace para strings)
    """
    cedulas_clean = [(c or "").strip() for c in (body.cedulas or []) if (c or "").strip()]
    cedulas_clean = list(dict.fromkeys(cedulas_clean))
    if not cedulas_clean:
        return {"prestamos": {}}

    resultado: dict[str, list] = {c: [] for c in cedulas_clean}
    cedulas_encontradas = set()
    
    # PASO 1: Búsqueda exacta (muy rápida, usa índices)
    q_exacto = (
        select(Prestamo.id, Prestamo.cliente_id, Prestamo.estado, Prestamo.cedula, Cliente.cedula)
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(or_(
            Cliente.cedula.in_(cedulas_clean),
            Prestamo.cedula.in_(cedulas_clean),
        ))
        .order_by(Prestamo.id.desc())
        .limit(50000)
    )
    
    for p_id, cli_id, p_estado, p_cedula, cli_cedula in db.execute(q_exacto):
        cedula_cli = (cli_cedula or p_cedula or "").strip()
        if cedula_cli in cedulas_clean:
            cedulas_encontradas.add(cedula_cli)
            resultado[cedula_cli].append({
                "id": p_id,
                "cliente_id": cli_id,
                "estado": p_estado,
                "cedula": cedula_cli,
            })
    
    # PASO 2: Para cédulas NO encontradas, buscar con normalización (sin guiones)
    cedulas_faltantes = [c for c in cedulas_clean if c not in cedulas_encontradas]
    if cedulas_faltantes:
        # Mapeo: cédula normalizada (sin guiones) → cédula original solicitada
        cedulas_norm_map = {}
        for ced in cedulas_faltantes:
            ced_norm = ced.replace("-", "").replace(" ", "").upper()
            cedulas_norm_map[ced_norm] = ced
        
        # Buscar préstamos: intentar primero por primeros 2 caracteres (prefijo) para reducir volumen
        # Ej: "V-17709701" normalizdo a "V17709701" → prefijo "V1"
        prefijos = set()
        for ced_norm in cedulas_norm_map.keys():
            if len(ced_norm) >= 2:
                prefijos.add(ced_norm[:2])  # Primeros 2 caracteres del código normalizado
        
        # Búsqueda: TODOS los préstamos (limit 100k para evitar memory issues)
        q_todos = (
            select(Prestamo.id, Prestamo.cliente_id, Prestamo.estado, Prestamo.cedula, Cliente.cedula)
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .order_by(Prestamo.id.desc())
            .limit(100000)  # Safety limit: máximo 100k préstamos
        )
        
        for p_id, cli_id, p_estado, p_cedula, cli_cedula in db.execute(q_todos):
            cedula_cli = (cli_cedula or p_cedula or "").strip()
            cedula_cli_norm = cedula_cli.replace("-", "").replace(" ", "").upper()
            
            # Match normalizado
            if cedula_cli_norm in cedulas_norm_map:
                ced_original = cedulas_norm_map[cedula_cli_norm]
                cedulas_encontradas.add(ced_original)
                resultado[ced_original].append({
                    "id": p_id,
                    "cliente_id": cli_id,
                    "estado": p_estado,
                    "cedula": cedula_cli,
                })
                # Eliminar del mapa para no procesar nuevamente
                del cedulas_norm_map[cedula_cli_norm]
                if not cedulas_norm_map:
                    break  # Ya encontró todas las cédulas faltantes

    return {"prestamos": resultado}


@router.get("/cedula/{cedula}", response_model=dict)
def listar_prestamos_por_cedula(cedula: str, db: Session = Depends(get_db)):
    """Listado de préstamos por cédula del cliente (integrado con frontend).
    Acepta coincidencia exacta o normalizada (sin guiones, mayúsculas) para Cliente.cedula y Prestamo.cedula.
    """
    cedula_clean = (cedula or "").strip()
    if not cedula_clean:
        return {"prestamos": [], "total": 0}
    cedula_norm = _normalizar_cedula_para_busqueda(cedula_clean)
    # Coincidencia: exacta o normalizada (V17709701 = V-17709701 = v17709701)
    cond_cliente = or_(
        Cliente.cedula == cedula_clean,
        func.upper(func.replace(func.replace(Cliente.cedula, "-", ""), " ", "")) == cedula_norm,
    )
    cond_prestamo = or_(
        Prestamo.cedula == cedula_clean,
        func.upper(func.replace(func.replace(Prestamo.cedula, "-", ""), " ", "")) == cedula_norm,
    )
    q = (
        select(Prestamo, Cliente.nombres, Cliente.cedula)
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(or_(cond_cliente, cond_prestamo))
        .order_by(Prestamo.id.desc())
    )
    rows = db.execute(q).all()
    prestamo_ids = [row[0].id for row in rows]
    cuotas_por_prestamo = {}
    if prestamo_ids:
        cuenta = (
            select(Cuota.prestamo_id, func.count())
            .select_from(Cuota)
            .where(Cuota.prestamo_id.in_(prestamo_ids))
            .group_by(Cuota.prestamo_id)
        )
        for pid, cnt in db.execute(cuenta).all():
            cuotas_por_prestamo[pid] = cnt
    items = []
    for row in rows:
        p, nombres_cliente, cedula_cliente = row[0], row[1], row[2]
        numero_cuotas = cuotas_por_prestamo.get(p.id) if cuotas_por_prestamo.get(p.id) is not None else p.numero_cuotas
        items.append(
            PrestamoListResponse(
                id=p.id,
                cliente_id=p.cliente_id,
                total_financiamiento=p.total_financiamiento,
                estado=p.estado,
                concesionario=p.concesionario,
                modelo=p.modelo,
                analista=p.analista,
                fecha_creacion=p.fecha_creacion,
                fecha_actualizacion=p.fecha_actualizacion,
                fecha_registro=p.fecha_registro,
                fecha_aprobacion=p.fecha_aprobacion,
                nombres=nombres_cliente or p.nombres,
                cedula=cedula_cliente or p.cedula,
                numero_cuotas=numero_cuotas,
                modalidad_pago=p.modalidad_pago,
            )
        )
    return {"prestamos": [i.model_dump() for i in items], "total": len(items)}


@router.get("/cedula/{cedula}/resumen", response_model=dict)
def resumen_prestamos_por_cedula(cedula: str, db: Session = Depends(get_db)):
    """Resumen de préstamos por cédula: total, saldo pendiente, cuotas en mora (integrado con frontend)."""
    cedula_clean = (cedula or "").strip()
    if not cedula_clean:
        return {
            "tiene_prestamos": False,
            "total_prestamos": 0,
            "total_saldo_pendiente": 0,
            "total_cuotas_mora": 0,
            "prestamos": [],
        }
    q = (
        select(Prestamo)
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Cliente.cedula == cedula_clean)
        .order_by(Prestamo.id.desc())
    )
    prestamos = db.execute(q).scalars().all()
    if not prestamos:
        return {
            "tiene_prestamos": False,
            "total_prestamos": 0,
            "total_saldo_pendiente": 0,
            "total_cuotas_mora": 0,
            "prestamos": [],
        }
    from datetime import date
    hoy = date.today()
    prestamo_ids = [p.id for p in prestamos]
    # Saldo pendiente y cuotas en mora por préstamo (solo cuotas sin fecha_pago)
    saldo_q = (
        select(Cuota.prestamo_id, func.coalesce(func.sum(Cuota.monto), 0))
        .select_from(Cuota)
        .where(Cuota.prestamo_id.in_(prestamo_ids), Cuota.fecha_pago.is_(None))
        .group_by(Cuota.prestamo_id)
    )
    saldos = {r[0]: float(r[1]) for r in db.execute(saldo_q).all()}
    mora_q = (
        select(Cuota.prestamo_id, func.count())
        .select_from(Cuota)
        .where(
            Cuota.prestamo_id.in_(prestamo_ids),
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < hoy,
        )
        .group_by(Cuota.prestamo_id)
    )
    moras = {r[0]: r[1] for r in db.execute(mora_q).all()}
    total_saldo = sum(saldos.get(pid, 0) for pid in prestamo_ids)
    total_mora = sum(moras.get(pid, 0) for pid in prestamo_ids)
    list_prestamos = []
    for p in prestamos:
        list_prestamos.append({
            "id": p.id,
            "modelo_vehiculo": p.modelo or "",
            "total_financiamiento": float(p.total_financiamiento) if p.total_financiamiento is not None else 0,
            "saldo_pendiente": saldos.get(p.id, 0),
            "cuotas_en_mora": moras.get(p.id, 0),
            "estado": p.estado or "",
            "fecha_registro": p.fecha_registro.isoformat() if p.fecha_registro else None,
        })
    return {
        "tiene_prestamos": True,
        "total_prestamos": len(prestamos),
        "total_saldo_pendiente": total_saldo,
        "total_cuotas_mora": total_mora,
        "prestamos": list_prestamos,
    }


@router.get("/{prestamo_id}", response_model=PrestamoResponse)
def get_prestamo(prestamo_id: int, db: Session = Depends(get_db)):
    """Obtiene un préstamo por ID desde BD. Incluye cedula/nombres del cliente (join si faltan en prestamo)."""
    row = db.execute(
        select(Prestamo, Cliente.nombres, Cliente.cedula)
        .select_from(Prestamo)
        .outerjoin(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Prestamo.id == prestamo_id)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    p, nombres_cliente, cedula_cliente = row[0], row[1], row[2]
    resp = PrestamoResponse.model_validate(p)
    # Preferir cedula/nombres del cliente (join) si faltan o vacíos en prestamo
    resp.nombres = nombres_cliente or p.nombres or ""
    resp.cedula = cedula_cliente or p.cedula or ""
    return resp


def _calcular_monto_cuota_frances(total: float, tasa_periodo: float, n: int) -> float:
    """
    Calcula la cuota fija de un préstamo con amortización francesa (sistema francés / annuity).
    Fórmula: C = P * [i * (1+i)^n] / [(1+i)^n - 1]
    donde P=capital, i=tasa por período, n=número de cuotas.
    Si tasa_periodo == 0 devuelve la cuota plana (P/n).
    """
    if tasa_periodo <= 0 or n <= 0:
        return total / n if n else 0
    factor = (1 + tasa_periodo) ** n
    return total * (tasa_periodo * factor) / (factor - 1)


def _resolver_monto_cuota(prestamo: "Prestamo", total: float, numero_cuotas: int) -> float:
    """
    [C1] Determina el monto de cuota considerando la tasa de interés del préstamo.
    - tasa_interes == 0 (o NULL): cuota plana = total / numero_cuotas.
    - tasa_interes > 0: amortización francesa.
      La tasa se almacena como porcentaje anual (ej. 12 = 12% anual).
      Se convierte al período: MENSUAL → tasa/12, QUINCENAL → tasa/24, SEMANAL → tasa/52.
    """
    tasa_anual = float(prestamo.tasa_interes or 0)
    if tasa_anual <= 0 or numero_cuotas <= 0:
        return total / numero_cuotas if numero_cuotas else 0
    modalidad = (prestamo.modalidad_pago or "MENSUAL").upper()
    periodos_por_anio = 12 if modalidad == "MENSUAL" else (24 if modalidad == "QUINCENAL" else 52)
    tasa_periodo = (tasa_anual / 100) / periodos_por_anio
    return _calcular_monto_cuota_frances(total, tasa_periodo, numero_cuotas)


def _generar_cuotas_amortizacion(db: Session, p: Prestamo, fecha_base: date, numero_cuotas: int, monto_cuota: float) -> int:
    """
    Genera filas en tabla cuotas para el préstamo dado.

    Fecha de vencimiento = fecha_base + (delta * n) - 1 días:
      - MENSUAL (30d):   cuota 1 → día 29, cuota 2 → día 59, etc.
      - QUINCENAL (15d): cuota 1 → día 14, cuota 2 → día 29, etc.
      - SEMANAL (7d):    cuota 1 → día 6, cuota 2 → día 13, etc.

    [C1] Cálculo del monto de cuota:
    - Si tasa_interes == 0 (o NULL): cuota plana = total_financiamiento / numero_cuotas.
    - Si tasa_interes > 0: amortización francesa. La tasa se interpreta como tasa ANUAL
      nominal; se convierte al período según modalidad_pago antes de calcular.
      El `monto_cuota` que recibe este helper ya viene calculado por el caller; si el
      caller quiere usar interés debe llamar a _calcular_monto_cuota_frances primero.

    Los campos monto_capital e monto_interes no se almacenan en cuotas (ver auditoría B3);
    se derivan en el frontend desde saldo_capital_inicial / saldo_capital_final.
    """
    modalidad = (p.modalidad_pago or "MENSUAL").upper()
    delta_dias = 30 if modalidad == "MENSUAL" else (15 if modalidad == "QUINCENAL" else 7)
    cliente_id = p.cliente_id
    total = monto_cuota * numero_cuotas
    monto_cuota_dec = Decimal(str(round(monto_cuota, 2)))
    creadas = 0
    for n in range(1, numero_cuotas + 1):
        next_date = fecha_base + timedelta(days=delta_dias * n - 1)
        saldo_inicial = Decimal(str(round(total - (n - 1) * monto_cuota, 2)))
        saldo_final = Decimal(str(round(total - n * monto_cuota, 2)))
        if saldo_final < 0:
            saldo_final = Decimal("0")
        c = Cuota(
            prestamo_id=p.id,
            cliente_id=cliente_id,
            numero_cuota=n,
            fecha_vencimiento=next_date,
            monto=monto_cuota_dec,
            saldo_capital_inicial=saldo_inicial,
            saldo_capital_final=saldo_final,
            # [B3] Calcular desglose: capital = diferencia de saldos; interés = residuo
            monto_capital=saldo_inicial - saldo_final,
            monto_interes=monto_cuota_dec - (saldo_inicial - saldo_final),
            estado="PENDIENTE",
            dias_mora=0,
        )
        db.add(c)
        creadas += 1
    return creadas


@router.get("/{prestamo_id}/cuotas", response_model=list)
def get_cuotas_prestamo(prestamo_id: int, db: Session = Depends(get_db)):
    """
    Lista las cuotas (tabla de amortización) de un préstamo, con info de pago conciliado.
    
    Estrategia mejorada:
    1. Obtiene todas las cuotas del préstamo.
    2. Para cada cuota, busca pagos coincidentes por fecha_vencimiento + rango de días.
    3. Consolida información: si hay pagos conciliados, los retorna.
    4. Calcula pago_conciliado=True si existe al menos un pago conciliado o verificado.
    5. Retorna pago_monto_conciliado como suma de montos conciliados en el rango de fechas.
    """
    row = db.get(Prestamo, prestamo_id)
    if not row:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    
    # Obtener todas las cuotas del préstamo
    cuotas = db.execute(
        select(Cuota).where(Cuota.prestamo_id == prestamo_id).order_by(Cuota.numero_cuota)
    ).scalars().all()
    
    resultado = []
    for c in cuotas:
        # Estrategia de búsqueda de pagos:
        # 1. Primero, si existe cuota.pago_id, buscar ese pago específico.
        # 2. Si no, buscar pagos por rango de fechas (+-15 días del vencimiento).
        
        pago_conciliado_flag = False
        pago_monto_conciliado = 0.0
        pago_verificado_concordancia = ""
        
        # [C2] pago_monto_conciliado = monto real abonado a ESTA cuota (cuota.total_pagado),
        # no el monto total del pago (que puede cubrir múltiples cuotas).
        pago_monto_conciliado = float(c.total_pagado or 0)

        if c.pago_id:
            # Caso 1: La cuota tiene un pago_id vinculado directamente
            pago = db.get(Pago, c.pago_id)
            if pago:
                pago_conciliado_flag = bool(pago.conciliado)
                pago_verificado_concordancia = str(pago.verificado_concordancia or "").strip().upper()
                if pago_verificado_concordancia == "SI":
                    pago_conciliado_flag = True
        else:
            # Caso 2: Sin pago_id directo — buscar pagos conciliados por rango de fechas
            # Solo necesitamos el flag de conciliación; el monto ya viene de cuota.total_pagado.
            if c.fecha_vencimiento:
                fecha_inicio = c.fecha_vencimiento - timedelta(days=15)
                fecha_fin = c.fecha_vencimiento + timedelta(days=15)

                pagos_en_rango = db.execute(
                    select(Pago)
                    .where(
                        Pago.prestamo_id == prestamo_id,
                        func.date(Pago.fecha_pago) >= fecha_inicio,
                        func.date(Pago.fecha_pago) <= fecha_fin,
                    )
                    .order_by(Pago.fecha_pago.desc())
                ).scalars().all()

                for pago in pagos_en_rango:
                    if pago.conciliado or (str(pago.verificado_concordancia or "").strip().upper() == "SI"):
                        pago_conciliado_flag = True
                        break  # un pago conciliado en rango es suficiente para marcar el flag
        
        # Construir respuesta de cuota
        resultado.append({
            "id": c.id,
            "prestamo_id": c.prestamo_id,
            "pago_id": c.pago_id,
            "numero_cuota": c.numero_cuota,
            "fecha_vencimiento": c.fecha_vencimiento.isoformat() if c.fecha_vencimiento else None,
            "monto": float(c.monto) if c.monto is not None else 0,
            "monto_cuota": float(c.monto) if c.monto is not None else 0,
            "monto_capital": float(c.monto_capital) if c.monto_capital is not None else 0,  # [B3]
            "monto_interes": float(c.monto_interes) if c.monto_interes is not None else 0,  # [B3]
            "saldo_capital_inicial": float(c.saldo_capital_inicial) if c.saldo_capital_inicial is not None else 0,
            "saldo_capital_final": float(c.saldo_capital_final) if c.saldo_capital_final is not None else 0,
            "capital_pagado": None,
            "interes_pagado": None,
            "total_pagado": float(c.total_pagado) if c.total_pagado is not None else 0,
            "fecha_pago": c.fecha_pago.isoformat() if c.fecha_pago else None,
            "estado": c.estado or "PENDIENTE",
            "dias_mora": c.dias_mora if c.dias_mora is not None else 0,
            "dias_morosidad": c.dias_morosidad if c.dias_morosidad is not None else 0,
            # pago_conciliado: True si existe pago conciliado O verificado_concordancia='SI'
            "pago_conciliado": pago_conciliado_flag,
            # pago_monto_conciliado: suma de montos de pagos conciliados
            "pago_monto_conciliado": pago_monto_conciliado,
        })
    
    return resultado


def _obtener_cuotas_para_export(db: Session, prestamo_id: int, prestamo: Prestamo) -> list:
    """Obtiene cuotas del préstamo con datos formateados para exportación Excel/PDF."""
    cuotas = db.execute(
        select(Cuota).where(Cuota.prestamo_id == prestamo_id).order_by(Cuota.numero_cuota)
    ).scalars().all()
    
    resultado = []
    for c in cuotas:
        saldo_inicial = float(c.saldo_capital_inicial) if c.saldo_capital_inicial is not None else 0
        saldo_final = float(c.saldo_capital_final) if c.saldo_capital_final is not None else 0
        monto_cuota = float(c.monto) if c.monto is not None else 0
        monto_capital = max(0, saldo_inicial - saldo_final)
        monto_interes = max(0, monto_cuota - monto_capital)
        
        resultado.append({
            "numero_cuota": c.numero_cuota,
            "fecha_vencimiento": c.fecha_vencimiento.isoformat() if c.fecha_vencimiento else "",
            "monto_capital": monto_capital,
            "monto_interes": monto_interes,
            "monto_cuota": monto_cuota,
            "saldo_capital_final": saldo_final,
            "estado": c.estado or "PENDIENTE",
        })
    return resultado


def _generar_excel_amortizacion(cuotas: list, prestamo: Prestamo) -> bytes:
    """Genera archivo Excel con tabla de amortización del préstamo."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tabla de Amortización"
    
    # Encabezados
    headers = ["Cuota", "Fecha Vencimiento", "Capital", "Interés", "Total", "Saldo Pendiente", "Estado"]
    ws.append(headers)
    header_row = ws[1]
    for cell in header_row:
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid")
    
    total_capital = 0
    total_interes = 0
    total_general = 0
    
    for c in cuotas:
        ws.append([
            c["numero_cuota"],
            c["fecha_vencimiento"],
            c["monto_capital"],
            c["monto_interes"],
            c["monto_cuota"],
            c["saldo_capital_final"],
            c["estado"],
        ])
        total_capital += c["monto_capital"]
        total_interes += c["monto_interes"]
        total_general += c["monto_cuota"]
    
    # Fila de resumen
    ws.append([])
    ws.append(["RESUMEN", "", total_capital, total_interes, total_general, "", ""])
    
    # Formato moneda para columnas numéricas
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=3, max_col=6):
        for cell in row:
            cell.number_format = '$#,##0.00'
    
    # Ajustar anchos de columna
    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 12
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].width = 15
    ws.column_dimensions["G"].width = 15
    
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _generar_pdf_amortizacion(cuotas: list, prestamo: Prestamo) -> bytes:
    """Genera archivo PDF con tabla de amortización del préstamo."""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    story.append(Paragraph("Tabla de Amortización", styles["Title"]))
    story.append(Paragraph(f"Cliente: {prestamo.nombres}", styles["Normal"]))
    story.append(Paragraph(f"Cédula: {prestamo.cedula}", styles["Normal"]))
    story.append(Paragraph(f"Préstamo #{prestamo.id}", styles["Normal"]))
    story.append(Paragraph(f"Total: ${float(prestamo.total_financiamiento or 0):,.2f}", styles["Normal"]))
    story.append(Spacer(1, 12))
    
    if not cuotas:
        story.append(Paragraph("No hay cuotas para este préstamo.", styles["Normal"]))
    else:
        rows = [["Cuota", "Fecha Venc.", "Capital", "Interés", "Total", "Saldo Pend.", "Estado"]]
        for c in cuotas:
            rows.append([
                str(c["numero_cuota"]),
                c["fecha_vencimiento"],
                f"${c['monto_capital']:,.2f}",
                f"${c['monto_interes']:,.2f}",
                f"${c['monto_cuota']:,.2f}",
                f"${c['saldo_capital_final']:,.2f}",
                c["estado"],
            ])
        t = Table(rows)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), "#3B82F6"),
            ("TEXTCOLOR", (0, 0), (-1, 0), "white"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (2, 0), (5, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, "#ccc"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [0xffffff, 0xf5f7fa]),
        ]))
        story.append(t)
    
    doc.build(story)
    return buf.getvalue()


@router.get("/{prestamo_id}/amortizacion/excel")
def exportar_amortizacion_excel(prestamo_id: int, db: Session = Depends(get_db)):
    """Exporta la tabla de amortización del préstamo en formato Excel."""
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    
    cuotas = _obtener_cuotas_para_export(db, prestamo_id, prestamo)
    content = _generar_excel_amortizacion(cuotas, prestamo)
    filename = f"Tabla_Amortizacion_{prestamo.cedula}_{prestamo.id}.xlsx"
    
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{prestamo_id}/amortizacion/pdf")
def exportar_amortizacion_pdf(prestamo_id: int, db: Session = Depends(get_db)):
    """Exporta la tabla de amortización del préstamo en formato PDF."""
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    
    cuotas = _obtener_cuotas_para_export(db, prestamo_id, prestamo)
    content = _generar_pdf_amortizacion(cuotas, prestamo)
    filename = f"Tabla_Amortizacion_{prestamo.cedula}_{prestamo.id}.pdf"
    
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/{prestamo_id}/generar-amortizacion", response_model=dict)
def generar_amortizacion(prestamo_id: int, db: Session = Depends(get_db)):
    """Genera la tabla de amortización (cuotas) para el préstamo. No crea si ya existen cuotas."""
    p = db.get(Prestamo, prestamo_id)
    if not p:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    existentes = db.scalar(select(func.count()).select_from(Cuota).where(Cuota.prestamo_id == prestamo_id)) or 0
    if existentes > 0:
        return {"message": "Ya existe tabla de amortización.", "cuotas": existentes, "creadas": 0}
    numero_cuotas = p.numero_cuotas or 12
    total = float(p.total_financiamiento or 0)
    if numero_cuotas <= 0 or total <= 0:
        raise HTTPException(status_code=400, detail="Préstamo sin número de cuotas o monto válido.")
    monto_cuota = _resolver_monto_cuota(p, total, numero_cuotas)  # [C1] usa amortización francesa si tasa > 0
    fecha_base = p.fecha_base_calculo if getattr(p, "fecha_base_calculo", None) else date.today()
    if hasattr(fecha_base, "date"):
        fecha_base = fecha_base.date() if callable(getattr(fecha_base, "date", None)) else fecha_base
    creadas = _generar_cuotas_amortizacion(db, p, fecha_base, numero_cuotas, monto_cuota)
    db.commit()
    return {"message": "Tabla de amortización generada.", "cuotas": creadas, "creadas": creadas}


@router.post("/{prestamo_id}/aplicar-condiciones-aprobacion", response_model=PrestamoResponse)
def aplicar_condiciones_aprobacion(prestamo_id: int, payload: AplicarCondicionesBody, db: Session = Depends(get_db)):
    """Aplica condiciones de aprobación: actualiza préstamo y opcionalmente genera cuotas."""
    p = db.get(Prestamo, prestamo_id)
    if not p:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    # [A3] Solo se pueden aplicar condiciones en estados previos a DESEMBOLSADO
    _ESTADOS_APROBABLES = ("DRAFT", "EN_REVISION", "APROBADO", "EVALUADO")
    if p.estado not in _ESTADOS_APROBABLES:
        raise HTTPException(
            status_code=400,
            detail=f"No se pueden aplicar condiciones a un préstamo en estado '{p.estado}'. "
                   f"Estados permitidos: {', '.join(_ESTADOS_APROBABLES)}.",
        )
    if payload.tasa_interes is not None:
        p.tasa_interes = Decimal(str(payload.tasa_interes))
    if payload.plazo_maximo is not None:
        p.numero_cuotas = payload.plazo_maximo
    if payload.fecha_base_calculo is not None:
        p.fecha_base_calculo = payload.fecha_base_calculo
    if payload.observaciones is not None:
        p.observaciones = payload.observaciones
    p.estado = "APROBADO"
    if p.fecha_aprobacion is None:
        fa = payload.fecha_base_calculo or getattr(p, "fecha_base_calculo", None) or date.today()
        if hasattr(fa, "date"):
            fa = fa.date() if callable(getattr(fa, "date", None)) else fa
        p.fecha_aprobacion = datetime.combine(fa, datetime.min.time())
    _registrar_en_revision_manual(db, prestamo_id)
    db.commit()
    # Generar cuotas si no existen
    existentes = db.scalar(select(func.count()).select_from(Cuota).where(Cuota.prestamo_id == prestamo_id)) or 0
    if existentes == 0:
        numero_cuotas = p.numero_cuotas or 12
        total = float(p.total_financiamiento or 0)
        monto_cuota = _resolver_monto_cuota(p, total, numero_cuotas)  # [C1] usa amortización francesa si tasa > 0
        fecha_base = p.fecha_base_calculo or date.today()
        if hasattr(fecha_base, "date"):
            fecha_base = fecha_base.date() if callable(getattr(fecha_base, "date", None)) else fecha_base
        _generar_cuotas_amortizacion(db, p, fecha_base, numero_cuotas, monto_cuota)
        db.commit()
    db.refresh(p)
    return PrestamoResponse.model_validate(p)


@router.post("/{prestamo_id}/evaluar-riesgo", response_model=PrestamoResponse)
def evaluar_riesgo(prestamo_id: int, payload: EvaluarRiesgoBody, db: Session = Depends(get_db)):
    """Registra evaluación de riesgo manual (ML) y opcionalmente estado/requiere_revision."""
    p = db.get(Prestamo, prestamo_id)
    if not p:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    if payload.ml_impago_nivel_riesgo_manual is not None:
        p.ml_impago_nivel_riesgo_manual = payload.ml_impago_nivel_riesgo_manual
    if payload.ml_impago_probabilidad_manual is not None:
        p.ml_impago_probabilidad_manual = Decimal(str(payload.ml_impago_probabilidad_manual))
    if payload.requiere_revision is not None:
        p.requiere_revision = payload.requiere_revision
    if payload.estado is not None:
        p.estado = payload.estado.strip().upper()
    db.commit()
    db.refresh(p)
    return PrestamoResponse.model_validate(p)


@router.patch("/{prestamo_id}/marcar-revision", response_model=PrestamoResponse)
def marcar_revision(
    prestamo_id: int,
    requiere_revision: bool = Query(..., alias="requiere_revision"),
    db: Session = Depends(get_db),
):
    """Marca o desmarca el préstamo como requiere_revision."""
    p = db.get(Prestamo, prestamo_id)
    if not p:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    p.requiere_revision = requiere_revision
    db.commit()
    db.refresh(p)
    return PrestamoResponse.model_validate(p)


@router.post("/{prestamo_id}/asignar-fecha-aprobacion", response_model=dict)
def asignar_fecha_aprobacion(prestamo_id: int, payload: AsignarFechaAprobacionBody, db: Session = Depends(get_db)):
    """Asigna fecha de aprobación/desembolso (misma fecha), cambia estado a DESEMBOLSADO y genera cuotas si no existen.
    Útil si el préstamo quedó en APROBADO sin fecha; en flujo normal, aprobar-manual ya desembolsa con la misma fecha."""
    p = db.get(Prestamo, prestamo_id)
    if not p:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    # [A3] Solo se puede desembolsar un préstamo aprobado, no uno ya desembolsado o rechazado
    _ESTADOS_DESEMBOLSABLES = ("DRAFT", "EN_REVISION", "APROBADO", "EVALUADO")
    if p.estado not in _ESTADOS_DESEMBOLSABLES:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede asignar fecha de desembolso a un préstamo en estado '{p.estado}'. "
                   f"Estados permitidos: {', '.join(_ESTADOS_DESEMBOLSABLES)}.",
        )
    p.fecha_aprobacion = datetime.combine(payload.fecha_aprobacion, datetime.min.time()) if isinstance(payload.fecha_aprobacion, date) else payload.fecha_aprobacion
    p.estado = "DESEMBOLSADO"
    _registrar_en_revision_manual(db, prestamo_id)
    existentes = db.scalar(select(func.count()).select_from(Cuota).where(Cuota.prestamo_id == prestamo_id)) or 0
    cuotas_recalculadas = 0
    if existentes == 0:
        numero_cuotas = p.numero_cuotas or 12
        total = float(p.total_financiamiento or 0)
        monto_cuota = _resolver_monto_cuota(p, total, numero_cuotas)  # [C1] usa amortización francesa si tasa > 0
        fecha_base = payload.fecha_aprobacion
        cuotas_recalculadas = _generar_cuotas_amortizacion(db, p, fecha_base, numero_cuotas, monto_cuota)
    db.commit()
    db.refresh(p)
    return {"prestamo": PrestamoResponse.model_validate(p), "cuotas_recalculadas": cuotas_recalculadas}


@router.post("/{prestamo_id}/aprobar-manual", response_model=dict)
def aprobar_manual(
    prestamo_id: int,
    payload: AprobarManualBody,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Aprobación manual de riesgo: una fecha (aprobación = desembolso, misma fecha). Confirmación de documentos
    y declaración de políticas. Actualiza datos editables del préstamo, genera tabla de amortización
    y registra en auditoría. Solo préstamos en DRAFT o EN_REVISION. Al aprobar se desembolsa automáticamente:
    estado resultante DESEMBOLSADO, fecha_aprobación = fecha de aprobación y desembolso.
    """
    if (getattr(current_user, "rol", None) or "").lower() != "administrador":
        raise HTTPException(
            status_code=403,
            detail="Solo administración puede aprobar préstamos (aprobación manual de riesgo).",
        )
    p = db.get(Prestamo, prestamo_id)
    if not p:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    if p.estado not in ("DRAFT", "EN_REVISION"):
        raise HTTPException(
            status_code=400,
            detail=f"Solo se puede aprobar manualmente un préstamo en DRAFT o EN_REVISION. Estado actual: {p.estado}",
        )
    if not payload.acepta_declaracion:
        raise HTTPException(status_code=400, detail="Debe aceptar la declaración de políticas y riesgo.")
    if not payload.documentos_analizados:
        raise HTTPException(status_code=400, detail="Debe confirmar que se analizaron los documentos del cliente.")

    fecha_ap = payload.fecha_aprobacion
    if hasattr(fecha_ap, "date"):
        fecha_ap = fecha_ap.date() if callable(getattr(fecha_ap, "date", None)) else fecha_ap

    try:
        if payload.total_financiamiento is not None:
            p.total_financiamiento = Decimal(str(payload.total_financiamiento))
        if payload.numero_cuotas is not None:
            p.numero_cuotas = payload.numero_cuotas
        if payload.modalidad_pago is not None:
            p.modalidad_pago = payload.modalidad_pago.strip().upper() or p.modalidad_pago
        if payload.cuota_periodo is not None:
            p.cuota_periodo = Decimal(str(payload.cuota_periodo))
        if payload.tasa_interes is not None:
            p.tasa_interes = Decimal(str(payload.tasa_interes))
        if payload.observaciones is not None:
            p.observaciones = payload.observaciones

        p.fecha_aprobacion = datetime.combine(fecha_ap, datetime.min.time())
        p.fecha_base_calculo = fecha_ap
        p.usuario_aprobador = current_user.email
        p.estado = "DESEMBOLSADO"

        db.execute(delete(Cuota).where(Cuota.prestamo_id == prestamo_id))
        numero_cuotas = p.numero_cuotas or 12
        total = float(p.total_financiamiento or 0)
        if numero_cuotas <= 0 or total <= 0:
            raise HTTPException(status_code=400, detail="Número de cuotas o monto de financiamiento inválido.")
        monto_cuota = _resolver_monto_cuota(p, total, numero_cuotas)  # [C1] usa amortización francesa si tasa > 0
        creadas = _generar_cuotas_amortizacion(db, p, fecha_ap, numero_cuotas, monto_cuota)

        audit = Auditoria(
            usuario_id=_audit_user_id(db, current_user),
            accion="APROBACION_MANUAL",
            entidad="prestamos",
            entidad_id=prestamo_id,
            detalles=f"Aprobación manual de riesgo. Préstamo {prestamo_id}. Fecha aprobación: {fecha_ap}. Usuario: {current_user.email}.",
            exito=True,
        )
        db.add(audit)
        _registrar_en_revision_manual(db, prestamo_id)
        db.commit()
        db.refresh(p)
        return {"prestamo": PrestamoResponse.model_validate(p), "cuotas_generadas": creadas}
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        logger.exception("aprobar_manual prestamo_id=%s IntegrityError: %s", prestamo_id, e)
        err_msg = str(e.orig) if getattr(e, "orig", None) else str(e)
        if "auditoria" in err_msg.lower() and ("usuario_id" in err_msg.lower() or "users" in err_msg.lower()):
            raise HTTPException(
                status_code=500,
                detail=(
                    "Error de integridad en auditoría (usuario_id). "
                    "Ejecuta la migración backend/sql/migracion_auditoria_fk_usuarios.sql en la BD."
                ),
            ) from e
        raise HTTPException(
            status_code=500,
            detail=f"Error de integridad en BD al aprobar: {err_msg[:200]}",
        ) from e
    except Exception as e:
        db.rollback()
        logger.exception("aprobar_manual prestamo_id=%s: %s", prestamo_id, e)
        raise HTTPException(
            status_code=500,
            detail="Error al aprobar el préstamo. Revisa los logs del servidor.",
        ) from e


@router.post("/{prestamo_id}/rechazar", response_model=PrestamoResponse)
def rechazar_prestamo(
    prestamo_id: int,
    payload: dict,  # {"motivo_rechazo": "string"}
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Rechaza un préstamo en estados tempranos (DRAFT, EN_REVISION, EVALUADO).
    Solo usuario con rol 'administrador' puede rechazar.
    Registra motivo en auditoría.
    """
    if (getattr(current_user, "rol", None) or "").lower() != "administrador":
        raise HTTPException(
            status_code=403,
            detail="Solo administración puede rechazar préstamos.",
        )
    
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    
    # Solo puedo rechazar en estados tempranos
    if prestamo.estado not in ("DRAFT", "EN_REVISION", "EVALUADO"):
        raise HTTPException(
            status_code=400,
            detail=f"No se puede rechazar préstamo en estado {prestamo.estado}. Solo DRAFT, EN_REVISION, EVALUADO.",
        )
    
    motivo = (payload.get("motivo_rechazo") or "Sin motivo especificado").strip()[:500]
    
    try:
        prestamo.estado = "RECHAZADO"
        prestamo.usuario_aprobador = current_user.email
        prestamo.fecha_aprobacion = datetime.now()
        prestamo.observaciones = f"[RECHAZADO] {motivo}" if prestamo.observaciones else f"Rechazado: {motivo}"
        
        # Auditar rechazo
        audit = Auditoria(
            usuario_id=_audit_user_id(db, current_user),
            accion="RECHAZO_PRESTAMO",
            entidad="prestamos",
            entidad_id=prestamo_id,
            detalles=f"Rechazo de préstamo. Motivo: {motivo}. Usuario: {current_user.email}.",
            exito=True,
        )
        db.add(audit)
        db.commit()
        db.refresh(prestamo)
        return PrestamoResponse.model_validate(prestamo)
    except Exception as e:
        db.rollback()
        logger.exception("Error rechazar prestamo_id=%s: %s", prestamo_id, e)
        raise HTTPException(
            status_code=500,
            detail="Error al rechazar el préstamo.",
        ) from e


@router.get("/{prestamo_id}/evaluacion-riesgo", response_model=dict)
def get_evaluacion_riesgo(prestamo_id: int, db: Session = Depends(get_db)):
    """Devuelve datos de evaluación de riesgo (ML manual/calculado) del préstamo."""
    p = db.get(Prestamo, prestamo_id)
    if not p:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    return {
        "ml_impago_nivel_riesgo_manual": getattr(p, "ml_impago_nivel_riesgo_manual", None),
        "ml_impago_probabilidad_manual": float(p.ml_impago_probabilidad_manual) if getattr(p, "ml_impago_probabilidad_manual", None) is not None else None,
        "ml_impago_nivel_riesgo_calculado": getattr(p, "ml_impago_nivel_riesgo_calculado", None),
        "ml_impago_probabilidad_calculada": float(p.ml_impago_probabilidad_calculada) if getattr(p, "ml_impago_probabilidad_calculada", None) is not None else None,
        "requiere_revision": getattr(p, "requiere_revision", False),
    }


@router.get("/{prestamo_id}/auditoria", response_model=list)
def get_auditoria_prestamo(prestamo_id: int, db: Session = Depends(get_db)):
    """Lista registros de auditoría asociados al préstamo (entidad=prestamos, entidad_id=prestamo_id)."""
    p = db.get(Prestamo, prestamo_id)
    if not p:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    q = select(Auditoria).where(Auditoria.entidad == "prestamos", Auditoria.entidad_id == prestamo_id).order_by(Auditoria.fecha.desc())
    registros = db.execute(q).scalars().all()
    return [
        {
            "id": r.id,
            "usuario_id": r.usuario_id,
            "accion": r.accion,
            "modulo": r.entidad,
            "descripcion": r.detalles,
            "fecha": r.fecha.isoformat() + "Z" if r.fecha else "",
        }
        for r in registros
    ]


@router.post("", response_model=PrestamoResponse, status_code=201)
def create_prestamo(payload: PrestamoCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    """Crea un préstamo en BD. Valida que cliente_id exista. cedula/nombres se toman del Cliente.
    Automáticamente genera las cuotas de amortización."""
    cliente = db.get(Cliente, payload.cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    from datetime import date
    hoy = date.today()
    
    # Usar email del usuario actual (no hardcoded)
    usuario_proponente_email = current_user.email if current_user else "itmaster@rapicreditca.com"
    
    es_carga_masiva = getattr(payload, "aprobado_por_carga_masiva", False)
    estado_inicial = "APROBADO" if es_carga_masiva else (payload.estado or "DRAFT")
    # Carga masiva: fecha_aprobacion = fecha_registro (se asigna después del commit/refresh)
    fecha_aprob = None if es_carga_masiva else None
    row = Prestamo(
        cliente_id=payload.cliente_id,
        cedula=cliente.cedula or "",
        nombres=cliente.nombres or "",
        total_financiamiento=payload.total_financiamiento,
        fecha_requerimiento=payload.fecha_requerimiento or hoy,
        modalidad_pago=payload.modalidad_pago or "MENSUAL",
        numero_cuotas=payload.numero_cuotas or 12,
        cuota_periodo=payload.cuota_periodo or 0,
        producto=payload.producto or "Financiamiento",
        estado=estado_inicial,
        fecha_aprobacion=fecha_aprob,
        concesionario=payload.concesionario,
        modelo_vehiculo=payload.modelo,
        analista=payload.analista or "",
        usuario_proponente=usuario_proponente_email,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    if es_carga_masiva and row.fecha_registro:
        row.fecha_aprobacion = row.fecha_registro
        db.commit()
        db.refresh(row)
    
    # [MEJORA] Generar cuotas automáticamente
    numero_cuotas = payload.numero_cuotas or 12
    total_financiamiento = float(payload.total_financiamiento)
    monto_cuota = _resolver_monto_cuota(row, total_financiamiento, numero_cuotas)
    prestamo_id = row.id  # guardar antes del try para no acceder a row tras rollback

    try:
        cuotas_generadas = _generar_cuotas_amortizacion(db, row, hoy, numero_cuotas, monto_cuota)
        db.commit()
        logger.info(f"Préstamo {prestamo_id}: {cuotas_generadas} cuotas generadas automáticamente")
    except Exception as e:
        db.rollback()
        logger.error("Error generando cuotas para préstamo %s: %s", prestamo_id, str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar cuotas: {str(e)}"
        )
    
    _registrar_en_revision_manual(db, row.id)
    db.commit()
    return PrestamoResponse.model_validate(row)


@router.put("/{prestamo_id}", response_model=PrestamoResponse)
def update_prestamo(prestamo_id: int, payload: PrestamoUpdate, db: Session = Depends(get_db)):
    """Actualiza un préstamo en BD."""
    row = db.get(Prestamo, prestamo_id)
    if not row:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    if payload.cliente_id is not None:
        cliente = db.get(Cliente, payload.cliente_id)
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        row.cliente_id = payload.cliente_id
    if payload.total_financiamiento is not None:
        row.total_financiamiento = payload.total_financiamiento
    if payload.estado is not None:
        row.estado = payload.estado
    if payload.concesionario is not None:
        row.concesionario = payload.concesionario
    if payload.modelo is not None:
        row.modelo_vehiculo = payload.modelo
    if payload.analista is not None:
        row.analista = payload.analista
    if payload.modalidad_pago is not None:
        row.modalidad_pago = payload.modalidad_pago
    if payload.numero_cuotas is not None:
        row.numero_cuotas = payload.numero_cuotas
    db.commit()
    db.refresh(row)
    return PrestamoResponse.model_validate(row)


@router.delete("/{prestamo_id}", status_code=204)
def delete_prestamo(prestamo_id: int, db: Session = Depends(get_db)):
    """Elimina un préstamo en BD. Borra antes las cuotas asociadas para evitar huérfanos o fallo de FK."""
    row = db.get(Prestamo, prestamo_id)
    if not row:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    db.execute(delete(Cuota).where(Cuota.prestamo_id == prestamo_id))
    db.delete(row)
    db.commit()
    return None


# ============================================================================
# CARGA MASIVA DE PRÉSTAMOS DESDE EXCEL
# ============================================================================

from fastapi import UploadFile, File
from app.models.prestamo_con_error import PrestamoConError

try:
    import openpyxl
except ImportError:
    openpyxl = None


def _validate_modalidad_pago(modalidad: str) -> bool:
    """Valida que modalidad sea MENSUAL, QUINCENAL o SEMANAL."""
    if not modalidad:
        return False
    mod = str(modalidad).strip().upper()
    return mod in ("MENSUAL", "QUINCENAL", "SEMANAL")


def _parse_decimal(value: any) -> Decimal:
    """Parsea valor a Decimal."""
    if value is None:
        return Decimal("0.00")
    try:
        return Decimal(str(value))
    except:
        return None


@router.post("/upload-excel", response_model=dict)
async def upload_prestamos_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Carga masiva de préstamos desde Excel.
    Formato esperado: Cédula Cliente | Monto Financiamiento | Modalidad Pago | Nº Cuotas | Producto | Analista | Concesionario
    
    Validaciones:
    - Cédula: válida en BD (cliente existe)
    - Monto: > 0
    - Modalidad: MENSUAL|QUINCENAL|SEMANAL
    - Nº Cuotas: 1-12
    - Analista: requerido
    - Concesionario: opcional
    
    Respuesta: {registros_creados, registros_con_error}
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
        prestamos_con_errores = []
        
        # Pre-cargar clientes para validar
        clientes_cedulas = {}
        for cliente in db.execute(select(Cliente.id, Cliente.cedula)).all():
            clientes_cedulas[cliente.cedula.upper() if cliente.cedula else ""] = cliente.id
        
        usuario_email = current_user.email if hasattr(current_user, 'email') else "sistema@rapicredit.com"
        hoy = date.today()
        
        # Procesar filas (saltar header)
        for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or all(cell is None for cell in row):
                continue
            
            try:
                cedula_raw = row[0] if len(row) > 0 else None
                monto_raw = row[1] if len(row) > 1 else None
                modalidad_raw = row[2] if len(row) > 2 else None
                cuotas_raw = row[3] if len(row) > 3 else None
                producto_raw = row[4] if len(row) > 4 else None
                analista_raw = row[5] if len(row) > 5 else None
                concesionario_raw = row[6] if len(row) > 6 else None
                
                errores = []
                
                # Validar cédula
                cedula = str(cedula_raw or "").strip().upper()
                if not cedula:
                    errores.append("Cédula es requerida")
                elif cedula not in clientes_cedulas:
                    errores.append(f"Cliente con cédula {cedula} no existe en BD")
                
                # Validar monto
                monto = _parse_decimal(monto_raw)
                if monto is None:
                    errores.append("Monto Financiamiento inválido")
                elif monto <= 0:
                    errores.append("Monto debe ser mayor a 0")
                
                # Validar modalidad
                modalidad = str(modalidad_raw or "").strip().upper()
                if not modalidad:
                    errores.append("Modalidad Pago es requerida (MENSUAL|QUINCENAL|SEMANAL)")
                elif not _validate_modalidad_pago(modalidad):
                    errores.append("Modalidad debe ser MENSUAL, QUINCENAL o SEMANAL")
                
                # Validar cuotas
                try:
                    cuotas = int(cuotas_raw) if cuotas_raw else None
                    if cuotas is None:
                        errores.append("Nº Cuotas es requerido")
                    elif cuotas < 1 or cuotas > 12:
                        errores.append("Nº Cuotas debe estar entre 1 y 12")
                except (ValueError, TypeError):
                    errores.append("Nº Cuotas debe ser número entero")
                
                # Validar producto
                producto = str(producto_raw or "").strip()
                if not producto:
                    errores.append("Producto es requerido")
                
                # Validar analista
                analista = str(analista_raw or "").strip()
                if not analista:
                    errores.append("Analista es requerido")
                
                # Concesionario es opcional
                concesionario = str(concesionario_raw or "").strip() if concesionario_raw else None
                
                # Si hay errores, agregar a lista de revisión
                if errores:
                    prestamo_error = PrestamoConError(
                        cedula_cliente=cedula or None,
                        total_financiamiento=monto,
                        modalidad_pago=modalidad or None,
                        numero_cuotas=cuotas if 'cuotas' in locals() and isinstance(cuotas, int) else None,
                        producto=producto or None,
                        analista=analista or None,
                        concesionario=concesionario,
                        estado="PENDIENTE",
                        errores_descripcion="; ".join(errores),
                        fila_origen=idx,
                        usuario_registro=usuario_email
                    )
                    db.add(prestamo_error)
                    registros_con_error += 1
                    prestamos_con_errores.append({
                        "cedula": cedula,
                        "fila": idx,
                        "errores": "; ".join(errores)
                    })
                    continue
                
                # Crear préstamo
                cliente_id = clientes_cedulas[cedula]
                cliente = db.get(Cliente, cliente_id)
                
                prestamo = Prestamo(
                    cliente_id=cliente_id,
                    cedula=cliente.cedula or "",
                    nombres=cliente.nombres or "",
                    total_financiamiento=monto,
                    fecha_requerimiento=hoy,
                    modalidad_pago=modalidad,
                    numero_cuotas=cuotas,
                    cuota_periodo=Decimal("0.00"),
                    producto=producto,
                    estado="DRAFT",
                    concesionario=concesionario,
                    analista=analista,
                    usuario_proponente=usuario_email,
                )
                db.add(prestamo)
                db.flush()  # Obtener ID del préstamo
                
                # Generar cuotas automáticamente
                monto_cuota = _resolver_monto_cuota(prestamo, float(monto), cuotas)
                _generar_cuotas_amortizacion(db, prestamo, hoy, cuotas, monto_cuota)
                
                # Registrar en revisión manual
                _registrar_en_revision_manual(db, prestamo.id)
                
                registros_creados += 1
                
            except Exception as e:
                logger.error(f"Error procesando fila {idx}: {e}")
                prestamo_error = PrestamoConError(
                    cedula_cliente=str(row[0]) if len(row) > 0 else None,
                    total_financiamiento=_parse_decimal(row[1]) if len(row) > 1 else None,
                    errores_descripcion=f"Error general: {str(e)[:200]}",
                    fila_origen=idx,
                    usuario_registro=usuario_email
                )
                db.add(prestamo_error)
                registros_con_error += 1
                prestamos_con_errores.append({
                    "cedula": str(row[0]) if len(row) > 0 else "?",
                    "fila": idx,
                    "errores": str(e)[:100]
                })
        
        db.commit()
        
        return {
            "registros_creados": registros_creados,
            "registros_con_error": registros_con_error,
            "mensaje": f"Se crearon {registros_creados} préstamo(s) y {registros_con_error} con error(es)",
            "prestamos_con_errores": prestamos_con_errores[:10]  # Mostrar primeros 10
        }
        
    except Exception as e:
        db.rollback()
        logger.exception("Error cargando Excel de préstamos: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando archivo: {str(e)[:200]}"
        )


class RevisarPrestamoAgregarBody(BaseModel):
    """Datos de una fila para enviar a revisión manual (prestamos_con_errores)."""
    cedula_cliente: Optional[str] = None
    total_financiamiento: Optional[float] = None
    modalidad_pago: Optional[str] = None
    numero_cuotas: Optional[int] = None
    producto: Optional[str] = None
    analista: Optional[str] = None
    concesionario: Optional[str] = None
    errores_descripcion: Optional[str] = None
    fila_origen: Optional[int] = None


@router.post("/revisar/agregar", response_model=dict)
def agregar_prestamo_a_revisar(
    body: RevisarPrestamoAgregarBody,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Envía una fila a la tabla prestamos_con_errores (revisar préstamos).
    Usado desde la carga masiva cuando el usuario pulsa "Enviar a Revisar Préstamos".
    """
    usuario_email = getattr(current_user, "email", None) or "sistema@rapicredit.com"
    row = PrestamoConError(
        cedula_cliente=body.cedula_cliente,
        total_financiamiento=Decimal(str(body.total_financiamiento)) if body.total_financiamiento is not None else None,
        modalidad_pago=body.modalidad_pago,
        numero_cuotas=body.numero_cuotas,
        producto=body.producto,
        analista=body.analista,
        concesionario=body.concesionario,
        estado="PENDIENTE",
        errores_descripcion=body.errores_descripcion or "Enviado a revisión desde carga masiva",
        fila_origen=body.fila_origen,
        usuario_registro=usuario_email,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "mensaje": "Préstamo enviado a Revisar Préstamos"}


@router.get("/revisar/lista", response_model=dict)
def get_prestamos_con_errores(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Listado de préstamos con errores de validación (pendientes de revisión).
    Paginado para facilitar corrección manual.
    """
    total = db.scalar(select(func.count()).select_from(PrestamoConError)) or 0
    rows = db.execute(
        select(PrestamoConError)
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
                "cedula_cliente": r.cedula_cliente,
                "total_financiamiento": str(r.total_financiamiento) if r.total_financiamiento else None,
                "modalidad_pago": r.modalidad_pago,
                "numero_cuotas": r.numero_cuotas,
                "producto": r.producto,
                "analista": r.analista,
                "concesionario": r.concesionario,
                "errores": r.errores_descripcion,
                "fila_origen": r.fila_origen,
                "estado": r.estado,
                "fecha_registro": r.fecha_registro.isoformat() if r.fecha_registro else None,
            }
            for r in rows
        ]
    }


class EliminarPorDescargaBody(BaseModel):
    """IDs de registros exportados a Excel para eliminar de prestamos_con_errores."""
    ids: list[int]


@router.post("/revisar/eliminar-por-descarga", response_model=dict)
def eliminar_prestamos_por_descarga(
    payload: EliminarPorDescargaBody = Body(...),
    db: Session = Depends(get_db),
):
    """
    Elimina de prestamos_con_errores los registros descargados (borrado en lote).
    Misma regla que Pagos: al descargar Excel se vacía la lista; se rellena al enviar desde Carga Masiva.
    """
    valid_ids = [i for i in payload.ids if isinstance(i, int) and i > 0]
    if not valid_ids:
        return {"eliminados": 0, "mensaje": "No hay IDs"}
    result = db.execute(delete(PrestamoConError).where(PrestamoConError.id.in_(valid_ids)))
    eliminados = result.rowcount
    db.commit()
    return {"eliminados": eliminados, "mensaje": f"{eliminados} eliminados de prestamos_con_errores"}


@router.delete("/revisar/{error_id}", status_code=204)
def resolver_prestamo_error(error_id: int, db: Session = Depends(get_db)):
    """Marcar préstamo con error como resuelto (eliminar de la lista)."""
    row = db.get(PrestamoConError, error_id)
    if not row:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    
    db.delete(row)
    db.commit()
    return None
