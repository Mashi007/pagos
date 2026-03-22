#!/usr/bin/env python3
"""
Smoke test HTTP contra la API ya levantada (uvicorn, etc.).

Comprueba rutas publicas: health, health/db, /docs, /openapi.json, auth/status.
Opcionalmente: login con ADMIN_EMAIL/ADMIN_PASSWORD (desde .env o entorno) y
GET a rutas protegidas (configurables) con Bearer.

Variables de entorno:
  SMOKE_BASE_URL          URL base (sin /api/v1 final).
  SMOKE_PROTECTED_PATHS   Lista separada por comas, rutas bajo /api/v1, ej:
                          auth/me,clientes,pagos
                          Por defecto: auth/me,clientes,pagos

No imprime contrasenas ni tokens completos.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_PROTECTED = ("auth/me", "clientes", "pagos")


def _load_dotenv(path: Path) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    if path.is_file():
        load_dotenv(path)


def _parse_protected_paths(raw: str | None) -> tuple[str, ...]:
    if not raw or not raw.strip():
        return DEFAULT_PROTECTED
    parts = []
    for p in raw.split(","):
        s = p.strip().strip("/")
        if s:
            parts.append(s)
    return tuple(parts) if parts else DEFAULT_PROTECTED


def _print_results_text(results: list[tuple[str, int | str, Any]]) -> None:
    for name, code, detail in results:
        print(f"{name} -> {code} | {detail}")


def _print_results_json(exit_code: int, results: list[tuple[str, int | str, Any]]) -> None:
    payload = {
        "exit_code": exit_code,
        "results": [
            {"name": name, "code": code, "detail": detail} for name, code, detail in results
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _evaluate(
    results: list[tuple[str, int | str, Any]],
    strict_db: bool,
    protected_labels: tuple[str, ...],
) -> int:
    protected_names = {f"GET /api/v1/{p}" for p in protected_labels}
    for name, code, detail in results:
        if name == "GET /api/v1/health/" and code != 200:
            return 1
        if name == "GET /docs" and code != 200:
            return 1
        if name == "GET /openapi.json" and code != 200:
            return 1
        if name == "GET /api/v1/health/db":
            if code != 200:
                return 2
            if strict_db and isinstance(detail, dict) and detail.get("status") != "ok":
                return 2
        if name == "POST /api/v1/auth/login" and code not in (200, "SKIP"):
            return 3
        if name == "token" and code == "ERR":
            return 3
        if name in protected_names and code != 200:
            return 3
    return 0


def _fetch_health_with_retries(
    client: Any,
    url: str,
    retries: int,
    delay_sec: float,
    record: Any,
) -> bool:
    last_err: str | None = None
    for attempt in range(max(1, retries)):
        try:
            r = client.get(url)
            if r.status_code == 200:
                if r.headers.get("content-type", "").startswith("application/json"):
                    record("GET /api/v1/health/", r.status_code, r.json())
                else:
                    record("GET /api/v1/health/", r.status_code, r.text[:200])
                return True
            last_err = f"HTTP {r.status_code}"
        except Exception as e:
            last_err = str(e)
        if attempt < retries - 1:
            time.sleep(max(0.0, delay_sec))
    record("GET /api/v1/health/", "ERR", last_err or "unknown")
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Smoke test HTTP: health, OpenAPI y rutas protegidas opcionales."
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("SMOKE_BASE_URL", "http://127.0.0.1:8000"),
        help="URL base (sin /api/v1). Por defecto SMOKE_BASE_URL o http://127.0.0.1:8000",
    )
    parser.add_argument("--timeout", type=float, default=60.0, help="Timeout HTTP en segundos")
    parser.add_argument(
        "--skip-auth",
        action="store_true",
        help="No intentar login ni rutas protegidas",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Ruta a .env (default: backend/.env relativo a este script)",
    )
    parser.add_argument(
        "--strict-db",
        action="store_true",
        help="Fallar si /health/db devuelve JSON con status distinto de ok",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Salida en JSON (incluye exit_code al final del objeto)",
    )
    parser.add_argument(
        "--health-retries",
        type=int,
        default=int(os.environ.get("SMOKE_HEALTH_RETRIES", "8")),
        help="Reintentos para GET /health/ al arrancar (default: env SMOKE_HEALTH_RETRIES o 8)",
    )
    parser.add_argument(
        "--health-delay",
        type=float,
        default=float(os.environ.get("SMOKE_HEALTH_DELAY", "0.75")),
        help="Segundos entre reintentos de health (default: env SMOKE_HEALTH_DELAY o 0.75)",
    )
    parser.add_argument(
        "--protected-paths",
        default=os.environ.get("SMOKE_PROTECTED_PATHS"),
        help="Rutas bajo /api/v1 separadas por comas (default: env SMOKE_PROTECTED_PATHS o auth/me,clientes,pagos)",
    )
    args = parser.parse_args(argv)

    try:
        import httpx
    except ImportError:
        print("Instala httpx: pip install httpx", file=sys.stderr)
        return 1

    base = args.base_url.rstrip("/")
    api = f"{base}/api/v1"
    protected = _parse_protected_paths(args.protected_paths)

    backend_dir = Path(__file__).resolve().parent.parent
    env_path = args.env_file if args.env_file is not None else (backend_dir / ".env")
    _load_dotenv(env_path)

    results: list[tuple[str, int | str, Any]] = []

    def record(name: str, code: int | str, detail: Any) -> None:
        results.append((name, code, detail))

    exit_early: int | None = None

    try:
        with httpx.Client(timeout=args.timeout) as client:
            if not _fetch_health_with_retries(
                client,
                f"{api}/health/",
                args.health_retries,
                args.health_delay,
                record,
            ):
                exit_early = 1

            if exit_early is None:
                rdb = client.get(f"{api}/health/db")
                db_json: dict[str, Any] = {}
                if rdb.headers.get("content-type", "").startswith("application/json"):
                    db_json = rdb.json()
                record(
                    "GET /api/v1/health/db",
                    rdb.status_code,
                    {
                        "status": db_json.get("status"),
                        "db_connected": db_json.get("db_connected"),
                    },
                )

                rdocs = client.get(f"{base}/docs")
                ct = rdocs.headers.get("content-type") or ""
                record(
                    "GET /docs",
                    rdocs.status_code,
                    "html" if "text/html" in ct else ct,
                )

                roa = client.get(f"{base}/openapi.json")
                if roa.status_code == 200:
                    try:
                        npaths = len(roa.json().get("paths", {}))
                        record("GET /openapi.json", roa.status_code, f"paths={npaths}")
                    except json.JSONDecodeError:
                        record("GET /openapi.json", roa.status_code, "invalid json")
                else:
                    record("GET /openapi.json", roa.status_code, roa.text[:120])

                rs = client.get(f"{api}/auth/status")
                if rs.headers.get("content-type", "").startswith("application/json"):
                    sj = rs.json()
                    record(
                        "GET /api/v1/auth/status",
                        rs.status_code,
                        {
                            k: sj.get(k)
                            for k in ("auth_configured", "message")
                            if k in sj
                        },
                    )
                else:
                    record("GET /api/v1/auth/status", rs.status_code, rs.text[:120])

                if args.skip_auth:
                    record("POST /api/v1/auth/login", "SKIP", "--skip-auth")
                else:
                    email = os.environ.get("ADMIN_EMAIL")
                    password = os.environ.get("ADMIN_PASSWORD")
                    if not email or not password:
                        record(
                            "POST /api/v1/auth/login",
                            "SKIP",
                            "ADMIN_EMAIL/ADMIN_PASSWORD no definidos (.env o entorno)",
                        )
                    else:
                        lr = client.post(
                            f"{api}/auth/login",
                            json={"email": email, "password": password, "remember": True},
                        )
                        if lr.status_code != 200:
                            record("POST /api/v1/auth/login", lr.status_code, lr.text[:200])
                            exit_early = 3
                        else:
                            record("POST /api/v1/auth/login", lr.status_code, "ok")
                            try:
                                body = lr.json()
                            except json.JSONDecodeError:
                                record("token", "ERR", "respuesta login no es JSON")
                                exit_early = 3
                            else:
                                token = body.get("access_token")
                                if not token:
                                    record("token", "ERR", "sin access_token en respuesta")
                                    exit_early = 3
                                else:
                                    h = {"Authorization": f"Bearer {token}"}
                                    for rel in protected:
                                        url = f"{api}/{rel}"
                                        params = None
                                        first_seg = rel.split("/")[0]
                                        if first_seg in ("clientes", "pagos"):
                                            params = {"page": 1, "page_size": 1}
                                        pr = client.get(url, headers=h, params=params)
                                        label = f"GET /api/v1/{rel}"
                                        if pr.status_code == 200 and pr.headers.get(
                                            "content-type", ""
                                        ).startswith("application/json"):
                                            detail: Any = "ok"
                                        else:
                                            detail = pr.text[:200]
                                        record(label, pr.status_code, detail)

    except httpx.RequestError as e:
        print(f"Error de red: {e}", file=sys.stderr)
        exit_early = exit_early or 1

    code = exit_early if exit_early is not None else _evaluate(results, args.strict_db, protected)

    if args.json:
        _print_results_json(code, results)
    else:
        _print_results_text(results)

    return code


if __name__ == "__main__":
    raise SystemExit(main())
