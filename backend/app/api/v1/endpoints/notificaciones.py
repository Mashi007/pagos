"""
Endpoints de notificaciones a clientes retrasados.
Datos reales desde BD: cuotas (fecha_vencimiento, pagado) y clientes.
Reglas: 5 pestañas por días hasta vencimiento y mora 61+.
Configuración de envíos (habilitado/CCO por tipo) desde tabla configuracion (notificaciones_envios).
"""
import json
from datetime import date
from typing import List

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.cuota import Cuota
from app.models.cliente import Cliente
from app.models.configuracion import Configuracion

CLAVE_NOTIFICACIONES_ENVIOS = "notificaciones_envios"

router = APIRouter(dependencies=[Depends(get_current_user)])


def get_notificaciones_envios_config(db: Session) -> dict:
    """Carga la configuración de envíos por tipo (habilitado, cco) desde BD para reglas de negocio."""
    try:
        row = db.get(Configuracion, CLAVE_NOTIFICACIONES_ENVIOS)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _item(cliente: Cliente, cuota: Cuota, dias_atraso: int = None) -> dict:
    """Un registro para lista: nombre, cedula, y datos de cuota."""
    d = {
        "cliente_id": cliente.id,
        "nombre": cliente.nombres,
        "cedula": cliente.cedula,
        "numero_cuota": cuota.numero_cuota,
        "fecha_vencimiento": cuota.fecha_vencimiento.isoformat() if cuota.fecha_vencimiento else None,
        "monto": float(cuota.monto) if cuota.monto is not None else None,
    }
    if dias_atraso is not None:
        d["dias_atraso"] = dias_atraso
    return d


def _item_tab(cliente: Cliente, cuota: Cuota, dias_atraso: int = None, dias_antes: int = None) -> dict:
    """Item con forma esperada por el frontend (pestañas): correo, telefono, estado, etc."""
    d = {
        "cliente_id": cliente.id,
        "nombre": cliente.nombres or "",
        "cedula": cliente.cedula or "",
        "correo": (cliente.email or "").strip(),
        "telefono": (cliente.telefono or "").strip(),
        "modelo_vehiculo": None,
        "fecha_vencimiento": cuota.fecha_vencimiento.isoformat() if cuota.fecha_vencimiento else None,
        "numero_cuota": cuota.numero_cuota,
        "monto_cuota": float(cuota.monto) if cuota.monto is not None else None,
        "prestamo_id": cliente.id,
        "estado": "PENDIENTE",
    }
    if dias_atraso is not None:
        d["dias_atraso"] = dias_atraso
    if dias_antes is not None:
        d["dias_antes_vencimiento"] = dias_antes
    return d


@router.get("")
def get_notificaciones_lista(
    page: int = 1,
    per_page: int = 20,
    estado: str = None,
    canal: str = None,
    db: Session = Depends(get_db),
):
    """
    Listado paginado de notificaciones (envíos). El frontend Email/WhatsApp Config lo usa para 'envíos recientes'.
    Sin tabla de notificaciones en BD se devuelve lista vacía para evitar 404. get_db inyectado para reglas de negocio.
    """
    total = 0
    total_pages = 0
    items = []
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": per_page,
        "total_pages": total_pages,
    }


@router.get("/estadisticas/resumen")
def get_notificaciones_resumen(db: Session = Depends(get_db)):
    """Resumen para sidebar. El frontend espera: no_leidas, total. get_db inyectado para consistencia."""
    return {"no_leidas": 0, "total": 0}


@router.get("/clientes-retrasados", response_model=dict)
def get_clientes_retrasados(db: Session = Depends(get_db)):
    """
    Clientes a notificar por cuotas no pagadas, agrupados en 5 reglas:
    1. Faltan 5 días para fecha_vencimiento (no pagado)
    2. Faltan 3 días para fecha_vencimiento (no pagado)
    3. Falta 1 día para fecha_vencimiento (no pagado)
    4. Hoy = fecha_vencimiento (no pagado)
    5. 61+ días de mora: informe de cada cuota atrasada una a una.
    Se usa la fecha del servidor; actualizar a las 2am con cron si se desea.
    """
    hoy = date.today()
    # Cuotas no pagadas (fecha_pago nula) con su cliente
    q = (
        select(Cuota, Cliente)
        .join(Cliente, Cuota.cliente_id == Cliente.id)
        .where(Cuota.fecha_pago.is_(None))
    )
    rows = db.execute(q).all()

    dias_5: List[dict] = []
    dias_3: List[dict] = []
    dias_1: List[dict] = []
    hoy_list: List[dict] = []
    mora_61_cuotas: List[dict] = []  # cada cuota 61+ atrasada, una a una

    for (cuota, cliente) in rows:
        fv = cuota.fecha_vencimiento
        if not fv:
            continue
        delta = (fv - hoy).days

        if delta == 5:
            dias_5.append(_item(cliente, cuota))
        elif delta == 3:
            dias_3.append(_item(cliente, cuota))
        elif delta == 1:
            dias_1.append(_item(cliente, cuota))
        elif delta == 0:
            hoy_list.append(_item(cliente, cuota))
        elif delta < 0:
            dias_atraso = -delta
            if dias_atraso >= 61:
                mora_61_cuotas.append(_item(cliente, cuota, dias_atraso=dias_atraso))

    # Ordenar mora_61 por dias_atraso desc, luego por cliente
    mora_61_cuotas.sort(key=lambda x: (-x["dias_atraso"], x["cedula"], x["numero_cuota"]))

    return {
        "actualizado_en": hoy.isoformat(),
        "dias_5": dias_5,
        "dias_3": dias_3,
        "dias_1": dias_1,
        "hoy": hoy_list,
        "mora_61": {
            "cuotas": mora_61_cuotas,
            "total_cuotas": len(mora_61_cuotas),
        },
    }


