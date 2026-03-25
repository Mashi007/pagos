import { useState } from 'react'

import {
  Download,
  Eye,
  FileText,
  CheckCircle,
  Clock,
  AlertCircle,
  RefreshCw,
} from 'lucide-react'

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'

import { Button } from '../../components/ui/button'

import { Badge } from '../../components/ui/badge'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table'

import { Prestamo } from '../../types'

import { prestamoService } from '../../services/prestamoService'

import { cuotasPrestamoQueryKey } from '../../constants/queryKeys'

import { useQuery } from '@tanstack/react-query'

import { formatDate } from '../../utils'

import {
  codigoEstadoCuotaParaUi,
  etiquetaEstadoCuotaRespaldo,
} from '../../utils/cuotaEstadoDisplay'

import { toast } from 'sonner'

interface Cuota {
  id: number

  numero_cuota: number

  fecha_vencimiento: string

  fecha_pago?: string | null

  monto_cuota: number

  monto_capital?: number // Opcional - puede no existir

  monto_interes?: number // Opcional - puede no existir

  saldo_capital_inicial: number

  saldo_capital_final: number

  capital_pagado?: number

  interes_pagado?: number

  total_pagado: number

  capital_pendiente?: number

  interes_pendiente?: number

  estado: string

  estado_etiqueta?: string

  dias_mora: number

  dias_morosidad?: number

  monto_morosidad?: number

  pago_id?: number | null

  pago_conciliado?: boolean

  pago_monto_conciliado?: number
}

interface TablaAmortizacionPrestamoProps {
  prestamo: Prestamo
}

