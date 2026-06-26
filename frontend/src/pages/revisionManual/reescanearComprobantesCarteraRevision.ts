/**
 * Re-escaneo cartera: misma API/prompts que Escanear (extraer-comprobante +
 * rescate_plantilla). Limpia campos OCR y persiste solo lo devuelto por la imagen.
 */
import {
  escanerInfopagosExtraerComprobante,
  escanerInfopagosLoteContextoRevision,
  type EscanerInfopagosExtraerResponse,
} from '../../services/cobrosService'
import {
  pagoService,
  type Pago,
  type PagoCreate,
} from '../../services/pagoService'
import { normalizarComprobanteArchivoParaEscaneo } from '../../utils/normalizarComprobanteArchivo'
import {
  buildFormDataEscanerComprobante,
  fechaPagoDesdeExtraccionOcrConfiable,
  mensajeErrorExtraccionEscaner,
} from '../../utils/escanerComprobanteInfopagos'
import {
  hayDuplicadoFila,
  filaDesdeRevisionPago,
} from '../escanerInfopagosLoteModel'
import {
  esInstitucionBinanceReescaneo,
  institucionDesdeSugerenciaOcrReescaneo,
  institucionEfectivaReescaneoCartera,
  omitirValidacionFechaBinanceReescaneo,
  omitirValidacionInstitucionReescaneoCartera,
  patchCompletoPagoDesdeOcrReescaneoCartera,
  motivosCamposDigitadosNoAplicadosReescaneo,
  filtrarMotivosAlertaReescaneo,
  sanitizarAlertasReescaneoPorPagoId,
  payloadUpdatePagoDesdeReescaneoOcrCartera,
  type CampoReescaneoOcr,
  cedulaPartesReescaneoCartera,
  partesCedulaParaEscaneoRevision,
  pagoTieneComprobanteInsertado,
} from './EditarRevisionManual.helpers'

const CHUNK_CONTEXTO_REVISION = 10

function fileDesdeBase64(
  b64: string,
  fileName: string,
  mimeType: string
): File {
  const bin = atob(b64)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
  return new File([bytes], fileName || 'comprobante', {
    type: mimeType || 'application/octet-stream',
  })
}

async function listarPagosPrestamo(
  cedula: string,
  prestamoId: number
): Promise<Pago[]> {
  const all: Pago[] = []
  let page = 1
  let totalPages = 1
  do {
    const res = await pagoService.getAllPagos(page, 100, {
      cedula,
      prestamo_cartera: 'todos',
      prestamo_id: prestamoId,
    })
    all.push(...res.pagos)
    totalPages = res.total_pages
    page++
  } while (page <= totalPages)
  return all.filter(p => Number(p.prestamo_id) === prestamoId)
}

function yieldToMain(): Promise<void> {
  return new Promise(resolve => {
    setTimeout(resolve, 0)
  })
}

function validacionReescaneoEfectiva(
  pago: Pago,
  res: EscanerInfopagosExtraerResponse
): { campos: string | null; reglas: string | null } {
  const instOcr = institucionDesdeSugerenciaOcrReescaneo(res.sugerencia ?? null)
  let campos = res.validacion_campos?.trim() || null
  let reglas = res.validacion_reglas?.trim() || null
  if (instOcr) {
    campos = omitirValidacionInstitucionReescaneoCartera(campos)
    reglas = omitirValidacionInstitucionReescaneoCartera(reglas)
  }
  const inst = instOcr || institucionEfectivaReescaneoCartera(pago, res)
  if (esInstitucionBinanceReescaneo(inst)) {
    campos = omitirValidacionFechaBinanceReescaneo(campos)
    reglas = omitirValidacionFechaBinanceReescaneo(reglas)
  }
  return { campos, reglas }
}

function duplicadoBloqueaReescaneo(
  pagoId: number,
  res: EscanerInfopagosExtraerResponse,
  validacion: { campos: string | null; reglas: string | null }
): boolean {
  const fila = filaDesdeRevisionPago(new File([], 'x'), {
    pago_id: pagoId,
    ok: true,
  })
  const filaTras = {
    ...fila,
    validacionCampos: validacion.campos,
    validacionReglas: validacion.reglas,
    escanerColision: {
      duplicado_en_pagos: Boolean(res.duplicado_en_pagos),
      pago_existente_id:
        typeof res.pago_existente_id === 'number'
          ? res.pago_existente_id
          : null,
      prestamo_existente_id:
        typeof res.prestamo_existente_id === 'number'
          ? res.prestamo_existente_id
          : null,
      prestamo_objetivo_id:
        typeof res.prestamo_objetivo_id === 'number'
          ? res.prestamo_objetivo_id
          : null,
    },
  }
  if (!hayDuplicadoFila(filaTras)) return false
  const existId = res.pago_existente_id
  return existId == null || Number(existId) !== pagoId
}

