"""Fix mojibake in DashboardMenu.tsx (bad UTF-8 sequences in comments and UI)."""
from pathlib import Path

path = Path(__file__).resolve().parent.parent / "frontend" / "src" / "pages" / "DashboardMenu.tsx"
raw = path.read_bytes()

replacements: list[tuple[bytes, bytes]] = [
    (
        b'  // \xc3\x83\xc2\xa2\xc3\x85"\xe2\x80\xa6 OPTIMIZACI\xc3\x83"N PRIORIDAD 1: Carga por batches con priorizaci\xc3\xb3n',
        "  // As\xc3\xad. OPTIMIZACI\xc3\x93N PRIORIDAD 1: Carga por batches con priorizaci\xc3\xb3n".encode(
            "utf-8"
        ),
    ),
    (
        b'    // \xc3\x83\xc2\xa2\xc3\x85"\xe2\x80\xa6 Prioridad m\xc3\xa1xima - carga inmediatamente',
        "    // Prioridad m\xc3\xa1xima - carga inmediatamente".encode("utf-8"),
    ),
    (
        b'    retry: 1, // \xc3\x83\xc2\xa2\xc3\x85"\xe2\x80\xa6 Permitir 1 reintento para errores de red',
        "    retry: 1, // Permitir 1 reintento para errores de red".encode("utf-8"),
    ),
    (
        b"<strong>\xc3\x9altimos 12 meses</strong>",
        b"<strong>\xc3\xbaltimos 12 meses</strong>",
    ),
]

for old, new in replacements:
    if old not in raw:
        raise SystemExit(f"pattern not found: {old[:50]!r}...")
    raw = raw.replace(old, new, 1)

path.write_bytes(raw)
print("patched", path)
