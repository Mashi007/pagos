# -*- coding: utf-8 -*-
from pathlib import Path
import re

P = Path(__file__).resolve().parents[1] / "backend/app/api/v1/endpoints/pagos.py"
s = P.read_text(encoding="utf-8")

imp = "from app.services.pago_numero_documento import numero_documento_ya_registrado\n"
if imp not in s:
    needle = "from app.core.documento import normalize_documento\n"
    s = s.replace(needle, needle + imp, 1)

s = s.replace("_numero_documento_ya_existe(", "numero_documento_ya_registrado(")

s = re.sub(
    r"\ndef _numero_documento_ya_existe\([\s\S]*?return db\.scalar\(q\) is not None\n\n\n\n",
    "\n",
    s,
    count=1,
)

new_validar = '''def validar_filas_batch(

    body: ValidarFilasBatchBody = Body(...),

    db: Session = Depends(get_db),

):

    """

    Valida en lote (carga masiva / preview):

    - Cédulas: deben existir en tabla préstamos (al menos un crédito con esa cédula normalizada).

    - Nº documento: clave canónica única global; ya usada en `pagos` o en `pagos_con_errores` → duplicado.

      (Un solo registro por documento; las cuotas referencian ese pago vía pago_id.)

    """

    cedulas_norm = list(

        {

            c.strip().replace("-", "").upper()

            for c in (body.cedulas or [])

            if c and c.strip()

        }

    )

    cedulas_existentes: set[str] = set()

    if cedulas_norm:

        pc = func.upper(func.replace(Prestamo.cedula, "-", ""))

        rows = db.execute(select(pc).where(pc.in_(cedulas_norm)).distinct()).all()

        cedulas_existentes = {r[0] for r in rows if r and r[0]}

    documentos_duplicados: list[dict] = []

    docs_norm = [

        normalize_documento(d)

        for d in (body.documentos or [])

        if d and d.strip()

    ]

    docs_norm_limpios = [d for d in docs_norm if d]

    if docs_norm_limpios:

        rows_pagos = db.execute(

            select(

                Pago.numero_documento,

                Pago.id,

                Pago.cedula_cliente,

                Pago.fecha_pago,

                Pago.monto_pagado,

            ).where(Pago.numero_documento.in_(docs_norm_limpios))

        ).all()

        for row in rows_pagos:

            documentos_duplicados.append(

                {

                    "numero_documento": row[0],

                    "pago_id": row[1],

                    "cedula": row[2],

                    "fecha_pago": row[3].isoformat() if row[3] else None,

                    "monto_pagado": float(row[4]) if row[4] else 0,

                    "estado": "duplicado",

                    "origen": "pagos",

                }

            )

        rows_pce = db.execute(

            select(

                PagoConError.numero_documento,

                PagoConError.id,

                PagoConError.cedula_cliente,

                PagoConError.fecha_pago,

                PagoConError.monto_pagado,

            ).where(PagoConError.numero_documento.in_(docs_norm_limpios))

        ).all()

        for row in rows_pce:

            documentos_duplicados.append(

                {

                    "numero_documento": row[0],

                    "pago_con_error_id": row[1],

                    "cedula": row[2],

                    "fecha_pago": row[3].isoformat() if row[3] else None,

                    "monto_pagado": float(row[4]) if row[4] else 0,

                    "estado": "duplicado",

                    "origen": "pagos_con_errores",

                }

            )

    return {

        "cedulas_existentes": list(cedulas_existentes),

        "documentos_duplicados": documentos_duplicados,

    }





'''

m_router = re.search(
    r"@router\.post\(\"/validar-filas-batch\"[\s\S]*?^def validar_filas_batch\(",
    s,
    re.MULTILINE,
)
if not m_router:
    raise SystemExit("decorator validar-filas-batch not found")
m_end = s.find('@router.post("/guardar-fila-editable"')
if m_end < 0:
    raise SystemExit("guardar-fila-editable not found")
start_fn = s.find("def validar_filas_batch", m_router.start())
if start_fn < 0 or start_fn > m_end:
    raise SystemExit("def validar_filas_batch not found in range")
s = s[:start_fn] + new_validar + s[m_end:]

# guardar_fila_editable block
old_guard_dup = """        # Validar duplicado en BD (documento)

        if numero_doc_norm:

            pago_existente = db.execute(

                select(Pago).where(Pago.numero_documento == numero_doc_norm).limit(1)

            ).first()

            if pago_existente:

                raise HTTPException(

                    status_code=409,

                    detail=f"Ya existe un pago con este documento: {numero_doc_norm}"

                )



        # Si prestamo_id es None, buscar automáticamente

        if prestamo_id is None:

            cliente_row = db.execute(

                select(Prestamo.id)

                .join(Cliente, Prestamo.cliente_id == Cliente.id)

                .where(Cliente.cedula == cedula)

                .limit(1)

            ).first()

            if cliente_row:

                prestamo_id = cliente_row[0]

"""
new_guard_dup = """        # Validar duplicado global (pagos + pagos_con_errores)

        if numero_doc_norm and numero_documento_ya_registrado(db, numero_doc_norm):

            raise HTTPException(

                status_code=409,

                detail=f"Ya existe un registro con este documento: {numero_doc_norm}",

            )



        # Si prestamo_id es None, buscar por cédula en préstamos (normalizada)

        if prestamo_id is None:

            ced_norm = (

                cedula.strip().replace("-", "").upper()

                if cedula

                else ""

            )

            if ced_norm:

                pc = func.upper(func.replace(Prestamo.cedula, "-", ""))

                prest_row = db.execute(

                    select(Prestamo.id)

                    .where(pc == ced_norm)

                    .order_by(Prestamo.id.desc())

                    .limit(1)

                ).first()

                if prest_row:

                    prestamo_id = prest_row[0]



        if prestamo_id is None:

            raise HTTPException(

                status_code=400,

                detail="La cédula no tiene préstamo asociado; registre el crédito antes de cargar el pago.",

            )

"""
if old_guard_dup not in s:
    raise SystemExit("guardar_fila_editable dup block not found")
