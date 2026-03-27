"""Patch monto-programado-proxima-semana: D+4 .. D+7 (4 days)."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "app" / "api" / "v1" / "endpoints" / "dashboard" / "graficos.py"
text = p.read_text(encoding="utf-8")

old = '''@router.get("/monto-programado-proxima-semana")
def get_monto_programado_proxima_semana(db: Session = Depends(get_db)):
    """Monto programado por día desde hoy hasta una semana después (7 días)."""
    try:
        hoy_utc = datetime.now(timezone.utc)
        hoy_date = date(hoy_utc.year, hoy_utc.month, hoy_utc.day)
        fin_date = hoy_date + timedelta(days=7)
        resultado = []
        nombres_mes = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")
        d = hoy_date
        while d <= fin_date:'''

# File may have different docstring encoding
if old not in text:
    import re

    m = re.search(
        r'(@router\.get\("/monto-programado-proxima-semana"\)\s*\n'
        r'def get_monto_programado_proxima_semana\(db: Session = Depends\(get_db\)\):\s*\n'
        r'    """[^"]*"""\s*\n'
        r'    try:\s*\n'
        r'        hoy_utc = datetime\.now\(timezone\.utc\)\s*\n'
        r'        hoy_date = date\(hoy_utc\.year, hoy_utc\.month, hoy_utc\.day\)\s*\n'
        r'        fin_date = hoy_date \+ timedelta\(days=7\)\s*\n'
        r'        resultado = \[\]\s*\n'
        r'        nombres_mes = \(.+\)\s*\n'
        r'        d = hoy_date\s*\n'
        r'        while d <= fin_date:)',
        text,
        re.S,
    )
    if not m:
        raise SystemExit("regex anchor not found")
    old = m.group(1)

new = '''@router.get("/monto-programado-proxima-semana")
def get_monto_programado_proxima_semana(db: Session = Depends(get_db)):
    """Monto programado por día: vencimientos entre hoy+4 y hoy+7 (4 días en el futuro)."""
    try:
        hoy_utc = datetime.now(timezone.utc)
        hoy_date = date(hoy_utc.year, hoy_utc.month, hoy_utc.day)
        inicio_date = hoy_date + timedelta(days=4)
        fin_date = hoy_date + timedelta(days=7)
        resultado = []
        nombres_mes = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")
        d = inicio_date
        while d <= fin_date:'''

if old not in text:
    raise SystemExit("old block not found for replace")
text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")
print("patched", p)
