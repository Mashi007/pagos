/**
 * Guarda/actualiza un pago de revisión manual tras cerrar el modal.
 * Sigue en segundo plano aunque el usuario cambie de módulo (poller global en Layout).
 */
import { toast } from 'sonner'

import { esInstitucionBinanceSerial } from './pagoExcelValidation'
import {
  pagoService,
  type PagoCreate,
} from '../services/pagoService'
import { getErrorMessage, isAxiosError, getErrorDetail } from '../types/errors'
import { trackRevisionManualCascadaBg } from './revisionManualCerrarBgPoller'

export type RevisionManualPagoBgSaveInput = {
  formData: PagoCreate
  numeroDocumentoNormalizado: string
  monedaRegistro: 'USD' | 'BS'
  tasaManual: string
  tasaBd: number | null | undefined
  archivoComprobante: File | null
  linkComprobanteInicial: string
  isEditing: boolean
  pagoId?: number
  revisionManualFullEdit: boolean
  bloquearCambioComprobanteCodigo: boolean
  prestamoId: number
  onComplete?: () => void
}

export function ejecutarGuardadoPagoRevisionManualBg(
  input: RevisionManualPagoBgSaveInput
): void {
  void (async () => {
    const {
      formData: fd,
      numeroDocumentoNormalizado,
      monedaRegistro,
      tasaManual,
      tasaBd,
      archivoComprobante,
      linkComprobanteInicial,
      isEditing,
      pagoId,
      revisionManualFullEdit,
      bloquearCambioComprobanteCodigo,
      prestamoId,
      onComplete,
    } = input

    try {
      let linkFinal = (fd.link_comprobante || '').trim() || linkComprobanteInicial

      if (archivoComprobante) {
        const up = await pagoService.uploadComprobanteImagen(archivoComprobante)
        linkFinal = (up.url || '').trim()
      }

      if (!linkFinal) {
        toast.error(
          'No se pudo guardar el pago en segundo plano: falta comprobante.'
        )
        return
      }

      const codigoTrim = String(fd.codigo_documento ?? '').trim()
      let codigoParaEnvio: string | null = codigoTrim || null
      if (esInstitucionBinanceSerial(fd.institucion_bancaria) && codigoTrim) {
        codigoParaEnvio = null
      }

      const datosEnvio = {
        ...fd,
        numero_documento: numeroDocumentoNormalizado,
        codigo_documento: codigoParaEnvio,
        moneda_registro: monedaRegistro,
        link_comprobante: linkFinal,
        origen_revision_manual: true,
      } as PagoCreate & {
        tasa_cambio_manual?: number
        conciliado?: boolean
        forzar_reaplicacion_cascada?: boolean
        verificado_concordancia?: string
      }

      if (isEditing && bloquearCambioComprobanteCodigo && !revisionManualFullEdit) {
        delete datosEnvio.link_comprobante
        delete datosEnvio.codigo_documento
      }

      if (isEditing) {
        datosEnvio.forzar_reaplicacion_cascada = true
      }

      if (monedaRegistro === 'BS' && !tasaBd) {
        const tm = parseFloat(String(tasaManual).replace(',', '.'))
        if (Number.isFinite(tm) && tm > 0) datosEnvio.tasa_cambio_manual = tm
      }

      if (fd.prestamo_id && fd.monto_pagado > 0) {
        datosEnvio.conciliado = true
        datosEnvio.verificado_concordancia = 'SI'
      }

      let resp:
        | {
            cascada_en_proceso?: boolean
            cascada_bg_token?: string
          }
        | undefined

      if (isEditing && pagoId) {
        resp = (await pagoService.updatePago(pagoId, datosEnvio)) as typeof resp
      } else {
        resp = (await pagoService.createPago(datosEnvio)) as typeof resp
      }

      if (resp?.cascada_en_proceso) {
        trackRevisionManualCascadaBg(
          prestamoId,
          typeof resp.cascada_bg_token === 'string'
            ? resp.cascada_bg_token
            : undefined
        )
      }

      toast.success(
        isEditing
          ? `Préstamo #${prestamoId}: pago guardado; cascada en el servidor.`
          : `Préstamo #${prestamoId}: pago registrado; cascada en el servidor.`
      )
      onComplete?.()
    } catch (error: unknown) {
      let msg = getErrorMessage(error)
      if (isAxiosError(error)) {
        const detail = getErrorDetail(error)
        if (detail) msg = detail
      }
      toast.error(
        `Préstamo #${prestamoId}: no se pudo guardar el pago en segundo plano. ${msg}`
      )
    }
  })()
}
