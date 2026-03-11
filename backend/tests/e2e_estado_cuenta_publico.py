# -*- coding: utf-8 -*-
"""
Tests E2E para el flujo público de estado de cuenta (rapicredit-estadocuenta).

Requisitos:
  - Frontend servido en FRONTEND_BASE_URL (ej. http://localhost:3000 o https://rapicredit.onrender.com).
  - Opcional: Backend en la misma red para completar flujo con código (si no, el test solo valida pasos 0 y 1).

Ejecutar (con Playwright instalado):
  pytest tests/e2e_estado_cuenta_publico.py -v
  FRONTEND_BASE_URL=http://localhost:3000 pytest tests/e2e_estado_cuenta_publico.py -v

Si FRONTEND_BASE_URL no está definida, los tests se omiten.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "").rstrip("/")
ESTADO_CUENTA_PATH = "/pagos/rapicredit-estadocuenta"


def _base_url():
    if not FRONTEND_BASE_URL:
        return None
    return FRONTEND_BASE_URL + ESTADO_CUENTA_PATH


@pytest.fixture(scope="module")
def page_base_url():
    url = _base_url()
    if not url:
        pytest.skip("FRONTEND_BASE_URL no configurada. Ej.: FRONTEND_BASE_URL=http://localhost:3000")
    return url


@pytest.mark.skipif(not FRONTEND_BASE_URL, reason="FRONTEND_BASE_URL no configurada")
def test_estado_cuenta_page_loads(page_base_url: str, page):  # noqa: ANN001
    """La página de estado de cuenta carga y muestra la pantalla de bienvenida."""
    page.goto(page_base_url, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=10000)
    # Debe verse el título o botón Iniciar
    assert page.get_by_role("button", name="Iniciar").is_visible() or page.locator("text=Bienvenido").is_visible()


@pytest.mark.skipif(not FRONTEND_BASE_URL, reason="FRONTEND_BASE_URL no configurada")
def test_estado_cuenta_paso_0_a_paso_1(page_base_url: str, page):  # noqa: ANN001
    """Desde bienvenida, al pulsar Iniciar se pasa al paso de ingresar cédula."""
    page.goto(page_base_url, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=10000)
    page.get_by_role("button", name="Iniciar").click()
    # Paso 1: input cédula y botón Enviar código
    page.wait_for_selector('input[placeholder*="V12345678"], input[placeholder*="cedula"]', timeout=5000)
    assert (
        page.get_by_role("button", name="Enviar código al correo").is_visible()
        or page.locator("text=Estado de cuenta").is_visible()
    )


@pytest.mark.skipif(not FRONTEND_BASE_URL, reason="FRONTEND_BASE_URL no configurada")
def test_estado_cuenta_paso_1_atras_vuelve_a_bienvenida(page_base_url: str, page):  # noqa: ANN001
    """En paso 1, Atrás vuelve a la pantalla de bienvenida."""
    page.goto(page_base_url, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=10000)
    page.get_by_role("button", name="Iniciar").click()
    page.wait_for_selector('input[placeholder*="V12345678"], input[placeholder*="cedula"]', timeout=5000)
    page.get_by_role("button", name="Atrás").first.click()
    assert page.get_by_role("button", name="Iniciar").is_visible()
