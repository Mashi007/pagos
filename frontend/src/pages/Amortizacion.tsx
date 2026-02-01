import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Calculator,
  Search,
  Filter,
  Download,
  Calendar,
  DollarSign,
  FileText,
  User,
  Car
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'

// Constantes de configuraciÃ³n
const DEFAULT_CUOTA_MENSUAL = 416.67
const DEFAULT_CUOTA_MENSUAL_ALT = 428.57
const DEFAULT_MONTO_FINANCIADO_1 = 20000.00
const DEFAULT_MONTO_FINANCIADO_2 = 15000.00
const DEFAULT_MONTO_FINANCIADO_3 = 18000.00
const DEFAULT_CUOTAS_TOTALES_1 = 48
const DEFAULT_CUOTAS_TOTALES_2 = 36
const DEFAULT_CUOTAS_TOTALES_3 = 42
const DEFAULT_CUOTAS_PAGADAS_1 = 12
const DEFAULT_CUOTAS_PAGADAS_2 = 8
const DEFAULT_CUOTAS_PAGADAS_3 = 15
const DEFAULT_SALDO_1 = 15000.00
const DEFAULT_SALDO_2 = 11666.67
const DEFAULT_SALDO_3 = 11571.43
const DEFAULT_PROXIMA_CUOTA = '2024-02-15'
const DEFAULT_PROXIMA_CUOTA_ALT = '2024-01-15'
const DEFAULT_PERCENTAGE_MULTIPLIER = 100

// Mock data para amortizaciÃ³n
const mockAmortizaciones = [
  {
    id: 1,
    cliente: 'Juan Carlos PÃ©rez GonzÃ¡lez',
    cedula: '12345678',
    vehiculo: 'Toyota Corolla 2022',
    monto_financiado: DEFAULT_MONTO_FINANCIADO_1,
    cuota_mensual: DEFAULT_CUOTA_MENSUAL,
    cuotas_pagadas: DEFAULT_CUOTAS_PAGADAS_1,
    cuotas_totales: DEFAULT_CUOTAS_TOTALES_1,
    saldo_pendiente: DEFAULT_SALDO_1,
    proxima_cuota: DEFAULT_PROXIMA_CUOTA,
    estado: 'al_dia'
  },
  {
    id: 2,
    cliente: 'MarÃ­a Elena RodrÃ­guez LÃ³pez',
    cedula: '87654321',
    vehiculo: 'Hyundai Accent 2023',
    monto_financiado: DEFAULT_MONTO_FINANCIADO_2,
    cuota_mensual: DEFAULT_CUOTA_MENSUAL,
    cuotas_pagadas: DEFAULT_CUOTAS_PAGADAS_2,
    cuotas_totales: DEFAULT_CUOTAS_TOTALES_2,
    saldo_pendiente: DEFAULT_SALDO_2,
    proxima_cuota: DEFAULT_PROXIMA_CUOTA,
    estado: 'al_dia'
  },
  {
    id: 3,
    cliente: 'Carlos Alberto MartÃ­nez Silva',
    cedula: '11223344',
    vehiculo: 'Nissan Versa 2021',
    monto_financiado: DEFAULT_MONTO_FINANCIADO_3,
    cuota_mensual: DEFAULT_CUOTA_MENSUAL_ALT,
    cuotas_pagadas: DEFAULT_CUOTAS_PAGADAS_3,
    cuotas_totales: DEFAULT_CUOTAS_TOTALES_3,
    saldo_pendiente: DEFAULT_SALDO_3,
    proxima_cuota: DEFAULT_PROXIMA_CUOTA_ALT,
    estado: 'en_mora'
  }
]

