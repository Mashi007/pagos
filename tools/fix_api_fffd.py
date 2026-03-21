# -*- coding: utf-8 -*-
"""Remove U+FFFD from frontend/src/services/api.ts by restoring Spanish accents."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "frontend/src/services/api.ts"


def main() -> None:
    t = API.read_text(encoding="utf-8", errors="strict")
    if "\ufffd" not in t:
        print("No U+FFFD in api.ts — nothing to do")
        return

    reps: list[tuple[str, str]] = [
        ("configuraci\ufffdn", "configuración"),
        ("m\ufffds", "más"),
        ("or\ufffdgenes", "orígenes"),
        ("est\ufffdn", "estén"),
        ("est\ufffd expirado", "esté expirado"),
        ("est\ufffd presente", "esté presente"),
        ("est\ufffd siendo", "está siendo"),
        ("est\ufffd disponible", "esté disponible"),
        ("est\ufffd funcionando", "esté funcionando"),
        ("est\ufffd tardando", "esté tardando"),
        ("est\ufffd reiniciando", "esté reiniciando"),
        ("autenticaci\ufffdn", "autenticación"),
        ("contrase\ufffda", "contraseña"),
        ("l\ufffdnea", "línea"),
        ("Sesi\ufffdn", "Sesión"),
        ("sesi\ufffdn", "sesión"),
        ("inv\ufffdlido", "inválido"),
        ("conexi\ufffdn", "conexión"),
        ("teor\ufffda", "teoría"),
        ("s\ufffd es", "sí es"),
        ("protecci\ufffdn", "protección"),
        ("petici\ufffdn", "petición"),
        ("despu\ufffds", "después"),
        ("validaci\ufffdn", "validación"),
        ("v\ufffdlida", "válida"),
        ("fall\ufffd.", "falló."),
        ("m\ufffds requests", "más requests"),
        ("c\ufffdula", "cédula"),
        ("c\ufffdulas", "cédulas"),
        ("CORRECCI\ufffdN", "CORRECCIÓN"),
        ("acci\ufffdn", "acción"),
        ("informaci\ufffdn", "información"),
        ("espec\ufffdfico", "específico"),
        ("espec\ufffdfica", "específica"),
        ("espec\ufffdficos", "específicos"),
        ("diagn\ufffdstico", "diagnóstico"),
        ("gen\ufffdrico", "genérico"),
        ("automat\ufffdticamente", "automáticamente"),
        ("ver\ufffd el", "verá el"),
        ("expl\ufffdcito", "explícito"),
        ("recibi\ufffd", "recibió"),
        ("(vac\ufffdo)", "(vacío)"),
        ("M\ufffdtodo", "Método"),
        ("FUNCI\ufffdN", "FUNCIÓN"),
        ("espec\ufffdficamente", "específicamente"),
        ("par\ufffdmetros", "parámetros"),
        ("s\ufffdncrono", "síncrono"),
        ("fr\ufffdo", "frío"),
        ("3\ufffd5 s", "3-5 s"),
        ("petici\ufffdn.", "petición."),
        ("petici\ufffdn)", "petición)"),
        ("petici\ufffdn ", "petición "),
        ("configuraci\ufffdn ", "configuración "),
        ("configuraci\ufffdn.", "configuración."),
        ("configuraci\ufffdn de", "configuración de"),
        ("Error en la configuraci\ufffdn", "Error en la configuración"),
        ("M\ufffdodos HTTP", "Métodos HTTP"),
        ("M\ufffdtodo para", "Método para"),
        ("espec\ufffdfico del", "específico del"),
        ("espec\ufffdficos del", "específicos del"),
        ("ahora m\ufffds espec\ufffdfico", "ahora más específico"),
        ("m\ufffds espec\ufffdfico", "más específico"),
        ("seg\ufffdn el", "según el"),
        ("m\ufffds descriptivo", "más descriptivo"),
        ("petici\ufffdn\n", "petición\n"),
    ]

    for a, b in reps:
        t = t.replace(a, b)

    if "\ufffd" in t:
        # Report remaining
        for i, line in enumerate(t.splitlines(), 1):
            if "\ufffd" in line:
                print("REMAINING", i, line.replace("\ufffd", "?")[:120])
        raise SystemExit(1)

    API.write_text(t, encoding="utf-8", newline="\n")
    print("api.ts: removed all U+FFFD")


if __name__ == "__main__":
    main()
