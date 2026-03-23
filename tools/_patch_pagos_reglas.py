# -*- coding: utf-8 -*-
"""Aplica mejoras reglas: documento unico (pagos+pce), cedula vs prestamos."""
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "backend/app/api/v1/endpoints/pagos.py"
s = P.read_text(encoding="utf-8")

imp = "from app.services.pago_numero_documento import numero_documento_ya_registrado\n"
if imp not in s:
    needle = "from app.core.documento import normalize_documento\n"
    if needle not in s:
        raise SystemExit("import anchor not found")
    s = s.replace(needle, needle + imp, 1)

s = s.replace("_numero_documento_ya_existe(", "numero_documento_ya_registrado(")

old_fn = '''def _numero_documento_ya_existe(

    db: Session, numero_documento: Optional[str], exclude_pago_id: Optional[int] = None

) -> bool:

    """Regla general: no duplicados en documentos. Comprueba si ya existe un pago con ese Nº documento."""

    num = normalize_documento(numero_documento)

    if not num:

        return False

    q = select(Pago.id).where(Pago.numero_documento == num)

    if exclude_pago_id is not None:

        q = q.where(Pago.id != exclude_pago_id)

    return db.scalar(q) is not None





'''

if old_fn in s:
    s = s.replace(old_fn, "", 1)
else:
    # Windows line endings / spacing variants
    import re

    s = re.sub(
        r"\ndef _numero_documento_ya_existe\([\s\S]*?return db\.scalar\(q\) is not None\n\n\n\n",
        "\n",
        s,
        count=1,
    )

# --- validar_filas_batch docstring + body ---
old_batch = '''    """

    Valida en lote:

    - Cédulas: deben existir en tabla clientes

    - Documentos: se verifica en tabla CUOTAS (si existe → confirmado/válido)

                  Si NO existe en CUOTAS pero SÍ en PAGOS → duplicado sin aplicar

    Retorna cédulas válidas y documentos con estado de confirmación.

    """

    from app.models.cuota import Cuota

    

    # Normalizar cédulas (sin guión, uppercase)

    cedulas_norm = list({

        c.strip().replace("-", "").upper()

        for c in (body.cedulas or [])

        if c and c.strip()

    })



    # Cédulas que existen en tabla clientes

    cedulas_existentes: set[str] = set()

    if cedulas_norm:

        # Búsqueda que acepta cédula con o sin guión en BD

        rows = db.execute(

            select(Cliente.cedula).where(func.replace(Cliente.cedula, "-", "").in_(cedulas_norm))

        ).all()

        cedulas_existentes = {r[0].strip().replace("-", "").upper() for r in rows}



    # Documentos: verificar contra CUOTAS (si existe → confirmado) y PAGOS (si existe sin cuota → duplicado)

    documentos_confirmados: list[dict] = []  # Documentos encontrados en CUOTAS (pago ya aplicado)

    documentos_duplicados: list[dict] = []   # Documentos en PAGOS pero NO aplicados a CUOTA

    

    docs_norm = [

        normalize_documento(d)

        for d in (body.documentos or [])

        if d and d.strip()

    ]

    docs_norm_limpios = [d for d in docs_norm if d]

    

    if docs_norm_limpios:

        # Buscar documentos que YA EXISTEN en tabla PAGOS (sin importar si están en CUOTAS)

        # Si existe en PAGOS = DUPLICADO (rechazar)

        rows_pagos = db.execute(

            select(Pago.numero_documento, Pago.id, Pago.cedula_cliente, 

                   Pago.fecha_pago, Pago.monto_pagado)

            .where(Pago.numero_documento.in_(docs_norm_limpios))

        ).all()

        

        for row in rows_pagos:

            documentos_duplicados.append({

                "numero_documento": row[0],

                "pago_id": row[1],

                "cedula": row[2],

                "fecha_pago": row[3].isoformat() if row[3] else None,

                "monto_pagado": float(row[4]) if row[4] else 0,

                "estado": "duplicado",

            })



    return {

        "cedulas_existentes": list(cedulas_existentes),

        "documentos_duplicados": documentos_duplicados,  # Documentos que YA existen en tabla PAGOS

    }
'''

new_batch = '''    """

    Valida en lote (carga masiva / preview):

    - Cédulas: deben existir en tabla préstamos (al menos un crédito con esa cédula normalizada).

    - Nº documento: clave canónica única global; ya usada en `pagos` o en `pagos_con_errores` → duplicado.

      (Un solo pago por documento; las cuotas referencian ese pago via pago_id — no hay segundo uso del mismo documento.)

    """

    # Normalizar cédulas (sin guión, uppercase)

    cedulas_norm = list({

        c.strip().replace("-", "").upper()

        for c in (body.cedulas or [])

        if c and c.strip()

    })



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

if old_batch in s:
    s = s.replace(old_batch, new_batch, 1)
else:
    raise SystemExit("validar_filas_batch block not found — archivo cambió")

# --- guardar_fila_editable: duplicado + autopick prestamo ---
old_guard_dup = '''        # Validar duplicado en BD (documento)

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

'''

new_guard_dup = '''        # Validar duplicado global (pagos + pagos_con_errores)

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

'''

if old_guard_dup in s:
    s = s.replace(old_guard_dup, new_guard_dup, 1)
else:
    raise SystemExit("guardar_fila_editable block not found")

# --- crear_pagos_batch: existing_docs + cédula con préstamo ---
old_pre = '''        if docs_no_vacios:

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
'''

new_pre = '''        if docs_no_vacios:

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

        # Compat: valid_cedulas contra clientes solo cuando hay prestamo_id en payload (crédito explícito)

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
'''

if old_pre in s:
    s = s.replace(old_pre, new_pre, 1)
else:
    raise SystemExit("crear_pagos_batch preload block not found")

old_val_loop = '''            cedula_normalizada = (payload.cedula_cliente or "").strip().upper()

            if payload.prestamo_id and payload.prestamo_id not in valid_prestamo_ids:

                validation_errors.append({"index": idx, "error": f"Credito #{payload.prestamo_id} no existe.", "status_code": 400})

                continue

            if cedula_normalizada and payload.prestamo_id and cedula_normalizada not in valid_cedulas:

                validation_errors.append({"index": idx, "error": f"No existe cliente con cedula {cedula_normalizada}", "status_code": 404})

                continue
'''

new_val_loop = '''            cedula_normalizada = (payload.cedula_cliente or "").strip().upper()

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
'''

if old_val_loop in s:
    s = s.replace(old_val_loop, new_val_loop, 1)
else:
    raise SystemExit("batch validation loop block not found")

P.write_text(s, encoding="utf-8")
print("pagos.py patched OK")
