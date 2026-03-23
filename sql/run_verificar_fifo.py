#!/usr/bin/env python3
"""Compat: ejecuta run_verificar_cascada.py (mismo flujo)."""
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
os.execv(sys.executable, [sys.executable, os.path.join(here, 'run_verificar_cascada.py')] + sys.argv[1:])