s = s.replace(old_guard_dup, new_guard_dup, 1)

old_pre = """        if docs_no_vacios:

            rows = db.execute(select(Pago.numero_documento).where(Pago.numero_documento.in_(docs_no_vacios))).scalars().all()

            existing_docs = {r for r in rows if r}

        # Preload: ids de préstamos válidos (una sola consulta)

        prestamo_ids = [p.prestamo_id for p in pagos_list if p.prestamo_id]

        valid_prestamo_ids: set[int] = set()

        if prestamo_ids:

            ids_rows = db.execute(select(Prestamo.id).where(Prestamo.id.in_(prestamo_ids))).scalars().all()

            valid_prestamo_ids = {r for r in ids_rows if r is not None}

        # Preload: cédulas de clientes que existen (una sola consulta)

        cedulas_con_prestamo = list({(p.cedula_cliente or "").strip().upper() for p in pagos_list if (p.cedula_cliente or "").strip() and p.prestamo_id})

        valid_cedulas: set[str] = set()

        if cedulas_con_prestamo:

            ced_rows = db.execute(select(Cliente.cedula).where(func.upper(Cliente.cedula).in_(cedulas_con_prestamo))).scalars().all()

            valid_cedulas = {(r or "").strip().upper() for r in ced_rows if r}
"""
new_pre = """        if docs_no_vacios:

            rows = db.execute(select(Pago.numero_documento).where(Pago.numero_documento.in_(docs_no_vacios))).scalars().all()

            existing_docs = {r for r in rows if r}

            rows_pe = db.execute(

                select(PagoConError.numero_documento).where(

                    PagoConError.numero_documento.in_(docs_no_vacios)

                )

            ).scalars().all()

            existing_docs.update({r for r in rows_pe if r})

        # Preload: ids de préstamos válidos (una sola consulta)

        prestamo_ids = [p.prestamo_id for p in pagos_list if p.prestamo_id]

        valid_prestamo_ids: set[int] = set()

        if prestamo_ids:

            ids_rows = db.execute(select(Prestamo.id).where(Prestamo.id.in_(prestamo_ids))).scalars().all()

            valid_prestamo_ids = {r for r in ids_rows if r is not None}

        # Preload: cédulas que tienen al menos un préstamo (normalizadas)

        cedulas_payload = list(

            {

                (p.cedula_cliente or "").strip().replace("-", "").upper()

                for p in pagos_list

                if (p.cedula_cliente or "").strip()

            }

        )

        valid_cedulas_prestamo: set[str] = set()

        if cedulas_payload:

            pc = func.upper(func.replace(Prestamo.cedula, "-", ""))

            ced_rows = db.execute(select(pc).where(pc.in_(cedulas_payload)).distinct()).scalars().all()

            valid_cedulas_prestamo = {(r or "").strip().replace("-", "").upper() for r in ced_rows if r}

        # Compat: cliente existe cuando el payload trae prestamo_id explícito

        cedulas_con_prestamo = list(

            {

                (p.cedula_cliente or "").strip().upper()

                for p in pagos_list

                if (p.cedula_cliente or "").strip() and p.prestamo_id

            }

        )

        valid_cedulas: set[str] = set()

        if cedulas_con_prestamo:

            ced_rows_c = db.execute(

                select(Cliente.cedula).where(func.upper(Cliente.cedula).in_(cedulas_con_prestamo))

            ).scalars().all()

            valid_cedulas = {(r or "").strip().upper() for r in ced_rows_c if r}
"""
if old_pre not in s:
    raise SystemExit("batch preload block not found")
s = s.replace(old_pre, new_pre, 1)

old_val_loop = """            cedula_normalizada = (payload.cedula_cliente or "").strip().upper()

            if payload.prestamo_id and payload.prestamo_id not in valid_prestamo_ids:

                validation_errors.append({"index": idx, "error": f"Credito #{payload.prestamo_id} no existe.", "status_code": 400})

                continue

            if cedula_normalizada and payload.prestamo_id and cedula_normalizada not in valid_cedulas:

                validation_errors.append({"index": idx, "error": f"No existe cliente con cedula {cedula_normalizada}", "status_code": 404})

                continue
"""
new_val_loop = """            cedula_normalizada = (payload.cedula_cliente or "").strip().upper()

            ced_norm_prest = (payload.cedula_cliente or "").strip().replace("-", "").upper()

            if ced_norm_prest and ced_norm_prest not in valid_cedulas_prestamo:

                validation_errors.append(

                    {

                        "index": idx,

                        "error": f"La cédula no tiene préstamo registrado: {cedula_normalizada}",

                        "status_code": 400,

                    }

                )

                continue

            if payload.prestamo_id and payload.prestamo_id not in valid_prestamo_ids:

                validation_errors.append({"index": idx, "error": f"Credito #{payload.prestamo_id} no existe.", "status_code": 400})

                continue

            if cedula_normalizada and payload.prestamo_id and cedula_normalizada not in valid_cedulas:

                validation_errors.append({"index": idx, "error": f"No existe cliente con cedula {cedula_normalizada}", "status_code": 404})

                continue
"""
if old_val_loop not in s:
    raise SystemExit("batch validation loop not found")
s = s.replace(old_val_loop, new_val_loop, 1)

P.write_text(s, encoding="utf-8")
print("OK")
