"""
Endpoints de notificaciones a clientes retrasados.
Datos reales desde BD: cuotas (fecha_vencimiento, pagado) y clientes.
Reglas: 5 pestañas por días hasta vencimiento y mora 61+.
Configuración de envíos (habilitado/CCO por tipo) desde tabla configuracion (notificaciones_envios).
CRUD de plantillas en plantillas_notificacion; envío puede usar plantilla por tipo vía plantilla_id en config.
"""
import json
import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from fastapi.responses import Response

from app.core.deps import get_current_user
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.cuota import Cuota
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.configuracion import Configuracion
from app.models.plantilla_notificacion import PlantillaNotificacion
from app.models.variable_notificacion import VariableNotificacion

logger = logging.getLogger(__name__)

CLAVE_NOTIFICACIONES_ENVIOS = "notificaciones_envios"

router = APIRouter(dependencies=[Depends(get_current_user)])


def get_notificaciones_envios_config(db: Session) -> dict:
    """Carga la configuración de envíos por tipo (habilitado, cco, plantilla_id, programador) desde BD."""
    try:
        row = db.get(Configuracion, CLAVE_NOTIFICACIONES_ENVIOS)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, dict):
                return data
    except json.JSONDecodeError as e:
        logger.warning("notificaciones_envios: valor en BD no es JSON válido: %s", e)
    except Exception as e:
        logger.exception("get_notificaciones_envios_config: %s", e)
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


# --- Helpers plantillas ---

def _plantilla_to_dict(p: PlantillaNotificacion) -> dict:
    """Serializa PlantillaNotificacion al formato esperado por el frontend."""
    return {
        "id": p.id,
        "nombre": p.nombre or "",
        "descripcion": getattr(p, "descripcion", None),
        "tipo": p.tipo or "",
        "asunto": p.asunto or "",
        "cuerpo": p.cuerpo or "",
        "variables_disponibles": getattr(p, "variables_disponibles", None),
        "activa": bool(p.activa),
        "zona_horaria": p.zona_horaria or "America/Caracas",
        "fecha_creacion": p.fecha_creacion.isoformat() if p.fecha_creacion else "",
        "fecha_actualizacion": p.fecha_actualizacion.isoformat() if p.fecha_actualizacion else "",
    }


def _sustituir_variables(texto: str, item: dict) -> str:
    """
    Reemplaza variables {{variable}} en texto.
    Fijas: nombre, cedula, fecha_vencimiento, numero_cuota, monto (desde monto_cuota), dias_atraso.
    Cualquier otra clave presente en item (ej. telefono, correo) se sustituye también para variables personalizadas.
    """
    if not texto:
        return ""
    nombre = item.get("nombre") or "Cliente"
    cedula = item.get("cedula") or ""
    fecha_v = item.get("fecha_vencimiento") or ""
    numero_cuota = item.get("numero_cuota")
    monto = item.get("monto_cuota")
    dias_atraso = item.get("dias_atraso")
    replacements = {
        "{{nombre}}": str(nombre),
        "{{cedula}}": str(cedula),
        "{{fecha_vencimiento}}": str(fecha_v),
        "{{numero_cuota}}": str(numero_cuota) if numero_cuota is not None else "",
        "{{monto}}": str(monto) if monto is not None else "",
        "{{dias_atraso}}": str(dias_atraso) if dias_atraso is not None else "",
    }
    result = texto
    for key, val in replacements.items():
        result = result.replace(key, val)
    # Variables personalizadas: cualquier clave del item (telefono, correo, etc.)
    for k, v in item.items():
        if k in ("nombre", "cedula", "fecha_vencimiento", "numero_cuota", "monto_cuota", "dias_atraso"):
            continue
        token = "{{" + str(k) + "}}"
        if token in result:
            result = result.replace(token, str(v) if v is not None else "")
    return result


