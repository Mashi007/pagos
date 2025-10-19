import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  CreditCard,
  DollarSign,
  CheckCircle,
  Clock,
  TrendingUp,
  Users,
  FileText,
  Download,
  Upload,
  Plus,
  Search,
  Filter,
  RefreshCw,
  AlertCircle,
  Eye,
  Edit,
  Trash2,
  Calendar,
  Building2,
  BarChart3,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { AlertWithIcon } from '@/components/ui/alert'
import { pagoService, type Pago, type KPIsPagos, type PagoListResponse } from '@/services/pagoService'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'

export function Pagos() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [filtros, setFiltros] = useState({
    cedula: '',
    conciliado: undefined as boolean | undefined,
    pagina: 1,
    por_pagina: 20
  })

  // ============================================
  // QUERIES
  // ============================================

  const { data: kpis, isLoading: kpisLoading, error: kpisError } = useQuery({
    queryKey: ['pagos-kpis'],
    queryFn: () => pagoService.obtenerKPIs(),
    refetchInterval: 30000, // Refrescar cada 30 segundos
  })

  const { data: pagosData, isLoading: pagosLoading, error: pagosError } = useQuery({
    queryKey: ['pagos-list', filtros],
    queryFn: () => pagoService.listarPagos(filtros),
    refetchInterval: 30000,
  })

  // ============================================
  // HANDLERS
  // ============================================

  const handleNuevoPago = () => {
    navigate('/pagos/nuevo')
  }

  const handleConciliacion = () => {
    navigate('/pagos/conciliacion')
  }

  const handleDescargarTemplate = async () => {
    try {
      await pagoService.descargarTemplateConciliacion()
      toast.success('✅ Template descargado exitosamente')
    } catch (error) {
      toast.error('❌ Error al descargar el template')
    }
  }

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['pagos-kpis'] })
    queryClient.invalidateQueries({ queryKey: ['pagos-list'] })
    toast.success('🔄 Datos actualizados')
  }

  const handleFiltroChange = (key: string, value: any) => {
    setFiltros(prev => ({
      ...prev,
      [key]: value,
      pagina: 1 // Reset página al cambiar filtros
    }))
  }

  const handleVerPago = (pago: Pago) => {
    navigate(`/pagos/${pago.id}`)
  }

  const handleEditarPago = (pago: Pago) => {
    navigate(`/pagos/${pago.id}/editar`)
  }

  // ============================================
  // RENDER
  // ============================================

  if (kpisError || pagosError) {
    return (
      <div className="p-6">
        <AlertWithIcon
          variant="destructive"
          title="Error cargando datos"
          description="No se pudieron cargar los datos de pagos. Intenta nuevamente."
        />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <CreditCard className="h-8 w-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Módulo de Pagos</h1>
            <p className="text-gray-600">Gestión de pagos y conciliación bancaria</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            onClick={handleRefresh}
            variant="outline"
            size="sm"
            disabled={kpisLoading || pagosLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${(kpisLoading || pagosLoading) ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
          <Button
            onClick={handleDescargarTemplate}
            variant="outline"
            size="sm"
          >
            <Download className="h-4 w-4 mr-2" />
            Template
          </Button>
          <Button
            onClick={handleConciliacion}
            variant="outline"
            size="sm"
          >
            <Building2 className="h-4 w-4 mr-2" />
            Conciliación
          </Button>
          <Button
            onClick={handleNuevoPago}
            size="sm"
          >
            <Plus className="h-4 w-4 mr-2" />
            Nuevo Pago
          </Button>
        </div>
      </div>

      {/* KPIs Dashboard */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Pagos</CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {kpisLoading ? '...' : kpis?.total_pagos || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Registros totales
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Dólares</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${kpisLoading ? '...' : (kpis?.total_dolares || 0).toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">
              Monto total
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Conciliados</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {kpisLoading ? '...' : kpis?.cantidad_conciliada || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Pagos conciliados
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pendientes</CardTitle>
            <Clock className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {kpisLoading ? '...' : kpis?.cantidad_no_conciliada || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Por conciliar
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">% Conciliación</CardTitle>
            <TrendingUp className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              {kpisLoading ? '...' : 
                kpis?.total_pagos ? 
                  Math.round((kpis.cantidad_conciliada / kpis.total_pagos) * 100) : 0
              }%
            </div>
            <p className="text-xs text-muted-foreground">
              Eficiencia
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filtros */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Filter className="h-5 w-5" />
            <span>Filtros</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700">Cédula</label>
              <Input
                placeholder="Buscar por cédula..."
                value={filtros.cedula}
                onChange={(e) => handleFiltroChange('cedula', e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Estado Conciliación</label>
              <select
                className="w-full p-2 border border-gray-300 rounded-md"
                value={filtros.conciliado === undefined ? '' : filtros.conciliado.toString()}
                onChange={(e) => handleFiltroChange('conciliado', 
                  e.target.value === '' ? undefined : e.target.value === 'true'
                )}
              >
                <option value="">Todos</option>
                <option value="true">Conciliados</option>
                <option value="false">Pendientes</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Por página</label>
              <select
                className="w-full p-2 border border-gray-300 rounded-md"
                value={filtros.por_pagina}
                onChange={(e) => handleFiltroChange('por_pagina', parseInt(e.target.value))}
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Lista de Pagos */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <FileText className="h-5 w-5" />
              <span>Lista de Pagos</span>
            </div>
            <Badge variant="outline">
              {pagosData?.total || 0} registros
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {pagosLoading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="h-6 w-6 animate-spin mr-2" />
              <span>Cargando pagos...</span>
            </div>
          ) : pagosData?.pagos.length === 0 ? (
            <div className="text-center py-8">
              <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No hay pagos</h3>
              <p className="text-gray-600 mb-4">No se encontraron pagos con los filtros aplicados.</p>
              <Button onClick={handleNuevoPago}>
                <Plus className="h-4 w-4 mr-2" />
                Crear Primer Pago
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {pagosData?.pagos.map((pago) => (
                <motion.div
                  key={pago.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="border rounded-lg p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="flex-shrink-0">
                        <div className={`w-3 h-3 rounded-full ${
                          pago.conciliado ? 'bg-green-500' : 'bg-orange-500'
                        }`} />
                      </div>
                      <div>
                        <h3 className="font-medium text-gray-900">
                          Cédula: {pago.cedula_cliente}
                        </h3>
                        <p className="text-sm text-gray-600">
                          Documento: {pago.numero_documento}
                        </p>
                        <p className="text-sm text-gray-500">
                          {new Date(pago.fecha_pago).toLocaleDateString()} - 
                          ${pago.monto_pagado.toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant={pago.conciliado ? "success" : "warning"}>
                        {pago.conciliado ? 'Conciliado' : 'Pendiente'}
                      </Badge>
                      <div className="flex space-x-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleVerPago(pago)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEditarPago(pago)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}

          {/* Paginación */}
          {pagosData && pagosData.total_paginas > 1 && (
            <div className="flex items-center justify-between mt-6">
              <div className="text-sm text-gray-700">
                Mostrando {((filtros.pagina - 1) * filtros.por_pagina) + 1} a{' '}
                {Math.min(filtros.pagina * filtros.por_pagina, pagosData.total)} de{' '}
                {pagosData.total} registros
              </div>
              <div className="flex space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleFiltroChange('pagina', filtros.pagina - 1)}
                  disabled={filtros.pagina === 1}
                >
                  Anterior
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleFiltroChange('pagina', filtros.pagina + 1)}
                  disabled={filtros.pagina === pagosData.total_paginas}
                >
                  Siguiente
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}