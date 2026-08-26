# -*- coding: utf-8 -*-
"""
Importación extracto (faltantes): parse Excel banco → comparar vs pagos en prestamos APROBADO.

Match 100%: misma cédula + mismo serial → no reimportar.
Se puede importar: serial ausente en esa cédula (APROBADO).
Semejante: % similitud para revisión manual → Visto.
Importar (OK individual o lote): crea pago con fecha/serial/monto + imagen placeholder.
"""
from __future__ import annotations

import base64
import io
import logging
import re
import uuid
from datetime import date, datetime, time as dt_time
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Any, Optional

from fastapi import HTTPException, UploadFile
from openpyxl import load_workbook
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.documento import compose_numero_documento_almacenado, normalize_documento
from app.models.cliente import Cliente
from app.models.importacion_extracto import ImportacionExtractoFila, ImportacionExtractoLote
from app.models.pago import Pago
from app.models.pago_comprobante_imagen import PagoComprobanteImagen
from app.models.prestamo import Prestamo
from app.services.pago_numero_documento import numero_documento_ya_registrado
from app.utils.cedula_almacenamiento import normalizar_cedula_almacenamiento

logger = logging.getLogger(__name__)

MAX_FILAS = 25000
USUARIO_REGISTRO = "importacion-extracto@sistema.rapicredit.com"

# PNG 1x1 blanco (placeholder genérico; no inventa comprobante real).
_PNG_BLANCO_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

_RE_CEDULA = re.compile(
    r"(?:^|[:\s])([VEJG])\s*-\s*(\d{6,12})\b",
    re.IGNORECASE,
)
_RE_CEDULA_ALT = re.compile(r"\b([VEJG])(\d{6,12})\b", re.IGNORECASE)


def ensure_schema(db: Session) -> None:
    """CREATE TABLE IF NOT EXISTS vía metadata (idempotente)."""
    from app.core.database import engine

    ImportacionExtractoLote.__table__.create(bind=engine, checkfirst=True)
    ImportacionExtractoFila.__table__.create(bind=engine, checkfirst=True)


def _solo_digitos(s: Optional[str]) -> str:
    return re.sub(r"\D+", "", (s or "").strip())


def _parse_fecha(val: Any) -> Optional[date]:
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    return None


def _parse_monto(val: Any) -> Optional[float]:
    if val is None or val == "":
        return None
    if isinstance(val, (int, float, Decimal)):
        return round(float(val), 2)
    s = str(val).strip().replace("+", "").replace(" ", "").replace(",", ".")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def extraer_cedula_descripcion(texto: Optional[str]) -> Optional[str]:
    """Extrae cédula de 'DP:V-019200177 JOSE…' sin inventar datos."""
    raw = (texto or "").strip()
    if not raw:
        return None
    m = _RE_CEDULA.search(raw) or _RE_CEDULA_ALT.search(raw)
    if not m:
        return None
    clave = f"{m.group(1).upper()}{m.group(2)}"
    return normalizar_cedula_almacenamiento(clave) or clave