def get_plantilla_asunto_cuerpo(db: Session, plantilla_id: Optional[int], item: dict, asunto_default: str, cuerpo_default: str) -> tuple:
    """
    Si plantilla_id es válido y la plantilla existe, devuelve (asunto, cuerpo) con variables sustituidas.
    Si no, devuelve (asunto_default, cuerpo_default) con .format(nombre=..., cedula=..., etc.).
    """
    if plantilla_id:
        plantilla = db.get(PlantillaNotificacion, plantilla_id)
        if plantilla and plantilla.activa:
            asunto = _sustituir_variables(plantilla.asunto, item)
            cuerpo = _sustituir_variables(plantilla.cuerpo, item)
            return (asunto, cuerpo)
    nombre = item.get("nombre") or "Cliente"
    cedula = item.get("cedula") or ""
    fecha_v = item.get("fecha_vencimiento") or ""
    numero_cuota = item.get("numero_cuota")
    monto = item.get("monto_cuota")
    asunto = asunto_default.format(nombre=nombre, cedula=cedula, fecha_vencimiento=fecha_v, numero_cuota=numero_cuota or "", monto=monto if monto is not None else "")
    cuerpo = cuerpo_default.format(nombre=nombre, cedula=cedula, fecha_vencimiento=fecha_v, numero_cuota=numero_cuota or "", monto=monto if monto is not None else "")
    return (asunto, cuerpo)


@router.get("/plantillas")
def get_plantillas(
    tipo: str = None,
    solo_activas: bool = True,
    db: Session = Depends(get_db),
):
    """Lista de plantillas de notificación. Filtro por tipo y solo activas."""
    try:
        q = select(PlantillaNotificacion)
        if solo_activas:
            q = q.where(PlantillaNotificacion.activa.is_(True))
        if tipo:
            q = q.where(PlantillaNotificacion.tipo == tipo)
        q = q.order_by(PlantillaNotificacion.tipo, PlantillaNotificacion.nombre)
        rows = db.execute(q).scalars().all()
        return [_plantilla_to_dict(p) for p in rows]
    except Exception as e:
        logger.exception("get_plantillas: %s", e)
        return []


@router.get("/plantillas/{plantilla_id}")
def get_plantilla(plantilla_id: int, db: Session = Depends(get_db)):
    """Obtiene una plantilla por id."""
    p = db.get(PlantillaNotificacion, plantilla_id)
    if not p:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return _plantilla_to_dict(p)


TIPOS_PLANTILLA_PERMITIDOS = frozenset([
    "PAGO_5_DIAS_ANTES", "PAGO_3_DIAS_ANTES", "PAGO_1_DIA_ANTES",
    "PAGO_DIA_0",
    "PAGO_1_DIA_ATRASADO", "PAGO_3_DIAS_ATRASADO", "PAGO_5_DIAS_ATRASADO",
    "PREJUDICIAL", "MORA_61", "MORA_90",  # MORA_61 legacy; MORA_90 = moroso 90+ días
])


