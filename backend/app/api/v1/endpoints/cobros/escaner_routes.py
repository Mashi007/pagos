"""Endpoints HTTP cobros: escaner Infopagos."""
"""
Endpoints de administración del módulo Cobros (requieren autenticación).
Listado de pagos reportados, detalle, aprobar, rechazar, histórico por cédula.
"""
import io
import logging
import base64
import hashlib
import json
import re
import threading
import time
from collections import Counter, defaultdict
from datetime import date, datetime, time as dt_time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Optional, List, Tuple, Any, Dict, Iterable, Set

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, and_, case, delete, text, update
from sqlalchemy.exc import ProgrammingError, OperationalError, IntegrityError

from app.core.database import get_db
from app.core.documento import normalize_documento
from app.core.deps import get_current_user
from app.services.cobros import infopagos_escaner_borrador_service as ieb
from app.services.cobros import digitalizacion_revision_manual as drm
from app.core.rate_limit_store import get_redis_client
from app.api.v1.endpoints.pagos.pago_integridad_db import _integridad_error_pgcode_y_constraint
from app.models.pago_reportado import PagoReportado, PagoReportadoHistorial
from app.models.pago_reportado_exportado import PagoReportadoExportado
from app.models.pago_pendiente_descargar import PagoPendienteDescargar
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.services.cobros.recibo_pdf import WHATSAPP_LINK, WHATSAPP_DISPLAY
from app.services.documentos_cliente_centro import generar_recibo_pdf_desde_pago_reportado
from app.core.email import cobros_recibo_attachments_or_oversize_note, send_email
from app.utils.cliente_emails import emails_destino_desde_objeto, unir_destinatarios_log
from app.services.notificaciones_exclusion_desistimiento import (
    cliente_bloqueado_por_desistimiento,
)
from app.core.email_config_holder import get_email_activo_servicio
from app.api.v1.endpoints.validadores import validate_cedula
from app.api.v1.endpoints.pagos import _aplicar_pago_a_cuotas_interno
from app.services.cobros.pago_reportado_documento import (
    claves_documento_pago_para_reportado,
    documento_numero_desde_pago_reportado,
    pago_reportado_colisiona_tabla_pagos,
    primer_pago_id_si_existe_para_claves_reportado,
    primer_reportado_id_por_norm_batch,
    primer_reportado_id_por_norm_peer_first_map,
    reportado_toca_claves_canonicas_en_pagos,
)
from app.services.cobros.cedula_reportar_bs_service import (
    load_autorizados_bs_claves,
    cedula_coincide_autorizados_bs,
    fuente_tasa_bs_efectiva_para_cedula,
)
from app.services.tasa_cambio_service import (
    convertir_bs_a_usd,
    normalizar_fuente_tasa,
    obtener_tasa_por_fecha,
    obtener_tasas_por_fechas,
    tasa_y_equivalente_usd_excel,
    valor_tasa_para_fuente,
)
from app.services.pagos_gmail.gemini_async import (
    compare_form_with_image_async,
    extract_infopagos_campos_desde_comprobante_async,
    extract_infopagos_campos_desde_comprobante_con_rescate_plantilla_async,
)
from app.services.pagos_gmail.gemini_service import (
    _canonical_institucion_escaner,
    compare_form_with_image,
)
from app.services.pagos.comprobante_adjunto_pago import comprobante_blob_para_pdf_desde_pago
from app.services.cobros import cobros_publico_reporte_service as cpr
from app.utils.cedula_almacenamiento import expr_cedula_normalizada_para_comparar
from app.services.pagos_gmail.comprobante_bd import url_comprobante_imagen_absoluta
from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials
from app.services.pagos_gmail.drive_service import build_drive_service
from app.services.pago_huella_funcional import conflicto_huella_para_creacion
from app.services.cobros.pago_reportado_comprobante_unico import (
    comprobante_bytes_y_content_type_desde_reportado,
    nombre_adjunto_email_desde_reportado,
)