def _similitud(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 100.0
    return round(SequenceMatcher(None, a, b).ratio() * 100.0, 2)


def _cell(row: tuple, idx: int) -> Any:
    return row[idx] if len(row) > idx else None


def _magic_excel(raw: bytes) -> str:
    """Clasifica bytes del archivo para mensajes y motor de lectura."""
    if not raw:
        return "vacio"
    head = raw[:8]
    if head[:2] == b"PK":
        return "xlsx_zip"
    if head[:4] == b"\xd0\xcf\x11\xe0":
        return "xls_ole"
    soft = raw.lstrip()[:200].lower()
    if soft.startswith(b"<?xml") or b"spreadsheetml" in soft or b"<workbook" in soft:
        return "xls_xml"
    if soft.startswith(b"<html") or soft.startswith(b"<!doctype html"):
        return "html"
    # CSV / TSV texto
    try:
        sample = raw[:4096].decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            sample = raw[:4096].decode("latin-1")
        except Exception:
            return "desconocido"
    if "," in sample or ";" in sample or "\t" in sample:
        return "csv"
    return "desconocido"


def _rows_from_openpyxl(raw: bytes) -> list[tuple]:
    wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    try:
        ws = wb.active
        if ws is None:
            raise ValueError("Excel sin hoja activa")
        out: list[tuple] = []
        for row in ws.iter_rows(values_only=True):
            out.append(tuple(row) if row is not None else tuple())
        return out
    finally:
        try:
            wb.close()
        except Exception:
            pass


def _rows_from_xlrd(raw: bytes) -> list[tuple]:
    import xlrd

    book = xlrd.open_workbook(file_contents=raw)
    sheet = book.sheet_by_index(0)
    out: list[tuple] = []
    for r in range(sheet.nrows):
        vals: list[Any] = []
        for c in range(sheet.ncols):
            cell = sheet.cell(r, c)
            # xlrd date type
            if cell.ctype == xlrd.XL_CELL_DATE:
                try:
                    vals.append(xlrd.xldate_as_datetime(cell.value, book.datemode))
                except Exception:
                    vals.append(cell.value)
            else:
                vals.append(cell.value)
        out.append(tuple(vals))
    return out


def _rows_from_pandas(raw: bytes, filename: str) -> list[tuple]:
    import pandas as pd

    name = (filename or "").lower()
    bio = io.BytesIO(raw)
    if name.endswith(".csv") or _magic_excel(raw) == "csv":
        # Separador ; típico en exports LatAm / banco
        try:
            df = pd.read_csv(bio, sep=None, engine="python")
        except Exception:
            bio.seek(0)
            df = pd.read_csv(bio, sep=";", engine="python")
    else:
        engine = "xlrd" if name.endswith(".xls") and not name.endswith(".xlsx") else None
        try:
            df = pd.read_excel(bio, engine=engine)
        except Exception:
            bio.seek(0)
            # Reintento forzado xlrd (bancos renombran .xls → .xlsx)
            df = pd.read_excel(bio, engine="xlrd")
    # Incluir encabezado como fila 0 para que min_row=2 siga siendo datos
    header = tuple("" if c is None else str(c) for c in df.columns.tolist())
    rows: list[tuple] = [header]
    for _, series in df.iterrows():
        rows.append(tuple(None if (isinstance(v, float) and v != v) else v for v in series.tolist()))
    return rows


def _rows_from_html(raw: bytes) -> list[tuple]:
    import pandas as pd

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="replace")
    tables = pd.read_html(io.StringIO(text))
    if not tables:
        raise ValueError("HTML sin tablas")
    df = tables[0]
    header = tuple("" if c is None else str(c) for c in df.columns.tolist())
    rows: list[tuple] = [header]
    for _, series in df.iterrows():
        rows.append(tuple(None if (isinstance(v, float) and v != v) else v for v in series.tolist()))
    return rows


