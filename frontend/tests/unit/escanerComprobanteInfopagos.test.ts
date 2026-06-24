import { describe, expect, it, vi } from 'vitest'

import {
  fechaPagoDesdeExtraccionOcrConfiable,
  mergePagoRegistrarDesdeSugerenciaOcr,
} from '../../src/utils/escanerComprobanteInfopagos'

vi.mock('../../src/utils/fechaZona', () => ({
  hoyYmdCaracas: () => '2026-06-23',
}))

describe('fechaPagoDesdeExtraccionOcrConfiable', () => {
  it('rechaza fecha vacía y hoy Caracas', () => {
    expect(fechaPagoDesdeExtraccionOcrConfiable('')).toBe('')
    expect(fechaPagoDesdeExtraccionOcrConfiable('2026-06-23')).toBe('')
  })

  it('acepta fecha del papel distinta de hoy', () => {
    expect(fechaPagoDesdeExtraccionOcrConfiable('2026-06-18')).toBe('2026-06-18')
  })
})

describe('mergePagoRegistrarDesdeSugerenciaOcr modoReescaneo', () => {
  const base = {
    fecha_pago: '2026-06-23',
    institucion_bancaria: 'BNC',
    numero_documento: '105137674',
    monto_pagado: 100,
    moneda_registro: 'USD' as const,
  }

  it('no conserva fecha previa si OCR devuelve hoy o vacío', () => {
    const merged = mergePagoRegistrarDesdeSugerenciaOcr(
      base,
      {
        fecha_pago: '2026-06-23',
        institucion_financiera: 'BNC',
        numero_operacion: '105137674',
        monto: 100,
        moneda: 'USD',
      },
      { modoReescaneo: true }
    )
    expect(merged.fecha_pago).toBe('')
  })

  it('aplica fecha OCR confiable en reescaneo', () => {
    const merged = mergePagoRegistrarDesdeSugerenciaOcr(
      base,
      {
        fecha_pago: '2026-06-18',
        institucion_financiera: 'Mercantil',
        numero_operacion: '740087408543435',
        monto: 96,
        moneda: 'USD',
      },
      { modoReescaneo: true }
    )
    expect(merged.fecha_pago).toBe('2026-06-18')
  })
})
