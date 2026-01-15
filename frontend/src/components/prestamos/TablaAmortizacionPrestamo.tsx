import { useState } from 'react'
import { Download, Eye, FileText, CheckCircle, Clock, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Prestamo } from '@/types'
import { prestamoService } from '@/services/prestamoService'
import { useQuery } from '@tanstack/react-query'
import { formatDate } from '@/utils'
import toast from 'react-hot-toast'
import { exportarAExcel, exportarAPDF } from '@/utils/exportUtils'

interface Cuota {
  id: number
  numero_cuota: number
  fecha_vencimiento: string
  monto_cuota: number
  monto_capital?: number  // Opcional - puede no existir
  monto_interes?: number  // Opcional - puede no existir
  saldo_capital_inicial: number
  saldo_capital_final: number
  capital_pagado?: number
  interes_pagado?: number
  total_pagado: number
  capital_pendiente?: number
  interes_pendiente?: number
  estado: string
  dias_mora: number
  dias_morosidad?: number
  monto_morosidad?: number
}

interface TablaAmortizacionPrestamoProps {
  prestamo: Prestamo
}

export function TablaAmortizacionPrestamo({ prestamo }: TablaAmortizacionPrestamoProps) {
  const [showFullTable, setShowFullTable] = useState(false)

  // Cargar cuotas del préstamo
  const { data: cuotas, isLoading, error } = useQuery({
    queryKey: ['cuotas-prestamo', prestamo.id],
    queryFn: async () => {
      const data = await prestamoService.getCuotasPrestamo(prestamo.id)
      // 🔍 DEBUG: Verificar qué estados están llegando
      console.log('📊 Cuotas recibidas del backend:', data)
      console.log('📊 Estados encontrados:', data?.map((c: Cuota) => c.estado))
      return data
    },
    enabled: prestamo.estado === 'APROBADO' || prestamo.estado === 'DESEMBOLSADO',
    staleTime: 0, // Siempre refetch para obtener datos actualizados
    refetchOnMount: true, // Refetch al montar el componente
    refetchOnWindowFocus: true, // Refetch al enfocar la ventana
  })

  // Función para determinar el estado correcto basado en los datos
  const determinarEstadoReal = (cuota: Cuota): string => {
    const totalPagado = cuota.total_pagado || 0
    const montoCuota = cuota.monto_cuota || 0
    
    // Si total_pagado >= monto_cuota, debería ser PAGADO
    if (totalPagado >= montoCuota) {
      return 'PAGADO'
    }
    // Si tiene algún pago pero no completo
    if (totalPagado > 0) {
      // Verificar si está vencida
      const hoy = new Date()
      const fechaVencimiento = cuota.fecha_vencimiento ? new Date(cuota.fecha_vencimiento) : null
      if (fechaVencimiento && fechaVencimiento < hoy) {
        return 'ATRASADO'
      }
      return 'PARCIAL'
    }
    // Si no hay pago, devolver el estado original o PENDIENTE
    return cuota.estado || 'PENDIENTE'
  }

  const getEstadoBadge = (estado: string) => {
    // Normalizar estado a mayúsculas para comparación
    const estadoNormalizado = estado?.toUpperCase() || 'PENDIENTE'

    const badges = {
      PENDIENTE: 'bg-yellow-100 text-yellow-800',
      PAGADO: 'bg-green-100 text-green-800',  // ✅ Corregido: BD usa "PAGADO" no "PAGADA"
      PAGADA: 'bg-green-100 text-green-800',   // Mantener compatibilidad
      ATRASADO: 'bg-red-100 text-red-800',     // ✅ Agregado: BD también usa "ATRASADO"
      VENCIDA: 'bg-red-100 text-red-800',      // Mantener compatibilidad
      PARCIAL: 'bg-blue-100 text-blue-800',
    }
    return badges[estadoNormalizado as keyof typeof badges] || badges.PENDIENTE
  }

  const getEstadoLabel = (estado: string) => {
    // Normalizar estado a mayúsculas para comparación
    const estadoNormalizado = estado?.toUpperCase() || 'PENDIENTE'

    const labels: Record<string, string> = {
      PENDIENTE: 'Pendiente',
      PAGADO: 'Pagado',      // ✅ Corregido: BD usa "PAGADO"
      PAGADA: 'Pagada',      // Mantener compatibilidad
      ATRASADO: 'Atrasado',  // ✅ Agregado: BD también usa "ATRASADO"
      VENCIDA: 'Vencida',    // Mantener compatibilidad
      PARCIAL: 'Parcial',
    }
    return labels[estadoNormalizado] || estado
  }

  const exportarExcel = async () => {
    if (!cuotas) {
      toast.error('No hay datos para exportar')
      return
    }

    const prestamoInfo = {
      id: prestamo.id,
      cedula: prestamo.cedula,
      nombres: prestamo.nombres,
      total_financiamiento: prestamo.total_financiamiento,
      numero_cuotas: prestamo.numero_cuotas,
      modalidad_pago: prestamo.modalidad_pago,
      fecha_requerimiento: prestamo.fecha_requerimiento
    }

    try {
      await exportarAExcel(cuotas, prestamoInfo)
      toast.success('Exportando a Excel...')
    } catch (error) {
      toast.error('Error al exportar a Excel')
    }
  }

  const exportarPDF = async () => {
    if (!cuotas) {
      toast.error('No hay datos para exportar')
      return
    }

    const prestamoInfo = {
      id: prestamo.id,
      cedula: prestamo.cedula,
      nombres: prestamo.nombres,
      total_financiamiento: prestamo.total_financiamiento,
      numero_cuotas: prestamo.numero_cuotas,
      modalidad_pago: prestamo.modalidad_pago,
      fecha_requerimiento: prestamo.fecha_requerimiento
    }

    try {
      await exportarAPDF(cuotas, prestamoInfo)
      toast.success('PDF exportado exitosamente')
    } catch (error) {
      console.error('Error al exportar a PDF:', error)
      toast.error('Error al exportar a PDF')
    }
  }

  if (prestamo.estado !== 'APROBADO' && prestamo.estado !== 'DESEMBOLSADO') {
    return (
      <Card className="border-yellow-200 bg-yellow-50">
        <CardContent className="pt-6">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-yellow-600" />
            <p className="text-sm text-yellow-800">
              La tabla de amortización solo se puede ver para préstamos APROBADOS o DESEMBOLSADOS.
              Estado actual: <strong>{prestamo.estado}</strong>
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
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="text-sm text-gray-600 mt-2">Cargando tabla de amortización...</p>
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
            <p className="text-sm text-red-800">Error al cargar la tabla de amortización</p>
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
              <p className="text-sm text-yellow-800 mb-2">
                No hay tabla de amortización generada para este préstamo.
              </p>
              {prestamo.fecha_base_calculo && (
                <Button size="sm" onClick={async () => {
                  try {
                    await prestamoService.generarAmortizacion(prestamo.id)
                    toast.success('Tabla de amortización generada exitosamente')
                    // Refrescar datos
                    window.location.reload()
                  } catch (error: any) {
                    toast.error(error.response?.data?.detail || 'Error al generar amortización')
                  }
                }}>
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
          <Button variant="outline" size="sm" onClick={exportarExcel}>
            <Download className="h-4 w-4 mr-2" />
            Exportar Excel
          </Button>
          <Button variant="outline" size="sm" onClick={exportarPDF}>
            <Download className="h-4 w-4 mr-2" />
            Exportar PDF
          </Button>
          {!showFullTable && cuotas.length > 5 && (
            <Button variant="outline" size="sm" onClick={() => setShowFullTable(true)}>
              Ver Todas ({cuotas.length})
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="rounded-lg border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Cuota</TableHead>
                <TableHead>Fecha Vencimiento</TableHead>
                <TableHead className="text-right">Capital</TableHead>
                <TableHead className="text-right">Interés</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead className="text-right">Saldo Pendiente</TableHead>
                <TableHead>Estado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {cuotasVisibles.map((cuota: Cuota) => {
                // Determinar el estado real basado en los datos
                const estadoReal = determinarEstadoReal(cuota)
                
                // Calcular monto_capital y monto_interes si no existen
                // Capital = diferencia entre saldo inicial y final
                const saldoInicial = typeof cuota.saldo_capital_inicial === 'number' ? cuota.saldo_capital_inicial : 0
                const saldoFinal = typeof cuota.saldo_capital_final === 'number' ? cuota.saldo_capital_final : 0
                const montoCuota = typeof cuota.monto_cuota === 'number' ? cuota.monto_cuota : 0
                
                const montoCapital = typeof cuota.monto_capital === 'number' && !isNaN(cuota.monto_capital)
                  ? cuota.monto_capital
                  : Math.max(0, saldoInicial - saldoFinal)
                
                const montoInteres = typeof cuota.monto_interes === 'number' && !isNaN(cuota.monto_interes)
                  ? cuota.monto_interes
                  : Math.max(0, montoCuota - montoCapital)

                return (
                  <TableRow key={cuota.id}>
                    <TableCell className="font-medium">{cuota.numero_cuota}</TableCell>
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
                    <TableCell>
                      <Badge className={getEstadoBadge(estadoReal)}>
                        {getEstadoLabel(estadoReal)}
                      </Badge>
                      {/* 🔍 DEBUG: Mostrar información de depuración */}
                      {process.env.NODE_ENV === 'development' && (
                        <div className="text-xs text-gray-400 mt-1">
                          <div>Estado BD: {cuota.estado || 'NULL'}</div>
                          <div>Estado Real: {estadoReal}</div>
                          <div>Pagado: ${(typeof cuota.total_pagado === 'number' ? cuota.total_pagado : 0).toFixed(2)} / ${montoCuota.toFixed(2)}</div>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}
              {!showFullTable && cuotas.length > 5 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-4">
                    <Button variant="ghost" onClick={() => setShowFullTable(true)}>
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
          <div className="mt-4 grid grid-cols-4 gap-4">
            <Card className="border-green-200 bg-green-50">
              <CardContent className="pt-4">
                <p className="text-sm text-green-600">Total Capital</p>
                <p className="text-2xl font-bold text-green-700">
                  ${cuotas.reduce((acc, c: Cuota) => {
                    const saldoInicial = typeof c.saldo_capital_inicial === 'number' ? c.saldo_capital_inicial : 0
                    const saldoFinal = typeof c.saldo_capital_final === 'number' ? c.saldo_capital_final : 0
                    const montoCapital = typeof c.monto_capital === 'number' && !isNaN(c.monto_capital)
                      ? c.monto_capital
                      : Math.max(0, saldoInicial - saldoFinal)
                    return acc + montoCapital
                  }, 0).toFixed(2)}
                </p>
              </CardContent>
            </Card>
            <Card className="border-blue-200 bg-blue-50">
              <CardContent className="pt-4">
                <p className="text-sm text-blue-600">Total Intereses</p>
                <p className="text-2xl font-bold text-blue-700">
                  ${cuotas.reduce((acc, c: Cuota) => {
                    const saldoInicial = typeof c.saldo_capital_inicial === 'number' ? c.saldo_capital_inicial : 0
                    const saldoFinal = typeof c.saldo_capital_final === 'number' ? c.saldo_capital_final : 0
                    const montoCuota = typeof c.monto_cuota === 'number' ? c.monto_cuota : 0
                    const montoCapital = typeof c.monto_capital === 'number' && !isNaN(c.monto_capital)
                      ? c.monto_capital
                      : Math.max(0, saldoInicial - saldoFinal)
                    const montoInteres = typeof c.monto_interes === 'number' && !isNaN(c.monto_interes)
                      ? c.monto_interes
                      : Math.max(0, montoCuota - montoCapital)
                    return acc + montoInteres
                  }, 0).toFixed(2)}
                </p>
              </CardContent>
            </Card>
            <Card className="border-purple-200 bg-purple-50">
              <CardContent className="pt-4">
                <p className="text-sm text-purple-600">Monto Total</p>
                <p className="text-2xl font-bold text-purple-700">
                  ${cuotas.reduce((acc, c: Cuota) => {
                    const montoCuota = typeof c.monto_cuota === 'number' ? c.monto_cuota : 0
                    return acc + montoCuota
                  }, 0).toFixed(2)}
                </p>
              </CardContent>
            </Card>
            <Card className="border-gray-200 bg-gray-50">
              <CardContent className="pt-4">
                <p className="text-sm text-gray-600">Pagadas</p>
                <p className="text-2xl font-bold text-gray-700">
                  {cuotas.filter((c: Cuota) => c.estado === 'PAGADO' || c.estado === 'PAGADA').length} / {cuotas.length}
                </p>
              </CardContent>
            </Card>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

