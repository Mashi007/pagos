# -*- coding: utf-8 -*-
"""Gestores de cobranza (referentes fijos, no usuarios del sistema)."""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Tuple

# Cartera elegible: cuotas con vencimiento desde esta fecha hasta hoy (America/Caracas).
FECHA_INICIO_CARTERA_GESTORES = date(2026, 3, 1)

# Orden estable de la UI / Excel / snapshots.
GESTORES: Tuple[Tuple[str, str], ...] = (
    ("bisleida-aponte", "Bisleida Aponte"),
    ("franyeli-tinoco", "Franyeli Tinoco"),
    ("francis-rangel", "Francis Rangel"),
    ("yohana-landaeta", "Yohana Landaeta"),
    ("yeny-ruiz", "Yeny Ruiz"),
    ("gean-moya", "Gean Moya"),
    ("fernanda-aguilera", "Fernanda Aguilera"),
    ("didnoira-camaripano", "Didnoira Camaripano"),
    ("glainet-dudamel", "Glainet Dudamel"),
)

GESTOR_NOMBRES: Dict[str, str] = {slug: nombre for slug, nombre in GESTORES}
GESTOR_SLUGS: List[str] = [slug for slug, _ in GESTORES]

EMAIL_GESTORES_TO = "operaciones@rapicreditca.com"
EMAIL_GESTORES_BCC = "itmaster@rapicreditca.com"
