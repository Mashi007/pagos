# Script one-off: add CORS headers to exception handlers in main.py
path = "app/main.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    \"\"\"Respuesta de error unificada: detail + code para el frontend.\"\"\"
    from app.core.exceptions import error_response_body
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response_body(exc.detail, exc.status_code),
    )"""

new = """def _cors_headers_for_request(request: Request):
    \"\"\"Cabeceras CORS para respuestas de error (500, etc.) que el navegador pueda leer.\"\"\"
    origin = request.headers.get("origin")
    allowed = settings.cors_origins_list
    if origin and origin in allowed:
        return {"Access-Control-Allow-Origin": origin}
    if allowed:
        return {"Access-Control-Allow-Origin": allowed[0]}
    return {}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    \"\"\"Respuesta de error unificada: detail + code para el frontend. Incluye CORS para evitar bloqueo en 4xx/5xx.\"\"\"
    from app.core.exceptions import error_response_body
    headers = _cors_headers_for_request(request)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response_body(exc.detail, exc.status_code),
        headers=headers,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    \"\"\"Captura excepciones no controladas y devuelve 500 con CORS para que el frontend reciba el error.\"\"\"
    logger.exception("Excepcion no controlada: %s", exc)
    headers = _cors_headers_for_request(request)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor", "code": 500},
        headers=headers,
    )"""

if old in content:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK: CORS exception handlers added")
else:
    print("OLD block not found")
    idx = content.find("exception_handler(HTTPException)")
    if idx >= 0:
        print("Context:", repr(content[idx : idx + 350]))
