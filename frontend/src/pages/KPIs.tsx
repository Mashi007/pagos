import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Users,
  CreditCard,
  AlertTriangle,
  CheckCircle,
  BarChart3,
  PieChart,
  LineChart,
  Calendar,
  Filter,
  RefreshCw,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { formatCurrency } from '@/utils'

// Mock data para KPIs
const mockKPIs = {
  financieros: {
    carteraTotal: 485750.00,
    carteraAnterior: 462300.00,
    totalCobrado: 125400.00,
    totalCobradoAnterior: 118200.00,
    ingresosCapital: 89500.00,
    ingresosInteres: 28750.00,
    ingresosMora: 7150.00,
    tasaRecuperacion: 85.4,
    tasaRecuperacionAnterior: 82.1,
  },
  cobranza: {
    tasaMorosidad: 12.5,
    tasaMorosidadAnterior: 15.2,
    promedioDiasMora: 8.5,
    promedioDiasMoraAnterior: 12.3,
    porcentajeCumplimiento: 87.6,
    porcentajeCumplimientoAnterior: 84.2,
    clientesMora: 45,
    clientesMoraAnterior: 52,
  },
  asesores: {
    totalAsesores: 8,
    asesoresActivos: 7,
    ventasMejorAsesor: 12,
    montoMejorAsesor: 75000.00,
    promedioVentas: 8.5,
    tasaConversion: 23.4,
    tasaConversionAnterior: 21.8,
  },
  productos: {
    modeloMasVendido: 'Toyota Corolla',
    ventasModeloMasVendido: 25,
    ticketPromedio: 18500.00,
    ticketPromedioAnterior: 17200.00,
    totalModelos: 12,
    modeloMenosVendido: 'Nissan Versa',
  }
}

const mockEvolucionMensual = [
  { mes: 'Ene', cartera: 420000, cobrado: 95000, morosidad: 18.2 },
  { mes: 'Feb', cartera: 435000, cobrado: 102000, morosidad: 16.8 },
  { mes: 'Mar', cartera: 448000, cobrado: 108000, morosidad: 15.5 },
  { mes: 'Abr', cartera: 456000, cobrado: 112000, morosidad: 14.2 },
  { mes: 'May', cartera: 462300, cobrado: 118200, morosidad: 15.2 },
  { mes: 'Jun', cartera: 475000, cobrado: 122000, morosidad: 13.8 },
  { mes: 'Jul', cartera: 485750, cobrado: 125400, morosidad: 12.5 },
]

const mockTopAsesores = [
  { nombre: 'Carlos Mendoza', ventas: 12, monto: 75000, clientes: 15, tasaConversion: 28.5 },
  { nombre: 'María González', ventas: 10, monto: 65000, clientes: 13, tasaConversion: 25.2 },
  { nombre: 'Luis Rodríguez', ventas: 9, monto: 58000, clientes: 11, tasaConversion: 22.8 },
  { nombre: 'Ana Pérez', ventas: 8, monto: 52000, clientes: 10, tasaConversion: 21.5 },
  { nombre: 'José Silva', ventas: 7, monto: 45000, clientes: 9, tasaConversion: 19.8 },
]