export function Amortizacion() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterEstado, setFilterEstado] = useState('')

  const getEstadoBadge = (estado: string) => {
    switch (estado) {
      case 'al_dia':
        return <Badge className="bg-green-100 text-green-800">Al DÃ­a</Badge>
      case 'en_mora':
        return <Badge className="bg-red-100 text-red-800">En Mora</Badge>
      case 'vencido':
        return <Badge className="bg-orange-100 text-orange-800">Vencido</Badge>
      default:
        return <Badge variant="secondary">{estado}</Badge>
    }
  }

  const filteredAmortizaciones = mockAmortizaciones.filter(amortizacion => {
    const matchesSearch = amortizacion.cliente.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         amortizacion.cedula.includes(searchTerm) ||
                         amortizacion.vehiculo.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesEstado = !filterEstado || amortizacion.estado === filterEstado
    return matchesSearch && matchesEstado
  })

  const totalFinanciado = mockAmortizaciones.reduce((sum, a) => sum + a.monto_financiado, 0)
  const totalSaldoPendiente = mockAmortizaciones.reduce((sum, a) => sum + a.saldo_pendiente, 0)
  const clientesEnMora = mockAmortizaciones.filter(a => a.estado === 'en_mora').length

  const calcularProgreso = (pagadas: number, totales: number) => {
    return (pagadas / totales) * DEFAULT_PERCENTAGE_MULTIPLIER
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Tablas de AmortizaciÃ³n</h1>
            <p className="text-gray-600 mt-1">Monitorea el progreso de los prÃ©stamos y su estado de pago</p>
          </div>
          <Button className="bg-blue-600 hover:bg-blue-700">
            <Calculator className="w-4 h-4 mr-2" />
            Generar Tabla
          </Button>
        </div>
      </motion.div>

      {/* Stats Cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.5 }}
        className="grid grid-cols-1 md:grid-cols-4 gap-6"
      >
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Financiado</CardTitle>
            <DollarSign className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              ${totalFinanciado.toLocaleString('es-ES', { minimumFractionDigits: 2 })}
            </div>
            <p className="text-xs text-gray-600">Monto total prestado</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Saldo Pendiente</CardTitle>
            <FileText className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              ${totalSaldoPendiente.toLocaleString('es-ES', { minimumFractionDigits: 2 })}
            </div>
            <p className="text-xs text-gray-600">Por cobrar</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Clientes en Mora</CardTitle>
            <User className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {clientesEnMora}
            </div>
            <p className="text-xs text-gray-600">Requieren seguimiento</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total PrÃ©stamos</CardTitle>
            <Car className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {mockAmortizaciones.length}
            </div>
            <p className="text-xs text-gray-600">Activos en el sistema</p>
          </CardContent>
        </Card>
      </motion.div>

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.5 }}
      >
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Filter className="w-5 h-5 mr-2" />
              Filtros y BÃºsqueda
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Buscar por cliente, cÃ©dula o vehÃ­culo..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
              <select
                value={filterEstado}
                onChange={(e) => setFilterEstado(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todos los estados</option>
                <option value="al_dia">Al DÃ­a</option>
                <option value="en_mora">En Mora</option>
                <option value="vencido">Vencido</option>
              </select>
              <Button variant="outline" className="flex items-center">
                <Download className="w-4 h-4 mr-2" />
                Exportar
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Amortizaciones List */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.5 }}
      >
        <Card>
          <CardHeader>
            <CardTitle>Estado de Amortizaciones</CardTitle>
            <CardDescription>
              Progreso de pago de todos los prÃ©stamos activos
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {filteredAmortizaciones.map((amortizacion) => {
                const progreso = calcularProgreso(amortizacion.cuotas_pagadas, amortizacion.cuotas_totales)

                return (
                  <div key={amortizacion.id} className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <Calculator className="w-5 h-5 text-blue-600" />
                          <div>
                            <h3 className="font-semibold text-gray-900">{amortizacion.cliente}</h3>
                            <p className="text-sm text-gray-600">CÃ©dula: {amortizacion.cedula}</p>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          <div>
                            <span className="text-gray-500">VehÃ­culo:</span>
                            <p className="font-medium">{amortizacion.vehiculo}</p>
                          </div>
                          <div>
                            <span className="text-gray-500">Cuota Mensual:</span>
                            <p className="font-medium">${amortizacion.cuota_mensual.toLocaleString('es-ES', { minimumFractionDigits: 2 })}</p>
                          </div>
                          <div>
                            <span className="text-gray-500">PrÃ³xima Cuota:</span>
                            <p className="font-medium">{new Date(amortizacion.proxima_cuota).toLocaleDateString('es-ES')}</p>
                          </div>
                          <div>
                            <span className="text-gray-500">Saldo Pendiente:</span>
                            <p className="font-medium">${amortizacion.saldo_pendiente.toLocaleString('es-ES', { minimumFractionDigits: 2 })}</p>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-3">
                        {getEstadoBadge(amortizacion.estado)}
                        <Button variant="outline" size="sm">
                          Ver Tabla
                        </Button>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="mt-4">
                      <div className="flex justify-between text-sm text-gray-600 mb-2">
                        <span>Progreso del prÃ©stamo</span>
                        <span>{amortizacion.cuotas_pagadas}/{amortizacion.cuotas_totales} cuotas ({progreso.toFixed(1)}%)</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${progreso}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                )
              })}

              {filteredAmortizaciones.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <Calculator className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                  <p>No se encontraron amortizaciones con los filtros aplicados</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}