def _cargar_filas_excel(raw: bytes, filename: Optional[str]) -> list[tuple]:
    """
    Lee extracto bancario en varios formatos reales:
    .xlsx (OOXML), .xls (OLE), XML Spreadsheet, HTML-as-xls, CSV.
    """
    kind = _magic_excel(raw)
    name = (filename or "extracto.xlsx").strip()
    errors: list[str] = []

    # 1) OOXML verdadero
    if kind == "xlsx_zip":
        try:
            return _rows_from_openpyxl(raw)
        except Exception as e:
            errors.append(f"openpyxl: {e}")
            try:
                return _rows_from_pandas(raw, name)
            except Exception as e2:
                errors.append(f"pandas: {e2}")

    # 2) Excel 97-2003 OLE (.xls)
    if kind == "xls_ole" or name.lower().endswith(".xls"):
        try:
            return _rows_from_xlrd(raw)
        except Exception as e:
            errors.append(f"xlrd: {e}")
            try:
                return _rows_from_pandas(raw, name if name.lower().endswith(".xls") else "a.xls")
            except Exception as e2:
                errors.append(f"pandas-xls: {e2}")

    # 3) HTML exportado como .xls/.xlsx
    if kind == "html" or (kind == "desconocido" and b"<table" in raw[:8000].lower()):
        try:
            return _rows_from_html(raw)
        except Exception as e:
            errors.append(f"html: {e}")

    # 4) CSV / XML / último recurso pandas
    if kind in ("csv", "xls_xml", "desconocido", "xlsx_zip"):
        try:
            return _rows_from_pandas(raw, name)
        except Exception as e:
            errors.append(f"pandas-fallback: {e}")

    if kind == "xls_ole":
        raise HTTPException(
            status_code=400,
            detail=(
                "El archivo es Excel antiguo (.xls). No se pudo leer. "
                "Ábralo en Excel y guarde como .xlsx, o reintente tras el deploy con soporte .xls. "
                f"Detalle: {'; '.join(errors)[:240]}"
            ),
        )
    if kind == "xlsx_zip":
        raise HTTPException(
            status_code=400,
            detail=(
                "Excel .xlsx dañado o incompleto (sin workbook válido). "
                "Vuelva a exportar/guardar como Libro de Excel (.xlsx). "
                f"Detalle: {'; '.join(errors)[:240]}"
            ),
        )
    raise HTTPException(
        status_code=400,
        detail=(
            "No se pudo leer el archivo como Excel/CSV. "
            "Use .xlsx (recomendado), .xls o CSV del extracto bancario. "
            f"Tipo detectado={kind}. Detalle: {'; '.join(errors)[:240]}"
        ),
    )