logger = logging.getLogger(__name__)
from .listado_kpis_cache import _enforce_escaner_rate_limit, _invalidate_cobros_listado_kpis_cache
from .reportados_listado_payload import _reencolar_escaner_infopagos_aprobado_sin_gestion_por_cedula

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.post("/escaner/extraer-comprobante")
async def escaner_extraer_comprobante_infopagos(
    request: Request,
    db: Session = Depends(get_db),
    tipo_cedula: str = Form(...),
    numero_cedula: str = Form(...),
    comprobante: UploadFile = File(...),
    fuente_tasa_cambio: str = Form("euro"),
    institucion_plantilla: str = Form(""),
    extraccion_sin_cliente: str = Form(""),
    prestamo_objetivo_id: str = Form(""),
):
    """
    Personal autenticado: sugiere campos del formulario Infopagos leyendo el comprobante con Gemini.
    Orden de uso: cédula del deudor + archivo. No guarda el reporte en `pagos_reportados`.
    Si fallan validadores (o hay duplicado en cartera), persiste borrador en `infopagos_escaner_borrador`
    con el comprobante para editar / eliminar / guardar luego; si todo pasa, no crea borrador.
    Opcional: `institucion_plantilla` (ej. Mercantil, BNC) añade al prompt pautas típicas del banco
    sin sustituir lo visible en la imagen (re-escaneo lote Infopagos).

    `extraccion_sin_cliente` (multipart, ej. "true"): solo personal autenticado; la cédula del formulario
    debe seguir siendo sintácticamente válida (placeholder), pero no se exige que exista en BD ni
    préstamo APROBADO único. Sirve para re-escanear comprobantes en revisión manual / finiquitos
    (varios créditos activos, LIQUIDADO, cédula pendiente, etc.).

    `prestamo_objetivo_id` (opcional): préstamo en contexto al re-escanear cartera en revisión;
    mejora metadatos de duplicado cuando `extraccion_sin_cliente=true`.
    """
    _enforce_escaner_rate_limit(request)

    sin_cliente = (extraccion_sin_cliente or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    cedula_input = f"{(tipo_cedula or '').strip()}{(numero_cedula or '').strip()}"
    val = validate_cedula(cedula_input)
    if not val.get("valido"):
        raise HTTPException(status_code=400, detail=val.get("error", "Cédula inválida."))

    cedula_lookup = (val.get("valor_formateado") or "").replace("-", "")
    if not cedula_lookup:
        raise HTTPException(status_code=400, detail="Formato de cédula no reconocido.")

    cliente = None
    prestamos_aprob: list = []

    if not sin_cliente:
        cliente = db.execute(
            select(Cliente).where(
                expr_cedula_normalizada_para_comparar(Cliente.cedula) == cedula_lookup
            )
        ).scalars().first()
        if not cliente:
            raise HTTPException(status_code=400, detail="La cédula no está registrada.")

        prestamos_aprob = cpr.prestamos_aprobados_del_cliente(db, cliente.id)
        err_pres = cpr.error_si_no_puede_reportar_en_web(prestamos_aprob)
        if err_pres:
            raise HTTPException(status_code=400, detail=err_pres)

    prestamo_objetivo_id_ctx: Optional[int] = None
    _raw_prest_obj = (prestamo_objetivo_id or "").strip()
    if _raw_prest_obj:
        try:
            _pid_obj = int(_raw_prest_obj)
            if _pid_obj > 0:
                prestamo_objetivo_id_ctx = _pid_obj
        except (TypeError, ValueError):
            prestamo_objetivo_id_ctx = None
    if prestamo_objetivo_id_ctx is None and len(prestamos_aprob) == 1:
        prestamo_objetivo_id_ctx = int(prestamos_aprob[0])

    content = await comprobante.read()
    fn_comp = comprobante.filename or "comprobante"
    ctype = cpr.mime_efectivo_comprobante_web(comprobante.content_type or "", fn_comp)
    err_file, content, filename, ctype = cpr.preparar_adjunto_comprobante_para_vision(
        content,
        ctype,
        fn_comp,
        mensaje_excel_largo=False,
    )
    if err_file:
        raise HTTPException(status_code=400, detail=err_file)

    tipo = (tipo_cedula or "").strip().upper()[:2]
    numero = (numero_cedula or "").strip()
    ctx_ced = f"{tipo}{numero}".replace("-", "")
    current_user = getattr(request.state, "user", None)
    usuario_escaner_id: Optional[int] = None
    if current_user is not None and getattr(current_user, "id", None) is not None:
        try:
            usuario_escaner_id = int(current_user.id)
        except (TypeError, ValueError):
            usuario_escaner_id = None

    plantilla = (institucion_plantilla or "").strip() or None
    t_gemini0 = time.perf_counter()
    gem = await extract_infopagos_campos_desde_comprobante_con_rescate_plantilla_async(
        ctx_ced, content, filename, institucion_plantilla=plantilla
    )
    gemini_ms = int((time.perf_counter() - t_gemini0) * 1000)
    if not gem.get("ok"):
        _base_escaner = (
            "Gemini no pudo digitalizar el comprobante con consistencia. "
            "Pase a revisión manual y complete/valide los campos antes de guardar."
        )
        _det = (str(gem.get("error") or "")).strip()
        # Mismo texto amigable; añadimos detalle del servicio (p. ej. JSON ilegible, API) — no es caché de Gmail.
        validacion_manual = (
            f"{_base_escaner} Detalle: {_det[:500]}" if _det else _base_escaner
        )
        borrador_id_fallo: Optional[str] = None
        if usuario_escaner_id is not None:
            try:
                payload_snap_fallo = {
                    "sugerencia": {
                        "fecha_pago": None,
                        "institucion_financiera": "",
                        "numero_operacion": "",
                        "monto": None,
                        "moneda": "BS",
                        "cedula_pagador_en_comprobante": "",
                        "notas_modelo": "",
                    },
                    "validacion_campos": None,
                    "validacion_reglas": validacion_manual,
                    "duplicado_en_pagos": False,
                    "pago_existente_id": None,
                    "prestamo_existente_id": None,
                    "prestamo_objetivo_id": prestamo_objetivo_id_ctx,
                    "motivo_digitalizacion": "gemini_no_digitaliza",
                }
                if cliente is not None:
                    borrador_id_fallo = ieb.crear_borrador_escaneo(
                        db,
                        cliente_id=int(cliente.id),
                        usuario_id=usuario_escaner_id,
                        tipo_cedula=tipo,
                        numero_cedula=numero,
                        cedula_normalizada=cedula_lookup,
                        fuente_tasa_cambio=fuente_tasa_cambio,
                        content=content,
                        ctype=ctype,
                        filename=filename,
                        payload=payload_snap_fallo,
                    )
                else:
                    borrador_id_fallo = None
                    logger.warning(
                        "[ESCANER] Gemini falló y extraccion_sin_cliente=True; no se persiste borrador sin cliente."
                    )
                if borrador_id_fallo:
                    db.commit()
                else:
                    db.rollback()
            except Exception as e:
                db.rollback()
                logger.exception("[ESCANER] fallo al guardar borrador por no digitalizar: %s", e)
        logger.info(
            "[ESCANER_TIMING] ok=False gemini_ms=%s bytes=%s filename=%r cedula_ctx=%s err=%s",
            gemini_ms,
            len(content) if content else 0,
            filename[:80] if filename else "",
            ctx_ced[:20],
            (str(gem.get("error") or "")[:120]),
        )
        return {
            "ok": False,
            "error": validacion_manual,
            "sugerencia": None,
            "validacion_campos": None,
            "validacion_reglas": validacion_manual,
            "borrador_id": borrador_id_fallo,
            "requiere_revision_manual": True,
        }

    fecha_d = gem.get("fecha_pago")
    fecha_iso = fecha_d.isoformat() if isinstance(fecha_d, date) else None
    monto = gem.get("monto")
    inst = gem.get("institucion_financiera") or ""
    num_op = gem.get("numero_operacion") or ""
    moneda = gem.get("moneda") or "BS"

    validacion_campos = None
    validacion_reglas = None
    mon_norm = None

    if monto is not None and inst.strip() and num_op.strip():
        err_campos, mon_norm = cpr.normalizar_y_validar_campos_formulario(
            tipo_cedula=tipo,
            numero_cedula=numero,
            institucion_financiera=inst,
            numero_operacion=num_op,
            monto=float(monto),
            moneda=moneda,
            observacion=None,
        )
        validacion_campos = err_campos
        if not err_campos and isinstance(fecha_d, date):
            err_reglas = cpr.validar_reglas_bs_tasa_monto_fecha(
                db,
                cedula_lookup=cedula_lookup,
                fecha_pago=fecha_d,
                monto=float(monto),
                mon=mon_norm,
                fuente_tasa_cambio=fuente_tasa_cambio,
            )
            validacion_reglas = err_reglas
        elif not err_campos and not isinstance(fecha_d, date):
            validacion_reglas = "Indique la fecha de pago (no se detectó con claridad en la imagen)."
    elif monto is None:
        validacion_reglas = "Complete el monto (no se detectó con claridad en la imagen)."
    elif not inst.strip():
        validacion_reglas = "Complete la institución financiera."
    elif not num_op.strip():
        validacion_reglas = "Complete el número de operación o referencia."

    validacion_reglas = cpr.fusionar_validacion_reglas_monto_alto_escaneo(
        validacion_reglas, monto, moneda=moneda
    )

    msg_rev = drm.digitalizacion_requiere_revision_manual(
        fecha_pago=fecha_d,
        institucion_financiera=inst,
        numero_operacion=num_op,
        monto=monto,
        notas_modelo=gem.get("notas") or "",
    )
    requiere_revision_manual = bool(msg_rev)
    if msg_rev:
        validacion_reglas = drm.fusionar_mensaje_revision(validacion_reglas, msg_rev)

    sugerencia = {
        "fecha_pago": fecha_iso,
        "institucion_financiera": inst,
        "numero_operacion": num_op,
        "monto": monto,
        "moneda": moneda if moneda in ("BS", "USD") else "BS",
        "cedula_pagador_en_comprobante": gem.get("cedula_pagador_en_comprobante") or "",
        "notas_modelo": gem.get("notas") or "",
    }

    # Misma colisión que detalle Cobros: documento ya en cartera + préstamo del pago existente / objetivo.
    duplicado_en_pagos = False
    pago_existente_id: Optional[int] = None
    prestamo_existente_id: Optional[int] = None
    t_post0 = time.perf_counter()
    num_op_trim = (num_op or "").strip()
    if num_op_trim:
        pr_scan = SimpleNamespace(
            numero_operacion=num_op_trim[:100],
            referencia_interna="",
        )
        duplicado_en_pagos = pago_reportado_colisiona_tabla_pagos(db, pr_scan)
        if duplicado_en_pagos:
            pago_existente_id = primer_pago_id_si_existe_para_claves_reportado(db, pr_scan)
            if pago_existente_id is not None:
                p_exist = db.execute(select(Pago).where(Pago.id == pago_existente_id)).scalars().first()
                if p_exist is not None:
                    prestamo_existente_id = getattr(p_exist, "prestamo_id", None)
    post_gemini_ms = int((time.perf_counter() - t_post0) * 1000)

    logger.info(
        "[ESCANER_TIMING] ok=True gemini_ms=%s post_gemini_ms=%s bytes=%s filename=%r dup=%s",
        gemini_ms,
        post_gemini_ms,
        len(content) if content else 0,
        filename[:80] if filename else "",
        duplicado_en_pagos,
    )

    borrador_id: Optional[str] = None
    necesita_borrador_bd = ieb.debe_persistir_borrador_escaneo(
        validacion_campos=validacion_campos,
        validacion_reglas=validacion_reglas,
        duplicado_en_pagos=duplicado_en_pagos,
    ) or requiere_revision_manual
    if necesita_borrador_bd and usuario_escaner_id is not None and cliente is not None:
        try:
            payload_snap = {
                "sugerencia": sugerencia,
                "validacion_campos": validacion_campos,
                "validacion_reglas": validacion_reglas,
                "duplicado_en_pagos": duplicado_en_pagos,
                "pago_existente_id": pago_existente_id,
                "prestamo_existente_id": prestamo_existente_id,
                "prestamo_objetivo_id": prestamo_objetivo_id_ctx,
                "motivo_digitalizacion": (
                    "campos_criticos_incompletos" if requiere_revision_manual else None
                ),
                "requiere_revision_manual": requiere_revision_manual,
            }
            borrador_id = ieb.crear_borrador_escaneo(
                db,
                cliente_id=int(cliente.id),
                usuario_id=usuario_escaner_id,
                tipo_cedula=tipo,
                numero_cedula=numero,
                cedula_normalizada=cedula_lookup,
                fuente_tasa_cambio=fuente_tasa_cambio,
                content=content,
                ctype=ctype,
                filename=filename,
                payload=payload_snap,
            )
            if borrador_id:
                db.commit()
            else:
                db.rollback()
                logger.warning(
                    "[ESCANER] validación con pendientes pero no se pudo persistir borrador cedula=%s",
                    cedula_lookup[:12],
                )
        except Exception as e:
            db.rollback()
            logger.exception("[ESCANER] fallo al guardar borrador temporal: %s", e)
    elif necesita_borrador_bd and usuario_escaner_id is None:
        logger.warning(
            "[ESCANER] validación con pendientes pero sin usuario en sesión; no se persiste borrador cedula=%s",
            cedula_lookup[:12],
        )
    elif necesita_borrador_bd and cliente is None:
        logger.warning(
            "[ESCANER] validación con pendientes y extraccion_sin_cliente; no se persiste borrador sin cliente cedula_ctx=%s",
            cedula_lookup[:12],
        )

    return {
        "ok": True,
        "error": None,
        "sugerencia": sugerencia,
        "validacion_campos": validacion_campos,
        "validacion_reglas": validacion_reglas,
        "duplicado_en_pagos": duplicado_en_pagos,
        "pago_existente_id": pago_existente_id,
        "prestamo_existente_id": prestamo_existente_id,
        "prestamo_objetivo_id": prestamo_objetivo_id_ctx,
        "borrador_id": borrador_id,
        "requiere_revision_manual": requiere_revision_manual,
    }


@router.get("/escaner/borradores")
def listar_infopagos_borradores_escaner(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Query(30, ge=1, le=100),
):
    """Borradores temporales del escáner (solo filas con validación pendiente), del usuario actual."""
    cur = getattr(request.state, "user", None)
    if cur is None or getattr(cur, "id", None) is None:
        raise HTTPException(status_code=401, detail="No autenticado.")
    uid = int(cur.id)
    items = ieb.listar_borradores_pendientes_usuario(db, usuario_id=uid, limit=limit)
    return {"ok": True, "items": items}


@router.get("/escaner/borrador/{borrador_id}")
def obtener_infopagos_borrador_escaner(
    request: Request,
    borrador_id: str,
    db: Session = Depends(get_db),
):
    """Detalle de un borrador para continuar editando en el escáner."""
    cur = getattr(request.state, "user", None)
    if cur is None or getattr(cur, "id", None) is None:
        raise HTTPException(status_code=401, detail="No autenticado.")
    uid = int(cur.id)
    data, err = ieb.obtener_borrador_para_edicion(db, borrador_id=borrador_id, usuario_id=uid)
    if err or not data:
        raise HTTPException(status_code=404, detail=err or "Borrador no encontrado.")
    return {"ok": True, "borrador": data}


@router.delete("/escaner/borrador/{borrador_id}")
def eliminar_infopagos_borrador_escaner(
    request: Request,
    borrador_id: str,
    db: Session = Depends(get_db),
):
    """Elimina un borrador temporal y el comprobante huérfano si no se usa en otro lado."""
    cur = getattr(request.state, "user", None)
    if cur is None or getattr(cur, "id", None) is None:
        raise HTTPException(status_code=401, detail="No autenticado.")
    uid = int(cur.id)
    ok_del, err_del = ieb.eliminar_borrador_escaneo(db, borrador_id=borrador_id, usuario_id=uid)
    if not ok_del:
        raise HTTPException(status_code=400, detail=err_del or "No se pudo eliminar.")
    return {"ok": True}


@router.get("/escaner/borrador/{borrador_id}/comprobante")
def descargar_comprobante_infopagos_borrador_escaner(
    request: Request,
    borrador_id: str,
    db: Session = Depends(get_db),
):
    """Binario del comprobante guardado en el borrador (misma auth que lista/detalle)."""
    cur = getattr(request.state, "user", None)
    if cur is None or getattr(cur, "id", None) is None:
        raise HTTPException(status_code=401, detail="No autenticado.")
    uid = int(cur.id)
    data, ctype, _fn, err = ieb.bytes_comprobante_borrador_escaneo_para_owner(
        db,
        borrador_id=borrador_id,
        usuario_id=uid,
    )
    if err or data is None or ctype is None:
        raise HTTPException(status_code=404, detail=err or "No disponible.")
    return Response(content=data, media_type=ctype)


def _extraer_folder_id_drive(raw: str) -> str:
    txt = (raw or "").strip()
    if not txt:
        return ""
    m = re.search(r"/folders/([a-zA-Z0-9_-]{10,})", txt)
    if m:
        return m.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]{10,}", txt):
        return txt
    return ""


