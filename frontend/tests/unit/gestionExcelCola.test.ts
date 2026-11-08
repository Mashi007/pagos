import { describe, expect, it } from 'vitest'
import {
  planificarColaExcel,
  tomarSiguienteBloque,
} from '../../src/utils/gestionExcelCola'

describe('planificarColaExcel', () => {
  it('1000 correos → 100 bloques de 10; primer bloque arranca y el resto queda en cola', () => {
    const emails = Array.from({ length: 1000 }, (_, i) => `u${i}@ex.com`)
    const plan = planificarColaExcel(emails, 10)
    expect(plan.totalEmails).toBe(1000)
    expect(plan.bloquesTotal).toBe(100)
    expect(plan.primerBloque).toHaveLength(10)
    expect(plan.primerBloque[0]).toBe('u0@ex.com')
    expect(plan.primerBloque[9]).toBe('u9@ex.com')
    expect(plan.restoCola).toHaveLength(990)
    expect(plan.restoCola[0]).toBe('u10@ex.com')
  })

  it('recorre todos los bloques hasta vaciar la cola', () => {
    const emails = Array.from({ length: 1000 }, (_, i) => `u${i}@ex.com`)
    const plan = planificarColaExcel(emails, 10)
    let cola = plan.restoCola
    const vistos = [...plan.primerBloque]
    let bloques = 1
    while (cola.length > 0) {
      const { chunk, resto } = tomarSiguienteBloque(cola, 10)
      expect(chunk.length).toBeGreaterThan(0)
      expect(chunk.length).toBeLessThanOrEqual(10)
      vistos.push(...chunk)
      cola = resto
      bloques += 1
    }
    expect(bloques).toBe(100)
    expect(vistos).toHaveLength(1000)
    expect(vistos[999]).toBe('u999@ex.com')
    expect(new Set(vistos).size).toBe(1000)
  })

  it('25 correos → 3 bloques (10+10+5)', () => {
    const emails = Array.from({ length: 25 }, (_, i) => `a${i}@x.com`)
    const plan = planificarColaExcel(emails, 10)
    expect(plan.bloquesTotal).toBe(3)
    expect(plan.primerBloque).toHaveLength(10)
    expect(plan.restoCola).toHaveLength(15)
    const b2 = tomarSiguienteBloque(plan.restoCola, 10)
    expect(b2.chunk).toHaveLength(10)
    expect(b2.resto).toHaveLength(5)
    const b3 = tomarSiguienteBloque(b2.resto, 10)
    expect(b3.chunk).toHaveLength(5)
    expect(b3.resto).toHaveLength(0)
  })
})