def _prestamos_aprobados_cedula(db: Session, cedula: str) -> list[Prestamo]:
    c = normalizar_cedula_almacenamiento(cedula) or (cedula or "").strip().upper()
    if not c:
        return []
    rows = list(
        db.execute(
            select(Prestamo)
            .outerjoin(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Prestamo.estado == "APROBADO",
                or_(
                    Prestamo.cedula == c,
                    Cliente.cedula == c,
                ),
            )
            .order_by(Prestamo.id)
        )
        .scalars()
        .all()
    )
    if rows:
        return rows
    dig = _solo_digitos(c)
    if not dig:
        return []
    # Fallback: comparar solo dígitos (ceros a la izquierda / guiones).
    all_ap = list(
        db.execute(
            select(Prestamo)
            .outerjoin(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(Prestamo.estado == "APROBADO")
        )
        .scalars()
        .all()
    )
    out: list[Prestamo] = []
    for p in all_ap:
        pc = _solo_digitos(normalizar_cedula_almacenamiento(p.cedula) or "")
        cc = ""
        if p.cliente_id:
            cli = db.get(Cliente, p.cliente_id)
            if cli:
                cc = _solo_digitos(normalizar_cedula_almacenamiento(cli.cedula) or "")
        if dig in (pc, cc):
            out.append(p)
    return out


def _pagos_aprobados_cedula(db: Session, cedula: str, prestamo_ids: list[int]) -> list[Pago]:
    if not prestamo_ids:
        return []
    c = normalizar_cedula_almacenamiento(cedula) or cedula
    return list(
        db.execute(
            select(Pago).where(
                Pago.prestamo_id.in_(prestamo_ids),
                or_(Pago.cedula_cliente == c, Pago.cedula_cliente.is_(None)),
            )
        )
        .scalars()
        .all()
    )


def _serial_pago_digitos(p: Pago) -> str:
    for cand in (p.numero_documento, p.referencia_pago, p.ref_norm, p.doc_canon_numero):
        d = _solo_digitos(cand or "")
        if d:
            return d
    return ""


def _evaluar_fila(
    db: Session,
    *,
    fecha: Optional[date],
    desc: str,
    serial_raw: str,
    monto: Optional[float],
) -> dict[str, Any]:
    cedula = extraer_cedula_descripcion(desc)
    serial_norm = _solo_digitos(serial_raw) or (
        normalize_documento(serial_raw) or ""
    ).strip()

    if not cedula:
        return {
            "cedula": None,
            "serial_norm": serial_norm or None,
            "estado": "PARSE_ERROR",
            "detalle": "No se pudo extraer cédula de Descripción",
            "similitud_pct": None,
            "pago_id_match": None,
            "prestamo_id": None,
        }
    if not serial_norm:
        return {
            "cedula": cedula,
            "serial_norm": None,
            "estado": "PARSE_ERROR",
            "detalle": "Referencia/serial vacío",
            "similitud_pct": None,
            "pago_id_match": None,
            "prestamo_id": None,
        }
    if monto is None or monto <= 0:
        return {
            "cedula": cedula,
            "serial_norm": serial_norm,
            "estado": "PARSE_ERROR",
            "detalle": "Monto Haber inválido o <= 0",
            "similitud_pct": None,
            "pago_id_match": None,
            "prestamo_id": None,
        }
    if fecha is None:
        return {
            "cedula": cedula,
            "serial_norm": serial_norm,
            "estado": "PARSE_ERROR",
            "detalle": "Fecha inválida",
            "similitud_pct": None,
            "pago_id_match": None,
            "prestamo_id": None,
        }

    prestamos = _prestamos_aprobados_cedula(db, cedula)
    if not prestamos:
        return {
            "cedula": cedula,
            "serial_norm": serial_norm,
            "estado": "SIN_PRESTAMO",
            "detalle": "Sin préstamo APROBADO para esta cédula",
            "similitud_pct": None,
            "pago_id_match": None,
            "prestamo_id": None,
        }
    if len(prestamos) > 1:
        return {
            "cedula": cedula,
            "serial_norm": serial_norm,
            "estado": "VARIOS_PRESTAMOS",
            "detalle": f"{len(prestamos)} préstamos APROBADO; no se importa automático",
            "similitud_pct": None,
            "pago_id_match": None,
            "prestamo_id": None,
        }

    prestamo_id = int(prestamos[0].id)
    pagos = _pagos_aprobados_cedula(db, cedula, [prestamo_id])
    # Ampliar: pagos de la cédula en ese préstamo (también por cédula en pago)
    pagos2 = list(
        db.execute(
            select(Pago).where(
                or_(
                    Pago.prestamo_id == prestamo_id,
                    Pago.cedula_cliente == cedula,
                )
            )
        )
        .scalars()
        .all()
    )
    by_id = {int(p.id): p for p in (pagos + pagos2)}
    pagos = list(by_id.values())

    for p in pagos:
        if _serial_pago_digitos(p) == serial_norm:
            return {
                "cedula": cedula,
                "serial_norm": serial_norm,
                "estado": "IGUAL_100",
                "detalle": f"100% cédula+serial (pago_id={p.id})",
                "similitud_pct": 100.0,
                "pago_id_match": int(p.id),
                "prestamo_id": prestamo_id,
            }

    best_pct = 0.0
    best_pid: Optional[int] = None
    for p in pagos:
        sp = _serial_pago_digitos(p)
        if not sp:
            continue
        pct = _similitud(serial_norm, sp)
        if pct > best_pct:
            best_pct = pct
            best_pid = int(p.id)

    # Umbral de “semejante” (manual): >= 70 y < 100
    if best_pct >= 70.0:
        return {
            "cedula": cedula,
            "serial_norm": serial_norm,
            "estado": "SEMEJANTE",
            "detalle": f"Serial semejante {best_pct}% al pago_id={best_pid}",
            "similitud_pct": best_pct,
            "pago_id_match": best_pid,
            "prestamo_id": prestamo_id,
        }

    return {
        "cedula": cedula,
        "serial_norm": serial_norm,
        "estado": "SE_PUEDE_IMPORTAR",
        "detalle": "No existe serial en préstamos APROBADO de esta cédula",
        "similitud_pct": best_pct if best_pct > 0 else None,
        "pago_id_match": best_pid,
        "prestamo_id": prestamo_id,
    }


def crear_lote_desde_excel(
    db: Session, archivo: UploadFile, usuario_id: Optional[int]
) -> dict[str, Any]:
    ensure_schema(db)
    raw = archivo.file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    rows = _cargar_filas_excel(raw, archivo.filename)

    lote = ImportacionExtractoLote(
        usuario_id=usuario_id,
        archivo_nombre=(archivo.filename or "extracto.xlsx")[:255],
        estado="COMPARADO",
    )
    db.add(lote)
    db.flush()

    stats: dict[str, int] = {}
    n = 0
    # Fila 0 = encabezado; datos desde índice 1 (equiv. Excel fila 2)
    for i, row in enumerate(rows[1:], start=2):
        if not row:
            continue
        fecha = _parse_fecha(_cell(row, 0))
        desc = str(_cell(row, 1) or "").strip()
        # Plantilla banco: Referencia col G (índice 6), Haber col H (índice 7)
        serial_raw = str(_cell(row, 6) or "").strip()
        monto = _parse_monto(_cell(row, 7))
        # Compat A/B/C/D si el usuario ya normalizó: Fecha|Cedula|Serial|Monto
        if not serial_raw and len(row) >= 4:
            maybe_ced = str(_cell(row, 1) or "").strip()
            maybe_ser = str(_cell(row, 2) or "").strip()
            maybe_mon = _parse_monto(_cell(row, 3))
            if maybe_ser and maybe_mon is not None:
                desc = maybe_ced if ":" not in maybe_ced else desc
                if re.match(r"^[VEJG]-?\d", maybe_ced, re.I):
                    desc = f"DP:{maybe_ced}"
                serial_raw = maybe_ser
                monto = maybe_mon

        if not desc and not serial_raw and monto is None and fecha is None:
            continue
        if n >= MAX_FILAS:
            break

        ev = _evaluar_fila(
            db,
            fecha=fecha,
            desc=desc,
            serial_raw=serial_raw,
            monto=monto,
        )
        fila = ImportacionExtractoFila(
            lote_id=lote.id,
            fila_excel=i,
            fecha_deposito=fecha,
            descripcion_raw=desc[:2000] if desc else None,
            cedula=ev.get("cedula"),
            serial=serial_raw[:100] if serial_raw else None,
            serial_norm=ev.get("serial_norm"),
            monto_usd=Decimal(str(monto)) if monto is not None else None,
            estado=ev["estado"],
            similitud_pct=(
                Decimal(str(ev["similitud_pct"]))
                if ev.get("similitud_pct") is not None
                else None
            ),
            pago_id_match=ev.get("pago_id_match"),
            prestamo_id=ev.get("prestamo_id"),
            detalle=(ev.get("detalle") or "")[:2000],
        )
        db.add(fila)
        stats[ev["estado"]] = stats.get(ev["estado"], 0) + 1
        n += 1

    if n == 0:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="No hay filas válidas. Plantilla: Fecha | Descripción | … | Referencia | Haber",
        )

    lote.notas = str(stats)
    db.commit()
    db.refresh(lote)
    return {
        "lote": _lote_dict(lote, stats),
        "stats": stats,
        "filas": n,
    }


