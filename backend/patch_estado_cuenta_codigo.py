# -*- coding: utf-8 -*-
"""Add solicitar-codigo and verificar-codigo endpoints to estado_cuenta_publico."""
import re

path = "app/api/v1/endpoints/estado_cuenta_publico.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1) Add imports
old_imports = "from datetime import date\nfrom typing import List, Optional"
new_imports = "from datetime import date, datetime, timedelta\nimport random\nimport string\nfrom typing import List, Optional"
if "timedelta" not in c:
    c = c.replace(old_imports, new_imports, 1)

old_rl = "check_rate_limit_estado_cuenta_solicitar,\n)"
new_rl = "check_rate_limit_estado_cuenta_solicitar,\n    check_rate_limit_estado_cuenta_verificar,\n)"
if "check_rate_limit_estado_cuenta_verificar" not in c:
    c = c.replace(old_rl, new_rl, 1)

c = c.replace(
    "from app.models.cuota import Cuota\nfrom app.api.v1.endpoints.validadores",
    "from app.models.cuota import Cuota\nfrom app.models.estado_cuenta_codigo import EstadoCuentaCodigo\nfrom app.api.v1.endpoints.validadores",
)

# 2) Add Pydantic models and CODIGO_EXPIRA_MINUTES
c = c.replace(
    "class SolicitarEstadoCuentaResponse(BaseModel):\n    ok: bool\n    pdf_base64: Optional[str] = None\n    mensaje: Optional[str] = None\n    error: Optional[str] = None\n\n\ndef _cedula_lookup",
    """class SolicitarEstadoCuentaResponse(BaseModel):
    ok: bool
    pdf_base64: Optional[str] = None
    mensaje: Optional[str] = None
    error: Optional[str] = None


class SolicitarCodigoRequest(BaseModel):
    cedula: str


class SolicitarCodigoResponse(BaseModel):
    ok: bool
    mensaje: Optional[str] = None
    error: Optional[str] = None


class VerificarCodigoRequest(BaseModel):
    cedula: str
    codigo: str


class VerificarCodigoResponse(BaseModel):
    ok: bool
    pdf_base64: Optional[str] = None
    error: Optional[str] = None


CODIGO_EXPIRA_MINUTES = 15


def _cedula_lookup""",
)

