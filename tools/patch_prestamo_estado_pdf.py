# -*- coding: utf-8 -*-
"""Patch descargarEstadoCuentaPDF with PDF vs Excel validation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "frontend" / "src" / "services" / "prestamoService.ts"
text = path.read_text(encoding="utf-8")

old = """  async descargarEstadoCuentaPDF(prestamoId: number): Promise<void> {
    const axiosInstance = apiClient.getAxiosInstance()

    const response = await axiosInstance.get(
      `${this.baseUrl}/${prestamoId}/estado-cuenta/pdf`,

      { responseType: 'blob' }
    )

    const blob = new Blob([response.data], { type: 'application/pdf' })

    const url = window.URL.createObjectURL(blob)

    const link = document.createElement('a')

    link.href = url

    link.download = `Estado_Cuenta_Prestamo_${prestamoId}.pdf`

    document.body.appendChild(link)

    link.click()

    document.body.removeChild(link)

    window.URL.revokeObjectURL(url)
  }"""

new = """  /**
   * PDF de estado de cuenta (mismo formato que rapicredit-estadocuenta).
   * GET /api/v1/prestamos/{id}/estado-cuenta/pdf
   */
  async descargarEstadoCuentaPDF(prestamoId: number): Promise<void> {
    const axiosInstance = apiClient.getAxiosInstance()

    const response = await axiosInstance.get(
      `${this.baseUrl}/${prestamoId}/estado-cuenta/pdf`,
      { responseType: 'blob' }
    )

    const raw: Blob = response.data instanceof Blob ? response.data : new Blob([response.data])
    const head = new Uint8Array(await raw.slice(0, 5).arrayBuffer())
    const looksPdf = head[0] === 0x25 && head[1] === 0x50 && head[2] === 0x44 && head[3] === 0x46
    const ct = String(response.headers?.['content-type'] || response.headers?.['Content-Type'] || '')
    const looksExcel =
      ct.includes('spreadsheet') ||
      ct.includes('excel') ||
      ct.includes('officedocument.spreadsheetml') ||
      (head[0] === 0x50 && head[1] === 0x4b)

    if (!looksPdf && looksExcel) {
      throw new Error(
        'La respuesta no es un PDF de estado de cuenta (se recibió Excel). Actualice la aplicación o revise el despliegue.'
      )
    }
    if (!looksPdf && !ct.includes('pdf')) {
      throw new Error('La respuesta no es un PDF válido. Verifique sesión e intente de nuevo.')
    }

    const blob = new Blob([raw], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `Estado_Cuenta_Prestamo_${prestamoId}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  }"""

if old not in text:
    raise SystemExit("Expected block not found; file may have changed.")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("patched", path)