def _lote_dict(lote: ImportacionExtractoLote, stats: Optional[dict] = None) -> dict:
    return {
        "id": lote.id,
        "archivo_nombre": lote.archivo_nombre,
        "estado": lote.estado,
        "usuario_id": lote.usuario_id,
        "creado_en": lote.creado_en.isoformat() if lote.creado_en else None,
        "stats": stats,
    }


def listar_lotes(db: Session, limit: int = 30) -> list[dict]:
    ensure_schema(db)
    rows = (
        db.execute(
            select(ImportacionExtractoLote)
            .order_by(ImportacionExtractoLote.id.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [_lote_dict(r) for r in rows]


def listar_filas(
    db: Session,
    lote_id: int,
    *,
    estado: Optional[str] = None,
    solo_importables: bool = False,
) -> list[dict]:
    ensure_schema(db)
    lote = db.get(ImportacionExtractoLote, lote_id)
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    q = select(ImportacionExtractoFila).where(
        ImportacionExtractoFila.lote_id == lote_id
    )
    if solo_importables:
        q = q.where(ImportacionExtractoFila.estado == "SE_PUEDE_IMPORTAR")
    elif estado:
        q = q.where(ImportacionExtractoFila.estado == estado)
    q = q.order_by(ImportacionExtractoFila.fila_excel)
    rows = db.execute(q).scalars().all()
    return [_fila_dict(f) for f in rows]


def _fila_dict(f: ImportacionExtractoFila) -> dict:
    return {
        "id": f.id,
        "lote_id": f.lote_id,
        "fila_excel": f.fila_excel,
        "fecha_deposito": f.fecha_deposito.isoformat() if f.fecha_deposito else None,
        "descripcion_raw": f.descripcion_raw,
        "cedula": f.cedula,
        "serial": f.serial,
        "serial_norm": f.serial_norm,
        "monto_usd": float(f.monto_usd) if f.monto_usd is not None else None,
        "estado": f.estado,
        "similitud_pct": float(f.similitud_pct) if f.similitud_pct is not None else None,
        "pago_id_match": f.pago_id_match,
        "prestamo_id": f.prestamo_id,
        "pago_id_creado": f.pago_id_creado,
        "detalle": f.detalle,
        "visto": bool(f.visto),
        "importado": bool(f.importado),
        "puede_ok_importar": f.estado == "SE_PUEDE_IMPORTAR" and not f.importado,
    }


def marcar_visto(db: Session, fila_ids: list[int]) -> dict[str, Any]:
    ensure_schema(db)
    ok = 0
    for fid in fila_ids:
        f = db.get(ImportacionExtractoFila, int(fid))
        if not f:
            continue
        if f.estado not in ("SEMEJANTE", "IGUAL_100", "SE_PUEDE_IMPORTAR"):
            continue
        if f.importado:
            continue
        f.visto = True
        f.estado = "VISTO"
        f.detalle = ((f.detalle or "") + " | Marcado Visto (revisión manual)").strip(" |")
        ok += 1
    db.commit()
    return {"ok": True, "marcados": ok}


def _guardar_placeholder_imagen(db: Session) -> str:
    img_id = uuid.uuid4().hex
    db.add(
        PagoComprobanteImagen(
            id=img_id,
            content_type="image/png",
            imagen_data=_PNG_BLANCO_1X1,
        )
    )
    db.flush()
    return img_id


def _crear_pago_desde_fila(db: Session, f: ImportacionExtractoFila) -> dict[str, Any]:
    """Crea pago con datos del Excel + placeholder. No inventa fecha/serial/monto."""
    if f.estado != "SE_PUEDE_IMPORTAR" or f.importado:
        return {"ok": False, "motivo": "no_importable", "fila_id": f.id}
    if not f.cedula or not f.serial_norm or f.monto_usd is None or not f.fecha_deposito:
        return {"ok": False, "motivo": "datos_incompletos", "fila_id": f.id}
    if not f.prestamo_id:
        return {"ok": False, "motivo": "sin_prestamo", "fila_id": f.id}

    numero_doc = compose_numero_documento_almacenado(f.serial or f.serial_norm, None)
    if not numero_doc:
        return {"ok": False, "motivo": "serial_invalido", "fila_id": f.id}
    if numero_documento_ya_registrado(db, numero_doc):
        f.estado = "IGUAL_100"
        f.detalle = "Serial ya registrado al importar (no se duplicó)"
        return {"ok": False, "motivo": "duplicado_documento", "fila_id": f.id}

    # Revalidar 100% cédula+serial vs APROBADO
    ev = _evaluar_fila(
        db,
        fecha=f.fecha_deposito,
        desc=f.descripcion_raw or f"DP:{f.cedula}",
        serial_raw=f.serial or f.serial_norm,
        monto=float(f.monto_usd),
    )
    if ev["estado"] == "IGUAL_100":
        f.estado = "IGUAL_100"
        f.pago_id_match = ev.get("pago_id_match")
        f.similitud_pct = Decimal("100")
        f.detalle = ev.get("detalle")
        return {"ok": False, "motivo": "igual_100", "fila_id": f.id}

    prest = db.get(Prestamo, int(f.prestamo_id))
    if not prest or str(prest.estado or "").upper() != "APROBADO":
        return {"ok": False, "motivo": "prestamo_no_aprobado", "fila_id": f.id}

    img_id = _guardar_placeholder_imagen(db)
    fecha_dt = datetime.combine(f.fecha_deposito, dt_time(12, 0, 0))
    monto = Decimal(str(round(float(f.monto_usd), 2)))

    pago = Pago(
        prestamo_id=int(f.prestamo_id),
        cedula_cliente=f.cedula,
        fecha_pago=fecha_dt,
        monto_pagado=monto,
        numero_documento=numero_doc[:100],
        referencia_pago=(f.serial or f.serial_norm)[:100],
        institucion_bancaria="Mercantil",
        estado="PAGADO",
        conciliado=True,
        verificado_concordancia="SI",
        fecha_conciliacion=datetime.utcnow(),
        usuario_registro=USUARIO_REGISTRO,
        notas="[IMPORTACION_EXTRACTO] placeholder imagen; origen Excel extracto",
        documento_nombre="placeholder-extracto.png",
        documento_tipo="image/png",
        documento_ruta=img_id,
        link_comprobante=None,
        moneda_registro="USD",
    )
    db.add(pago)
    db.flush()

    try:
        from app.api.v1.endpoints import pagos as pagos_ep

        cc, cp = pagos_ep._aplicar_pago_a_cuotas_interno(pago, db)
        pagos_ep._estado_conciliacion_post_cascada(pago, cc, cp)
    except Exception as e:
        logger.warning(
            "[importacion-extracto] cascada pago_id=%s: %s", pago.id, e
        )

    f.pago_id_creado = int(pago.id)
    f.importado = True
    f.estado = "IMPORTADO"
    f.detalle = f"Importado pago_id={pago.id} (placeholder)"
    return {"ok": True, "fila_id": f.id, "pago_id": int(pago.id)}


def importar_filas(db: Session, fila_ids: list[int]) -> dict[str, Any]:
    """Autoriza importación (OK individual o lote). Solo SE_PUEDE_IMPORTAR."""
    ensure_schema(db)
    resultados = []
    for fid in fila_ids:
        f = db.get(ImportacionExtractoFila, int(fid))
        if not f:
            resultados.append({"ok": False, "fila_id": fid, "motivo": "no_existe"})
            continue
        try:
            r = _crear_pago_desde_fila(db, f)
            resultados.append(r)
        except Exception as e:
            db.rollback()
            ensure_schema(db)
            logger.exception("[importacion-extracto] importar fila %s", fid)
            resultados.append(
                {"ok": False, "fila_id": fid, "motivo": "error", "detalle": str(e)[:200]}
            )
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar: {e}") from e
    ok_n = sum(1 for r in resultados if r.get("ok"))
    return {"ok": True, "importados": ok_n, "resultados": resultados}