# 3) Add helper _obtener_datos_pdf and _generar_codigo_numero
# Insert after _cedula_lookup and before _obtener_amortizacion_prestamo
_cedula_end = "return valor.replace(\"-\", \"\") if valor else \"\"\n\ndef _obtener_amortizacion_prestamo"
_datos_helper = r'''
def _generar_codigo_6() -> str:
    return "".join(random.choices(string.digits, k=6))


def _obtener_datos_pdf(db: Session, cedula_lookup: str):
    """Obtiene cliente y datos para PDF. Retorna dict o None si no existe cliente."""
    cliente_row = db.execute(
        select(Cliente).where(func.replace(Cliente.cedula, "-", "") == cedula_lookup)
    ).scalars().first()
    if not cliente_row:
        return None
    cliente = cliente_row[0] if hasattr(cliente_row, "__getitem__") else cliente_row
    cliente_id = getattr(cliente, "id", None)
    nombre = (getattr(cliente, "nombres", None) or "").strip()
    email = (getattr(cliente, "email", None) or "").strip()
    cedula_display = (getattr(cliente, "cedula", None) or "").strip()
    prestamos_rows = db.execute(
        select(Prestamo).where(Prestamo.cliente_id == cliente_id)
    ).scalars().all()
    prestamos_list = []
    prestamo_ids = []
    for row in prestamos_rows:
        p = row[0] if hasattr(row, "__getitem__") else row
        prestamo_ids.append(p.id)
        prestamos_list.append({
            "id": p.id,
            "producto": getattr(p, "producto", None) or "",
            "total_financiamiento": float(getattr(p, "total_financiamiento", 0) or 0),
            "estado": getattr(p, "estado", None) or "",
        })
    cuotas_pendientes = []
    total_pendiente = 0.0
    if prestamo_ids:
        cuotas_rows = db.execute(
            select(Cuota)
            .where(Cuota.prestamo_id.in_(prestamo_ids), Cuota.fecha_pago.is_(None))
            .order_by(Cuota.prestamo_id, Cuota.numero_cuota)
        ).scalars().all()
        for cu in cuotas_rows:
            c = cu[0] if hasattr(cu, "__getitem__") else cu
            m = float(getattr(c, "monto", 0) or 0)
            total_pendiente += m
            cuotas_pendientes.append({
                "prestamo_id": getattr(c, "prestamo_id", ""),
                "numero_cuota": getattr(c, "numero_cuota", ""),
                "fecha_vencimiento": (getattr(c, "fecha_vencimiento", None) or "").isoformat() if getattr(c, "fecha_vencimiento", None) else "",
                "monto": m,
                "estado": getattr(c, "estado", None) or "PENDIENTE",
            })
    fecha_corte = date.today()
    amortizaciones_por_prestamo = []
    for p in prestamos_list:
        estado = (p.get("estado") or "").strip().upper()
        if estado not in ("APROBADO", "DESEMBOLSADO"):
            continue
        prestamo_id = p.get("id")
        if not prestamo_id:
            continue
        cuotas = _obtener_amortizacion_prestamo(db, prestamo_id)
        if not cuotas:
            continue
        amortizaciones_por_prestamo.append({
            "prestamo_id": prestamo_id,
            "producto": p.get("producto") or "Prestamo",
            "cuotas": cuotas,
        })
    return {
        "cedula_display": cedula_display,
        "nombre": nombre,
        "email": email,
        "prestamos_list": prestamos_list,
        "cuotas_pendientes": cuotas_pendientes,
        "total_pendiente": total_pendiente,
        "fecha_corte": fecha_corte,
        "amortizaciones_por_prestamo": amortizaciones_por_prestamo,
    }


'''
if "_generar_codigo_6" not in c:
    c = c.replace(_cedula_end, _cedula_end.replace("def _obtener_amortizacion_prestamo", _datos_helper + "def _obtener_amortizacion_prestamo"), 1)

# 4) Add POST solicitar-codigo: before @router.post("/solicitar-estado-cuenta")
solicitar_codigo = '''
@router.post("/solicitar-codigo", response_model=SolicitarCodigoResponse)
def solicitar_codigo_estado_cuenta(
    request: Request,
    body: SolicitarCodigoRequest,
    db: Session = Depends(get_db),
):
    """
    Envia un codigo de un solo uso al email del cliente. El usuario debe ingresar
    ese codigo en verificar-codigo para descargar el PDF. Mensaje generico para no revelar si la cedula existe.
    Rate limit: 5/hora por IP.
    """
    cedula = (body.cedula or "").strip()
    ip = get_client_ip(request)
    check_rate_limit_estado_cuenta_solicitar(ip)
    if not cedula:
        return SolicitarCodigoResponse(ok=False, error="Ingrese el numero de cedula.")
    if len(cedula) > MAX_CEDULA_LENGTH:
        return SolicitarCodigoResponse(ok=False, error="Datos invalidos.")
    result = validate_cedula(cedula)
    if not result.get("valido"):
        return SolicitarCodigoResponse(ok=False, error=result.get("error", "Cedula invalida."))
    cedula_lookup = _cedula_lookup(cedula)
    if not cedula_lookup:
        return SolicitarCodigoResponse(ok=False, error="Formato de cedula no reconocido.")
    datos = _obtener_datos_pdf(db, cedula_lookup)
    if not datos or not (datos.get("email") or "").strip():
        return SolicitarCodigoResponse(
            ok=True,
            mensaje="Si la cedula esta registrada, recibiras un codigo en tu correo en los proximos minutos.",
        )
    email = (datos.get("email") or "").strip()
    nombre = datos.get("nombre") or "Cliente"
    codigo = _generar_codigo_6()
    expira_en = datetime.utcnow() + timedelta(minutes=CODIGO_EXPIRA_MINUTES)
    creado_en = datetime.utcnow()
    row = EstadoCuentaCodigo(
        cedula_normalizada=cedula_lookup,
        email=email,
        codigo=codigo,
        expira_en=expira_en,
        usado=False,
        creado_en=creado_en,
    )
    db.add(row)
    db.commit()
    try:
        send_email(
            [email],
            "Codigo para estado de cuenta - RapiCredit",
            f"Estimado(a) {nombre},\\n\\nTu codigo de verificacion es: {codigo}\\n\\nValido por {CODIGO_EXPIRA_MINUTES} minutos. No lo compartas.\\n\\nSaludos,\\nRapiCredit",
        )
    except Exception as e:
        logger.warning("No se pudo enviar codigo por email a %s: %s", email, e)
    return SolicitarCodigoResponse(
        ok=True,
        mensaje="Si la cedula esta registrada, recibiras un codigo en tu correo en los proximos minutos.",
    )


'''
# Fix: datetime.utcnow is a method
solicitar_codigo = solicitar_codigo.replace("datetime.utcnow +", "datetime.utcnow() +").replace("datetime.utcnow()", "datetime.utcnow()", 1)
solicitar_codigo = solicitar_codigo.replace("creado_en = datetime.utcnow()", "creado_en = datetime.utcnow()")

