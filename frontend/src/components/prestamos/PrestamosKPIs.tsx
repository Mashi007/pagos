import { useState, useMemo } from 'react'
import { DollarSign, TrendingUp, Users, CreditCard, Calendar } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { usePrestamosKPIs } from '../../hooks/usePrestamos'

const MESES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]

interface PrestamosKPIsProps {
  analista?: string
  concesionario?: string
  modelo?: string
  fecha_inicio?: string
  fecha_fin?: string
}

export function PrestamosKPIs({
  analista,
  concesionario,
  modelo,
  fecha_inicio,
  fecha_fin,
}: PrestamosKPIsProps) {
  const now = new Date()
  const [mesSel, setMesSel] = useState<number>(now.getMonth() + 1)
  const [anioSel, setAnioSel] = useState<number>(now.getFullYear())

  const aniosDisponibles = useMemo(() => {
    const y = new Date().getFullYear()
    return Array.from({ length: 10 }, (_, i) => y - 5 + i)
  }, [])

  const { data: kpiData, isLoading, error } = usePrestamosKPIs({
    analista,
    concesionario,
    modelo,
    fecha_inicio,
    fecha_fin,
    mes: mesSel,
    anio: anioSel,
  })

  const kpiDataFinal = kpiData || {
    totalFinanciamiento: 0,
    totalPrestamos: 0,
    promedioMonto: 0,
    totalCarteraVigente: 0,
    mes: mesSel,
    anio: anioSel,
  }
  const nombreMes = MESES[(kpiDataFinal.mes ?? mesSel) - 1]
  const añoLabel = kpiDataFinal.anio ?? anioSel

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-gray-900">KPIs de Préstamos</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  <div className="h-4 w-24 bg-gray-200 rounded animate-pulse" />
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-8 w-32 bg-gray-200 rounded animate-pulse mb-2" />
                <div className="h-3 w-20 bg-gray-200 rounded animate-pulse" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-gray-900">KPIs de Préstamos</h2>
        </div>
        <Card>
          <CardContent className="pt-6">
            <p className="text-red-600 text-center">
              Error al cargar los KPIs. Por favor, intenta nuevamente.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Encabezado con selector de mes/año */}
      <div className="flex flex-wrap justify-between items-center gap-4">
        <h2 className="text-2xl font-bold text-gray-900">KPIs de Préstamos (mensuales)</h2>
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-gray-500" />
          <Select value={String(mesSel)} onValueChange={(v) => setMesSel(Number(v))}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Mes" />
            </SelectTrigger>
            <SelectContent>
              {MESES.map((nombre, i) => (
                <SelectItem key={i} value={String(i + 1)}>{nombre}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={String(anioSel)} onValueChange={(v) => setAnioSel(Number(v))}>
            <SelectTrigger className="w-[100px]">
              <SelectValue placeholder="Año" />
            </SelectTrigger>
            <SelectContent>
              {aniosDisponibles.map((y) => (
                <SelectItem key={y} value={String(y)}>{y}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <span className="text-sm text-gray-500 tabular-nums">{nombreMes} {añoLabel}</span>
        </div>
      </div>

      {/* Vista General con KPIs principales */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Financiamiento (mensual)</CardTitle>
            <DollarSign className="h-5 w-5 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              ${kpiDataFinal.totalFinanciamiento.toLocaleString('es-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </div>
            <p className="text-xs text-gray-600 mt-1">
              Total aprobado en {nombreMes}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Préstamos (mensual)</CardTitle>
            <CreditCard className="h-5 w-5 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{kpiDataFinal.totalPrestamos}</div>
            <p className="text-xs text-gray-600 mt-1">Aprobados en {nombreMes}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Promedio (mensual)</CardTitle>
            <TrendingUp className="h-5 w-5 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600">
              ${kpiDataFinal.promedioMonto.toLocaleString('es-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </div>
            <p className="text-xs text-gray-600 mt-1">Monto promedio del mes</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Por cobrar (mensual)</CardTitle>
            <Users className="h-5 w-5 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              ${kpiDataFinal.totalCarteraVigente.toLocaleString('es-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </div>
            <p className="text-xs text-gray-600 mt-1">Cuotas con vencimiento en {nombreMes} no cobradas</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
