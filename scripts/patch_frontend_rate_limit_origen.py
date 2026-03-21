"""Patch frontend to pass origen=informes / infopagos en validar-cedula."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_estado_cuenta_service() -> None:
    p = ROOT / "frontend" / "src" / "services" / "estadoCuentaService.ts"
    t = p.read_text(encoding="utf-8")
    old = """/** Público: validar cédula (formato + existe en clientes). Sin auth. */
export async function validarCedulaEstadoCuenta(cedula: string): Promise<ValidarCedulaEstadoCuentaResponse> {
  const url = `${BASE}/validar-cedula?cedula=${encodeURIComponent(cedula.slice(0, 20))}`
  const res = await fetch(url, { credentials: 'same-origin' })"""
    new = """/** Público: validar cédula (formato + existe en clientes). Sin auth. */
export async function validarCedulaEstadoCuenta(
  cedula: string,
  opts?: { origen?: string },
): Promise<ValidarCedulaEstadoCuentaResponse> {
  const o = (opts?.origen || '').trim()
  const q = new URLSearchParams({ cedula: cedula.slice(0, 20) })
  if (o) q.set('origen', o)
  const url = `${BASE}/validar-cedula?${q.toString()}`
  const res = await fetch(url, { credentials: 'same-origin' })"""
    if old not in t:
        raise SystemExit("estadoCuentaService.ts: validar block not found")
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("OK:", p)


def patch_estado_cuenta_page() -> None:
    p = ROOT / "frontend" / "src" / "pages" / "EstadoCuentaPublicoPage.tsx"
    t = p.read_text(encoding="utf-8")
    old = "      const validacion = await validarCedulaEstadoCuenta(cedulaEnviar)\n"
    new = "      const validacion = await validarCedulaEstadoCuenta(\n        cedulaEnviar,\n        isInformesRoute ? { origen: 'informes' } : undefined,\n      )\n"
    if old not in t:
        raise SystemExit("EstadoCuentaPublicoPage.tsx: validar call not found")
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("OK:", p)


def patch_cobros_service() -> None:
    p = ROOT / "frontend" / "src" / "services" / "cobrosService.ts"
    t = p.read_text(encoding="utf-8")
    old = """/** Público: validar cédula (formato + tiene préstamo). Sin auth. Sin envío de token. */
export async function validarCedulaPublico(cedula: string): Promise<ValidarCedulaResponse> {
  const url = `${BASE_PUBLIC}/validar-cedula?cedula=${encodeURIComponent(cedula.slice(0, 20))}`
  const res = await fetch(url, { credentials: 'same-origin' })"""
    new = """/** Público: validar cédula (formato + tiene préstamo). Sin auth. Sin envío de token. */
export async function validarCedulaPublico(
  cedula: string,
  opts?: { origen?: string },
): Promise<ValidarCedulaResponse> {
  const o = (opts?.origen || '').trim()
  const q = new URLSearchParams({ cedula: cedula.slice(0, 20) })
  if (o) q.set('origen', o)
  const url = `${BASE_PUBLIC}/validar-cedula?${q.toString()}`
  const res = await fetch(url, { credentials: 'same-origin' })"""
    if old not in t:
        raise SystemExit("cobrosService.ts: validar block not found")
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("OK:", p)


def patch_reporte_pago_page() -> None:
    p = ROOT / "frontend" / "src" / "pages" / "ReportePagoPage.tsx"
    t = p.read_text(encoding="utf-8")
    old = "      const res = await validarCedulaPublico(cedulaEnviar)\n"
    new = "      const res = await validarCedulaPublico(\n        cedulaEnviar,\n        isInfopagos ? { origen: 'infopagos' } : undefined,\n      )\n"
    if old not in t:
        raise SystemExit("ReportePagoPage.tsx: validar call not found")
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("OK:", p)


if __name__ == "__main__":
    patch_estado_cuenta_service()
    patch_estado_cuenta_page()
    patch_cobros_service()
    patch_reporte_pago_page()
