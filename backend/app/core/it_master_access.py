# -*- coding: utf-8 -*-
"""Acceso restringido al administrador IT (itmaster@rapicreditca.com)."""
from __future__ import annotations

from typing import Optional

IT_MASTER_EMAIL = "itmaster@rapicreditca.com"


def is_it_master_email(email: Optional[str]) -> bool:
    return (email or "").strip().lower() == IT_MASTER_EMAIL