/** Motivos de alerta (Visto, escritura, duplicado, OCR fallido). */
export function evaluarAlertaReescaneoCartera(
  pago: Pago,
  res: EscanerInfopagosExtraerResponse,
  contextoError?: string | null
): string[] {
  const pagoId = Number(pago.id)
  const motivos: string[] = []

  if (contextoError?.trim()) {
    motivos.push(contextoError.trim())
    return motivos
  }

  if (!res.ok || !res.sugerencia) {
    const inst = institucionEfectivaReescaneoCartera(pago, res)
    const instOcr = institucionDesdeSugerenciaOcrReescaneo(
      res.sugerencia ?? null
    )
    let msg =
      res.validacion_reglas?.trim() ||
      res.validacion_campos?.trim() ||
      res.error?.trim() ||
      'No se pudo digitalizar el comprobante; revise manualmente.'
    if (esInstitucionBinanceReescaneo(inst)) {
      msg =
        omitirValidacionFechaBinanceReescaneo(msg) ||
        omitirValidacionFechaBinanceReescaneo(res.error) ||
        ''
    }
    if (instOcr) {
      msg = omitirValidacionInstitucionReescaneoCartera(msg) || ''
    }
    if (msg) motivos.push(msg)
    return filtrarMotivosAlertaReescaneo(motivos)
  }

  const validacion = validacionReescaneoEfectiva(pago, res)
  if (validacion.campos) motivos.push(validacion.campos)
  if (validacion.reglas) motivos.push(validacion.reglas)
  if (duplicadoBloqueaReescaneo(pagoId, res, validacion)) {
    motivos.push(
      'Posible duplicado en cartera; revise y use Visto si corresponde.'
    )
  }

  return filtrarMotivosAlertaReescaneo(motivos)
}

export function resultadoPersistenciaReescaneoOcr(
  pago: Pago,
  res: EscanerInfopagosExtraerResponse
): {
  patch: Partial<PagoCreate> & { monto_bs_original?: number | null }
  hayCambios: boolean
  camposAplicados: CampoReescaneoOcr[]
  limpiarNumeroDocumentoOcr: boolean
} | null {
  if (!res.ok || !res.sugerencia) return null
  const completo = patchCompletoPagoDesdeOcrReescaneoCartera(
    pago,
    res.sugerencia
  )
  return {
    patch: completo.patch,
    hayCambios: completo.hayCambios,
    camposAplicados: completo.camposAplicados,
    limpiarNumeroDocumentoOcr: completo.limpiarNumeroDocumentoOcr,
  }
}

export function evaluarAlertaReescaneoTrasPersistencia(
  pago: Pago,
  res: EscanerInfopagosExtraerResponse,
  camposAplicados: CampoReescaneoOcr[]
): string[] {
  if (!res.ok || !res.sugerencia) {
    return evaluarAlertaReescaneoCartera(pago, res)
  }
  const validacion = validacionReescaneoEfectiva(pago, res)
  const bloquearNumero = duplicadoBloqueaReescaneo(
    Number(pago.id),
    res,
    validacion
  )
  const parciales = motivosCamposDigitadosNoAplicadosReescaneo(
    pago,
    res.sugerencia,
    validacion,
    camposAplicados,
    { bloquearNumeroPorDuplicado: bloquearNumero }
  )
  const motivos = [...parciales]
  const instOcr = institucionDesdeSugerenciaOcrReescaneo(res.sugerencia)
  if (
    !esInstitucionBinanceReescaneo(instOcr || '') &&
    !camposAplicados.includes('fecha') &&
    !fechaPagoDesdeExtraccionOcrConfiable(res.sugerencia.fecha_pago)
  ) {
    motivos.push(
      'Fecha no detectada en el comprobante; indíquela manualmente (no se usa la fecha de hoy).'
    )
  }
  if (duplicadoBloqueaReescaneo(Number(pago.id), res, validacion)) {
    motivos.push(
      'Posible duplicado en cartera; revise y use Visto si corresponde.'
    )
  }
  return filtrarMotivosAlertaReescaneo(motivos)
}

/** @deprecated Use resultadoPersistenciaReescaneoOcr */
export function puedeActualizarPagoDesdeOcrReescaneo(
  pago: Pago,
  res: EscanerInfopagosExtraerResponse
): boolean {
  return resultadoPersistenciaReescaneoOcr(pago, res) != null
}

export type ReescaneoCarteraProgreso = {
  hecho: number
  total: number
  fase: 'ocr' | 'cascada'
}

export type ReescaneoCarteraResultado = {
  alertas: Record<number, string[]>
  escaneados: number
  actualizados: number
  omitidosSinImagen: number
}

/**
 * Re-escanea solo comprobantes ya insertados en el préstamo (OCR + actualización).
 * Pagos sin imagen no se tocan. Por cada pago: vacía campos OCR y persiste solo
 * lo detectado en esta pasada (digitalización desde cero, sin hint de banco previo).
 */
