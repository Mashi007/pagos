import { toast } from 'sonner'

import {
  TIMEOUT_MS_ENVIO_NOTIFICACIONES_MANUAL,
} from '../../services/notificacionService'

import { getErrorMessage, isAxiosTimeoutError } from '../../types/errors'

/** Fecha calendario actual en America/Caracas como YYYY-MM-DD (para max en input date). */
export function fechaHoyCaracasISO(): string {
  return new Date().toLocaleDateString('en-CA', {
    timeZone: 'America/Caracas',
  })
}

/** Interpreta la respuesta del envío manual para que no parezca «no pasó nada» si enviados = 0. */
export function toastResultadoEnvioNotificaciones(
  res: {
    mensaje?: string
    enviados?: number
    sin_email?: number
    fallidos?: number
    total_en_lista?: number
    omitidos_config?: number
    omitidos_paquete_incompleto?: number
  },
  filasVisiblesEnTabla: number
): void {
  const enviados = Number(res.enviados ?? 0)
  const totalLista =
    res.total_en_lista != null && !Number.isNaN(Number(res.total_en_lista))
      ? Number(res.total_en_lista)
      : filasVisiblesEnTabla
  const sinEmail = Number(res.sin_email ?? 0)
  const fallidos = Number(res.fallidos ?? 0)
  const omitPkg = Number(res.omitidos_paquete_incompleto ?? 0)
  const omitCfg = Number(res.omitidos_config ?? 0)
  const msgBase = (res.mensaje ?? 'Envío finalizado').trim()

  if (enviados === 0 && totalLista > 0) {
    toast.warning(
      `${msgBase} Nadie recibió correo aunque la lista tenía ${totalLista} fila(s). Revise: email del cliente, modo prueba, fila «Envío» en Configuración, plantilla y PDF de cobranza (paquete incompleto). Sin email: ${sinEmail}. Omitidos por config: ${omitCfg}. Paquete incompleto: ${omitPkg}. Fallidos SMTP: ${fallidos}.`,
      { duration: 14000 }
    )
    return
  }

  if (enviados === 0 && totalLista === 0) {
    toast.message(
      'No había destinatarios en la lista para esta fecha y criterio. No se envió ningún correo.',
      { duration: 7000 }
    )
    return
  }

  toast.success(
    `${msgBase} Enviados: ${enviados}. Sin email: ${sinEmail}. Fallidos: ${fallidos}.`,
    { duration: 9000 }
  )
}

export function toastErrorTrasEnvioManual(
  e: unknown,
  fraseRevisionConfig: string
): void {
  if (isAxiosTimeoutError(e)) {
    const min = Math.max(
      1,
      Math.round(TIMEOUT_MS_ENVIO_NOTIFICACIONES_MANUAL / 60000)
    )
    toast.warning(
      `El navegador dejó de esperar tras ${min} min (timeout). Con muchas filas y adjuntos el envío puede seguir en el servidor: antes de reintentar, revise «Último envío por lote» o el historial para no duplicar correos. ${fraseRevisionConfig}`,
      { duration: 20000 }
    )
    return
  }

  toast.error(
    `No se pudo completar el envío: ${getErrorMessage(e)}. ${fraseRevisionConfig}`
  )
}