@router.get("/escaner/lote/contexto-revision")
def escaner_lote_contexto_revision(
    db: Session = Depends(get_db),
    ids: str = Query(..., description="IDs de pagos en revisión, separados por coma (máx. 10)"),
):
    """
    Precarga escáner lote desde /pagos (revisión): comprobante en BD + metadatos del pago.
    No llama a Gemini; la digitalización sigue en el cliente vía /escaner/extraer-comprobante.
    """
    raw_ids = [x.strip() for x in (ids or "").split(",") if x.strip()]
    pago_ids: list[int] = []
    for x in raw_ids[:10]:
        try:
            pago_ids.append(int(x))
        except (TypeError, ValueError):
            continue
    if not pago_ids:
        raise HTTPException(status_code=400, detail="Indique al menos un ID de pago válido.")

    pagos = (
        db.execute(select(Pago).where(Pago.id.in_(pago_ids))).scalars().all()
    )
    by_id = {int(p.id): p for p in pagos if p is not None}
    items: list[dict] = []
    cedulas: set[str] = set()

    for pid in pago_ids:
        p = by_id.get(pid)
        if not p:
            items.append(
                {
                    "pago_id": pid,
                    "ok": False,
                    "error": "Pago no encontrado.",
                }
            )
            continue
        ced = (getattr(p, "cedula_cliente", None) or "").strip()
        if ced:
            cedulas.add(ced.replace("-", ""))
        blob, ctype, nombre = comprobante_blob_para_pdf_desde_pago(db, p)
        if not blob:
            items.append(
                {
                    "pago_id": pid,
                    "ok": False,
                    "error": "Sin comprobante en BD para este pago.",
                    "cedula": ced,
                    "prestamo_id": getattr(p, "prestamo_id", None),
                    "numero_documento": (getattr(p, "numero_documento", None) or "").strip(),
                    "fecha_pago": (
                        p.fecha_pago.date().isoformat()
                        if getattr(p, "fecha_pago", None)
                        else None
                    ),
                    "monto_usd": float(p.monto_pagado) if p.monto_pagado is not None else None,
                    "institucion_bancaria": (
                        _canonical_institucion_escaner(
                            (getattr(p, "institucion_bancaria", None) or "").strip()
                        )
                        or (getattr(p, "institucion_bancaria", None) or "").strip()
                    ),
                }
            )
            continue
        fn = (nombre or f"comprobante_pago_{pid}.jpg").strip()
        inst = (getattr(p, "institucion_bancaria", None) or "").strip()
        inst_canon = _canonical_institucion_escaner(inst) or inst
        items.append(
            {
                "pago_id": pid,
                "ok": True,
                "error": None,
                "cedula": ced,
                "prestamo_id": getattr(p, "prestamo_id", None),
                "numero_documento": (getattr(p, "numero_documento", None) or "").strip(),
                "fecha_pago": (
                    p.fecha_pago.date().isoformat()
                    if getattr(p, "fecha_pago", None)
                    else None
                ),
                "monto_usd": float(p.monto_pagado) if p.monto_pagado is not None else None,
                "institucion_bancaria": inst_canon,
                "nombre_archivo": fn,
                "mime_type": (ctype or "application/octet-stream").split(";")[0],
                "archivo_b64": base64.b64encode(blob).decode("ascii"),
            }
        )

    cedula_comun = ""
    if len(cedulas) == 1:
        cedula_comun = next(iter(cedulas))
    nombre_cliente = ""
    if cedula_comun:
        cli = db.execute(
            select(Cliente).where(
                expr_cedula_normalizada_para_comparar(Cliente.cedula) == cedula_comun
            )
        ).scalars().first()
        if cli:
            nombre_cliente = (
                f"{getattr(cli, 'nombre', '') or ''} {getattr(cli, 'apellido', '') or ''}"
            ).strip()

    return {
        "ok": True,
        "items": items,
        "cedula_comun": cedula_comun,
        "nombre_cliente": nombre_cliente,
        "cedulas_distintas": len(cedulas) > 1,
    }


