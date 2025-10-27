import { useState } from 'react'
import { DollarSign, TrendingUp, Users, Building, Calendar, CreditCard } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Prestamo } from '@/types'

interface KPIData {
  totalFinanciamiento: number
  totalPrestamos: number
  promedioMonto: number
  totalCuotas: number
  totalCarteraVigente: number
}

interface PrestamosKPIsProps {
  prestamos: Prestamo[]
}

export function PrestamosKPIs({ prestamos }: PrestamosKPIsProps) {
  const [filtroTipo, setFiltroTipo] = useState<string>('general')

  // Calcular métricas generales
  const kpiData: KPIData = prestamos.reduce(
    (acc, prestamo) => {
      acc.totalFinanciamiento += prestamo.total_financiamiento
      acc.totalPrestamos += 1
      acc.totalCuotas += prestamo.numero_cuotas
      if (prestamo.estado === 'APROBADO') {
        acc.totalCarteraVigente += prestamo.total_financiamiento
      }
      return acc
    },
    {
      totalFinanciamiento: 0,
      totalPrestamos: 0,
      promedioMonto: 0,
      totalCuotas: 0,
      totalCarteraVigente: 0,
    }
  )

  kpiData.promedioMonto = kpiData.totalFinanciamiento / (kpiData.totalPrestamos || 1)

  // Agrupar por concesionario
  const porConcesionario = prestamos.reduce((acc: any, prestamo: any) => {
    // Nota: necesitaríamos agregar campo concesionario al modelo Prestamo
    const concesionario = prestamo.concesionario || 'Sin asignar'
    if (!acc[concesionario]) {
      acc[concesionario] = { total: 0, cantidad: 0 }
    }
    acc[concesionario].total += prestamo.total_financiamiento
    acc[concesionario].cantidad += 1
    return acc
  }, {})

  // Agrupar por analista
  const porAnalista = prestamos.reduce((acc: any, prestamo) => {
    const analista = prestamo.producto_financiero || 'Sin asignar'
    if (!acc[analista]) {
      acc[analista] = { total: 0, cantidad: 0 }
    }
    acc[analista].total += prestamo.total_financiamiento
    acc[analista].cantidad += 1
    return acc
  }, {})

  // Agrupar por modelo de vehículo
  const porModelo = prestamos.reduce((acc: any, prestamo) => {
    const modelo = prestamo.producto || 'Sin asignar'
    if (!acc[modelo]) {
      acc[modelo] = { total: 0, cantidad: 0 }
    }
    acc[modelo].total += prestamo.total_financiamiento
    acc[modelo].cantidad += 1
    return acc
  }, {})

  // Agrupar por mes de aprobación
  const porMes = prestamos
    .filter((p) => p.estado === 'APROBADO' && p.fecha_aprobacion)
    .reduce((acc: any, prestamo) => {
      const fecha = new Date(prestamo.fecha_aprobacion!)
      const mes = `${fecha.getFullYear()}-${String(fecha.getMonth() + 1).padStart(2, '0')}`
      if (!acc[mes]) {
        acc[mes] = { total: 0, cantidad: 0, fecha }
      }
      acc[mes].total += prestamo.total_financiamiento
      acc[mes].cantidad += 1
      return acc
    }, {})

  const sortedPorMes = Object.entries(porMes).sort(
    ([a]: any, [b]: any) => new Date(b.fecha).getTime() - new Date(a.fecha).getTime()
  )

  return (
    <div className="space-y-6">
      {/* Filtro */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">KPIs de Préstamos</h2>
        <Select value={filtroTipo} onValueChange={setFiltroTipo}>
          <SelectTrigger className="w-[200px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="general">Vista General</SelectItem>
            <SelectItem value="concesionario">Por Concesionario</SelectItem>
            <SelectItem value="analista">Por Analista</SelectItem>
            <SelectItem value="modelo">Por Modelo</SelectItem>
            <SelectItem value="mes">Por Mes</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Vista General */}
      {filtroTipo === 'general' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Financiamiento</CardTitle>
              <DollarSign className="h-5 w-5 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                ${kpiData.totalFinanciamiento.toLocaleString('es-US', {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>
              <p className="text-xs text-gray-600 mt-1">
                Cartera total aprobada
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Préstamos</CardTitle>
              <CreditCard className="h-5 w-5 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{kpiData.totalPrestamos}</div>
              <p className="text-xs text-gray-600 mt-1">Préstamos gestionados</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Promedio Monto</CardTitle>
              <TrendingUp className="h-5 w-5 text-purple-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-purple-600">
                ${kpiData.promedioMonto.toLocaleString('es-US', {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>
              <p className="text-xs text-gray-600 mt-1">Monto promedio</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Cartera Vigente</CardTitle>
              <Users className="h-5 w-5 text-orange-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-600">
                ${kpiData.totalCarteraVigente.toLocaleString('es-US', {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>
              <p className="text-xs text-gray-600 mt-1">Préstamos aprobados</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Vista Por Concesionario */}
      {filtroTipo === 'concesionario' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(porConcesionario).map(([concesionario, data]: [string, any]) => (
            <Card key={concesionario}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Building className="h-5 w-5 text-blue-600" />
                    {concesionario}
                  </CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-blue-600">
                  ${data.total.toLocaleString('es-US', { minimumFractionDigits: 2 })}
                </div>
                <p className="text-sm text-gray-600 mt-1">{data.cantidad} préstamos</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Vista Por Analista */}
      {filtroTipo === 'analista' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(porAnalista).map(([analista, data]: [string, any]) => (
            <Card key={analista}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Users className="h-5 w-5 text-green-600" />
                    {analista}
                  </CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">
                  ${data.total.toLocaleString('es-US', { minimumFractionDigits: 2 })}
                </div>
                <p className="text-sm text-gray-600 mt-1">{data.cantidad} préstamos</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Vista Por Modelo */}
      {filtroTipo === 'modelo' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(porModelo).map(([modelo, data]: [string, any]) => (
            <Card key={modelo}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <CreditCard className="h-5 w-5 text-purple-600" />
                    {modelo}
                  </CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-purple-600">
                  ${data.total.toLocaleString('es-US', { minimumFractionDigits: 2 })}
                </div>
                <p className="text-sm text-gray-600 mt-1">{data.cantidad} préstamos</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Vista Por Mes (Flujo de Cartera) */}
      {filtroTipo === 'mes' && (
        <div className="space-y-4">
          {sortedPorMes.map(([mes, data]: [string, any]) => (
            <Card key={mes}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Calendar className="h-5 w-5 text-orange-600" />
                    {mes}
                  </CardTitle>
                  <span className="text-sm text-gray-600">{data.cantidad} préstamos</span>
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-orange-600">
                  ${data.total.toLocaleString('es-US', { minimumFractionDigits: 2 })}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