export function KPIs() {
  const [periodo, setPeriodo] = useState('mes')
  const [categoria, setCategoria] = useState('todos')

  const calcularVariacion = (actual: number, anterior: number) => {
    const variacion = ((actual - anterior) / anterior) * 100
    return {
      valor: variacion,
      esPositivo: variacion > 0,
      icono: variacion > 0 ? TrendingUp : TrendingDown,
      color: variacion > 0 ? 'text-green-600' : 'text-red-600'
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard de KPIs</h1>
          <p className="text-gray-600">Indicadores clave de rendimiento del sistema.</p>
        </div>
        <div className="flex space-x-2">
          <Select value={periodo} onValueChange={setPeriodo}>
            <SelectTrigger className="w-[140px]">
              <Calendar className="mr-2 h-4 w-4" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="dia">Hoy</SelectItem>
              <SelectItem value="semana">Esta semana</SelectItem>
              <SelectItem value="mes">Este mes</SelectItem>
              <SelectItem value="año">Este año</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm">
            <RefreshCw className="mr-2 h-4 w-4" /> Actualizar
          </Button>
        </div>
      </div>

      {/* KPIs Financieros */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cartera Total</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(mockKPIs.financieros.carteraTotal)}</div>
            <div className="flex items-center text-xs">
              {(() => {
                const variacion = calcularVariacion(
                  mockKPIs.financieros.carteraTotal,
                  mockKPIs.financieros.carteraAnterior
                )
                const IconComponent = variacion.icono
                return (
                  <>
                    <IconComponent className={`h-3 w-3 mr-1 ${variacion.color}`} />
                    <span className={variacion.color}>
                      {Math.abs(variacion.valor).toFixed(1)}% vs mes anterior
                    </span>
                  </>
                )
              })()}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Cobrado</CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(mockKPIs.financieros.totalCobrado)}</div>
            <div className="flex items-center text-xs">
              {(() => {
                const variacion = calcularVariacion(
                  mockKPIs.financieros.totalCobrado,
                  mockKPIs.financieros.totalCobradoAnterior
                )
                const IconComponent = variacion.icono
                return (
                  <>
                    <IconComponent className={`h-3 w-3 mr-1 ${variacion.color}`} />
                    <span className={variacion.color}>
                      {Math.abs(variacion.valor).toFixed(1)}% vs mes anterior
                    </span>
                  </>
                )
              })()}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tasa de Recuperación</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockKPIs.financieros.tasaRecuperacion}%</div>
            <div className="flex items-center text-xs">
              {(() => {
                const variacion = calcularVariacion(
                  mockKPIs.financieros.tasaRecuperacion,
                  mockKPIs.financieros.tasaRecuperacionAnterior
                )
                const IconComponent = variacion.icono
                return (
                  <>
                    <IconComponent className={`h-3 w-3 mr-1 ${variacion.color}`} />
                    <span className={variacion.color}>
                      {Math.abs(variacion.valor).toFixed(1)}% vs mes anterior
                    </span>
                  </>
                )
              })()}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tasa de Morosidad</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{mockKPIs.cobranza.tasaMorosidad}%</div>
            <div className="flex items-center text-xs">
              {(() => {
                const variacion = calcularVariacion(
                  mockKPIs.cobranza.tasaMorosidad,
                  mockKPIs.cobranza.tasaMorosidadAnterior
                )
                const IconComponent = variacion.icono
                return (
                  <>
                    <IconComponent className={`h-3 w-3 mr-1 ${variacion.color}`} />
                    <span className={variacion.color}>
                      {Math.abs(variacion.valor).toFixed(1)}% vs mes anterior
                    </span>
                  </>
                )
              })()}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Gráficos y Métricas Detalladas */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Evolución Mensual */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <LineChart className="mr-2 h-5 w-5" /> Evolución Mensual
            </CardTitle>
            <CardDescription>Comparativo de cartera, cobrado y morosidad por mes.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {mockEvolucionMensual.map((mes, index) => (
                <div key={mes.mes} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="font-medium">{mes.mes}</div>
                  <div className="flex space-x-4 text-sm">
                    <div>
                      <span className="text-gray-500">Cartera:</span>
                      <span className="font-semibold ml-1">{formatCurrency(mes.cartera)}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Cobrado:</span>
                      <span className="font-semibold ml-1 text-green-600">{formatCurrency(mes.cobrado)}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Mora:</span>
                      <span className="font-semibold ml-1 text-red-600">{mes.morosidad}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Top Asesores */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Users className="mr-2 h-5 w-5" /> Top Asesores
            </CardTitle>
            <CardDescription>Ranking de asesores por ventas y rendimiento.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {mockTopAsesores.map((asesor, index) => (
                <div key={asesor.nombre} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                      index === 0 ? 'bg-yellow-500 text-white' : 
                      index === 1 ? 'bg-gray-400 text-white' : 
                      index === 2 ? 'bg-orange-500 text-white' : 'bg-gray-200 text-gray-600'
                    }`}>
                      {index + 1}
                    </div>
                    <div>
                      <div className="font-semibold">{asesor.nombre}</div>
                      <div className="text-sm text-gray-500">{asesor.clientes} clientes</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold">{formatCurrency(asesor.monto)}</div>
                    <div className="text-sm text-gray-500">{asesor.ventas} ventas</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Métricas Detalladas */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Ingresos por Tipo */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <PieChart className="mr-2 h-5 w-5" /> Ingresos por Tipo
            </CardTitle>
            <CardDescription>Desglose de ingresos por categoría.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span>Capital</span>
                <Badge variant="outline">{formatCurrency(mockKPIs.financieros.ingresosCapital)}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span>Intereses</span>
                <Badge variant="outline">{formatCurrency(mockKPIs.financieros.ingresosInteres)}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span>Mora</span>
                <Badge variant="outline">{formatCurrency(mockKPIs.financieros.ingresosMora)}</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Métricas de Cobranza */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <BarChart3 className="mr-2 h-5 w-5" /> Métricas de Cobranza
            </CardTitle>
            <CardDescription>Indicadores de eficiencia en cobranza.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span>Promedio días mora</span>
                <Badge variant="outline">{mockKPIs.cobranza.promedioDiasMora} días</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span>% Cumplimiento</span>
                <Badge variant="success">{mockKPIs.cobranza.porcentajeCumplimiento}%</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span>Clientes en mora</span>
                <Badge variant="destructive">{mockKPIs.cobranza.clientesMora}</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Métricas de Productos */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <TrendingUp className="mr-2 h-5 w-5" /> Métricas de Productos
            </CardTitle>
            <CardDescription>Análisis de productos y modelos.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span>Modelo más vendido</span>
                <Badge variant="outline">{mockKPIs.productos.modeloMasVendido}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span>Ventas del modelo</span>
                <Badge variant="outline">{mockKPIs.productos.ventasModeloMasVendido}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span>Ticket promedio</span>
                <Badge variant="outline">{formatCurrency(mockKPIs.productos.ticketPromedio)}</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </motion.div>
  )
}