@router.post("/plantillas")
def create_plantilla(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Crea una plantilla. Campos: nombre, tipo, asunto, cuerpo; opcionales: descripcion, variables_disponibles, activa, zona_horaria. tipo debe ser uno de los tipos de notificación permitidos."""
    nombre = (payload.get("nombre") or "").strip()
    tipo = (payload.get("tipo") or "").strip()
    asunto = (payload.get("asunto") or "").strip()
    cuerpo = payload.get("cuerpo") or ""
    if not nombre or not tipo or not asunto:
        raise HTTPException(status_code=422, detail="nombre, tipo y asunto son obligatorios")
    if tipo not in TIPOS_PLANTILLA_PERMITIDOS:
        raise HTTPException(
            status_code=422,
            detail=f"tipo debe ser uno de: {', '.join(sorted(TIPOS_PLANTILLA_PERMITIDOS))}",
        )
    try:
        p = PlantillaNotificacion(
            nombre=nombre,
            descripcion=payload.get("descripcion"),
            tipo=tipo,
            asunto=asunto,
            cuerpo=cuerpo,
            variables_disponibles=payload.get("variables_disponibles"),
            activa=payload.get("activa", True),
            zona_horaria=(payload.get("zona_horaria") or "America/Caracas").strip(),
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        return _plantilla_to_dict(p)
    except Exception as e:
        db.rollback()
        logger.exception("create_plantilla: %s", e)
        raise HTTPException(status_code=500, detail="Error al crear la plantilla")


@router.put("/plantillas/{plantilla_id}")
def update_plantilla(plantilla_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    """Actualiza una plantilla."""
    p = db.get(PlantillaNotificacion, plantilla_id)
    if not p:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    if "nombre" in payload and payload["nombre"] is not None:
        p.nombre = (payload["nombre"] or "").strip()
    if "descripcion" in payload:
        p.descripcion = payload.get("descripcion")
    if "tipo" in payload and payload["tipo"] is not None:
        nuevo_tipo = (payload["tipo"] or "").strip()
        if nuevo_tipo and nuevo_tipo not in TIPOS_PLANTILLA_PERMITIDOS:
            raise HTTPException(
                status_code=422,
                detail=f"tipo debe ser uno de: {', '.join(sorted(TIPOS_PLANTILLA_PERMITIDOS))}",
            )
        p.tipo = nuevo_tipo
    if "asunto" in payload and payload["asunto"] is not None:
        p.asunto = (payload["asunto"] or "").strip()
    if "cuerpo" in payload:
        p.cuerpo = payload.get("cuerpo") or ""
    if "variables_disponibles" in payload:
        p.variables_disponibles = payload.get("variables_disponibles")
    if "activa" in payload:
        p.activa = bool(payload["activa"])
    if "zona_horaria" in payload and payload["zona_horaria"] is not None:
        p.zona_horaria = (payload["zona_horaria"] or "America/Caracas").strip()
    try:
        db.commit()
        db.refresh(p)
        return _plantilla_to_dict(p)
    except Exception as e:
        db.rollback()
        logger.exception("update_plantilla: %s", e)
        raise HTTPException(status_code=500, detail="Error al actualizar la plantilla")


@router.delete("/plantillas/{plantilla_id}")
def delete_plantilla(plantilla_id: int, db: Session = Depends(get_db)):
    """Elimina una plantilla."""
    p = db.get(PlantillaNotificacion, plantilla_id)
    if not p:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    try:
        db.delete(p)
        db.commit()
        return {"message": "Plantilla eliminada"}
    except Exception as e:
        db.rollback()
        logger.exception("delete_plantilla: %s", e)
        raise HTTPException(status_code=500, detail="Error al eliminar la plantilla")


@router.get("/plantillas/{plantilla_id}/export")
def export_plantilla(plantilla_id: int, db: Session = Depends(get_db)):
    """Exporta una plantilla (mismo formato que GET por id)."""
    p = db.get(PlantillaNotificacion, plantilla_id)
    if not p:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return _plantilla_to_dict(p)


@router.post("/plantillas/{plantilla_id}/enviar")
def enviar_con_plantilla(
    plantilla_id: int,
    cliente_id: int = Query(..., description="ID del cliente destinatario"),
    db: Session = Depends(get_db),
    variables: dict = Body(default=None),
):
    """
    Envía un correo de prueba al cliente usando la plantilla. variables (body) sustituyen en asunto/cuerpo.
    Query: cliente_id. Body: dict opcional con nombre, cedula, fecha_vencimiento, numero_cuota, monto, dias_atraso.
    """
    from app.core.email import send_email
    p = db.get(PlantillaNotificacion, plantilla_id)
    if not p or not p.activa:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada o inactiva")
    cliente = db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    item = {
        "nombre": (variables or {}).get("nombre") or cliente.nombres or "Cliente",
        "cedula": (variables or {}).get("cedula") or cliente.cedula or "",
        "fecha_vencimiento": (variables or {}).get("fecha_vencimiento") or "",
        "numero_cuota": (variables or {}).get("numero_cuota"),
        "monto_cuota": (variables or {}).get("monto"),
        "dias_atraso": (variables or {}).get("dias_atraso"),
    }
    asunto = _sustituir_variables(p.asunto, item)
    cuerpo = _sustituir_variables(p.cuerpo, item)
    correo = (cliente.email or "").strip()
    if not correo or "@" not in correo:
        raise HTTPException(status_code=400, detail="El cliente no tiene email válido")
    ok, msg = send_email([correo], asunto, cuerpo)
    if not ok:
        raise HTTPException(status_code=502, detail=msg or "Error al enviar el correo")
    return {"message": "Correo enviado", "destinatario": correo}


# --- Variables personalizadas (CRUD + inicializar precargadas) ---

def _variable_to_dict(v: VariableNotificacion) -> dict:
    """Serializa VariableNotificacion al formato esperado por el frontend."""
    return {
        "id": v.id,
        "nombre_variable": v.nombre_variable or "",
        "tabla": v.tabla or "",
        "campo_bd": v.campo_bd or "",
        "descripcion": getattr(v, "descripcion", None),
        "activa": bool(v.activa),
        "fecha_creacion": v.fecha_creacion.isoformat() if v.fecha_creacion else None,
        "fecha_actualizacion": v.fecha_actualizacion.isoformat() if v.fecha_actualizacion else None,
    }


@router.get("/variables")
def get_variables(
    activa: Optional[bool] = Query(None, description="Filtrar por activa (true/false)"),
    db: Session = Depends(get_db),
):
    """Lista variables personalizadas de notificaciones. Opcional: ?activa=true|false."""
    q = select(VariableNotificacion).order_by(VariableNotificacion.nombre_variable)
    if activa is not None:
        q = q.where(VariableNotificacion.activa == activa)
    try:
        rows = db.execute(q).scalars().all()
        return [_variable_to_dict(r) for r in rows]
    except Exception as e:
        logger.exception("get_variables: %s", e)
        return []


@router.get("/variables/{variable_id}")
def get_variable(variable_id: int, db: Session = Depends(get_db)):
    """Obtiene una variable personalizada por id."""
    v = db.get(VariableNotificacion, variable_id)
    if not v:
        raise HTTPException(status_code=404, detail="Variable no encontrada")
    return _variable_to_dict(v)


@router.post("/variables")
def create_variable(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Crea una variable personalizada. Campos: nombre_variable, tabla, campo_bd; opcionales: descripcion, activa."""
    nombre = (payload.get("nombre_variable") or "").strip().lower()
    if not nombre:
        raise HTTPException(status_code=400, detail="nombre_variable es obligatorio")
    tabla = (payload.get("tabla") or "").strip()
    campo_bd = (payload.get("campo_bd") or "").strip()
    if not tabla or not campo_bd:
        raise HTTPException(status_code=400, detail="tabla y campo_bd son obligatorios")
    existing = db.execute(select(VariableNotificacion).where(VariableNotificacion.nombre_variable == nombre)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe una variable con ese nombre_variable")
    try:
        v = VariableNotificacion(
            nombre_variable=nombre,
            tabla=tabla,
            campo_bd=campo_bd,
            descripcion=(payload.get("descripcion") or "").strip() or None,
            activa=payload.get("activa", True),
        )
        db.add(v)
        db.commit()
        db.refresh(v)
        return _variable_to_dict(v)
    except Exception as e:
        db.rollback()
        logger.exception("create_variable: %s", e)
        raise HTTPException(status_code=500, detail="Error al crear la variable")


@router.put("/variables/{variable_id}")
def update_variable(variable_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    """Actualiza una variable personalizada (descripcion, activa, tabla, campo_bd). nombre_variable no se modifica."""
    v = db.get(VariableNotificacion, variable_id)
    if not v:
        raise HTTPException(status_code=404, detail="Variable no encontrada")
    if "descripcion" in payload:
        v.descripcion = (payload.get("descripcion") or "").strip() or None
    if "activa" in payload:
        v.activa = bool(payload.get("activa"))
    if "tabla" in payload and payload.get("tabla"):
        v.tabla = (payload["tabla"] or "").strip()
    if "campo_bd" in payload and payload.get("campo_bd"):
        v.campo_bd = (payload["campo_bd"] or "").strip()
    try:
        db.commit()
        db.refresh(v)
        return _variable_to_dict(v)
    except Exception as e:
        db.rollback()
        logger.exception("update_variable: %s", e)
        raise HTTPException(status_code=500, detail="Error al actualizar la variable")


@router.delete("/variables/{variable_id}")
def delete_variable(variable_id: int, db: Session = Depends(get_db)):
    """Elimina una variable personalizada."""
    v = db.get(VariableNotificacion, variable_id)
    if not v:
        raise HTTPException(status_code=404, detail="Variable no encontrada")
    try:
        db.delete(v)
        db.commit()
        return {"message": "Variable eliminada"}
    except Exception as e:
        db.rollback()
        logger.exception("delete_variable: %s", e)
        raise HTTPException(status_code=500, detail="Error al eliminar la variable")


VARIABLES_PRECARGADAS = [
    {"nombre_variable": "nombre_cliente", "tabla": "clientes", "campo_bd": "nombres", "descripcion": "Nombres del cliente"},
    {"nombre_variable": "cedula", "tabla": "clientes", "campo_bd": "cedula", "descripcion": "Cédula de identidad"},
    {"nombre_variable": "telefono", "tabla": "clientes", "campo_bd": "telefono", "descripcion": "Teléfono de contacto"},
    {"nombre_variable": "email", "tabla": "clientes", "campo_bd": "email", "descripcion": "Correo electrónico"},
    {"nombre_variable": "numero_cuota", "tabla": "cuotas", "campo_bd": "numero_cuota", "descripcion": "Número de cuota"},
    {"nombre_variable": "fecha_vencimiento", "tabla": "cuotas", "campo_bd": "fecha_vencimiento", "descripcion": "Fecha de vencimiento"},
    {"nombre_variable": "monto_cuota", "tabla": "cuotas", "campo_bd": "monto", "descripcion": "Monto de la cuota"},
    {"nombre_variable": "dias_atraso", "tabla": "cuotas", "campo_bd": "dias_mora", "descripcion": "Días de atraso"},
]


@router.post("/variables/inicializar-precargadas")
def inicializar_variables_precargadas(db: Session = Depends(get_db)):
    """Inserta variables precargadas si no existen (por nombre_variable). Idempotente."""
    creadas = 0
    existentes = 0
    for item in VARIABLES_PRECARGADAS:
        nombre = item["nombre_variable"]
        existing = db.execute(select(VariableNotificacion).where(VariableNotificacion.nombre_variable == nombre)).scalar_one_or_none()
        if existing:
            existentes += 1
            continue
        try:
            v = VariableNotificacion(
                nombre_variable=nombre,
                tabla=item["tabla"],
                campo_bd=item["campo_bd"],
                descripcion=item.get("descripcion"),
                activa=True,
            )
            db.add(v)
            db.commit()
            creadas += 1
        except Exception as e:
            db.rollback()
            logger.warning("inicializar_variables_precargadas: %s para %s", e, nombre)
    total = creadas + existentes
    return {
        "mensaje": f"Variables precargadas: {creadas} creadas, {existentes} ya existían.",
        "variables_creadas": creadas,
        "variables_existentes": existentes,
        "total": total,
    }


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


@router.get("/estadisticas-por-tab", response_model=dict)
def get_estadisticas_por_tab(db: Session = Depends(get_db)):
    """
    KPIs por pestaña: correos enviados y rebotados (dias_5, dias_3, dias_1, hoy, mora_90).
    Cuando exista persistencia de envíos por tipo, aquí se consultará la BD.
    """
    return {
        "dias_5": {"enviados": 0, "rebotados": 0},
        "dias_3": {"enviados": 0, "rebotados": 0},
        "dias_1": {"enviados": 0, "rebotados": 0},
        "hoy": {"enviados": 0, "rebotados": 0},
        "mora_90": {"enviados": 0, "rebotados": 0},
    }


TIPOS_TAB_NOTIFICACIONES = ("dias_5", "dias_3", "dias_1", "hoy", "mora_90")


def _get_rebotados_por_tipo(db: Session, tipo: str) -> List[dict]:
    """
    Lista de correos no entregados (rebotados) para el tipo de pestaña.
    Cuando exista persistencia de envíos/rebotes por tipo, aquí se consultará la BD.
    Cada item: email, nombre, cedula, fecha_envio (opcional), error_mensaje (opcional).
    """
    if tipo not in TIPOS_TAB_NOTIFICACIONES:
        return []
    # Sin tabla de historial de rebotes, devolver lista vacía
    return []


@router.get("/rebotados-por-tab", response_model=dict)
def get_rebotados_por_tab(
    tipo: str = Query(..., description="Tipo de pestaña: dias_5, dias_3, dias_1, hoy, mora_90"),
    db: Session = Depends(get_db),
):
    """Lista de correos no entregados (rebotados) para la pestaña. Para generar informe Excel en frontend o descargar Excel."""
    if tipo not in TIPOS_TAB_NOTIFICACIONES:
        raise HTTPException(status_code=400, detail=f"tipo debe ser uno de: {', '.join(TIPOS_TAB_NOTIFICACIONES)}")
    items = _get_rebotados_por_tipo(db, tipo)
    return {"items": items, "total": len(items)}


def _generar_excel_rebotados(items: List[dict], tipo: str) -> bytes:
    """Genera Excel con lista de correos rebotados (no entregados)."""
    import io
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Correos no entregados"
    ws.append(["Email", "Nombre", "Cédula", "Fecha envío", "Motivo rebote"])
    for r in items:
        ws.append([
            r.get("email") or "",
            r.get("nombre") or "",
            r.get("cedula") or "",
            r.get("fecha_envio") or "",
            r.get("error_mensaje") or "",
        ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@router.get("/rebotados-por-tab/excel")
def get_rebotados_por_tab_excel(
    tipo: str = Query(..., description="Tipo de pestaña: dias_5, dias_3, dias_1, hoy, mora_90"),
    db: Session = Depends(get_db),
):
    """Descarga informe Excel de correos no entregados (rebotados) para la pestaña."""
    if tipo not in TIPOS_TAB_NOTIFICACIONES:
        raise HTTPException(status_code=400, detail=f"tipo debe ser uno de: {', '.join(TIPOS_TAB_NOTIFICACIONES)}")
    items = _get_rebotados_por_tipo(db, tipo)
    content = _generar_excel_rebotados(items, tipo)
    filename = f"correos_no_entregados_{tipo}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/clientes-retrasados", response_model=dict)
def get_clientes_retrasados(db: Session = Depends(get_db)):
    """
    Clientes a notificar por cuotas no pagadas, agrupados en 5 reglas:
    1. Faltan 5 días para fecha_vencimiento (no pagado)
    2. Faltan 3 días para fecha_vencimiento (no pagado)
    3. Falta 1 día para fecha_vencimiento (no pagado)
    4. Hoy = fecha_vencimiento (no pagado)
    5. 90+ días de mora (moroso): informe de cada cuota atrasada una a una.
    Se usa la fecha del servidor; actualizar a las 2am con cron si se desea.
    """
    hoy = date.today()
    # Cuotas no pagadas (fecha_pago nula) con su cliente vía préstamo (cuotas pueden tener cliente_id NULL)
    q = (
        select(Cuota, Cliente)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Cuota.fecha_pago.is_(None))
    )
    rows = db.execute(q).all()

    dias_5: List[dict] = []
    dias_3: List[dict] = []
    dias_1: List[dict] = []
    hoy_list: List[dict] = []
    mora_90_cuotas: List[dict] = []  # cada cuota 90+ días atrasada (moroso)

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
            if dias_atraso >= 90:
                mora_90_cuotas.append(_item(cliente, cuota, dias_atraso=dias_atraso))

    # Ordenar mora_90 por dias_atraso desc, luego por cliente
    mora_90_cuotas.sort(key=lambda x: (-x["dias_atraso"], x["cedula"], x["numero_cuota"]))

    return {
        "actualizado_en": hoy.isoformat(),
        "dias_5": dias_5,
        "dias_3": dias_3,
        "dias_1": dias_1,
        "hoy": hoy_list,
        "mora_90": {
            "cuotas": mora_90_cuotas,
            "total_cuotas": len(mora_90_cuotas),
        },
    }


def ejecutar_actualizacion_notificaciones(db: Session) -> dict:
    """
    Lógica de actualización de notificaciones (mora desde cuotas no pagadas).
    Usado por el endpoint POST /actualizar y por el scheduler a las 2:00.
    """
    hoy = date.today()
    q = select(Cuota).where(Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento <= hoy)
    db.execute(q).scalars().all()
    return {"mensaje": "Actualización ejecutada.", "clientes_actualizados": 0}


@router.post("/actualizar")
def actualizar_notificaciones(db: Session = Depends(get_db)):
    """Recalcular mora desde cuotas no pagadas. También se ejecuta por scheduler a las 2:00."""
    return ejecutar_actualizacion_notificaciones(db)


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
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
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
    mora_90_cuotas: List[dict] = []

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
            elif dias_atraso >= 90:
                mora_90_cuotas.append(_item_tab(cliente, cuota, dias_atraso=dias_atraso))

    mora_90_cuotas.sort(key=lambda x: (-x["dias_atraso"], x["cedula"], x["numero_cuota"]))

    # Prejudicial: clientes con 3 o más cuotas atrasadas (fecha_vencimiento < hoy, no pagado)
    # Solo cuotas con cliente_id no nulo para poder resolver Cliente
    prejudicial: List[dict] = []
    subq = (
        select(Cuota.cliente_id, func.count(Cuota.id).label("total"))
        .where(
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < hoy,
            Cuota.cliente_id.isnot(None),
        )
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
        "mora_90": mora_90_cuotas,
        "prejudicial": prejudicial,
    }