@router.post("/actualizar")
def actualizar_notificaciones(db: Session = Depends(get_db)):
    """
    Recalcular mora desde cuotas no pagadas. La tabla clientes no tiene columna dias_mora;
    los datos de mora se calculan al vuelo desde cuotas en get_clientes_retrasados.
    Llamar desde cron a las 2am (ej: 0 2 * * * curl -X POST .../notificaciones/actualizar).
    """
    hoy = date.today()
    q = select(Cuota).where(Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento <= hoy)
    cuotas = db.execute(q).scalars().all()
    # Solo contamos cuotas en mora; no actualizamos clientes.dias_mora (no existe en la BD)
    clientes_actualizados = 0
    return {"mensaje": "Actualización ejecutada.", "clientes_actualizados": clientes_actualizados}


def get_notificaciones_tabs_data(db: Session):
    """
    Datos para las pestañas de Notificaciones (previas, día pago, retrasadas, prejudicial).
    Cada item tiene forma para el frontend: nombre, cedula, correo, telefono, estado, etc.
    Incluye retraso 1/3/5 días y clientes con 3+ cuotas atrasadas (prejudicial).
    """
    from sqlalchemy import func

    hoy = date.today()
    q = (
        select(Cuota, Cliente)
        .join(Cliente, Cuota.cliente_id == Cliente.id)
        .where(Cuota.fecha_pago.is_(None))
    )
    rows = db.execute(q).all()

    dias_5: List[dict] = []
    dias_3: List[dict] = []
    dias_1: List[dict] = []
    hoy_list: List[dict] = []
    dias_1_retraso: List[dict] = []
    dias_3_retraso: List[dict] = []
    dias_5_retraso: List[dict] = []
    mora_61_cuotas: List[dict] = []

    for (cuota, cliente) in rows:
        fv = cuota.fecha_vencimiento
        if not fv:
            continue
        delta = (fv - hoy).days

        if delta == 5:
            dias_5.append(_item_tab(cliente, cuota, dias_antes=5))
        elif delta == 3:
            dias_3.append(_item_tab(cliente, cuota, dias_antes=3))
        elif delta == 1:
            dias_1.append(_item_tab(cliente, cuota, dias_antes=1))
        elif delta == 0:
            hoy_list.append(_item_tab(cliente, cuota))
        elif delta < 0:
            dias_atraso = -delta
            if dias_atraso == 1:
                dias_1_retraso.append(_item_tab(cliente, cuota, dias_atraso=1))
            elif dias_atraso == 3:
                dias_3_retraso.append(_item_tab(cliente, cuota, dias_atraso=3))
            elif dias_atraso == 5:
                dias_5_retraso.append(_item_tab(cliente, cuota, dias_atraso=5))
            elif dias_atraso >= 61:
                mora_61_cuotas.append(_item_tab(cliente, cuota, dias_atraso=dias_atraso))

    mora_61_cuotas.sort(key=lambda x: (-x["dias_atraso"], x["cedula"], x["numero_cuota"]))

    # Prejudicial: clientes con 3 o más cuotas atrasadas (fecha_vencimiento < hoy, no pagado)
    prejudicial: List[dict] = []
    subq = (
        select(Cuota.cliente_id, func.count(Cuota.id).label("total"))
        .where(Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < hoy)
        .group_by(Cuota.cliente_id)
        .having(func.count(Cuota.id) >= 3)
    )
    clientes_prejudicial = db.execute(subq).all()
    for (cliente_id, total_cuotas) in clientes_prejudicial:
        cliente = db.get(Cliente, cliente_id)
        if not cliente:
            continue
        # Primera cuota atrasada para mostrar en la tarjeta
        primera = db.execute(
            select(Cuota)
            .where(Cuota.cliente_id == cliente_id, Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < hoy)
            .order_by(Cuota.fecha_vencimiento.asc())
            .limit(1)
        ).scalars().first()
        cuota_ref = primera
        if not cuota_ref:
            cuota_ref = type("DummyCuota", (), {"fecha_vencimiento": hoy, "numero_cuota": 0, "monto": 0})()
        item = _item_tab(cliente, cuota_ref)
        item["total_cuotas_atrasadas"] = total_cuotas
        prejudicial.append(item)

    return {
        "dias_5": dias_5,
        "dias_3": dias_3,
        "dias_1": dias_1,
        "hoy": hoy_list,
        "dias_1_retraso": dias_1_retraso,
        "dias_3_retraso": dias_3_retraso,
        "dias_5_retraso": dias_5_retraso,
        "mora_61": mora_61_cuotas,
        "prejudicial": prejudicial,
    }
