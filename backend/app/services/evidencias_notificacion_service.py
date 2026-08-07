"""
Evidencias de notificaciones: escaneo Gmail (itmaster) por etiquetas
DIA SIGUIENTE / 1 CUOTA / 2 CUOTAS O MAS -> PDF unico (correo + anexo) en BD.

En Gmail (itmaster) viven bajo el padre NOTIFICACIONES; el nombre API suele ser
``NOTIFICACIONES/<nombre>``. El nombre corto ``2 CUOTAS O MAS`` es el real en UI
(no ``2 O MAS CUOTAS``).
"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from email.utils import parseaddr, parsedate_to_datetime
from io import BytesIO
from typing import Any, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.evidencia_notificacion import EvidenciaNotificacion
from app.models.envio_notificacion import EnvioNotificacion
from app.models.envio_notificacion_adjunto import EnvioNotificacionAdjunto

logger = logging.getLogger(__name__)

ETIQUETAS_EVIDENCIAS = (
    "DIA SIGUIENTE",
    "1 CUOTA",
    "2 CUOTAS O MAS",
)

# Filtros UI / legado -> nombre canonico guardado en BD
ETIQUETAS_ALIAS = {
    "2 O MAS CUOTAS": "2 CUOTAS O MAS",
}

ETIQUETA_PROCESADO = "EVIDENCIA_OK"

ETIQUETA_CON_ANEXO = "DIA SIGUIENTE"
TIPO_CASO_ANEXO_SISTEMA = "dias_1_retraso"
TIPO_TAB_ANEXO_SISTEMA = "dias_1_retraso"

ITMASTER_EMAIL = "itmaster@rapicreditca.com"
RAPICREDIT_DOMAINS = ("rapicreditca.com", "rapicredit.com")

_RE_EMAIL = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)
_RE_FWD_TO = re.compile(
    r"(?:^|\n)\s*(?:To|Para)\s*:\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)




def _normalizar_etiqueta_filtro(etiqueta: Optional[str]) -> Optional[str]:
    etiq = (etiqueta or "").strip()
    if not etiq:
        return None
    etiq = ETIQUETAS_ALIAS.get(etiq, etiq)
    if etiq in ETIQUETAS_EVIDENCIAS:
        return etiq
    return None


def _candidatos_nombres_etiqueta(canonical: str) -> list[str]:
    """Nombres posibles en Gmail API (plano o anidado bajo NOTIFICACIONES)."""
    names = [canonical, f"NOTIFICACIONES/{canonical}"]
    if canonical == "2 CUOTAS O MAS":
        names.extend(["2 O MAS CUOTAS", "NOTIFICACIONES/2 O MAS CUOTAS"])
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _resolver_id_etiqueta_evidencia(service: Any, canonical: str) -> Optional[str]:
    """
    Resuelve id de etiqueta de usuario por nombre corto o anidado.
    No crea etiquetas (solo lectura).
    """
    from app.services.pagos_gmail.gmail_service import (
        get_existing_user_label_id,
        list_gmail_user_label_ids,
    )

    for name in _candidatos_nombres_etiqueta(canonical):
        lid = get_existing_user_label_id(service, name)
        if lid:
            logger.info(
                "[EVIDENCIAS] etiqueta resuelta canonical=%r gmail_name=%r id=%s",
                canonical,
                name,
                lid,
            )
            return lid

    _ids, id_to_name, ok = list_gmail_user_label_ids(service)
    if not ok:
        return None
    target = canonical.casefold().strip()
    for lid, name in id_to_name.items():
        n = (name or "").strip()
        nf = n.casefold()
        if nf == target or nf.endswith("/" + target):
            logger.info(
                "[EVIDENCIAS] etiqueta resuelta (suffix) canonical=%r gmail_name=%r id=%s",
                canonical,
                n,
                lid,
            )
            return str(lid)
    return None

def _norm_email(raw: Optional[str]) -> str:
    if not raw:
        return ""
    _, addr = parseaddr(raw.strip())
    return (addr or raw).strip().lower()


def _es_interno(email: str) -> bool:
    """True para cualquier @rapicreditca.com / @rapicredit.com (y subdominios) o itmaster."""
    em = _norm_email(email)
    if not em or "@" not in em:
        return True
    if em == ITMASTER_EMAIL:
        return True
    domain = em.rsplit("@", 1)[-1].lower()
    if domain in RAPICREDIT_DOMAINS:
        return True
    if domain.endswith(".rapicreditca.com") or domain.endswith(".rapicredit.com"):
        return True
    return False


def _email_cliente_valido(raw: Optional[str]) -> Optional[str]:
    """
    Solo emails de cliente para clasificar evidencias.
    Rechaza vacio, invalidos y CUALQUIER cuenta @rapicreditca.com / @rapicredit.com.
    """
    em = _norm_email(raw)
    if not em or "@" not in em:
        return None
    if _es_interno(em):
        return None
    local = em.split("@", 1)[0]
    if local in ("mailer-daemon", "postmaster", "noreply", "no-reply"):
        return None
    if "mailer-daemon" in em:
        return None
    return em


def _headers_from_payload(payload: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for h in payload.get("headers") or []:
        name = (h.get("name") or "").strip()
        if name:
            out[name.lower()] = (h.get("value") or "").strip()
    return out


def _fecha_mensaje(headers: dict[str, str], internal_date_ms: Optional[str]) -> Optional[datetime]:
    date_str = headers.get("date") or ""
    if date_str:
        try:
            dt = parsedate_to_datetime(date_str)
            return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt
        except Exception:
            pass
    if internal_date_ms:
        try:
            return datetime.utcfromtimestamp(int(internal_date_ms) / 1000.0)
        except Exception:
            pass
    return None


def _cedula_por_correo(db: Session, email_raw: str) -> Optional[str]:
    em = _norm_email(email_raw)
    if not em:
        return None
    try:
        rows_main = (
            db.execute(
                select(Cliente.cedula)
                .where(func.lower(func.trim(Cliente.email)) == em)
                .limit(2)
            )
            .scalars()
            .all()
        )
        if len(rows_main) == 1:
            return rows_main[0]
        if len(rows_main) > 1:
            return None
        rows_sec = (
            db.execute(
                select(Cliente.cedula)
                .where(Cliente.email_secundario.isnot(None))
                .where(func.trim(Cliente.email_secundario) != "")
                .where(func.lower(func.trim(Cliente.email_secundario)) == em)
                .limit(2)
            )
            .scalars()
            .all()
        )
        if len(rows_sec) == 1:
            return rows_sec[0]
        return None
    except Exception as ex:
        logger.warning("[EVIDENCIAS] lookup cedula: %s", ex)
        return None


def _email_es_cliente_conocido(db: Session, email_raw: str) -> bool:
    return _cedula_por_correo(db, email_raw) is not None


def _extraer_emails_candidato(texto: str) -> list[str]:
    """Emails externos (nunca @rapicreditca.com) en orden de aparicion."""
    seen: set[str] = set()
    out: list[str] = []
    for m in _RE_EMAIL.finditer(texto or ""):
        em = _email_cliente_valido(m.group(0))
        if not em or em in seen:
            continue
        seen.add(em)
        out.append(em)
    return out


def _emails_desde_linea_to(linea: str) -> list[str]:
    """Parsea una linea To:/Para: y devuelve solo emails de cliente."""
    out: list[str] = []
    seen: set[str] = set()
    raw = (linea or "").strip()
    if not raw:
        return out
    parts = raw.split(",") if "," in raw else [raw]
    for part in parts:
        em = _email_cliente_valido(part)
        if em and em not in seen:
            seen.add(em)
            out.append(em)
            continue
        for em2 in _extraer_emails_candidato(part):
            if em2 not in seen:
                seen.add(em2)
                out.append(em2)
    return out


def _from_es_cuenta_rapicredit(headers: dict[str, str]) -> bool:
    """True si el From externo es cuenta operativa Rapicredit (cobranza/notificaciones/pagos)."""
    em = _norm_email(headers.get("from") or "")
    if not em or "@" not in em:
        return False
    local, domain = em.rsplit("@", 1)
    if domain not in RAPICREDIT_DOMAINS:
        return False
    return local in ("cobranza", "notificaciones", "pagos")


_RE_FWD_BLOCK = re.compile(
    r"(?:mensaje\s+reenviado|forwarded\s+message|original\s+message)",
    re.IGNORECASE,
)
_RE_TO_IN_BLOCK = re.compile(
    r"(?:To|Para)\s*:\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)


def resolver_email_cliente(
    db: Session,
    *,
    headers: dict[str, str],
    cuerpo: str,
) -> Optional[str]:
    """
    Email del CLIENTE para clasificar la evidencia.
    Nunca devuelve @rapicreditca.com / @rapicredit.com / itmaster.
    Prioridad: encabezados externos -> To/Para de reenvio -> bloque
    Mensaje reenviado -> email conocido en BD -> primer externo del cuerpo
    si el From es cobranza/notificaciones/pagos.
    """
    for key in ("to", "cc", "delivered-to", "x-original-to", "x-forwarded-to"):
        for em in _emails_desde_linea_to(headers.get(key) or ""):
            return em

    body = cuerpo or ""

    for m in _RE_FWD_TO.finditer(body):
        for em in _emails_desde_linea_to(m.group(1)):
            return em

    for m in _RE_FWD_BLOCK.finditer(body):
        window = body[m.end() : m.end() + 1200]
        for tm in _RE_TO_IN_BLOCK.finditer(window):
            for em in _emails_desde_linea_to(tm.group(1)):
                return em

    for em in _extraer_emails_candidato(body):
        if _email_es_cliente_conocido(db, em):
            return em

    # Reenvio Cobranza/Notificaciones a itmaster: To del cliente en el cuerpo.
    if _from_es_cuenta_rapicredit(headers):
        for em in _extraer_emails_candidato(body):
            return em

    return None


def merge_pdfs(pdf_parts: list[bytes]) -> Optional[bytes]:
    """Fusiona varios PDFs en uno. Si solo hay uno, lo devuelve."""
    parts = [p for p in pdf_parts if p and p[:4] == b"%PDF"]
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    try:
        from pypdf import PdfReader, PdfWriter

        writer = PdfWriter()
        for blob in parts:
            try:
                reader = PdfReader(BytesIO(blob))
                for page in reader.pages:
                    writer.add_page(page)
            except Exception as ex:
                logger.warning("[EVIDENCIAS] omitiendo PDF invalido en merge: %s", ex)
        if len(writer.pages) == 0:
            return parts[0]
        buf = BytesIO()
        writer.write(buf)
        return buf.getvalue()
    except Exception as ex:
        logger.exception("[EVIDENCIAS] merge_pdfs: %s", ex)
        return parts[0]


def _pdfs_desde_gmail(service: Any, message_id: str, payload: dict) -> list[bytes]:
    """PDFs adjuntos (recorrido recursive de partes MIME)."""
    from app.services.pagos_gmail.gmail_service import (
        get_attachment_image_pdf_files_for_message,
        get_attachments_for_message,
    )

    out: list[bytes] = []
    seen: set[int] = set()

    def _add(content: bytes) -> None:
        if not content or content[:4] != b"%PDF":
            return
        key = hash(content[:64] + str(len(content)).encode())
        if key in seen:
            return
        seen.add(key)
        out.append(content)

    try:
        for filename, content, mime in get_attachment_image_pdf_files_for_message(
            service, message_id, payload
        ) or []:
            name = (filename or "").lower()
            mime_l = (mime or "").lower()
            if name.endswith(".pdf") or "pdf" in mime_l or mime_l == "application/pdf":
                _add(content)
    except Exception as ex:
        logger.warning("[EVIDENCIAS] adjuntos gmail recursive %s: %s", message_id, ex)

    if not out:
        try:
            for filename, content, mime in get_attachments_for_message(
                service, message_id, payload
            ) or []:
                name = (filename or "").lower()
                mime_l = (mime or "").lower()
                if name.endswith(".pdf") or "pdf" in mime_l:
                    _add(content)
        except Exception as ex:
            logger.warning("[EVIDENCIAS] adjuntos gmail flat %s: %s", message_id, ex)
    return out


def _pdfs_anexo_sistema(db: Session, email_cliente: str) -> list[bytes]:
    """Preferencia: adjuntos del ultimo envio dias_1_retraso; si no, PDFs fijos del caso."""
    out: list[bytes] = []
    em = _norm_email(email_cliente)
    try:
        envio_id = db.execute(
            select(EnvioNotificacion.id)
            .where(func.lower(func.trim(EnvioNotificacion.email)) == em)
            .where(EnvioNotificacion.tipo_tab == TIPO_TAB_ANEXO_SISTEMA)
            .where(EnvioNotificacion.exito.is_(True))
            .order_by(EnvioNotificacion.fecha_envio.desc())
            .limit(1)
        ).scalar_one_or_none()
        if envio_id:
            rows = (
                db.execute(
                    select(EnvioNotificacionAdjunto.contenido)
                    .where(EnvioNotificacionAdjunto.envio_notificacion_id == envio_id)
                    .order_by(EnvioNotificacionAdjunto.orden)
                )
                .scalars()
                .all()
            )
            for blob in rows:
                if blob and blob[:4] == b"%PDF":
                    out.append(blob)
    except Exception as ex:
        logger.warning("[EVIDENCIAS] anexo desde envios_notificacion: %s", ex)

    if out:
        return out

    try:
        from app.services.adjunto_fijo_cobranza import get_adjuntos_fijos_por_caso

        for _nombre, contenido in get_adjuntos_fijos_por_caso(db, TIPO_CASO_ANEXO_SISTEMA) or []:
            if contenido and contenido[:4] == b"%PDF":
                out.append(contenido)
    except Exception as ex:
        logger.warning("[EVIDENCIAS] anexo fijo sistema: %s", ex)
    return out


def _construir_pdf_evidencia(
    db: Session,
    service: Any,
    *,
    message_id: str,
    payload: dict,
    raw_eml: bytes,
    etiqueta: str,
    email_cliente: str,
) -> tuple[Optional[bytes], bool, str]:
    from app.services.pagos_gmail.email_to_pdf import eml_bytes_to_pdf

    email_pdf = eml_bytes_to_pdf(raw_eml)
    if not email_pdf:
        return None, False, "ninguno"

    partes: list[bytes] = [email_pdf]
    fuente = "ninguno"
    tiene_anexo = False

    if etiqueta == ETIQUETA_CON_ANEXO:
        gmail_pdfs = _pdfs_desde_gmail(service, message_id, payload)
        if gmail_pdfs:
            partes.extend(gmail_pdfs)
            fuente = "gmail"
            tiene_anexo = True
        else:
            sistema_pdfs = _pdfs_anexo_sistema(db, email_cliente)
            if sistema_pdfs:
                partes.extend(sistema_pdfs)
                fuente = "sistema"
                tiene_anexo = True

    merged = merge_pdfs(partes)
    return merged, tiene_anexo, fuente

def _ids_existentes_en_bd(db: Session, message_ids) -> set[str]:
    """Devuelve message_ids que ya estan en BD (consulta por lotes; no carga toda la tabla)."""
    ids = [str(x) for x in (message_ids or []) if x]
    if not ids:
        return set()
    existing: set[str] = set()
    chunk_size = 100
    for i in range(0, len(ids), chunk_size):
        chunk = ids[i : i + chunk_size]
        rows = (
            db.execute(
                select(EvidenciaNotificacion.gmail_message_id).where(
                    EvidenciaNotificacion.gmail_message_id.in_(chunk)
                )
            )
            .scalars()
            .all()
        )
        existing.update(str(x) for x in rows if x)
    return existing


def buscar_evidencias(
    db: Session,
    *,
    q: str,
    skip: int = 0,
    limit: int = 50,
    etiqueta: Optional[str] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
) -> tuple[list[EvidenciaNotificacion], int]:
    term = (q or "").strip()
    if not term:
        return [], 0

    like = f"%{term.lower()}%"
    # Digitos: tambien buscar cedula sin espacios
    digits = re.sub(r"\D", "", term)
    clauses = [
        EvidenciaNotificacion.email_cliente_norm.ilike(like),
        func.lower(func.coalesce(EvidenciaNotificacion.cedula, "")).ilike(like),
    ]
    if digits and len(digits) >= 5:
        clauses.append(
            func.regexp_replace(func.coalesce(EvidenciaNotificacion.cedula, ""), r"\D", "", "g").ilike(
                f"%{digits}%"
            )
        )

    filters = [or_(*clauses)]
    etiq = _normalizar_etiqueta_filtro(etiqueta)
    if etiq:
        filters.append(EvidenciaNotificacion.etiqueta_gmail == etiq)
    if fecha_desde is not None:
        filters.append(EvidenciaNotificacion.fecha_mensaje >= fecha_desde)
    if fecha_hasta is not None:
        filters.append(EvidenciaNotificacion.fecha_mensaje <= fecha_hasta)

    where = and_(*filters)
    total = db.execute(
        select(func.count()).select_from(EvidenciaNotificacion).where(where)
    ).scalar() or 0
    rows = (
        db.execute(
            select(EvidenciaNotificacion)
            .where(where)
            .order_by(
                EvidenciaNotificacion.fecha_mensaje.desc().nullslast(),
                EvidenciaNotificacion.id.desc(),
            )
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return list(rows), int(total)


def obtener_pdf(db: Session, evidencia_id: int) -> Optional[EvidenciaNotificacion]:
    return db.get(EvidenciaNotificacion, evidencia_id)


def procesar_evidencias_gmail(
    db: Session,
    *,
    procesado_por: str,
    max_messages: int = 40,
    presupuesto_segundos: float = 90.0,
) -> dict[str, Any]:
    """
    Escaneo manual: mensajes con etiquetas DIA SIGUIENTE / 1 CUOTA / 2 CUOTAS O MAS.
    Idempotente por gmail_message_id. Marca EVIDENCIA_OK al guardar o si ya existia.
    """
    from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials
    from app.services.pagos_gmail.gmail_service import (
        add_message_user_labels_only,
        build_gmail_service,
        ensure_user_label_id,
        get_message_all_text_parts,
        get_message_raw_bytes,
    )

    empty = {
        "ok": False,
        "error": None,
        "mensaje": None,
        "candidatos": 0,
        "revisados": 0,
        "guardados": 0,
        "omitidos": 0,
        "ya_existentes": 0,
        "sin_correo": 0,
        "sin_pdf": 0,
        "etiquetados": 0,
        "etiquetas_faltantes": [],
        "truncado": False,
    }

    creds = get_pagos_gmail_credentials()
    if creds is None:
        return {
            **empty,
            "error": "no_credentials",
            "mensaje": "No hay credenciales Gmail (misma conexion que Pagos Gmail / itmaster).",
        }

    service = build_gmail_service(creds)
    ok_label_id = ensure_user_label_id(service, ETIQUETA_PROCESADO)

    etiquetas_faltantes: list[str] = []
    # (nombre_canonico, label_id)
    label_queries: list[tuple[str, str]] = []
    for nombre in ETIQUETAS_EVIDENCIAS:
        lid = _resolver_id_etiqueta_evidencia(service, nombre)
        if not lid:
            etiquetas_faltantes.append(nombre)
            continue
        label_queries.append((nombre, lid))

    if not label_queries:
        return {
            **empty,
            "error": "labels_missing",
            "mensaje": (
                "No existen en Gmail las etiquetas: "
                + ", ".join(ETIQUETAS_EVIDENCIAS)
                + " (o NOTIFICACIONES/<nombre>). "
                "Creelas en itmaster bajo NOTIFICACIONES y programe el filtrado."
            ),
            "etiquetas_faltantes": etiquetas_faltantes,
        }
    if etiquetas_faltantes:
        logger.warning(
            "[EVIDENCIAS] etiquetas no resueltas (se escanean las demas): %s",
            etiquetas_faltantes,
        )

    def _marcar_procesado(mid: str) -> bool:
        if not ok_label_id or not mid:
            return False
        try:
            add_message_user_labels_only(service, mid, [ok_label_id])
            return True
        except Exception as ex:
            logger.warning(
                "[EVIDENCIAS] etiquetar %s %s: %s", ETIQUETA_PROCESADO, mid, ex
            )
            return False

    lote_objetivo = max(1, min(int(max_messages), 200))
    list_scan_cap = 1000
    msg_refs: list[tuple[str, dict]] = []
    saltados_ya_bd = 0
    listados_gmail = 0
    etiquetados = 0
    refs_seen: set[str] = set()

    for etiqueta, label_id in label_queries:
        if len(msg_refs) >= lote_objetivo:
            break
        page_token: Optional[str] = None
        while len(msg_refs) < lote_objetivo and listados_gmail < list_scan_cap:
            params: dict[str, Any] = {
                "userId": "me",
                "labelIds": [label_id],
                "q": f'-label:"{ETIQUETA_PROCESADO}"',
                "maxResults": min(100, list_scan_cap - listados_gmail),
                "includeSpamTrash": False,
            }
            if page_token:
                params["pageToken"] = page_token
            try:
                resp = service.users().messages().list(**params).execute()
            except Exception as e:
                logger.exception("[EVIDENCIAS] list messages %s: %s", etiqueta, e)
                return {
                    **empty,
                    "error": "gmail_list_failed",
                    "mensaje": str(e),
                    "ya_existentes": saltados_ya_bd,
                    "etiquetados": etiquetados,
                    "etiquetas_faltantes": etiquetas_faltantes,
                }
            batch = resp.get("messages") or []
            if not batch:
                break
            page_ids = [str(r.get("id")) for r in batch if r.get("id")]
            existentes_pagina = _ids_existentes_en_bd(db, page_ids)
            for ref in batch:
                listados_gmail += 1
                mid = ref.get("id")
                if not mid:
                    continue
                if mid in existentes_pagina:
                    saltados_ya_bd += 1
                    if _marcar_procesado(mid):
                        etiquetados += 1
                    continue
                if mid in refs_seen:
                    continue
                refs_seen.add(mid)
                msg_refs.append((etiqueta, ref))
                if len(msg_refs) >= lote_objetivo:
                    break
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

    candidatos = len(msg_refs)
    labels = [n for n, _ in label_queries]
    logger.info(
        "[EVIDENCIAS] post-list labels=%s listados_gmail=%s candidatos=%s "
        "saltados_ya_bd=%s etiquetas_faltantes=%s",
        labels,
        listados_gmail,
        candidatos,
        saltados_ya_bd,
        etiquetas_faltantes,
    )
    revisados = 0
    guardados = 0
    omitidos = 0
    ya_existentes = saltados_ya_bd
    sin_correo = 0
    sin_pdf = 0
    truncado = False
    t0 = time.monotonic()
    deadline = t0 + max(15.0, float(presupuesto_segundos))

    for etiqueta, ref in msg_refs:
        if time.monotonic() >= deadline:
            truncado = True
            break
        mid = ref.get("id")
        if not mid:
            continue
        revisados += 1
        try:
            msg = service.users().messages().get(
                userId="me", id=mid, format="full"
            ).execute()
        except Exception as ex:
            logger.warning("[EVIDENCIAS] get message %s: %s", mid, ex)
            omitidos += 1
            continue

        payload = msg.get("payload") or {}
        headers = _headers_from_payload(payload)

        cuerpo = ""
        try:
            cuerpo = get_message_all_text_parts(payload) or ""
        except Exception:
            cuerpo = ""

        email_cliente = _email_cliente_valido(
            resolver_email_cliente(db, headers=headers, cuerpo=cuerpo)
        )
        if not email_cliente:
            sin_correo += 1
            omitidos += 1
            continue

        raw = get_message_raw_bytes(service, mid)
        if not raw:
            sin_pdf += 1
            omitidos += 1
            continue

        pdf_bytes, tiene_anexo, fuente_anexo = _construir_pdf_evidencia(
            db,
            service,
            message_id=mid,
            payload=payload,
            raw_eml=raw,
            etiqueta=etiqueta,
            email_cliente=email_cliente,
        )
        if not pdf_bytes:
            sin_pdf += 1
            omitidos += 1
            continue

        cedula = _cedula_por_correo(db, email_cliente)
        row = EvidenciaNotificacion(
            gmail_message_id=mid,
            gmail_thread_id=msg.get("threadId") or ref.get("threadId"),
            etiqueta_gmail=etiqueta,
            email_cliente=email_cliente,
            email_cliente_norm=email_cliente,  # ya validado: nunca @rapicreditca.com
            cedula=cedula,
            asunto=(headers.get("subject") or "")[:500] or None,
            fecha_mensaje=_fecha_mensaje(headers, msg.get("internalDate")),
            pdf_contenido=pdf_bytes,
            pdf_tamano_bytes=len(pdf_bytes),
            tiene_anexo=tiene_anexo,
            fuente_anexo=fuente_anexo,
            procesado_por=(procesado_por or "")[:150] or None,
        )
        try:
            db.add(row)
            db.commit()
            guardados += 1
            if _marcar_procesado(mid):
                etiquetados += 1
        except IntegrityError:
            db.rollback()
            ya_existentes += 1
            if _marcar_procesado(mid):
                etiquetados += 1
        except Exception as ex:
            db.rollback()
            logger.exception("[EVIDENCIAS] guardar %s: %s", mid, ex)
            omitidos += 1

    mensaje = (
        f"Escaneo: revisados={revisados}, guardados={guardados}, "
        f"ya_en_bd={ya_existentes}, omitidos={omitidos}, etiquetados={etiquetados}"
        + (" (truncado por tiempo)" if truncado else "")
    )
    if etiquetas_faltantes:
        mensaje += (
            ". Etiquetas no encontradas en Gmail: "
            + ", ".join(etiquetas_faltantes)
        )
    elif candidatos == 0:
        mensaje += (
            ". No hay mensajes nuevos en "
            + " / ".join(ETIQUETAS_EVIDENCIAS)
            + f' (excluyendo etiqueta "{ETIQUETA_PROCESADO}").'
        )
    elif sin_correo and guardados == 0:
        mensaje += (
            ". Varios reenvios de Cobranza quedaron sin correo de cliente: "
            "el bloque reenviado debe incluir To:/Para: del destinatario "
            "(p. ej. To: <cliente@gmail.com>)."
        )

    return {
        "ok": True,
        "error": None,
        "mensaje": mensaje,
        "candidatos": candidatos,
        "revisados": revisados,
        "guardados": guardados,
        "omitidos": omitidos,
        "ya_existentes": ya_existentes,
        "sin_correo": sin_correo,
        "sin_pdf": sin_pdf,
        "etiquetados": etiquetados,
        "etiquetas_faltantes": etiquetas_faltantes,
        "truncado": truncado,
    }
