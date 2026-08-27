/**
 * Guardado in-place de filas del escáner (revisión manual / Pagos → escaner-lote).
 * No usa enviar-reporte ni confirmacion_humana: actualiza el pago en cartera.
 * Las observaciones OCR (validacionCampos / validacionReglas) se conservan en la fila UI.
 */
import toast from 'react-hot-toast'

import { pagoService, type PagoCreate } from '../../services/pagoService'
import { normalizarComprobanteArchivoParaEscaneo } from '../../utils/normalizarComprobanteArchivo'
import { normalizarNumeroDocumento } from '../../utils/pagoExcelValidation'
import { mensajeErrorExtraccionEscaner } from '../../utils/escanerComprobanteInfopagos'
import { trackRevisionManualCascadaBg } from '../../utils/revisionManualCerrarBgPoller'
import type { FilaLote } from '../escanerInfopagosLoteModel'

export function institucionEfectivaFilaLote(
  fila: Pick<FilaLote, 'institucion' | 'otroInstitucion'>
): string {
  const inst = (fila.institucion || '').trim()
  if (inst && inst !== 'Otros') return inst
  return (fila.otroInstitucion || '').trim()
}

export function payloadUpdatePagoDesdeFilaEscanerRevision(
  fila: FilaLote,
  opts: { fechaPago: string; monto: number; linkComprobante: string }
): Partial<PagoCreate> & {
  reescaneo_ocr: boolean
  origen_revision_manual: boolean
  forzar_reaplicacion_cascada: boolean
} {
  const inst = institucionEfectivaFilaLote(fila)
  const numeroRaw = (fila.numeroOperacion || '').trim()
  const numeroDoc =
    normalizarNumeroDocumento(numeroRaw, { institucionBancaria: inst }) ||
    numeroRaw.replace(/\D/g, '') ||
    numeroRaw

  const payload: Partial<PagoCreate> & {
    reescaneo_ocr: boolean
    origen_revision_manual: boolean
    forzar_reaplicacion_cascada: boolean
    monto_bs_original?: number | null
  } = {
    reescaneo_ocr: true,
    origen_revision_manual: true,
    forzar_reaplicacion_cascada: true,
    fecha_pago: opts.fechaPago,
    institucion_bancaria: inst,
    numero_documento: numeroDoc,
    link_comprobante: opts.linkComprobante,
    moneda_registro: fila.moneda === 'BS' ? 'BS' : 'USD',
  }

  if (fila.moneda === 'BS') {
    payload.monto_bs_original = opts.monto
  } else {
    payload.monto_pagado = opts.monto
  }

  return payload
}

type PayloadGuardarEscanerRevision = ReturnType<
  typeof payloadUpdatePagoDesdeFilaEscanerRevision
>

function esErrorNumeroDocumentoDuplicado(msg: string): boolean {
  return /misma combinaci[oó]n comprobante/i.test(msg)
}

export type GuardarFilaEscanerRevisionResult =
  | {
      ok: true
      pagoId: number
      advertencias: string[]
      cascadaBg: boolean
      cascadaToken?: string
    }
  | { ok: false; error: string }

export async function guardarPagoDesdeFilaEscanerRevision(opts: {
  pagoId: number
  fila: FilaLote
  fechaPago: string
  monto: number
}): Promise<GuardarFilaEscanerRevisionResult> {
  const { pagoId, fila, fechaPago, monto } = opts

  let linkComprobante = ''
  if (fila.archivo) {
    try {
      const archivo = await normalizarComprobanteArchivoParaEscaneo(fila.archivo)
      const up = await pagoService.uploadComprobanteImagen(archivo)
      linkComprobante = (up.url || '').trim()
    } catch (err) {
      return {
        ok: false,
        error:
          err instanceof Error
            ? err.message
            : 'No se pudo subir el comprobante.',
      }
    }
  }

  if (!linkComprobante) {
    return {
      ok: false,
      error: 'Falta comprobante para actualizar el pago en revisión manual.',
    }
  }

  const basePayload = payloadUpdatePagoDesdeFilaEscanerRevision(fila, {
    fechaPago,
    monto,
    linkComprobante,
  })

  const advertencias: string[] = []

  const aplicarPut = async (
    payload: PayloadGuardarEscanerRevision & { codigo_documento?: string | null }
  ) => {
    const res = (await pagoService.updatePago(pagoId, payload)) as {
      reescaneo_advertencias?: string[]
      cascada_en_proceso?: boolean
      cascada_bg_token?: string
      prestamo_id?: number
    }
    if (Array.isArray(res.reescaneo_advertencias)) {
      advertencias.push(...res.reescaneo_advertencias.filter(Boolean))
    }
    return res
  }

  try {
    let res = await aplicarPut(basePayload)
    if (res.cascada_en_proceso && res.prestamo_id) {
      trackRevisionManualCascadaBg(res.prestamo_id, res.cascada_bg_token)
    }
    return {
      ok: true,
      pagoId,
      advertencias,
      cascadaBg: Boolean(res.cascada_en_proceso),
      cascadaToken: res.cascada_bg_token,
    }
  } catch (err) {
    const msg = mensajeErrorExtraccionEscaner(err)
    if (
      esErrorNumeroDocumentoDuplicado(msg) &&
      basePayload.numero_documento
    ) {
      try {
        const retry = { ...basePayload, codigo_documento: `P${pagoId}` }
        const res = await aplicarPut(retry)
        advertencias.push(
          'Serial repetido en cartera; se guardó con código P' +
            `${pagoId} (misma regla que Visto).`
        )
        if (res.cascada_en_proceso && res.prestamo_id) {
          trackRevisionManualCascadaBg(res.prestamo_id, res.cascada_bg_token)
        }
        return {
          ok: true,
          pagoId,
          advertencias,
          cascadaBg: Boolean(res.cascada_en_proceso),
          cascadaToken: res.cascada_bg_token,
        }
      } catch (retryErr) {
        return {
          ok: false,
          error: mensajeErrorExtraccionEscaner(retryErr),
        }
      }
    }
    return { ok: false, error: msg }
  }
}

/** Aviso al operador si hay observaciones OCR pero el guardado fue in-place (no cola Cobros). */
export function toastObservacionesEscanerRevisionManual(
  fila: Pick<FilaLote, 'validacionCampos' | 'validacionReglas' | 'requiereRevisionManual'>
): void {
  const obs = [fila.validacionCampos, fila.validacionReglas]
    .map(s => (s || '').trim())
    .filter(Boolean)
  if (!obs.length && !fila.requiereRevisionManual) return
  toast(
    obs.length
      ? `Pago actualizado en revisión manual. Revise observaciones: ${obs.join(' / ')}`
      : 'Pago actualizado en revisión manual (sin enviar a cola Cobros).',
    { duration: 8000 }
  )
}
