import { pagoConErrorService } from '../services/pagoConErrorService'
import { pagoService } from '../services/pagoService'
import { getErrorMessage, isAxiosError } from '../types/errors'

export type ResultadoEliminarPagoRevision =
  | 'con_error'
  | 'cartera'
  | 'ya_ausente'

/**
 * Elimina un pago de revisión (`pagos_con_errores`). Si ya fue movido a cartera
 * (404), elimina el pago operativo cuando se conoce su ID o informa ausencia sin error.
 */
export async function eliminarPagoRevisionOConError(opts: {
  idConError: number
  idCartera?: number | null
}): Promise<ResultadoEliminarPagoRevision> {
  const { idConError, idCartera } = opts

  try {
    await pagoConErrorService.delete(idConError)
    return 'con_error'
  } catch (error) {
    const es404 =
      isAxiosError(error) &&
      error.response?.status === 404 &&
      /pago con error no encontrado/i.test(getErrorMessage(error))

    if (!es404) throw error

    if (idCartera != null && idCartera > 0) {
      await pagoService.deletePago(idCartera)
      return 'cartera'
    }

    return 'ya_ausente'
  }
}