export async function reescanearComprobantesCarteraPrestamo(opts: {
  cedula: string
  prestamoId: number
  onProgreso?: (progreso: ReescaneoCarteraProgreso) => void
}): Promise<ReescaneoCarteraResultado> {
  if (!Number.isFinite(opts.prestamoId) || opts.prestamoId <= 0) {
    throw new Error('Préstamo inválido para re-escanear comprobantes.')
  }

  const pagos = await listarPagosPrestamo(opts.cedula, opts.prestamoId)
  const pagosConImagen = pagos.filter(pagoTieneComprobanteInsertado)
  const omitidosSinImagen = pagos.length - pagosConImagen.length

  const ids = pagosConImagen
    .map(p => Number(p.id))
    .filter(id => Number.isFinite(id) && id > 0)

  if (!ids.length) {
    return {
      alertas: {},
      escaneados: 0,
      actualizados: 0,
      omitidosSinImagen,
    }
  }

  const pagoById = new Map(pagosConImagen.map(p => [Number(p.id), p]))
  const alertas: Record<number, string[]> = {}
  let hecho = 0
  let actualizados = 0
  const total = ids.length
  opts.onProgreso?.({ hecho: 0, total, fase: 'ocr' })

  for (let i = 0; i < ids.length; i += CHUNK_CONTEXTO_REVISION) {
    const chunkIds = ids.slice(i, i + CHUNK_CONTEXTO_REVISION)
    const ctx = await escanerInfopagosLoteContextoRevision(chunkIds)

    for (const item of ctx.items) {
      const pago = pagoById.get(item.pago_id)
      if (!pago) {
        hecho++
        opts.onProgreso?.({ hecho, total, fase: 'ocr' })
        continue
      }

      if (!item.ok || !(item.archivo_b64 || '').trim()) {
        const motivos = evaluarAlertaReescaneoCartera(
          pago,
          { ok: false, sugerencia: null },
          item.error ||
            'No se pudo cargar el comprobante guardado para re-escanear.'
        )
        if (motivos.length) alertas[item.pago_id] = motivos
        hecho++
        opts.onProgreso?.({ hecho, total, fase: 'ocr' })
        await yieldToMain()
        continue
      }

      let archivo = fileDesdeBase64(
        item.archivo_b64!,
        item.nombre_archivo || `pago_${item.pago_id}.jpg`,
        item.mime_type || 'image/jpeg'
      )
      try {
        archivo = await normalizarComprobanteArchivoParaEscaneo(archivo)
      } catch {
        alertas[item.pago_id] = [
          'No se pudo preparar el comprobante para escanear (HEIC/PDF).',
        ]
        hecho++
        opts.onProgreso?.({ hecho, total, fase: 'ocr' })
        await yieldToMain()
        continue
      }

      const cedulaPartes = cedulaPartesReescaneoCartera(
        opts.cedula,
        pago.cedula_cliente
      )

      const fd = buildFormDataEscanerComprobante({
        tipoCedula: cedulaPartes.tipo,
        numeroCedula: cedulaPartes.numero,
        comprobante: archivo,
        extraccionSinCliente: true,
        prestamoObjetivoId: opts.prestamoId,
      })

      try {
        const res = await escanerInfopagosExtraerComprobante(fd)
        const persistencia = resultadoPersistenciaReescaneoOcr(pago, res)
        if (persistencia) {
          const payload = payloadUpdatePagoDesdeReescaneoOcrCartera(
            persistencia.patch,
            {
              limpiarNumeroDocumentoOcr:
                persistencia.limpiarNumeroDocumentoOcr,
            }
          )
          const debePersistir =
            persistencia.hayCambios ||
            persistencia.camposAplicados.length > 0 ||
            persistencia.limpiarNumeroDocumentoOcr
          if (debePersistir) {
            await pagoService.updatePago(item.pago_id, payload)
            actualizados++
            const motivos = evaluarAlertaReescaneoTrasPersistencia(
              pago,
              res,
              persistencia.camposAplicados
            )
            if (motivos.length) {
              alertas[item.pago_id] = motivos
            }
          } else {
            const motivos = evaluarAlertaReescaneoCartera(pago, res)
            if (motivos.length) {
              alertas[item.pago_id] = motivos
            }
          }
        } else {
          const motivos = evaluarAlertaReescaneoCartera(pago, res)
          if (motivos.length) {
            alertas[item.pago_id] = motivos
          }
        }
      } catch (err) {
        alertas[item.pago_id] = [mensajeErrorExtraccionEscaner(err)]
      }

      hecho++
      opts.onProgreso?.({ hecho, total, fase: 'ocr' })
      await yieldToMain()
    }
  }

  return {
    alertas: sanitizarAlertasReescaneoPorPagoId(alertas),
    escaneados: total,
    actualizados,
    omitidosSinImagen,
  }
}
