# -*- coding: utf-8 -*-
"""Gestores de cobranza (referentes fijos, no usuarios del sistema)."""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Tuple

# Universo gestores: prestamos con fecha_aprobacion desde esta fecha hasta hoy (Caracas).
# Ademas deben tener al menos MIN_CUOTAS_ATRASO_GESTORES cuotas VENCIDO/MORA (<= hoy).
FECHA_INICIO_APROBACION_GESTORES = date(2026, 3, 1)
# Alias histórico (mismo valor) por si algún import externo lo usa.
FECHA_INICIO_CARTERA_GESTORES = FECHA_INICIO_APROBACION_GESTORES
MIN_CUOTAS_ATRASO_GESTORES = 2

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
