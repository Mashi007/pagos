"""One-off patch: sin rate limit en informes (estado cuenta) e infopagos (cobros)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_estado_cuenta() -> None:
    p = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "estado_cuenta_publico.py"
    t = p.read_text(encoding="utf-8")

    old1 = """@router.get("/validar-cedula", response_model=ValidarCedulaEstadoCuentaResponse)
def validar_cedula_estado_cuenta(
    request: Request,
    cedula: str,
    db: Session = Depends(get_db),
):
    \"\"\"
    Valida cédula y verifica que exista en tabla clientes.
    Público, sin auth. Rate limit: 30 req/min por IP. Retorna nombre y email si ok.
    \"\"\"
    ip = get_client_ip(request)
    check_rate_limit_estado_cuenta_validar(ip)"""

    new1 = """@router.get("/validar-cedula", response_model=ValidarCedulaEstadoCuentaResponse)
def validar_cedula_estado_cuenta(
    request: Request,
    cedula: str,
    origen: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    \"\"\"
    Valida cédula y verifica que exista en tabla clientes.
    Público, sin auth. Rate limit: 30 req/min por IP. Retorna nombre y email si ok.
    Sin límite cuando origen=informes (ruta /pagos/informes, uso interno).
    \"\"\"
    ip = get_client_ip(request)
    if (origen or "").strip().lower() != "informes":
        check_rate_limit_estado_cuenta_validar(ip)"""

    if old1 not in t:
        raise SystemExit("estado_cuenta_publico.py: block validar not found")
    t = t.replace(old1, new1, 1)

    old2 = """    cedula = (body.cedula or "").strip()
    ip = get_client_ip(request)
    check_rate_limit_estado_cuenta_solicitar(ip)
    if not cedula:
        return SolicitarEstadoCuentaResponse(ok=False, error="Ingrese el número de cédula.")"""

    new2 = """    cedula = (body.cedula or "").strip()
    ip = get_client_ip(request)
    if (body.origen or "").strip().lower() != "informes":
        check_rate_limit_estado_cuenta_solicitar(ip)
    if not cedula:
        return SolicitarEstadoCuentaResponse(ok=False, error="Ingrese el número de cédula.")"""

    if old2 not in t:
        raise SystemExit("estado_cuenta_publico.py: block solicitar not found")
    t = t.replace(old2, new2, 1)

    p.write_text(t, encoding="utf-8")
    print("OK:", p)


def patch_cobros() -> None:
    p = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "cobros_publico.py"
    t = p.read_text(encoding="utf-8")

    old_v = """@router.get("/validar-cedula", response_model=ValidarCedulaResponse)
def validar_cedula_publico(
    request: Request,
    cedula: str,
    db: Session = Depends(get_db),
):
    \"\"\"
    Valida cédula (formato V/E/J + dígitos) y verifica si tiene préstamo.
    Público, sin auth. Rate limit: 30 req/min por IP. Retorna nombre y correo enmascarado si ok.
    \"\"\"
    ip = get_client_ip(request)
    check_rate_limit_validar_cedula(ip)"""

    new_v = """@router.get("/validar-cedula", response_model=ValidarCedulaResponse)
def validar_cedula_publico(
    request: Request,
    cedula: str,
    origen: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    \"\"\"
    Valida cédula (formato V/E/J + dígitos) y verifica si tiene préstamo.
    Público, sin auth. Rate limit: 30 req/min por IP. Retorna nombre y correo enmascarado si ok.
    Sin límite cuando origen=infopagos (ruta /pagos/infopagos, uso interno).
    \"\"\"
    ip = get_client_ip(request)
    if (origen or "").strip().lower() != "infopagos":
        check_rate_limit_validar_cedula(ip)"""

    if old_v not in t:
        raise SystemExit("cobros_publico.py: block validar not found")
    t = t.replace(old_v, new_v, 1)

    old_i = """    ip = get_client_ip(request)
    check_rate_limit_enviar_reporte(ip)
    if contact_website and str(contact_website).strip():
        logger.warning("[INFOPAGOS] Honeypot activado desde IP %s", ip)"""

    new_i = """    ip = get_client_ip(request)
    if contact_website and str(contact_website).strip():
        logger.warning("[INFOPAGOS] Honeypot activado desde IP %s", ip)"""

    if old_i not in t:
        raise SystemExit("cobros_publico.py: infopagos block not found")
    t = t.replace(old_i, new_i, 1)

    p.write_text(t, encoding="utf-8")
    print("OK:", p)


if __name__ == "__main__":
    patch_estado_cuenta()
    patch_cobros()