verificar_codigo = '''
@router.post("/verificar-codigo", response_model=VerificarCodigoResponse)
def verificar_codigo_estado_cuenta(
    request: Request,
    body: VerificarCodigoRequest,
    db: Session = Depends(get_db),
):
    """
    Verifica el codigo enviado al email y devuelve el PDF de estado de cuenta.
    El codigo es de un solo uso. Rate limit: 15 intentos/15 min por IP.
    """
    cedula = (body.cedula or "").strip()
    codigo = (body.codigo or "").strip()
    ip = get_client_ip(request)
    check_rate_limit_estado_cuenta_verificar(ip)
    if not cedula or not codigo:
        return VerificarCodigoResponse(ok=False, error="Ingrese cedula y codigo.")
    cedula_lookup = _cedula_lookup(cedula)
    if not cedula_lookup:
        return VerificarCodigoResponse(ok=False, error="Formato de cedula no reconocido.")
    from sqlalchemy import and_
    now = datetime.utcnow()
    fila = db.execute(
        select(EstadoCuentaCodigo).where(
            and_(
                EstadoCuentaCodigo.cedula_normalizada == cedula_lookup,
                EstadoCuentaCodigo.codigo == codigo.strip(),
                EstadoCuentaCodigo.expira_en > now,
                EstadoCuentaCodigo.usado == False,
            )
        )
    ).scalars().first()
    if not fila:
        return VerificarCodigoResponse(ok=False, error="Codigo invalido o expirado. Solicite uno nuevo.")
    rec = fila[0] if hasattr(fila, "__getitem__") else fila
    rec.usado = True
    db.commit()
    datos = _obtener_datos_pdf(db, cedula_lookup)
    if not datos:
        return VerificarCodigoResponse(ok=False, error="Error al generar el documento.")
    pdf_bytes = _generar_pdf_estado_cuenta(
        cedula=datos["cedula_display"],
        nombre=datos["nombre"],
        prestamos=datos["prestamos_list"],
        cuotas_pendientes=datos["cuotas_pendientes"],
        total_pendiente=datos["total_pendiente"],
        fecha_corte=datos["fecha_corte"],
        amortizaciones_por_prestamo=datos["amortizaciones_por_prestamo"],
    )
    import base64
    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
    return VerificarCodigoResponse(ok=True, pdf_base64=pdf_b64)


'''

if "@router.post(\"/solicitar-codigo\"" not in c:
    c = c.replace(
        '@router.post("/solicitar-estado-cuenta", response_model=SolicitarEstadoCuentaResponse)',
        solicitar_codigo + '@router.post("/solicitar-estado-cuenta", response_model=SolicitarEstadoCuentaResponse)',
        1,
    )
if "@router.post(\"/verificar-codigo\"" not in c:
    c = c.replace(
        '@router.post("/solicitar-estado-cuenta", response_model=SolicitarEstadoCuentaResponse)',
        verificar_codigo + '@router.post("/solicitar-estado-cuenta", response_model=SolicitarEstadoCuentaResponse)',
        1,
    )

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("OK: solicitar-codigo and verificar-codigo added")
