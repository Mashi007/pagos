/**





 * Seccion de pagos con errores en la carga masiva.





 * Muestra filas rechazadas durante validacion y permite revisar o descartar.





 */

import { motion } from 'framer-motion'

import { AlertTriangle, Eye, X, Loader2 } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'

import { Button } from '../ui/button'

import { Badge } from '../ui/badge'

export interface PagoConError {
  id: number

  fila_origen: number

  cedula: string

  monto: number

  errores: string[]

  accion: string
}

interface PagosConErroresSectionProps {
  pagosConErrores: PagoConError[]

  registrosConError: number

  isProcessing: boolean

  onMoveToReview: (id: number) => Promise<void> | void

  onDismiss: (id: number) => void

  onMoveAllToReview?: () => Promise<void> | void
}

export function PagosConErroresSection({
  pagosConErrores,

  registrosConError,

  isProcessing,

  onMoveToReview,

  onDismiss,

  onMoveAllToReview,
}: PagosConErroresSectionProps) {
  if (registrosConError === 0 || pagosConErrores.length === 0) {
    return null
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3 }}
      className="space-y-4"
    >
      <Card className="border-orange-300 bg-orange-50 shadow-md">
        <CardHeader className="bg-gradient-to-r from-orange-100 to-orange-50 pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-orange-600" />

              <CardTitle className="text-orange-600">
                Pagos para Revisar
              </CardTitle>

              <Badge
                variant="secondary"
                className="ml-2 bg-orange-200 text-orange-800"
              >
                {registrosConError}
              </Badge>
            </div>

            <Badge
              variant="outline"
              className="border-orange-300 bg-white text-orange-700"
            >
              ⚠️ Requiere Revision
            </Badge>
          </div>

          <p className="ml-7 mt-2 text-sm text-orange-700">
            Las siguientes filas no cumplieron con las validaciones. Puedes
            revisar cada una o descartar.
          </p>
        </CardHeader>

        <CardContent className="pt-4">
          <div className="max-h-[400px] space-y-2 overflow-y-auto pr-2">
            {pagosConErrores.map((pago, index) => (
              <motion.div
                key={pago.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ delay: index * 0.05 }}
                className="flex items-start justify-between rounded-lg border border-orange-200 bg-white p-3 transition-shadow hover:border-orange-400 hover:shadow-md"
              >
                <div className="min-w-0 flex-1 space-y-2">
                  {/* Fila, Cedula, Monto */}

                  <div className="flex flex-wrap items-center gap-y-1 space-x-3">
                    <span className="inline-block rounded bg-orange-100 px-2 py-1 text-xs font-semibold text-orange-800">
                      Fila {pago.fila_origen}
                    </span>

                    <span className="text-sm font-medium text-gray-700">
                      {pago.cedula}
                    </span>

                    <span className="text-sm text-gray-600">
                      $
                      {pago.monto.toLocaleString('es-VE', {
                        maximumFractionDigits: 2,
                      })}
                    </span>
                  </div>

                  {/* Errores */}

                  <div className="ml-2 space-y-1">
                    {pago.errores.map((error, idx) => (
                      <div
                        key={idx}
                        className="flex items-start space-x-2 text-sm text-orange-700"
                      >
                        <span className="mt-0.5 text-orange-500">•</span>

                        <span className="break-words">{error}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Botones */}

                <div className="ml-4 flex flex-shrink-0 items-center space-x-1">
                  <Button
                    size="sm"
                    variant="outline"
                    className="whitespace-nowrap border-orange-300 text-orange-600 hover:bg-orange-100 hover:text-orange-700"
                    onClick={() => onMoveToReview(pago.id)}
                    disabled={isProcessing}
                  >
                    {isProcessing ? (
                      <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                    ) : (
                      <Eye className="mr-1 h-4 w-4" />
                    )}
                    Revisar
                  </Button>

                  <Button
                    size="sm"
                    variant="ghost"
                    className="px-2 text-gray-400 hover:bg-red-50 hover:text-red-600"
                    onClick={() => onDismiss(pago.id)}
                    disabled={isProcessing}
                    title="Descartar esta fila"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Footer con Revisar Todos */}

          <div className="mt-4 flex items-center justify-between border-t border-orange-200 pt-4">
            <div className="text-sm text-gray-600">
              <span className="font-medium">{pagosConErrores.length}</span>{' '}
              fila(s) guardada(s) para revisar
            </div>

            {pagosConErrores.length > 1 && onMoveAllToReview && (
              <Button
                size="sm"
                className="bg-orange-600 text-white hover:bg-orange-700"
                onClick={onMoveAllToReview}
                disabled={isProcessing}
              >
                {isProcessing ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Eye className="mr-2 h-4 w-4" />
                )}
                Revisar Todos ({pagosConErrores.length})
              </Button>
            )}
          </div>

          {/* Info adicional */}

          <div className="mt-3 rounded border border-orange-200 bg-orange-100 p-3 text-sm text-orange-800">
            <strong>Nota:</strong> Los pagos con error se guardan en la tabla de
            errores. Puede revisarlos y moverlos a "Revisar Pagos" para análisis
            posterior.
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}
