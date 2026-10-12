# -*- coding: utf-8 -*-
"""Herramienta HTML (solo itmaster vía token) si el SPA en Render no se ha reconstruido."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_MANUAL_UI_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Pagos confirmados — edición manual (itmaster)</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 1.5rem; max-width: 960px; color: #0f172a; }
    h1 { font-size: 1.25rem; }
    .muted { color: #64748b; font-size: 0.875rem; }
    table { border-collapse: collapse; width: 100%; margin-top: 1rem; }
    th, td { border: 1px solid #e2e8f0; padding: 0.5rem; text-align: right; }
    th:first-child, td:first-child { text-align: left; }
    input { width: 5rem; text-align: right; }
    input.wide { width: 7rem; }
    button { margin-top: 0.35rem; padding: 0.25rem 0.5rem; cursor: pointer; }
    .err { color: #b91c1c; }
    .ok { color: #15803d; }
    a { color: #0369a1; }
  </style>
</head>
<body>
  <h1>Pagos confirmados — edición manual</h1>
  <p class="muted">Solo <strong>itmaster@rapicreditca.com</strong>. Usa el mismo token de sesión que
    <a href="/pagos/cobranzas">/pagos/cobranzas</a> (inicie sesión antes).</p>
  <p id="status" class="muted">Cargando…</p>
  <div id="wrap"></div>
  <script>
(function () {
  const status = document.getElementById('status');
  const wrap = document.getElementById('wrap');

  function readToken() {
    try {
      const remember = localStorage.getItem('remember_me') === 'true';
      const primary = remember ? localStorage : sessionStorage;
      const fallback = remember ? sessionStorage : localStorage;
      return primary.getItem('access_token') || fallback.getItem('access_token') || '';
    } catch (e) {
      return '';
    }
  }

  async function api(path, opts) {
    const token = readToken();
    if (!token) throw new Error('Sin token. Inicie sesión en /pagos/ y vuelva a abrir esta página.');
    const res = await fetch('/api/v1' + path, {
      ...opts,
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + token,
        ...(opts && opts.headers ? opts.headers : {}),
      },
    });
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch (_) {}
    if (!res.ok) {
      const msg = (data && data.detail) ? (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)) : res.status + ' ' + text.slice(0, 200);
      throw new Error(msg);
    }
    return data;
  }

  function esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
  }

  async function load() {
    try {
      const me = await api('/auth/me');
      const email = (me && me.email || '').toLowerCase();
      if (email !== 'itmaster@rapicreditca.com') {
        status.innerHTML = '<span class="err">Su sesión no es itmaster@. Otros administradores no pueden editar aquí.</span>';
        return;
      }
      const analisis = await api('/cobranzas/universo/analisis');
      const des = analisis.desempeno_lecturas || {};
      const lecturas = (des.pagos_confirmados && des.pagos_confirmados.lecturas) || [];
      if (!lecturas.length) {
        status.textContent = 'No hay lecturas de Pagos confirmados en el análisis.';
        return;
      }
      status.innerHTML = '<span class="ok">Sesión itmaster OK. Edite y pulse Guardar por fila.</span>';
      let html = '<table><thead><tr><th>Fecha columna</th><th>Cantidad</th><th>USD</th><th></th></tr></thead><tbody>';
      for (const L of lecturas) {
        const f = String(L.fecha).slice(0, 10);
        const cant = Number(L.cantidad || 0);
        const usd = Number(L.monto_usd || 0);
        const manual = L.manual_override ? ' (manual)' : '';
        html += '<tr data-fecha="' + esc(f) + '"><td>' + esc(f) + esc(manual) + '</td>';
        html += '<td><input type="number" min="0" step="1" class="cant" value="' + cant + '"></td>';
        html += '<td><input type="number" min="0" step="0.01" class="usd wide" value="' + usd + '"></td>';
        html += '<td><button type="button" class="save">Guardar</button> ';
        if (L.manual_override) html += '<button type="button" class="restore">Restaurar auto</button>';
        html += '</td></tr>';
      }
      html += '</tbody></table>';
      wrap.innerHTML = html;
      wrap.querySelectorAll('button.save').forEach(btn => {
        btn.addEventListener('click', async () => {
          const tr = btn.closest('tr');
          const fecha = tr.getAttribute('data-fecha');
          const cant = parseInt(tr.querySelector('.cant').value, 10) || 0;
          const usd = Math.round((parseFloat(tr.querySelector('.usd').value) || 0) * 100) / 100;
          btn.disabled = true;
          try {
            await api('/cobranzas/pagos-confirmados/manual-lectura', {
              method: 'PUT',
              body: JSON.stringify({ fecha, cantidad: cant, monto_usd: usd }),
            });
            status.innerHTML = '<span class="ok">Guardado ' + esc(fecha) + '. Recargue /pagos/cobranzas para ver neto.</span>';
            await load();
          } catch (e) {
            status.innerHTML = '<span class="err">' + esc(e.message) + '</span>';
          } finally {
            btn.disabled = false;
          }
        });
      });
      wrap.querySelectorAll('button.restore').forEach(btn => {
        btn.addEventListener('click', async () => {
          const tr = btn.closest('tr');
          const fecha = tr.getAttribute('data-fecha');
          btn.disabled = true;
          try {
            await api('/cobranzas/pagos-confirmados/manual-lectura?fecha=' + encodeURIComponent(fecha), { method: 'DELETE' });
            status.innerHTML = '<span class="ok">Restaurado automático ' + esc(fecha) + '</span>';
            await load();
          } catch (e) {
            status.innerHTML = '<span class="err">' + esc(e.message) + '</span>';
          } finally {
            btn.disabled = false;
          }
        });
      });
    } catch (e) {
      status.innerHTML = '<span class="err">' + esc(e.message) + '</span>';
    }
  }

  load();
})();
  </script>
</body>
</html>
"""


@router.get(
    "/pagos-confirmados/manual-ui",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def pagos_confirmados_manual_ui() -> HTMLResponse:
    """Página auxiliar: misma API que el SPA; no requiere rebuild del frontend."""
    return HTMLResponse(content=_MANUAL_UI_HTML)
