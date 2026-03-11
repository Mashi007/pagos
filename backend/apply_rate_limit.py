path = "app/core/cobros_public_rate_limit.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
if "ESTADO_CUENTA_VERIFICAR_WINDOW_SEC" not in c:
    c = c.replace(
        "ESTADO_CUENTA_SOLICITAR_MAX = 5",
        "ESTADO_CUENTA_SOLICITAR_MAX = 5\nESTADO_CUENTA_VERIFICAR_WINDOW_SEC = 900\nESTADO_CUENTA_VERIFICAR_MAX = 15",
    )
if "_estado_cuenta_verificar_attempts" not in c:
    c = c.replace(
        "_estado_cuenta_solicitar_attempts: dict[str, list[float]] = defaultdict(list)\n_lock = Lock()",
        "_estado_cuenta_solicitar_attempts: dict[str, list[float]] = defaultdict(list)\n_estado_cuenta_verificar_attempts: dict[str, list[float]] = defaultdict(list)\n_lock = Lock()",
    )
newfn = """

def check_rate_limit_estado_cuenta_verificar(ip: str) -> None:
    with _lock:
        now = time.time()
        attempts = _estado_cuenta_verificar_attempts[ip]
        attempts[:] = [t for t in attempts if now - t < ESTADO_CUENTA_VERIFICAR_WINDOW_SEC]
        if len(attempts) >= ESTADO_CUENTA_VERIFICAR_MAX:
            raise HTTPException(status_code=429, detail="Demasiados intentos. Espere 15 minutos e intente de nuevo.")
        attempts.append(now)
"""
if "check_rate_limit_estado_cuenta_verificar" not in c:
    c = c.replace("\ndef get_client_ip(request: Request)", newfn + "\ndef get_client_ip(request: Request)")
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("OK: rate limit verificar")
