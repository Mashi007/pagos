"""
Shared helpers for reportes endpoints.
"""
from datetime import date
from typing import List, Optional


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _parse_fecha(s: Optional[str]) -> date:
    if not s:
        return date.today()
    try:
        return date.fromisoformat(s)
    except ValueError:
        return date.today()


def _periodos_desde_filtros(
    anos_str: Optional[str],
    meses_str: Optional[str],
    meses_default: int = 12,
) -> List[tuple]:
    """
    Retorna lista de (año, mes) ordenada descendente.
    Si anos_str y meses_str están presentes, usa esos. Si no, usa últimos meses_default meses.
    """
    if anos_str and meses_str:
        try:
            anos = sorted([int(x.strip()) for x in anos_str.split(",") if x.strip()], reverse=True)
            meses = sorted([int(x.strip()) for x in meses_str.split(",") if x.strip() and 1 <= int(x.strip()) <= 12])
            if anos and meses:
                periodos = [(a, m) for a in anos for m in meses]
                periodos.sort(key=lambda p: (-p[0], -p[1]))
                return periodos
        except (ValueError, TypeError):
            pass
    hoy = date.today()
    result = []
    for i in range(meses_default):
        ano = hoy.year
        mes = hoy.month - i
        while mes <= 0:
            mes += 12
            ano -= 1
        result.append((ano, mes))
    return result