@router.post("/escaner/lote/drive-digitalizar")
async def escaner_lote_drive_digitalizar(
    request: Request,
    db: Session = Depends(get_db),
    tipo_cedula: str = Form(...),
    numero_cedula: str = Form(...),
    drive_folder: str = Form(...),
    max_archivos: int = Form(15),
    fuente_tasa_cambio: str = Form("euro"),
):
    """
    Escáner lote desde carpeta compartida de Drive:
    - toma hasta `max_archivos` (tope duro 15),
    - digitaliza y valida cada comprobante como el escáner unitario,
    - si hay validación pendiente o duplicado en cartera, persiste borrador (como el unitario)
      y devuelve `borrador_id` en el ítem cuando hay usuario en sesión,
    - elimina de Drive los archivos leídos para dejar la carpeta lista (tras persistir borrador).
    """
    max_items = max(1, min(int(max_archivos or 15), 15))
    folder_id = _extraer_folder_id_drive(drive_folder)
    if not folder_id:
        raise HTTPException(status_code=400, detail="Carpeta de Drive inválida.")

    cedula_input = f"{(tipo_cedula or '').strip()}{(numero_cedula or '').strip()}"
    val = validate_cedula(cedula_input)
    if not val.get("valido"):
        raise HTTPException(status_code=400, detail=val.get("error", "Cédula inválida."))
    cedula_lookup = (val.get("valor_formateado") or "").replace("-", "")
    if not cedula_lookup:
        raise HTTPException(status_code=400, detail="Formato de cédula no reconocido.")

    cliente = db.execute(
        select(Cliente).where(expr_cedula_normalizada_para_comparar(Cliente.cedula) == cedula_lookup)
    ).scalars().first()
    if not cliente:
        raise HTTPException(status_code=400, detail="La cédula no está registrada.")
    prestamos_aprob = cpr.prestamos_aprobados_del_cliente(db, cliente.id)
    err_pres = cpr.error_si_no_puede_reportar_en_web(prestamos_aprob)
    if err_pres:
        raise HTTPException(status_code=400, detail=err_pres)

    creds = get_pagos_gmail_credentials()
    if not creds:
        raise HTTPException(status_code=503, detail="Google Drive no está configurado.")
    drive_svc, _ = build_drive_service(creds)

    q = (
        f"'{folder_id}' in parents and trashed=false "
        "and mimeType!='application/vnd.google-apps.folder'"
    )
    try:
        listed = (
            drive_svc.files()
            .list(
                q=q,
                spaces="drive",
                fields="files(id,name,mimeType,size,createdTime)",
                orderBy="createdTime asc",
                pageSize=max_items,
            )
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"No se pudo leer la carpeta de Drive: {str(e)[:180]}") from e

    files = listed.get("files", []) or []
    if not files:
        return {
            "ok": True,
            "items": [],
            "total_leidos": 0,
            "total_eliminados": 0,
            "mensaje": "La carpeta de Drive no tiene imágenes para procesar.",
        }

    tipo = (tipo_cedula or "").strip().upper()[:2]
    numero = (numero_cedula or "").strip()
    ctx_ced = f"{tipo}{numero}".replace("-", "")
    prestamo_objetivo_id: Optional[int] = int(prestamos_aprob[0]) if len(prestamos_aprob) == 1 else None

    current_user = getattr(request.state, "user", None)
    usuario_escaner_id: Optional[int] = None
    if current_user is not None and getattr(current_user, "id", None) is not None:
        try:
            usuario_escaner_id = int(current_user.id)
        except (TypeError, ValueError):
            usuario_escaner_id = None

    items = []
    delete_ok = 0
    for f in files:
        fid = str(f.get("id") or "").strip()
        fname = str(f.get("name") or "comprobante")
        mime_drive = str(f.get("mimeType") or "")
        if not fid:
            continue
        content = b""
        try:
            req = drive_svc.files().get_media(fileId=fid)
            out = io.BytesIO()
            from googleapiclient.http import MediaIoBaseDownload

            dl = MediaIoBaseDownload(out, req)
            done = False
            while not done:
                _, done = dl.next_chunk()
            content = out.getvalue()
        except Exception:
            items.append(
                {
                    "drive_file_id": fid,
                    "nombre_archivo": fname,
                    "mime_type": mime_drive,
                    "archivo_b64": None,
                    "ok": False,
                    "error": "No se pudo descargar desde Drive.",
                    "sugerencia": None,
                    "validacion_campos": None,
                    "validacion_reglas": None,
                    "duplicado_en_pagos": False,
                    "pago_existente_id": None,
                    "prestamo_existente_id": None,
                    "prestamo_objetivo_id": prestamo_objetivo_id,
                }
            )
            continue

        ctype = cpr.mime_efectivo_comprobante_web(mime_drive, fname)
        err_file, content, filename, ctype = cpr.preparar_adjunto_comprobante_para_vision(
            content,
            ctype,
            fname,
            mensaje_excel_largo=False,
        )
        archivo_b64 = base64.b64encode(content).decode("ascii")
        if err_file:
            items.append(
                {
                    "drive_file_id": fid,
                    "nombre_archivo": fname,
                    "mime_type": ctype,
                    "archivo_b64": archivo_b64,
                    "ok": False,
                    "error": err_file,
                    "sugerencia": None,
                    "validacion_campos": None,
                    "validacion_reglas": None,
                    "duplicado_en_pagos": False,
                    "pago_existente_id": None,
                    "prestamo_existente_id": None,
                    "prestamo_objetivo_id": prestamo_objetivo_id,
                }
            )
        else:
            gem = await extract_infopagos_campos_desde_comprobante_con_rescate_plantilla_async(
                ctx_ced, content, filename
            )
            if not gem.get("ok"):
                _base_escaner_lote = (
                    "Gemini no pudo digitalizar el comprobante con consistencia. "
                    "Pase a revisión manual y complete/valide los campos antes de guardar."
                )
                _det_lote = (str(gem.get("error") or "")).strip()
                validacion_manual = (
                    f"{_base_escaner_lote} Detalle: {_det_lote[:500]}"
                    if _det_lote
                    else _base_escaner_lote
                )
                borrador_id_fallo: Optional[str] = None
                if usuario_escaner_id is not None:
                    try:
                        payload_snap_fallo = {
                            "source": "lote_drive",
                            "drive_file_id": fid,
                            "nombre_archivo": fname,
                            "sugerencia": {
                                "fecha_pago": None,
                                "institucion_financiera": "",
                                "numero_operacion": "",
                                "monto": None,
                                "moneda": "BS",
                                "cedula_pagador_en_comprobante": "",
                                "notas_modelo": "",
                            },
                            "validacion_campos": None,
                            "validacion_reglas": validacion_manual,
                            "duplicado_en_pagos": False,
                            "pago_existente_id": None,
                            "prestamo_existente_id": None,
                            "prestamo_objetivo_id": prestamo_objetivo_id,
                            "motivo_digitalizacion": "gemini_no_digitaliza",
                        }
                        borrador_id_fallo = ieb.crear_borrador_escaneo(
                            db,
                            cliente_id=int(cliente.id),
                            usuario_id=usuario_escaner_id,
                            tipo_cedula=tipo,
                            numero_cedula=numero,
                            cedula_normalizada=cedula_lookup,
                            fuente_tasa_cambio=fuente_tasa_cambio,
                            content=content,
                            ctype=ctype,
                            filename=filename,
                            payload=payload_snap_fallo,
                        )
                        if borrador_id_fallo:
                            db.commit()
                        else:
                            db.rollback()
                    except Exception as e:
                        db.rollback()
                        logger.exception(
                            "[ESCANER_LOTE_DRIVE] fallo al guardar borrador por no digitalizar file_id=%s: %s",
                            fid,
                            e,
                        )
                items.append(
                    {
                        "drive_file_id": fid,
                        "nombre_archivo": fname,
                        "mime_type": ctype,
                        "archivo_b64": archivo_b64,
                        "ok": False,
                        "error": validacion_manual,
                        "sugerencia": None,
                        "validacion_campos": None,
                        "validacion_reglas": validacion_manual,
                        "duplicado_en_pagos": False,
                        "pago_existente_id": None,
                        "prestamo_existente_id": None,
                        "prestamo_objetivo_id": prestamo_objetivo_id,
                        "borrador_id": borrador_id_fallo,
                        "requiere_revision_manual": True,
                    }
                )
            else:
                fecha_d = gem.get("fecha_pago")
                fecha_iso = fecha_d.isoformat() if isinstance(fecha_d, date) else None
                monto = gem.get("monto")
                inst = gem.get("institucion_financiera") or ""
                num_op = gem.get("numero_operacion") or ""
                moneda = gem.get("moneda") or "BS"
                validacion_campos = None
                validacion_reglas = None
                if monto is not None and inst.strip() and num_op.strip():
                    err_campos, mon_norm = cpr.normalizar_y_validar_campos_formulario(
                        tipo_cedula=tipo,
                        numero_cedula=numero,
                        institucion_financiera=inst,
                        numero_operacion=num_op,
                        monto=float(monto),
                        moneda=moneda,
                        observacion=None,
                    )
                    validacion_campos = err_campos
                    if not err_campos and isinstance(fecha_d, date):
                        validacion_reglas = cpr.validar_reglas_bs_tasa_monto_fecha(
                            db,
                            cedula_lookup=cedula_lookup,
                            fecha_pago=fecha_d,
                            monto=float(monto),
                            mon=mon_norm,
                            fuente_tasa_cambio=fuente_tasa_cambio,
                        )
                    elif not err_campos and not isinstance(fecha_d, date):
                        validacion_reglas = (
                            "Indique la fecha de pago (no se detectó con claridad en la imagen)."
                        )
                elif monto is None:
                    validacion_reglas = "Complete el monto (no se detectó con claridad en la imagen)."
                elif not inst.strip():
                    validacion_reglas = "Complete la institución financiera."
                elif not num_op.strip():
                    validacion_reglas = "Complete el número de operación o referencia."

                validacion_reglas = cpr.fusionar_validacion_reglas_monto_alto_escaneo(
                    validacion_reglas, monto, moneda=moneda
                )

                msg_rev = drm.digitalizacion_requiere_revision_manual(
                    fecha_pago=fecha_d,
                    institucion_financiera=inst,
                    numero_operacion=num_op,
                    monto=monto,
                    notas_modelo=gem.get("notas") or "",
                )
                requiere_revision_manual = bool(msg_rev)
                if msg_rev:
                    validacion_reglas = drm.fusionar_mensaje_revision(validacion_reglas, msg_rev)

                duplicado_en_pagos = False
                pago_existente_id: Optional[int] = None
                prestamo_existente_id: Optional[int] = None
                num_op_trim = (num_op or "").strip()
                if num_op_trim:
                    pr_scan = SimpleNamespace(
                        numero_operacion=num_op_trim[:100],
                        referencia_interna="",
                    )
                    duplicado_en_pagos = pago_reportado_colisiona_tabla_pagos(db, pr_scan)
                    if duplicado_en_pagos:
                        pago_existente_id = primer_pago_id_si_existe_para_claves_reportado(
                            db, pr_scan
                        )
                        if pago_existente_id is not None:
                            p_exist = (
                                db.execute(select(Pago).where(Pago.id == pago_existente_id))
                                .scalars()
                                .first()
                            )
                            if p_exist is not None:
                                prestamo_existente_id = getattr(p_exist, "prestamo_id", None)

                sugerencia = {
                    "fecha_pago": fecha_iso,
                    "institucion_financiera": inst,
                    "numero_operacion": num_op,
                    "monto": monto,
                    "moneda": moneda if moneda in ("BS", "USD") else "BS",
                    "cedula_pagador_en_comprobante": gem.get("cedula_pagador_en_comprobante") or "",
                    "notas_modelo": gem.get("notas") or "",
                }

                borrador_id: Optional[str] = None
                necesita_borrador_bd = ieb.debe_persistir_borrador_escaneo(
                    validacion_campos=validacion_campos,
                    validacion_reglas=validacion_reglas,
                    duplicado_en_pagos=duplicado_en_pagos,
                ) or requiere_revision_manual
                if necesita_borrador_bd and usuario_escaner_id is not None:
                    try:
                        payload_snap = {
                            "source": "lote_drive",
                            "drive_file_id": fid,
                            "nombre_archivo": fname,
                            "sugerencia": sugerencia,
                            "validacion_campos": validacion_campos,
                            "validacion_reglas": validacion_reglas,
                            "duplicado_en_pagos": duplicado_en_pagos,
                            "motivo_digitalizacion": (
                                "campos_criticos_incompletos" if requiere_revision_manual else None
                            ),
                            "requiere_revision_manual": requiere_revision_manual,
                            "pago_existente_id": pago_existente_id,
                            "prestamo_existente_id": prestamo_existente_id,
                            "prestamo_objetivo_id": prestamo_objetivo_id,
                        }
                        borrador_id = ieb.crear_borrador_escaneo(
                            db,
                            cliente_id=int(cliente.id),
                            usuario_id=usuario_escaner_id,
                            tipo_cedula=tipo,
                            numero_cedula=numero,
                            cedula_normalizada=cedula_lookup,
                            fuente_tasa_cambio=fuente_tasa_cambio,
                            content=content,
                            ctype=ctype,
                            filename=filename,
                            payload=payload_snap,
                        )
                        if borrador_id:
                            db.commit()
                        else:
                            db.rollback()
                            logger.warning(
                                "[ESCANER_LOTE_DRIVE] validación con pendientes pero no se pudo persistir borrador file_id=%s",
                                fid,
                            )
                    except Exception as e:
                        db.rollback()
                        logger.exception(
                            "[ESCANER_LOTE_DRIVE] fallo al guardar borrador temporal file_id=%s: %s",
                            fid,
                            e,
                        )
                elif necesita_borrador_bd and usuario_escaner_id is None:
                    logger.warning(
                        "[ESCANER_LOTE_DRIVE] validación con pendientes pero sin usuario en sesión; no se persiste borrador file_id=%s",
                        fid,
                    )

                items.append(
                    {
                        "drive_file_id": fid,
                        "nombre_archivo": fname,
                        "mime_type": ctype,
                        "archivo_b64": archivo_b64,
                        "ok": True,
                        "error": None,
                        "sugerencia": sugerencia,
                        "validacion_campos": validacion_campos,
                        "validacion_reglas": validacion_reglas,
                        "duplicado_en_pagos": duplicado_en_pagos,
                        "pago_existente_id": pago_existente_id,
                        "prestamo_existente_id": prestamo_existente_id,
                        "prestamo_objetivo_id": prestamo_objetivo_id,
                        "borrador_id": borrador_id,
                        "requiere_revision_manual": requiere_revision_manual,
                    }
                )

        # No borrar en Drive si el OCR falló/incompleto y no hay borrador: evita truncar el proceso.
        ultimo = items[-1] if items else {}
        tiene_borrador = bool((ultimo.get("borrador_id") or "").strip())
        ocr_ok = bool(ultimo.get("ok"))
        rev_manual = bool(ultimo.get("requiere_revision_manual"))
        if (not ocr_ok or rev_manual) and not tiene_borrador:
            logger.warning(
                "[ESCANER_LOTE_DRIVE] se conserva archivo Drive file_id=%s (sin borrador; revisión manual)",
                fid,
            )
        else:
            try:
                drive_svc.files().delete(fileId=fid).execute()
                delete_ok += 1
            except Exception:
                logger.warning("[ESCANER_LOTE_DRIVE] No se pudo eliminar file_id=%s", fid)

    return {
        "ok": True,
        "items": items,
        "total_leidos": len(items),
        "total_eliminados": delete_ok,
        "mensaje": f"Se procesaron {len(items)} archivo(s) desde Drive.",
    }