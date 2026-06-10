import { describe, expect, it } from 'vitest'

import {
  normalizarCedulaParaProcesar,
  quitarCerosIzquierdaNumeroCedula,
} from '../../src/utils/cedulaConsultaPublica'

describe('cedulaConsultaPublica', () => {
  it('quita ceros a la izquierda del bloque numérico', () => {
    expect(quitarCerosIzquierdaNumeroCedula('0006832631')).toBe('6832631')
    expect(quitarCerosIzquierdaNumeroCedula('08752971')).toBe('8752971')
  })

  it('normaliza OCR con ceros a la izquierda a V+dígitos', () => {
    const v = normalizarCedulaParaProcesar('0006832631')
    expect(v.valido).toBe(true)
    expect(v.valorParaEnviar).toBe('V6832631')
  })

  it('normaliza cédula con prefijo y ceros en el número', () => {
    const v = normalizarCedulaParaProcesar('V0006832631')
    expect(v.valido).toBe(true)
    expect(v.valorParaEnviar).toBe('V6832631')
  })
})
