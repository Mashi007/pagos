# Add verificar rate limit
path = "app/core/cobros_public_rate_limit.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
# Add constants
c = c.replace(
    "ESTADO_CUENTA_SOLICITAR_MAX = 5\n\n_validar_attempts",
    "ESTADO_CUENTA_SOLICITAR_MAX = 5\nESTADO_CUENTA_VERIFICAR_WINDOW_SEC = 900  # 15 min\nESTADO_CUENTA_VERIFICAR_MAX = 15\n\n_validar_attempts",
)
# Add dict for verificar
c = c.replace(
    "_estado_cuenta_solicitar_attempts: dict[str, list[float]] = defaultdict(list)\n_lock = Lock()",
    "_estado_cuenta_solicitar_attempts: dict[str, list[float]] = defaultdict(list)\n_estado_cuenta_verificar_attempts: dict[str, list[float]] = defaultdict(list)\n_lock = Lock()",
)
# Add function before get_client_ip (insert before "def get_client_ip")
old = "        attempts.append(now)\n\n\ndef get_client_ip(request: Request)"
new = "        attempts.append(now)\n\n\ndef check_rate_limit_estado_cuenta_verificar(ip: str) -> None:\n    \"\"\"Lanza 429 si se supera el limite de verificar codigo (estado de cuenta) por IP.\"\"\"\n    with _lock:\n        now = time.time()\n        attempts = _estado_cuenta_verificar_attempts[ip]\n        attempts[:] = [t for t in attempts if now - t < ESTADO_CUENTA_VERIFICAR_WINDOW_SEC]\n        if len(attempts) >= ESTADO_CUENTA_VERIFICAR_MAX:\n            raise HTTPException(\n                status_code=429,\n                detail=\"Demasiados intentos. Espere 15 minutos e intente de nuevo.\",\n            )\n        attempts.append(now)\n\n\ndef get_client_ip(request: Request)"
if old not in c:
    print("old block not found")
    exit(1)
c = c.replace(old, new, 1)
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("OK: rate limit verificar added")