export function TablaAmortizacionPrestamo({
  prestamo,
}: TablaAmortizacionPrestamoProps) {
  const [showFullTable, setShowFullTable] = useState(false)

  const [descargandoRecibo, setDescargandoRecibo] = useState<number | null>(
    null
  )

  const descargarRecibo = async (cuota: Cuota) => {
    setDescargandoRecibo(cuota.id)

    try {
      await prestamoService.getReciboCuotaPdf(prestamo.id, cuota.id)

      toast.success(`Recibo cuota ${cuota.numero_cuota} descargado`)
    } catch (err) {
      console.error('Error generando recibo:', err)

      toast.error('Error al generar el recibo')
    } finally {
      setDescargandoRecibo(null)
    }
  }

  // Cargar cuotas del préstamo (tabla de amortización desde BD: pagos aplicados a cuotas)

  const {
    data: cuotas,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: cuotasPrestamoQueryKey(prestamo.id),

    queryFn: () => prestamoService.getCuotasPrestamo(prestamo.id),

    enabled: prestamo.estado === 'APROBADO' || prestamo.estado === 'LIQUIDADO',

    staleTime: 0,

    refetchOnMount: 'always',

    refetchOnWindowFocus: true,
  })

  // Estado: codigo y etiqueta vienen del backend (get_cuotas_prestamo); sin segunda clasificacion en cliente.

  const getEstadoBadge = (estado: string) => {
    const estadoNormalizado = estado?.toUpperCase() || 'PENDIENTE'

    const badges = {
      PENDIENTE: 'bg-yellow-100 text-yellow-800',

      PAGADO: 'bg-green-100 text-green-800',

      PAGADA: 'bg-green-100 text-green-800',

      PAGO_ADELANTADO: 'bg-blue-100 text-blue-800',

      VENCIDO: 'bg-orange-100 text-orange-800',

      MORA: 'bg-red-100 text-red-800',

      PARCIAL: 'bg-amber-100 text-amber-900',
    }

    return badges[estadoNormalizado as keyof typeof badges] || badges.PENDIENTE
  }

  const getEstadoLabel = (estado: string) => {
    const estadoNormalizado = estado?.toUpperCase() || 'PENDIENTE'

    const labels: Record<string, string> = {
      PENDIENTE: 'Pendiente',

      PAGADO: 'Pagado',

      PAGADA: 'Pagada',

      PAGO_ADELANTADO: 'Pago adelantado',

      VENCIDO: 'Vencido',

      MORA: 'Mora (92+ d)',

      PARCIAL: 'Pendiente parcial',
    }

    return labels[estadoNormalizado] || estado
  }

  // Total pendiente por pagar (cuotas no cubiertas al 100%) - usa total_pagado y pago_monto_conciliado

  const totalPendientePagar = cuotas
    ? cuotas.reduce((acc: number, c: Cuota) => {
        const montoCuota = typeof c.monto_cuota === 'number' ? c.monto_cuota : 0

        const totalPagado =
          typeof c.total_pagado === 'number' ? c.total_pagado : 0

        const montoConciliado =
          typeof c.pago_monto_conciliado === 'number'
            ? c.pago_monto_conciliado
            : 0

        const montoPagado = Math.max(totalPagado, montoConciliado)

        const pendiente = Math.max(0, montoCuota - montoPagado)

        return acc + pendiente
      }, 0)
    : 0

  const exportarExcel = async () => {
    try {
      await prestamoService.descargarAmortizacionExcel(
        prestamo.id,
        prestamo.cedula
      )

      toast.success('Excel descargado exitosamente')
    } catch (error) {
      console.error('Error al exportar a Excel:', error)

      toast.error('Error al exportar a Excel')
    }
  }

  const exportarPDF = async () => {
    try {
      await prestamoService.descargarEstadoCuentaPDF(prestamo.id)

      toast.success('Estado de cuenta PDF descargado exitosamente')
    } catch (error) {
      console.error('Error al exportar a PDF:', error)

      toast.error('Error al exportar estado de cuenta PDF')
    }
  }

  if (prestamo.estado !== 'APROBADO' && prestamo.estado !== 'LIQUIDADO') {
    return (
      <Card className="border-yellow-200 bg-yellow-50">
        <CardContent className="pt-6">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-yellow-600" />

            <p className="text-sm text-yellow-800">
              La tabla de amortización solo se puede ver para préstamos
              aprobados o liquidados. Estado actual:{' '}
              <strong>{prestamo.estado}</strong>
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="py-8 text-center">
            <div className="mx-auto h-8 w-8 animate-spin rounded-full border-b-2 border-blue-600"></div>

            <p className="mt-2 text-sm text-gray-600">
              Cargando tabla de amortización...
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="border-red-200 bg-red-50">
        <CardContent className="pt-6">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-red-600" />

            <p className="text-sm text-red-800">
              Error al cargar la tabla de amortización
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!cuotas || cuotas.length === 0) {
    return (
      <Card className="border-yellow-200 bg-yellow-50">
        <CardContent className="pt-6">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-yellow-600" />

            <div>
              <p className="mb-2 text-sm text-yellow-800">
                No hay tabla de amortización generada para este préstamo.
              </p>

              {prestamo.fecha_base_calculo && (
                <Button
                  size="sm"
                  onClick={async () => {
                    try {
                      await prestamoService.generarAmortizacion(prestamo.id)

                      toast.success(
                        'Tabla de amortización generada exitosamente'
                      )

                      // Refrescar datos

                      window.location.reload()
                    } catch (error: any) {
                      toast.error(
                        error.response?.data?.detail ||
                          'Error al generar amortización'
                      )
                    }
                  }}
                >
                  Generar Tabla
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Mostrar solo primeras 5 cuotas por defecto

  const cuotasVisibles = showFullTable ? cuotas : cuotas.slice(0, 5)

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="flex items-center gap-3">
          <FileText className="h-6 w-6 text-blue-600" />

          <CardTitle>Tabla de Amortización</CardTitle>

          <Badge variant="secondary">{cuotas.length} cuotas</Badge>
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            title="Actualizar tabla con los últimos pagos aplicados"
          >
            <RefreshCw
              className={`mr-2 h-4 w-4 ${isFetching ? 'animate-spin' : ''}`}
            />
            Refrescar
          </Button>

          <Button variant="outline" size="sm" onClick={exportarExcel}>
            <Download className="mr-2 h-4 w-4" />
            Exportar Excel
          </Button>

          <Button variant="outline" size="sm" onClick={exportarPDF}>
            <Download className="mr-2 h-4 w-4" />
            Exportar PDF
          </Button>

          {!showFullTable && cuotas.length > 5 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowFullTable(true)}
            >
              Ver Todas ({cuotas.length})
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent>
        <div className="overflow-hidden rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Cuota</TableHead>

                <TableHead>Fecha Vencimiento</TableHead>

                <TableHead className="text-right">Capital</TableHead>

                <TableHead className="text-right">Interés</TableHead>

                <TableHead className="text-right">Total</TableHead>

                <TableHead className="text-right">Saldo Pendiente</TableHead>

                <TableHead className="text-right">Pago conciliado</TableHead>

                <TableHead>Estado</TableHead>

                <TableHead className="text-center">Recibo</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {cuotasVisibles.map((cuota: Cuota) => {
                // Determinar el estado real basado en los datos

                const codigoEstado = codigoEstadoCuotaParaUi(cuota.estado)

                const textoEstadoCuota =
                  (cuota.estado_etiqueta && cuota.estado_etiqueta.trim()) ||
                  etiquetaEstadoCuotaRespaldo(cuota.estado)

                const totalPagado =
                  typeof cuota.total_pagado === 'number'
                    ? cuota.total_pagado
                    : parseFloat(String(cuota.total_pagado ?? 0)) || 0

                const montoConciliadoBackend =
                  typeof cuota.pago_monto_conciliado === 'number'
                    ? cuota.pago_monto_conciliado
                    : parseFloat(String(cuota.pago_monto_conciliado ?? 0)) || 0

                const montoCuota =
                  typeof cuota.monto_cuota === 'number'
                    ? cuota.monto_cuota
                    : parseFloat(String(cuota.monto_cuota ?? 0)) || 0

                const estaPagado =
                  totalPagado > 0 ||
                  montoConciliadoBackend > 0 ||
                  ['PAGADO', 'PAGADA', 'PAGO_ADELANTADO'].includes(codigoEstado)

                // Priorizar pago_monto_conciliado del backend (valores conciliados por préstamo), luego total_pagado, luego monto_cuota si está pagado

                const montoPagoConciliado =
                  montoConciliadoBackend > 0
                    ? montoConciliadoBackend
                    : totalPagado > 0
                      ? totalPagado
                      : estaPagado
                        ? montoCuota
                        : 0

                // Enlace recibo: cuota totalmente pagada (por estado o por monto)

                const estadoBackend = (cuota.estado || '').toUpperCase()

                const cuotaCubiertaPorMonto =
                  montoCuota > 0 &&
                  (totalPagado >= montoCuota - 0.01 ||
                    montoConciliadoBackend >= montoCuota - 0.01)

                const puedeDescargarRecibo =
                  ['PAGADO', 'PAGADA', 'PAGO_ADELANTADO'].includes(
                    codigoEstado
                  ) ||
                  ['PAGADO', 'PAGADA', 'PAGO_ADELANTADO'].includes(
                    estadoBackend
                  ) ||
                  cuotaCubiertaPorMonto

                // Calcular monto_capital y monto_interes si no existen

                // Capital = diferencia entre saldo inicial y final

                const saldoInicial =
                  typeof cuota.saldo_capital_inicial === 'number'
                    ? cuota.saldo_capital_inicial
                    : 0

                const saldoFinal =
                  typeof cuota.saldo_capital_final === 'number'
                    ? cuota.saldo_capital_final
                    : 0

                const montoCapital =
                  typeof cuota.monto_capital === 'number' &&
                  !isNaN(cuota.monto_capital)
                    ? cuota.monto_capital
                    : Math.max(0, saldoInicial - saldoFinal)

                const montoInteres =
                  typeof cuota.monto_interes === 'number' &&
                  !isNaN(cuota.monto_interes)
                    ? cuota.monto_interes
                    : Math.max(0, montoCuota - montoCapital)

                return (
                  <TableRow key={cuota.id}>
                    <TableCell className="font-medium">
                      {cuota.numero_cuota}
                    </TableCell>

                    <TableCell>{formatDate(cuota.fecha_vencimiento)}</TableCell>

                    <TableCell className="text-right">
                      ${montoCapital.toFixed(2)}
                    </TableCell>

                    <TableCell className="text-right">
                      ${montoInteres.toFixed(2)}
                    </TableCell>

                    <TableCell className="text-right font-semibold">
                      ${montoCuota.toFixed(2)}
                    </TableCell>

                    <TableCell className="text-right text-gray-600">
                      ${saldoFinal.toFixed(2)}
                    </TableCell>

                    <TableCell className="text-right">
                      {montoPagoConciliado > 0 ? (
                        <span
                          className={
                            cuota.pago_conciliado
                              ? 'font-medium text-emerald-600'
                              : 'font-medium text-blue-600'
                          }
                        >
                          ${montoPagoConciliado.toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </TableCell>

                    <TableCell>
                      <Badge className={getEstadoBadge(codigoEstado)}>
                        {textoEstadoCuota}
                      </Badge>

                      {/* ðŸ" DEBUG: Mostrar información de depuración */}

                      {process.env.NODE_ENV === 'development' && (
                        <div className="mt-1 text-xs text-gray-400">
                          <div>Estado BD: {cuota.estado || 'NULL'}</div>

                          <div>Etiqueta: {textoEstadoCuota}</div>

                          <div>
                            Pagado: $
                            {(typeof cuota.total_pagado === 'number'
                              ? cuota.total_pagado
                              : 0
                            ).toFixed(2)}{' '}
                            / ${montoCuota.toFixed(2)}
                          </div>
                        </div>
                      )}
                    </TableCell>

                    <TableCell className="text-center">
                      {puedeDescargarRecibo ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          title={`Descargar recibo cuota ${cuota.numero_cuota}`}
                          onClick={() => descargarRecibo(cuota)}
                          disabled={descargandoRecibo === cuota.id}
                          className="inline-flex h-8 items-center gap-1 px-2 text-red-600 hover:bg-red-50 hover:text-red-800"
                        >
                          {descargandoRecibo === cuota.id ? (
                            <span className="text-xs">⏳</span>
                          ) : (
                            <>
                              <FileText className="h-4 w-4 shrink-0" />

                              <span className="text-xs">Ver recibo</span>
                            </>
                          )}
                        </Button>
                      ) : (
                        <span className="text-xs text-gray-400">-</span>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}

              {!showFullTable && cuotas.length > 5 && (
                <TableRow>
                  <TableCell colSpan={9} className="py-4 text-center">
                    <Button
                      variant="ghost"
                      onClick={() => setShowFullTable(true)}
                    >
                      Ver {cuotas.length - 5} cuotas más...
                    </Button>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        {/* Resumen */}

        {cuotas.length > 0 && (
          <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-5">
            <Card className="border-amber-200 bg-amber-50">
              <CardContent className="pt-4">
                <p className="text-sm font-medium text-amber-700">
                  Total pendiente pagar
                </p>

                <p className="text-2xl font-bold text-amber-800">
                  ${totalPendientePagar.toFixed(2)}
                </p>
              </CardContent>
            </Card>

            <Card className="border-green-200 bg-green-50">
              <CardContent className="pt-4">
                <p className="text-sm text-green-600">Total Capital</p>

                <p className="text-2xl font-bold text-green-700">
                  $
                  {cuotas
                    .reduce((acc, c: Cuota) => {
                      const saldoInicial =
                        typeof c.saldo_capital_inicial === 'number'
                          ? c.saldo_capital_inicial
                          : 0

                      const saldoFinal =
                        typeof c.saldo_capital_final === 'number'
                          ? c.saldo_capital_final
                          : 0

                      const montoCapital =
                        typeof c.monto_capital === 'number' &&
                        !isNaN(c.monto_capital)
                          ? c.monto_capital
                          : Math.max(0, saldoInicial - saldoFinal)

                      return acc + montoCapital
                    }, 0)
                    .toFixed(2)}
                </p>
              </CardContent>
            </Card>

            <Card className="border-blue-200 bg-blue-50">
              <CardContent className="pt-4">
                <p className="text-sm text-blue-600">Total Intereses</p>

                <p className="text-2xl font-bold text-blue-700">
                  $
                  {cuotas
                    .reduce((acc, c: Cuota) => {
                      const saldoInicial =
                        typeof c.saldo_capital_inicial === 'number'
                          ? c.saldo_capital_inicial
                          : 0

                      const saldoFinal =
                        typeof c.saldo_capital_final === 'number'
                          ? c.saldo_capital_final
                          : 0

                      const montoCuota =
                        typeof c.monto_cuota === 'number' ? c.monto_cuota : 0

                      const montoCapital =
                        typeof c.monto_capital === 'number' &&
                        !isNaN(c.monto_capital)
                          ? c.monto_capital
                          : Math.max(0, saldoInicial - saldoFinal)

                      const montoInteres =
                        typeof c.monto_interes === 'number' &&
                        !isNaN(c.monto_interes)
                          ? c.monto_interes
                          : Math.max(0, montoCuota - montoCapital)

                      return acc + montoInteres
                    }, 0)
                    .toFixed(2)}
                </p>
              </CardContent>
            </Card>

            <Card className="border-purple-200 bg-purple-50">
              <CardContent className="pt-4">
                <p className="text-sm text-purple-600">Monto Total</p>

                <p className="text-2xl font-bold text-purple-700">
                  $
                  {cuotas
                    .reduce((acc, c: Cuota) => {
                      const montoCuota =
                        typeof c.monto_cuota === 'number' ? c.monto_cuota : 0

                      return acc + montoCuota
                    }, 0)
                    .toFixed(2)}
                </p>
              </CardContent>
            </Card>

            <Card className="border-gray-200 bg-gray-50">
              <CardContent className="pt-4">
                <p className="text-sm text-gray-600">Pagadas</p>

                <p className="text-2xl font-bold text-gray-700">
                  {
                    cuotas.filter((c: Cuota) => {
                      const totalPagado = c.total_pagado ?? 0

                      const montoConciliado = c.pago_monto_conciliado ?? 0

                      const montoPagado = Math.max(
                        Number(totalPagado) || 0,
                        Number(montoConciliado) || 0
                      )

                      const montoCuota = c.monto_cuota || 0

                      return montoPagado >= montoCuota - 0.01
                    }).length
                  }{' '}
                  / {cuotas.length}
                </p>
              </CardContent>
            </Card>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
