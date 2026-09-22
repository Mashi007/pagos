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
import { prestamoService } from '../services/prestamoService'
import {
  getErrorMessage,
  isAxiosError,
  getErrorDetail,
  esDuplicadoEnviadoARevision,
  esDuplicadoResolverEnSitio,
  getErrorDetailRecord,
  esPagoEnProcesoBloqueado,
  avisarPagoEnProceso,
  MSG_PAGO_EN_PROCESO_NO_INGRESAR,
} from '../types/errors'
import { trackRevisionManualCascadaBg } from './revisionManualCerrarBgPoller'
import { invalidateCobrosListadoKpisCache } from '../services/cobrosService'

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
  /** Tras POST exitoso: refrescar tabla de pagos (antes de terminar cascada). */
  onPagoPersistido?: (pagoId?: number) => void
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
      onPagoPersistido,
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

      datosEnvio.forzar_reaplicacion_cascada = true

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
            id?: number
            cascada_en_proceso?: boolean
            cascada_bg_token?: string
            cascada_sincronizada?: boolean
            tiene_aplicacion_cuotas?: boolean
          }
        | undefined

      if (isEditing && pagoId) {
        resp = (await pagoService.updatePago(pagoId, datosEnvio)) as typeof resp
      } else {
        resp = (await pagoService.createPago(datosEnvio)) as typeof resp
      }

      const pagoPersistidoId =
        resp?.id != null
          ? Number(resp.id)
          : isEditing && pagoId
            ? Number(pagoId)
            : undefined
      if (
        pagoPersistidoId != null &&
        Number.isFinite(pagoPersistidoId) &&
        pagoPersistidoId > 0
      ) {
        onPagoPersistido?.(pagoPersistidoId)
      }

      // Opción D: pago guardado; cascada en hilo BG → poll global (Layout / editor).
      // No llamar onComplete aquí: refrescar cuotas solo cuando el poller marque ok
      // (onCascadaTerminal / onProcesamientoCascadaCompleto vía terminal).
      if (resp?.cascada_en_proceso || resp?.cascada_bg_token) {
        trackRevisionManualCascadaBg(prestamoId, resp.cascada_bg_token)
        invalidateCobrosListadoKpisCache()
        return
      }

      const cascadaHecha = Boolean(resp?.cascada_sincronizada)
      if (!cascadaHecha) {
        try {
          await prestamoService.reaplicarCascadaAplicacion(prestamoId)
        } catch (cascadaErr: unknown) {
          let extra = getErrorMessage(cascadaErr)
          if (isAxiosError(cascadaErr)) {
            const detail = getErrorDetail(cascadaErr)
            if (detail) extra = detail
          }
          toast.warning(
            `Préstamo #${prestamoId}: pago guardado y conciliado, pero la cascada no se aplicó. ${extra}`
          )
          onComplete?.()
          return
        }
      }

      toast.success(
        isEditing
          ? `Préstamo #${prestamoId}: pago actualizado, conciliado y aplicado a cuotas.`
          : `Préstamo #${prestamoId}: pago guardado, conciliado y aplicado a cuotas.`
      )
      invalidateCobrosListadoKpisCache()
      onComplete?.()
    } catch (error: unknown) {
      if (isAxiosError(error) && esPagoEnProcesoBloqueado(error)) {
        const rec = getErrorDetailRecord(error)
        const msg =
          (typeof rec?.message === 'string' && rec.message.trim()) ||
          getErrorDetail(error) ||
          MSG_PAGO_EN_PROCESO_NO_INGRESAR
        avisarPagoEnProceso(msg)
        onComplete?.()
        return
      }
      if (isAxiosError(error) && esDuplicadoResolverEnSitio(error)) {
        const rec = getErrorDetailRecord(error)
        const pc = rec?.pago_conflicto_id
        const pr = rec?.prestamo_conflicto_id
        const donde =
          pc != null
            ? ` Ya está en cartera (pago n.º ${pc}${
                pr != null ? `, préstamo ${pr}` : ''
              }).`
            : ''
        toast.warning(
          `Préstamo #${prestamoId}: comprobante duplicado. Resuélvalo aquí en revisión manual; no se reenvió a Revisar pagos.${donde}`
        )
        onComplete?.()
        return
      }
      if (isAxiosError(error) && esDuplicadoEnviadoARevision(error)) {
        const rec = getErrorDetailRecord(error)
        const pe = rec?.pago_con_error_id
        const pc = rec?.pago_conflicto_id
        const pr = rec?.prestamo_conflicto_id
        const donde =
          pc != null
            ? ` Ya está en cartera (pago n.º ${pc}${
                pr != null ? `, préstamo ${pr}` : ''
              }).`
            : ''
        toast.warning(
          `Préstamo #${prestamoId}: comprobante duplicado. Caso enviado a Revisar pagos${
            pe != null ? ` (#${pe})` : ''
          } para revisión humana.${donde}`
        )
        onComplete?.()
        return
      }
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
