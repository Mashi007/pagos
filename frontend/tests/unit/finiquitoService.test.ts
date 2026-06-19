import { describe, expect, it, vi, beforeEach } from 'vitest'

import type { FiniquitoTerminadoItem } from '@/services/finiquitoService'

const { apiGet } = vi.hoisted(() => ({
  apiGet: vi.fn(),
}))

vi.mock('@/services/api', () => ({
  apiClient: {
    get: apiGet,
  },
}))

import { finiquitoAdminListarTerminadosCompleto } from '@/services/finiquitoService'

function terminadoItem(id: number): FiniquitoTerminadoItem {
  return {
    id,
    prestamo_id: id + 1000,
    cedula: `V${id}`,
    nombre: `Cliente ${id}`,
    total_financiamiento: '1000',
    fecha_aprobacion: '2026-01-01',
    fecha_termino_pago: '2026-02-01',
    fecha_terminado: '2026-03-01',
  }
}

describe('finiquitoAdminListarTerminadosCompleto', () => {
  beforeEach(() => {
    apiGet.mockReset()
  })

  it('collects all paginated terminados instead of returning only the first page', async () => {
    const firstPage = Array.from({ length: 2000 }, (_, i) => terminadoItem(i + 1))
    const secondPage = Array.from({ length: 500 }, (_, i) =>
      terminadoItem(i + 2001)
    )

    apiGet
      .mockResolvedValueOnce({
        items: firstPage,
        total: 2500,
        limit: 2000,
        offset: 0,
      })
      .mockResolvedValueOnce({
        items: secondPage,
        total: 2500,
        limit: 2000,
        offset: 2000,
      })

    const result = await finiquitoAdminListarTerminadosCompleto(' V123 ')

    expect(result.items).toHaveLength(2500)
    expect(result.total).toBe(2500)
    expect(apiGet).toHaveBeenCalledTimes(2)
    expect(apiGet.mock.calls[0][0]).toContain('/admin/casos/terminados?')
    expect(apiGet.mock.calls[0][0]).toContain('cedula=V123')
    expect(apiGet.mock.calls[0][0]).toContain('limit=2000')
    expect(apiGet.mock.calls[0][0]).toContain('offset=0')
    expect(apiGet.mock.calls[1][0]).toContain('offset=2000')
  })
})
