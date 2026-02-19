"""
Endpoints de préstamos. Datos reales desde BD (tabla prestamos).
Todos los endpoints usan Depends(get_db). No hay stubs ni datos demo.
"""
import calendar
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import delete, func, select, text
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


# --- Schemas para body de endpoints adicionales ---
class AplicarCondicionesBody(BaseModel):
    tasa_interes: Optional[float] = None
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
    tasa_interes: Optional[float] = None
    observaciones: Optional[str] = None


@router.get("", response_model=dict)
@router.get("/", include_in_schema=False, response_model=dict)
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
    total = db.scalar(select(func.count()).select_from(q_base.subquery())) or 0
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
    total_fin = db.scalar(select(func.coalesce(func.sum(Prestamo.total_financiamiento), 0)).select_from(q_base.subquery())) or 0
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


@router.get("/cedula/{cedula}", response_model=dict)
def listar_prestamos_por_cedula(cedula: str, db: Session = Depends(get_db)):
    """Listado de préstamos por cédula del cliente (integrado con frontend)."""
    cedula_clean = (cedula or "").strip()
    if not cedula_clean:
        return {"prestamos": [], "total": 0}
    q = (
        select(Prestamo, Cliente.nombres, Cliente.cedula)
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Cliente.cedula == cedula_clean)
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


def _generar_cuotas_amortizacion(db: Session, p: Prestamo, fecha_base: date, numero_cuotas: int, monto_cuota: float) -> int:
    """Genera filas en cuotas. fecha_vencimiento = último día del período (fecha_base + delta*n - 1).
    MENSUAL 30d, QUINCENAL 15d, SEMANAL 7d. Ej: base 1 ene QUINCENAL → cuota 1 vence 15 ene, cuota 2 vence 31 ene."""
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
            estado="PENDIENTE",
        )
        db.add(c)
        creadas += 1
    return creadas


@router.get("/{prestamo_id}/cuotas", response_model=list)
def get_cuotas_prestamo(prestamo_id: int, db: Session = Depends(get_db)):
    """Lista las cuotas (tabla de amortización) de un préstamo, con info de pago conciliado."""
    row = db.get(Prestamo, prestamo_id)
    if not row:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    q = (
        select(Cuota, Pago.conciliado, Pago.monto_pagado)
        .select_from(Cuota)
        .outerjoin(Pago, Cuota.pago_id == Pago.id)
        .where(Cuota.prestamo_id == prestamo_id)
        .order_by(Cuota.numero_cuota)
    )
    rows = db.execute(q).all()
    return [
        {
            "id": c.id,
            "prestamo_id": c.prestamo_id,
            "pago_id": c.pago_id,
            "numero_cuota": c.numero_cuota,
            "fecha_vencimiento": c.fecha_vencimiento.isoformat() if c.fecha_vencimiento else None,
            "monto": float(c.monto) if c.monto is not None else 0,
            "monto_cuota": float(c.monto) if c.monto is not None else 0,
            "saldo_capital_inicial": float(c.saldo_capital_inicial) if c.saldo_capital_inicial is not None else 0,
            "saldo_capital_final": float(c.saldo_capital_final) if c.saldo_capital_final is not None else 0,
            "total_pagado": float(c.total_pagado) if c.total_pagado is not None else 0,
            "fecha_pago": c.fecha_pago.isoformat() if c.fecha_pago else None,
            "estado": c.estado or "PENDIENTE",
            "dias_mora": c.dias_mora if c.dias_mora is not None else 0,
            "pago_conciliado": bool(pago_conciliado) if pago_conciliado is not None else False,
            "pago_monto_conciliado": float(pago_monto) if pago_conciliado and pago_monto is not None else 0,
        }
        for c, pago_conciliado, pago_monto in rows
    ]


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
    monto_cuota = total / numero_cuotas
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
    if payload.tasa_interes is not None:
        p.tasa_interes = Decimal(str(payload.tasa_interes))
    if payload.plazo_maximo is not None:
        p.numero_cuotas = payload.plazo_maximo
    if payload.fecha_base_calculo is not None:
        p.fecha_base_calculo = payload.fecha_base_calculo
    if payload.observaciones is not None:
        p.observaciones = payload.observaciones
    p.estado = "APROBADO"
    db.commit()
    # Generar cuotas si no existen
    existentes = db.scalar(select(func.count()).select_from(Cuota).where(Cuota.prestamo_id == prestamo_id)) or 0
    if existentes == 0:
        numero_cuotas = p.numero_cuotas or 12
        total = float(p.total_financiamiento or 0)
        monto_cuota = total / numero_cuotas if numero_cuotas else 0
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
    """Asigna fecha de aprobación, cambia estado a DESEMBOLSADO y genera cuotas si no existen."""
    p = db.get(Prestamo, prestamo_id)
    if not p:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    p.fecha_aprobacion = datetime.combine(payload.fecha_aprobacion, datetime.min.time()) if isinstance(payload.fecha_aprobacion, date) else payload.fecha_aprobacion
    p.estado = "DESEMBOLSADO"
    existentes = db.scalar(select(func.count()).select_from(Cuota).where(Cuota.prestamo_id == prestamo_id)) or 0
    cuotas_recalculadas = 0
    if existentes == 0:
        numero_cuotas = p.numero_cuotas or 12
        total = float(p.total_financiamiento or 0)
        monto_cuota = total / numero_cuotas if numero_cuotas else 0
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
    Aprobación manual de riesgo: una fecha (aprobación y base amortización), confirmación de documentos
    y declaración de políticas. Actualiza datos editables del préstamo, genera tabla de amortización
    y registra en auditoría. Solo préstamos en DRAFT o EN_REVISION. Estado resultante: APROBADO.
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
        p.estado = "APROBADO"

        db.execute(delete(Cuota).where(Cuota.prestamo_id == prestamo_id))
        numero_cuotas = p.numero_cuotas or 12
        total = float(p.total_financiamiento or 0)
        if numero_cuotas <= 0 or total <= 0:
            raise HTTPException(status_code=400, detail="Número de cuotas o monto de financiamiento inválido.")
        monto_cuota = total / numero_cuotas
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
def create_prestamo(payload: PrestamoCreate, db: Session = Depends(get_db)):
    """Crea un préstamo en BD. Valida que cliente_id exista. cedula/nombres se toman del Cliente."""
    cliente = db.get(Cliente, payload.cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    from datetime import date
    hoy = date.today()
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
        estado=payload.estado or "DRAFT",
        concesionario=payload.concesionario,
        modelo_vehiculo=payload.modelo,
        analista=payload.analista or "",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
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
