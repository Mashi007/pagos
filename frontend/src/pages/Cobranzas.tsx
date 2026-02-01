import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Input } from '../components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import {
  AlertTriangle,
  TrendingDown,
  DollarSign,
  Users,
  Download,
  BarChart3,
  Bell,
  Loader2,
  Eye,
  Search,
  ChevronDown,
  ChevronUp,
  Save,
  X,
  Edit
} from 'lucide-react'
import { cobranzasService } from '../services/cobranzasService'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { ClienteAtrasado, CobranzasPorAnalista } from '../services/cobranzasService'
import { InformesCobranzas } from '../components/cobranzas/InformesCobranzas'
import { toast } from 'sonner'
import { userService } from '../services/userService'

export function Cobranzas() {
  const [tabActiva, setTabActiva] = useState('cuotas')
  const [filtroDiasRetraso, setFiltroDiasRetraso] = useState<number | undefined>(undefined)
  const [rangoDiasMin, setRangoDiasMin] = useState<number | undefined>(undefined)
  const [rangoDiasMax, setRangoDiasMax] = useState<number | undefined>(undefined)
  const [errorRangoDias, setErrorRangoDias] = useState<string | null>(null)
  
  // ✅ Función de validación de rango de días
  const validarRangoDias = (min: number | undefined, max: number | undefined): boolean => {
    if (min !== undefined && max !== undefined && min > max) {
      setErrorRangoDias('Los días mínimos no pueden ser mayores que los días máximos')
      return false
    }
    if (min !== undefined && min < 0) {
      setErrorRangoDias('Los días mínimos deben ser un número positivo')
      return false
    }
    if (max !== undefined && max < 0) {
      setErrorRangoDias('Los días máximos deben ser un número positivo')
      return false
    }
    setErrorRangoDias(null)
    return true
  }
  const [filtroCuotasMinimas, setFiltroCuotasMinimas] = useState<number | undefined>(undefined)
  const [soloCuotasImpagas, setSoloCuotasImpagas] = useState(true)
  const [procesandoNotificaciones, setProcesandoNotificaciones] = useState(false)
  const [mostrandoDiagnostico, setMostrandoDiagnostico] = useState(false)
  const [diagnosticoData, setDiagnosticoData] = useState<any>(null)
  const [busquedaResumen, setBusquedaResumen] = useState<string>('')
  const [analistasExpandidos, setAnalistasExpandidos] = useState<Set<string>>(new Set())
  const [clientesPorAnalista, setClientesPorAnalista] = useState<Record<string, ClienteAtrasado[]>>({})
  const [cargandoClientesAnalista, setCargandoClientesAnalista] = useState<Record<string, boolean>>({})
  const [busquedaPorAnalista, setBusquedaPorAnalista] = useState<Record<string, string>>({})
  const [editandoAnalista, setEditandoAnalista] = useState<number | null>(null)
  const [analistaTemporal, setAnalistaTemporal] = useState<string>('')
  const [guardandoAnalista, setGuardandoAnalista] = useState<number | null>(null)
  const [editandoMLImpago, setEditandoMLImpago] = useState<number | null>(null)
  const [mlImpagoTemporal, setMLImpagoTemporal] = useState<{ nivelRiesgo: string; probabilidad: number } | null>(null)
  const [guardandoMLImpago, setGuardandoMLImpago] = useState<number | null>(null)
  
  // ✅ QueryClient para invalidación inteligente de caché
  const queryClient = useQueryClient()

  // Query para resumen
  const {
    data: resumen,
    isLoading: cargandoResumen,
    isError: errorResumen,
    error: errorResumenDetalle,
    refetch: refetchResumen
  } = useQuery({
    queryKey: ['cobranzas-resumen'],
    queryFn: () => cobranzasService.getResumen(),
    retry: 2,
    retryDelay: 1000,
  })

  // Query para clientes atrasados
  // ✅ OPTIMIZACIÓN: Desactivar ML por defecto para carga inicial más rápida
  // El ML se puede cargar después si es necesario (lazy loading)
  const {
    data: clientesAtrasados,
    isLoading: cargandoClientes,
    isError: errorClientes,
    error: errorClientesDetalle,
    refetch: refetchClientes
  } = useQuery({
    queryKey: ['cobranzas-clientes', filtroDiasRetraso, rangoDiasMin, rangoDiasMax],
    queryFn: () => cobranzasService.getClientesAtrasados(
      filtroDiasRetraso,
      rangoDiasMin,
      rangoDiasMax,
      false, // incluirAdmin
      false  // ✅ incluirML: false por defecto para carga rápida (2868 clientes es demasiado para ML)
    ),
    retry: 2,
    retryDelay: 3000, // ✅ Aumentar delay entre retries para dar más tiempo al servidor
    gcTime: 5 * 60 * 1000, // ✅ Mantener en cache 5 minutos para evitar recargas innecesarias
    staleTime: 2 * 60 * 1000, // ✅ Considerar datos frescos por 2 minutos
    // ✅ No mostrar error si es un timeout que se resolvió en retry
    onError: (error: any) => {
      // Solo mostrar error si NO es un timeout que se resolvió (ECONNABORTED)
      // React Query manejará el retry automáticamente
      if (error?.code !== 'ECONNABORTED' && !error?.message?.includes('timeout')) {
        console.error('âŒ [Cobranzas] Error cargando clientes atrasados:', error)
      }
    },
  })

  // Query para por analista
  const {
    data: porAnalista,
    isLoading: cargandoAnalistas,
    isError: errorAnalistas,
    error: errorAnalistasDetalle,
    refetch: refetchAnalistas
  } = useQuery({
    queryKey: ['cobranzas-por-analista'],
    queryFn: () => cobranzasService.getCobranzasPorAnalista(),
    retry: 2,
    retryDelay: 1000,
  })

  // Query para obtener usuarios activos (para el dropdown de analistas)
  const {
    data: usuariosData,
    isLoading: cargandoUsuarios
  } = useQuery({
    queryKey: ['usuarios-activos'],
    queryFn: async () => {
      const response = await userService.listarUsuarios(1, 1000, true)
      return response.items.filter((u: any) => u.is_active && !u.is_admin)
    },
    retry: 2,
    retryDelay: 1000,
  })

  // Query para obtener analistas activos (para el dropdown de analistas)
  const {
    data: analistasData,
    isLoading: cargandoAnalistasData
  } = useQuery({
    queryKey: ['analistas-activos'],
    queryFn: async () => {
      const { analistaService } = await import('../services/analistaService')
      return await analistaService.listarAnalistasActivos()
    },
    retry: 2,
    retryDelay: 1000,
  })

  // Efecto para mostrar errores automáticamente
  useEffect(() => {
    if (errorResumen) {
      console.error('Error cargando resumen de cobranzas:', errorResumenDetalle)
      toast.error('Error al cargar resumen de cobranzas', {
        description: errorResumenDetalle instanceof Error
          ? errorResumenDetalle.message
          : 'No se pudieron cargar los datos del resumen',
        duration: 5000,
      })
    }
  }, [errorResumen, errorResumenDetalle])

  useEffect(() => {
    if (errorClientes) {
      console.error('Error cargando clientes atrasados:', errorClientesDetalle)
      toast.error('Error al cargar clientes atrasados', {
        description: errorClientesDetalle instanceof Error
          ? errorClientesDetalle.message
          : 'No se pudieron cargar los clientes atrasados',
        duration: 5000,
      })
    }
  }, [errorClientes, errorClientesDetalle])

  useEffect(() => {
    if (errorAnalistas) {
      console.error('Error cargando datos por analista:', errorAnalistasDetalle)
      toast.error('Error al cargar datos por analista', {
        description: errorAnalistasDetalle instanceof Error
          ? errorAnalistasDetalle.message
          : 'No se pudieron cargar los datos por analista',
        duration: 5000,
      })
    }
  }, [errorAnalistas, errorAnalistasDetalle])

  // Función para exportar clientes de un analista
  const exportarClientesAnalista = async (nombreAnalista: string) => {
    try {
      const clientes = await cobranzasService.getClientesPorAnalista(nombreAnalista)
      await exportarAExcel(
        clientes,
        `clientes-${nombreAnalista.replace('@', '')}`,
        ['cedula', 'nombres', 'telefono', 'prestamo_id', 'cuotas_vencidas', 'total_adeudado', 'fecha_primera_vencida']
      )
    } catch (error) {
      console.error('Error obteniendo clientes del analista:', error)
      alert('Error al obtener clientes del analista')
    }
  }

  // Función para expandir/colapsar analista y cargar sus clientes
  const toggleAnalista = async (nombreAnalista: string) => {
    const expandidos = new Set(analistasExpandidos)

    if (expandidos.has(nombreAnalista)) {
      // Colapsar
      expandidos.delete(nombreAnalista)
      setAnalistasExpandidos(expandidos)
    } else {
      // Expandir y cargar clientes si no están cargados
      expandidos.add(nombreAnalista)
      setAnalistasExpandidos(expandidos)

      if (!clientesPorAnalista[nombreAnalista]) {
        setCargandoClientesAnalista(prev => ({ ...prev, [nombreAnalista]: true }))
        try {
          const clientes = await cobranzasService.getClientesPorAnalista(nombreAnalista)
          setClientesPorAnalista(prev => ({ ...prev, [nombreAnalista]: clientes }))
        } catch (error) {
          console.error(`Error cargando clientes del analista ${nombreAnalista}:`, error)
          toast.error(`Error al cargar clientes de ${nombreAnalista}`)
        } finally {
          setCargandoClientesAnalista(prev => ({ ...prev, [nombreAnalista]: false }))
        }
      }
    }
  }

  // Función para iniciar edición del analista
  const iniciarEdicionAnalista = (prestamoId: number, analistaActual: string) => {
    setEditandoAnalista(prestamoId)
    setAnalistaTemporal(analistaActual || '')
  }

  // Función para cancelar edición del analista
  const cancelarEdicionAnalista = () => {
    setEditandoAnalista(null)
    setAnalistaTemporal('')
  }

  // Función para guardar el analista actualizado
  const guardarAnalista = async (prestamoId: number) => {
    if (!analistaTemporal || analistaTemporal.trim() === '') {
      toast.error('Debe seleccionar un analista')
      return
    }

    setGuardandoAnalista(prestamoId)
    try {
      await cobranzasService.actualizarAnalista(prestamoId, analistaTemporal)
      toast.success('Analista actualizado correctamente')
      setEditandoAnalista(null)
      setAnalistaTemporal('')
      // Refrescar los datos de ambas secciones
      refetchClientes()
      refetchAnalistas()
      // Si estamos en la sección "Por Analista", también refrescar los clientes de cada analista
      // Limpiar los clientes cargados para forzar recarga
      setClientesPorAnalista({})
    } catch (error: any) {
      console.error('Error actualizando analista:', error)
      toast.error(error?.response?.data?.detail || 'Error al actualizar el analista')
    } finally {
      setGuardandoAnalista(null)
    }
  }

  // Función para iniciar edición de ML Impago
  const iniciarEdicionMLImpago = (prestamoId: number, mlImpagoActual: { nivel_riesgo: string; probabilidad_impago: number } | null | undefined) => {
    setEditandoMLImpago(prestamoId)
    if (mlImpagoActual) {
      setMLImpagoTemporal({
        nivelRiesgo: mlImpagoActual.nivel_riesgo,
        probabilidad: mlImpagoActual.probabilidad_impago,
      })
    } else {
      setMLImpagoTemporal({
        nivelRiesgo: 'Medio',
        probabilidad: 0.5,
      })
    }
  }

  // Función para cancelar edición de ML Impago
  const cancelarEdicionMLImpago = () => {
    setEditandoMLImpago(null)
    setMLImpagoTemporal(null)
  }

  // Función para guardar ML Impago actualizado
  const guardarMLImpago = async (prestamoId: number) => {
    if (!mlImpagoTemporal) {
      toast.error('Debe completar los datos de ML Impago')
      return
    }

    if (mlImpagoTemporal.probabilidad < 0 || mlImpagoTemporal.probabilidad > 1) {
      toast.error('La probabilidad debe estar entre 0 y 1')
      return
    }

    setGuardandoMLImpago(prestamoId)
    try {
      await cobranzasService.actualizarMLImpago(
        prestamoId,
        mlImpagoTemporal.nivelRiesgo,
        mlImpagoTemporal.probabilidad
      )
      toast.success('Riesgo ML Impago actualizado correctamente')
      setEditandoMLImpago(null)
      setMLImpagoTemporal(null)
      // ✅ Invalidar caché de cobranzas para refrescar datos actualizados
      queryClient.invalidateQueries({ queryKey: ['cobranzas-resumen'] })
      queryClient.invalidateQueries({ queryKey: ['cobranzas-clientes'] })
      // Refrescar los datos
      refetchClientes()
      refetchResumen()
      // Si estamos en la sección "Por Analista", también refrescar
      setClientesPorAnalista({})
    } catch (error: any) {
      console.error('Error actualizando ML Impago:', error)
      toast.error(error?.response?.data?.detail || 'Error al actualizar el Riesgo ML Impago')
    } finally {
      setGuardandoMLImpago(null)
    }
  }

  // Función para eliminar valores manuales de ML Impago
  const eliminarMLImpagoManual = async (prestamoId: number) => {
    setGuardandoMLImpago(prestamoId)
    try {
      await cobranzasService.eliminarMLImpagoManual(prestamoId)
      toast.success('Valores manuales eliminados. Se usarán valores calculados por ML.')
      // ✅ Invalidar caché de cobranzas para refrescar datos actualizados
      queryClient.invalidateQueries({ queryKey: ['cobranzas-resumen'] })
      queryClient.invalidateQueries({ queryKey: ['cobranzas-clientes'] })
      // Refrescar los datos
      refetchClientes()
      refetchResumen()
      setClientesPorAnalista({})
    } catch (error: any) {
      console.error('Error eliminando ML Impago manual:', error)
      toast.error(error?.response?.data?.detail || 'Error al eliminar valores manuales')
    } finally {
      setGuardandoMLImpago(null)
    }
  }

  // Función para exportar a Excel
  const exportarAExcel = async (data: Record<string, unknown>[], nombre: string, columnas?: string[]) => {
    if (!data || data.length === 0) {
      alert('No hay datos para exportar')
      return
    }

    try {
      // Importar dinámicamente exceljs
      const { createAndDownloadExcel } = await import('../types/exceljs')

      // Obtener columnas del primer objeto si no se especifican
      const keys = columnas || Object.keys(data[0])

      // Preparar datos para Excel
      const datosExcel = data.map(item => {
        const row: Record<string, unknown> = {}
        keys.forEach(key => {
          row[key] = item[key] ?? ''
        })
        return row
      })

      // Generar fecha para nombre de archivo
      const fecha = new Date().toISOString().split('T')[0]
      const nombreArchivo = `${nombre}_${fecha}.xlsx`

      // Descargar usando exceljs
      await createAndDownloadExcel(datosExcel, 'Datos', nombreArchivo)
    } catch (error) {
      console.error('Error exportando a Excel:', error)
      alert('Error al exportar a Excel')
    }
  }

  // Función para determinar color del badge según días de retraso
  const getColorBadge = (diasRetraso: number) => {
    if (diasRetraso === 1) return 'bg-green-100 text-green-800'
    if (diasRetraso === 3) return 'bg-yellow-100 text-yellow-800'
    if (diasRetraso === 5) return 'bg-orange-100 text-orange-800'
    return 'bg-red-100 text-red-800'
  }

  // Procesar notificaciones de atrasos
  const procesarNotificaciones = async () => {
    setProcesandoNotificaciones(true)
    try {
      const resultado = await cobranzasService.procesarNotificacionesAtrasos()
      const stats = resultado.estadisticas || {}
      const enviadas = stats.enviadas || 0
      const fallidas = stats.fallidas || 0
      const errores = stats.errores || 0

      // ✅ Invalidar caché de cobranzas después de procesar notificaciones
      // Los datos pueden haber cambiado después de enviar notificaciones
      queryClient.invalidateQueries({ queryKey: ['cobranzas-resumen'] })
      queryClient.invalidateQueries({ queryKey: ['cobranzas-clientes'] })
      queryClient.invalidateQueries({ queryKey: ['cobranzas-por-analista'] })
      // Refrescar datos
      refetchResumen()
      refetchClientes()
      refetchAnalistas()

      if (enviadas > 0 || fallidas > 0) {
        toast.success(
          `Notificaciones procesadas: ${enviadas} enviadas${fallidas > 0 ? `, ${fallidas} fallidas` : ''}`,
          {
            duration: 5000,
            action: {
              label: 'Ver Historial',
              onClick: () => window.location.href = '/notificaciones'
            }
          }
        )
      } else {
        toast.info('No hay notificaciones pendientes para procesar')
      }
    } catch (error: unknown) {
      const { getErrorMessage, getErrorDetail } = await import('../types/errors')
      let errorMessage = getErrorMessage(error)
      const detail = getErrorDetail(error)
      if (detail) {
        errorMessage = detail
      }
      console.error('Error exportando a Excel:', errorMessage)
      toast.error(errorMessage || 'Error al procesar notificaciones')
    } finally {
      setProcesandoNotificaciones(false)
    }
  }

  // Ejecutar diagnóstico
  const ejecutarDiagnostico = async () => {
    setMostrandoDiagnostico(true)
    try {
      const resultado = await cobranzasService.getDiagnostico()
      setDiagnosticoData(resultado)
      toast.success('Diagnóstico completado. Revisa la consola para más detalles.')
    } catch (error: unknown) {
      const { getErrorMessage } = await import('../types/errors')
      const errorMessage = getErrorMessage(error)
      console.error('Error obteniendo diagnóstico:', errorMessage)
      toast.error(errorMessage || 'Error al obtener diagnóstico')
      setDiagnosticoData(null)
    } finally {
      setMostrandoDiagnostico(false)
    }
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Gestión de Cobranzas</h1>
          <p className="text-gray-600 mt-2">
            Seguimiento de pagos atrasados y cartera vencida
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={ejecutarDiagnostico}
            disabled={mostrandoDiagnostico}
            variant="outline"
            className="flex items-center gap-2"
          >
            {mostrandoDiagnostico ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Ejecutando...
              </>
            ) : (
              <>
                <AlertTriangle className="h-4 w-4" />
                🔍 Diagnóstico
              </>
            )}
          </Button>
          <Button
            onClick={procesarNotificaciones}
            disabled={procesandoNotificaciones}
            className="flex items-center gap-2"
          >
            {procesandoNotificaciones ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Procesando...
              </>
            ) : (
              <>
                <Bell className="h-4 w-4" />
                Procesar Notificaciones Ahora
              </>
            )}
          </Button>
          <Button
            variant="outline"
            onClick={() => window.location.href = '/notificaciones'}
            className="flex items-center gap-2"
          >
            <Eye className="h-4 w-4" />
            Ver Historial
          </Button>
        </div>
      </div>

      {/* Mostrar diagnóstico si está disponible */}
      {diagnosticoData && (
        <Card className="border-blue-200 bg-blue-50">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">🔍 Diagnóstico de Cobranzas</CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setDiagnosticoData(null)}
              >
                ✓
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Total Cuotas BD</p>
                  <p className="text-2xl font-bold">{diagnosticoData.diagnosticos?.total_cuotas_bd || 0}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Cuotas Vencidas</p>
                  <p className="text-2xl font-bold">{diagnosticoData.diagnosticos?.cuotas_vencidas_solo_fecha || 0}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Pago Incompleto</p>
                  <p className="text-2xl font-bold">{diagnosticoData.diagnosticos?.cuotas_pago_incompleto || 0}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Vencidas + Incompletas</p>
                  <p className="text-2xl font-bold">{diagnosticoData.diagnosticos?.cuotas_vencidas_incompletas || 0}</p>
                </div>
              </div>

              {diagnosticoData.diagnosticos?.estados_prestamos_con_cuotas_vencidas && (
                <div>
                  <p className="text-sm font-semibold mb-2">Estados de Préstamos con Cuotas Vencidas:</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(diagnosticoData.diagnosticos.estados_prestamos_con_cuotas_vencidas).map(([estado, cantidad]: [string, any]) => (
                      <Badge key={estado} variant="outline">
                        {estado}: {cantidad}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {diagnosticoData.analisis_filtros && (
                <div>
                  <p className="text-sm font-semibold mb-2">Análisis de Filtros:</p>
                  <div className="space-y-1 text-sm">
                    <p>• Perdidas por estado: {diagnosticoData.analisis_filtros.cuotas_perdidas_por_estado || 0}</p>
                    <p>• Perdidas por admin: {diagnosticoData.analisis_filtros.cuotas_perdidas_por_admin || 0}</p>
                    <p>• Perdidas por user admin: {diagnosticoData.analisis_filtros.cuotas_perdidas_por_user_admin || 0}</p>
                  </div>
                </div>
              )}

              <div className="mt-4">
                <p className="text-xs text-gray-500">
                  💡 Revisa la consola del navegador (F12) para ver el diagnóstico completo con todos los detalles.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Mensajes de error globales */}
      {errorResumen && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-red-800">
              <AlertTriangle className="h-5 w-5" />
              <div className="flex-1">
                <p className="font-semibold">Error al cargar resumen de cobranzas</p>
                <p className="text-sm text-red-600">
                  {errorResumenDetalle instanceof Error
                    ? errorResumenDetalle.message
                    : 'No se pudieron cargar los datos del resumen. Por favor, intenta nuevamente.'}
                </p>
              </div>
              <Button size="sm" variant="outline" onClick={() => refetchResumen()}>
                Reintentar
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* KPIs Resumen */}
      {cargandoResumen ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Cargando...</CardTitle>
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">-</div>
                <p className="text-xs text-muted-foreground">Cargando datos...</p>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : resumen ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Cuotas Vencidas</CardTitle>
              <TrendingDown className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{resumen.total_cuotas_vencidas}</div>
              <p className="text-xs text-muted-foreground">Cuotas pendientes de cobro</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Monto Total Adeudado</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                ${resumen.monto_total_adeudado.toLocaleString('es-VE')}
              </div>
              <p className="text-xs text-muted-foreground">En cartera vencida</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Clientes Atrasados</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{resumen.clientes_atrasados}</div>
              <p className="text-xs text-muted-foreground">Requieren seguimiento</p>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {/* Tabs de análisis */}
      <Tabs value={tabActiva} onValueChange={setTabActiva}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="cuotas">Cuotas</TabsTrigger>
          <TabsTrigger value="por-dias">Por Días</TabsTrigger>
          <TabsTrigger value="por-analista">Por Analista</TabsTrigger>
          <TabsTrigger value="informes">📊 Informes</TabsTrigger>
        </TabsList>

        {/* Tab Cuotas - Clientes con cuotas impagas */}
        <TabsContent value="cuotas" className="space-y-4">
          {/* Indicador de filtro activo */}
          {(rangoDiasMin !== undefined || rangoDiasMax !== undefined || filtroDiasRetraso !== undefined) && (
            <Card className="bg-blue-50 border-blue-200">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-blue-900">Filtro de Días de Retraso Activo:</p>
                    <p className="text-sm text-blue-700">
                      {filtroDiasRetraso !== undefined
                        ? `Mostrando clientes con exactamente ${filtroDiasRetraso} días de retraso`
                        : rangoDiasMin !== undefined && rangoDiasMax !== undefined
                        ? `Mostrando clientes con ${rangoDiasMin} a ${rangoDiasMax} días de retraso`
                        : rangoDiasMin !== undefined
                        ? `Mostrando clientes con ${rangoDiasMin} o más días de retraso`
                        : rangoDiasMax !== undefined
                        ? `Mostrando clientes con hasta ${rangoDiasMax} días de retraso`
                        : ''}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setRangoDiasMin(undefined)
                      setRangoDiasMax(undefined)
                      setFiltroDiasRetraso(undefined)
                    }}
                  >
                    Limpiar Filtro
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <CardTitle>Clientes con Cuotas Impagas</CardTitle>
                  <CardDescription>
                    Listado de clientes con cuotas no pagadas. Se muestra el número de cuotas impagas por cliente.
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={async () => {
                    // Filtrar clientes según búsqueda y filtros para exportar
                    let clientesParaExportar = clientesAtrasados || []

                    // Aplicar filtro de cuotas mínimas
                    if (filtroCuotasMinimas !== undefined) {
                      clientesParaExportar = clientesParaExportar.filter(
                        cliente => (cliente.cuotas_vencidas || 0) >= filtroCuotasMinimas!
                      )
                    }

                    // Aplicar búsqueda
                    if (busquedaResumen.trim()) {
                      clientesParaExportar = clientesParaExportar.filter(cliente =>
                        cliente.cedula.toLowerCase().includes(busquedaResumen.toLowerCase()) ||
                        cliente.nombres.toLowerCase().includes(busquedaResumen.toLowerCase())
                      )
                    }

                    await exportarAExcel(
                      clientesParaExportar,
                      busquedaResumen.trim()
                        ? `cuotas-impagas-${busquedaResumen.replace(/\s+/g, '-')}`
                        : 'cuotas-impagas',
                      ['cedula', 'nombres', 'analista', 'prestamo_id', 'cuotas_vencidas', 'total_adeudado', 'fecha_primera_vencida']
                    )
                  }}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Exportar Excel
                </Button>
              </div>

              {/* Mensaje de error de validación */}
              {errorRangoDias && (
                <Card className="border-red-200 bg-red-50 mb-4">
                  <CardContent className="pt-6">
                    <div className="flex items-center gap-2 text-red-800">
                      <AlertTriangle className="h-5 w-5" />
                      <p className="text-sm">{errorRangoDias}</p>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Filtros */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                {/* Filtro por cantidad mínima de cuotas impagas */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2 block">
                    Filtrar por cantidad mínima de cuotas impagas
                  </label>
                  <div className="flex gap-2">
                    <Input
                      type="number"
                      placeholder="Ej: 1, 2, 3..."
                      min="1"
                      value={filtroCuotasMinimas ?? ''}
                      onChange={(e) => {
                        const value = e.target.value ? parseInt(e.target.value) : undefined
                        setFiltroCuotasMinimas(value)
                      }}
                      className="flex-1"
                    />
                    {filtroCuotasMinimas !== undefined && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setFiltroCuotasMinimas(undefined)}
                      >
                        Limpiar
                      </Button>
                    )}
                  </div>
                </div>

                {/* Búsqueda */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2 block">
                    Buscar cliente
                  </label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      type="text"
                      placeholder="Buscar por nombre o cédula..."
                      value={busquedaResumen}
                      onChange={(e) => setBusquedaResumen(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>
              </div>

              {/* Información del filtro activo */}
              {filtroCuotasMinimas !== undefined && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-amber-800">
                      <span className="font-semibold">Filtro activo:</span> Mostrando solo clientes con {filtroCuotasMinimas} o más cuotas impagas
                    </p>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setFiltroCuotasMinimas(undefined)}
                    >
                      Limpiar
                    </Button>
                  </div>
                </div>
              )}
            </CardHeader>
            <CardContent>
              {cargandoClientes ? (
                <div className="text-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">Cargando clientes atrasados...</p>
                </div>
              ) : errorClientes ? (
                <div className="text-center py-8">
                  <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-red-500" />
                  <p className="text-sm font-semibold text-red-800 mb-2">Error al cargar clientes atrasados</p>
                  <p className="text-xs text-red-600 mb-4">
                    {errorClientesDetalle instanceof Error
                      ? errorClientesDetalle.message
                      : 'No se pudieron cargar los datos. Por favor, intenta nuevamente.'}
                  </p>
                  <Button size="sm" variant="outline" onClick={() => refetchClientes()}>
                    Reintentar
                  </Button>
                </div>
              ) : !clientesAtrasados || clientesAtrasados.length === 0 ? (
                <div className="text-center py-8">
                  <Users className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    {filtroDiasRetraso
                      ? `No hay clientes con cuotas impagas con exactamente ${filtroDiasRetraso} días de retraso`
                      : rangoDiasMin !== undefined && rangoDiasMax !== undefined
                      ? `No hay clientes con cuotas impagas con ${rangoDiasMin} a ${rangoDiasMax} días de retraso`
                      : rangoDiasMin !== undefined
                      ? `No hay clientes con cuotas impagas con ${rangoDiasMin} o más días de retraso`
                      : rangoDiasMax !== undefined
                      ? `No hay clientes con cuotas impagas con hasta ${rangoDiasMax} días de retraso`
                      : filtroCuotasMinimas !== undefined
                      ? `No hay clientes con ${filtroCuotasMinimas} o más cuotas impagas`
                      : 'No hay clientes con cuotas impagas en este momento'}
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  {(() => {
                    // Filtrar clientes según búsqueda
                    let clientesFiltrados = busquedaResumen.trim()
                      ? clientesAtrasados.filter(cliente =>
                          cliente.cedula.toLowerCase().includes(busquedaResumen.toLowerCase()) ||
                          cliente.nombres.toLowerCase().includes(busquedaResumen.toLowerCase())
                        )
                      : clientesAtrasados

                    // Aplicar filtro de cuotas mínimas
                    if (filtroCuotasMinimas !== undefined) {
                      clientesFiltrados = clientesFiltrados.filter(
                        cliente => (cliente.cuotas_vencidas || 0) >= filtroCuotasMinimas!
                      )
                    }

                    // Ordenar por número de cuotas impagas (mayor a menor), luego por total adeudado
                    clientesFiltrados = [...clientesFiltrados].sort((a, b) => {
                      const cuotasA = a.cuotas_vencidas || 0
                      const cuotasB = b.cuotas_vencidas || 0
                      if (cuotasA !== cuotasB) {
                        return cuotasB - cuotasA // Más cuotas primero
                      }
                      return (b.total_adeudado || 0) - (a.total_adeudado || 0) // Luego por monto
                    })

                    if (clientesFiltrados.length === 0) {
                      return (
                        <div className="text-center py-8">
                          <Search className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                          <p className="text-sm text-muted-foreground">
                            {busquedaResumen.trim() && filtroCuotasMinimas !== undefined
                              ? `No se encontraron clientes que coincidan con "${busquedaResumen}" y tengan ${filtroCuotasMinimas} o más cuotas impagas`
                              : busquedaResumen.trim()
                              ? `No se encontraron clientes que coincidan con "${busquedaResumen}"`
                              : filtroCuotasMinimas !== undefined
                              ? `No se encontraron clientes con ${filtroCuotasMinimas} o más cuotas impagas`
                              : 'No hay clientes con cuotas impagas'}
                          </p>
                        </div>
                      )
                    }

                    return (
                      <>
                        {(busquedaResumen.trim() || filtroCuotasMinimas !== undefined) && (
                          <div className="mb-4 text-sm text-muted-foreground">
                            Mostrando {clientesFiltrados.length} de {clientesAtrasados.length} clientes
                            {filtroCuotasMinimas !== undefined && (
                              <span className="ml-2 text-amber-700 font-semibold">
                                (filtrado: {filtroCuotasMinimas}+ cuotas impagas)
                              </span>
                            )}
                          </div>
                        )}

                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b bg-gray-50">
                              <th className="text-left p-2 font-semibold">Cédula</th>
                              <th className="text-left p-2 font-semibold">Nombres</th>
                              <th className="text-left p-2 font-semibold">Analista</th>
                              <th className="text-center p-2 font-semibold">Cuotas Impagas</th>
                              <th className="text-right p-2 font-semibold">Total Adeudado</th>
                            </tr>
                          </thead>
                          <tbody>
                            {clientesFiltrados.map((cliente, index) => {
                              const cuotasImpagas = cliente.cuotas_vencidas || 0
                              const estaEditando = editandoAnalista === cliente.prestamo_id
                              const estaGuardando = guardandoAnalista === cliente.prestamo_id
                              return (
                                <tr key={`${cliente.prestamo_id}-${index}`} className="border-b hover:bg-gray-50 transition-colors group">
                                  <td className="p-2 font-mono text-xs">{cliente.cedula}</td>
                                  <td className="p-2">{cliente.nombres}</td>
                                  <td className="p-2">
                                    {estaEditando ? (
                                      <div className="flex items-center gap-2">
                                        <Select
                                          value={analistaTemporal}
                                          onValueChange={setAnalistaTemporal}
                                          disabled={estaGuardando}
                                        >
                                          <SelectTrigger className="w-[200px] h-8">
                                            <SelectValue placeholder="Seleccionar analista" />
                                          </SelectTrigger>
                                          <SelectContent>
                                            {/* Mostrar analistas primero (por nombre) */}
                                            {analistasData?.map((analista: any) => (
                                              <SelectItem key={`analista-${analista.id}`} value={analista.nombre}>
                                                {analista.nombre} (Analista)
                                              </SelectItem>
                                            ))}
                                            {/* Luego mostrar usuarios (por email) */}
                                            {usuariosData?.map((usuario: any) => (
                                              <SelectItem key={`usuario-${usuario.id}`} value={usuario.email}>
                                                {usuario.email} (Usuario)
                                              </SelectItem>
                                            ))}
                                          </SelectContent>
                                        </Select>
                                        <Button
                                          size="sm"
                                          variant="ghost"
                                          onClick={() => guardarAnalista(cliente.prestamo_id)}
                                          disabled={estaGuardando}
                                          className="h-8 w-8 p-0"
                                        >
                                          {estaGuardando ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                          ) : (
                                            <Save className="h-4 w-4 text-green-600" />
                                          )}
                                        </Button>
                                        <Button
                                          size="sm"
                                          variant="ghost"
                                          onClick={cancelarEdicionAnalista}
                                          disabled={estaGuardando}
                                          className="h-8 w-8 p-0"
                                        >
                                          <X className="h-4 w-4 text-red-600" />
                                        </Button>
                                      </div>
                                    ) : (
                                      <div className="flex items-center gap-2">
                                        <span className="text-sm">{cliente.analista || 'N/A'}</span>
                                        <Button
                                          size="sm"
                                          variant="ghost"
                                          onClick={() => iniciarEdicionAnalista(cliente.prestamo_id, cliente.analista || '')}
                                          className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity hover:opacity-100"
                                          title="Editar analista"
                                        >
                                          <Edit className="h-3 w-3" />
                                        </Button>
                                      </div>
                                    )}
                                  </td>
                                  <td className="p-2 text-center">
                                    <Badge
                                      variant="outline"
                                      className={
                                        cuotasImpagas >= 5
                                          ? "bg-red-100 text-red-800 border-red-300 font-bold"
                                          : cuotasImpagas >= 3
                                          ? "bg-orange-100 text-orange-800 border-orange-300 font-semibold"
                                          : cuotasImpagas >= 2
                                          ? "bg-yellow-100 text-yellow-800 border-yellow-300"
                                          : "bg-blue-100 text-blue-800 border-blue-300"
                                      }
                                    >
                                      {cuotasImpagas} {cuotasImpagas === 1 ? 'cuota' : 'cuotas'}
                                    </Badge>
                                  </td>
                                  <td className="p-2 text-right font-semibold text-red-600">
                                    ${(cliente.total_adeudado || 0).toLocaleString('es-VE')}
                                  </td>
                                </tr>
                              )
                            })}
                          </tbody>
                        </table>
                      </>
                    )
                  })()}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab Por Días de Retraso */}
        <TabsContent value="por-dias" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Filtro por Días de Retraso</CardTitle>
              <CardDescription>
                Filtre clientes con cuotas no pagadas según días de retraso desde la fecha de vencimiento
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Filtro de rango personalizado */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg border">
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2 block">
                    Días Mínimo de Retraso
                  </label>
                  <Input
                    type="number"
                    placeholder="Ej: 1"
                    min="0"
                    value={rangoDiasMin ?? ''}
                    onChange={(e) => {
                      const value = e.target.value ? parseInt(e.target.value) : undefined
                      if (value !== undefined && validarRangoDias(value, rangoDiasMax)) {
                        setRangoDiasMin(value)
                        if (value !== undefined) {
                          setFiltroDiasRetraso(undefined) // Limpiar filtro simple
                        }
                      } else if (value === undefined) {
                        setRangoDiasMin(undefined)
                        setErrorRangoDias(null)
                        setFiltroDiasRetraso(undefined)
                      }
                    }}
                    className={errorRangoDias ? 'border-red-500' : ''}
                  />
                  {errorRangoDias && (
                    <p className="text-xs text-red-500 mt-1">{errorRangoDias}</p>
                  )}
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-2 block">
                    Días Máximo de Retraso
                  </label>
                  <Input
                    type="number"
                    placeholder="Ej: 30"
                    min="0"
                    value={rangoDiasMax ?? ''}
                    onChange={(e) => {
                      const value = e.target.value ? parseInt(e.target.value) : undefined
                      if (value !== undefined && validarRangoDias(rangoDiasMin, value)) {
                        setRangoDiasMax(value)
                        if (value !== undefined) {
                          setFiltroDiasRetraso(undefined) // Limpiar filtro simple
                        }
                      } else if (value === undefined) {
                        setRangoDiasMax(undefined)
                        setErrorRangoDias(null)
                        setFiltroDiasRetraso(undefined)
                      }
                    }}
                    className={errorRangoDias ? 'border-red-500' : ''}
                  />
                </div>
                <div className="flex items-end">
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => {
                      setRangoDiasMin(undefined)
                      setRangoDiasMax(undefined)
                      setFiltroDiasRetraso(undefined)
                      setTabActiva('cuotas')
                    }}
                  >
                    Limpiar Filtros
                  </Button>
                </div>
              </div>

              {/* Botones de rangos predefinidos */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Rangos Predefinidos</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <Button
                    variant="outline"
                    className="flex flex-col items-center p-4 h-auto"
                    onClick={() => {
                      setRangoDiasMin(1)
                      setRangoDiasMax(7)
                      setFiltroDiasRetraso(undefined)
                      setTabActiva('cuotas')
                    }}
                  >
                    <Badge className="bg-green-100 text-green-800 mb-2">1-7 Días</Badge>
                    <span className="text-xs text-gray-600">Retraso Leve</span>
                  </Button>

                  <Button
                    variant="outline"
                    className="flex flex-col items-center p-4 h-auto"
                    onClick={() => {
                      setRangoDiasMin(8)
                      setRangoDiasMax(30)
                      setFiltroDiasRetraso(undefined)
                      setTabActiva('cuotas')
                    }}
                  >
                    <Badge className="bg-yellow-100 text-yellow-800 mb-2">8-30 Días</Badge>
                    <span className="text-xs text-gray-600">Retraso Moderado</span>
                  </Button>

                  <Button
                    variant="outline"
                    className="flex flex-col items-center p-4 h-auto"
                    onClick={() => {
                      setRangoDiasMin(31)
                      setRangoDiasMax(60)
                      setFiltroDiasRetraso(undefined)
                      setTabActiva('cuotas')
                    }}
                  >
                    <Badge className="bg-orange-100 text-orange-800 mb-2">31-60 Días</Badge>
                    <span className="text-xs text-gray-600">Retraso Alto</span>
                  </Button>

                  <Button
                    variant="outline"
                    className="flex flex-col items-center p-4 h-auto"
                    onClick={() => {
                      setRangoDiasMin(61)
                      setRangoDiasMax(undefined)
                      setFiltroDiasRetraso(undefined)
                      setTabActiva('cuotas')
                    }}
                  >
                    <Badge className="bg-red-100 text-red-800 mb-2">61+ Días</Badge>
                    <span className="text-xs text-gray-600">Retraso Crítico</span>
                  </Button>
                </div>
              </div>

              {/* Botón para aplicar filtro personalizado */}
              {(rangoDiasMin !== undefined || rangoDiasMax !== undefined) && (
                <div className="flex justify-center">
                  <Button
                    onClick={() => setTabActiva('cuotas')}
                    className="w-full md:w-auto"
                  >
                    Ver Clientes con {rangoDiasMin !== undefined ? `mínimo ${rangoDiasMin} días` : ''}
                    {rangoDiasMin !== undefined && rangoDiasMax !== undefined ? ' y ' : ''}
                    {rangoDiasMax !== undefined ? `máximo ${rangoDiasMax} días` : ''}
                    {rangoDiasMin === undefined && rangoDiasMax !== undefined ? ' de retraso' : ''}
                    {rangoDiasMin !== undefined && rangoDiasMax === undefined ? ' o más de retraso' : ''}
                  </Button>
                </div>
              )}

              {/* Información del filtro activo */}
              {(rangoDiasMin !== undefined || rangoDiasMax !== undefined || filtroDiasRetraso !== undefined) && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-semibold text-blue-900">Filtro Activo:</p>
                      <p className="text-sm text-blue-700">
                        {filtroDiasRetraso !== undefined
                          ? `Clientes con exactamente ${filtroDiasRetraso} días de retraso`
                          : rangoDiasMin !== undefined && rangoDiasMax !== undefined
                          ? `Clientes con ${rangoDiasMin} a ${rangoDiasMax} días de retraso`
                          : rangoDiasMin !== undefined
                          ? `Clientes con ${rangoDiasMin} o más días de retraso`
                          : rangoDiasMax !== undefined
                          ? `Clientes con hasta ${rangoDiasMax} días de retraso`
                          : ''}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setRangoDiasMin(undefined)
                        setRangoDiasMax(undefined)
                        setFiltroDiasRetraso(undefined)
                      }}
                    >
                      Limpiar
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab Por Analista */}
        <TabsContent value="por-analista" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Análisis por Analista</CardTitle>
              <CardDescription>
                Montos sin cobrar y cantidad de clientes atrasados por analista
              </CardDescription>
            </CardHeader>
            <CardContent>
              {cargandoAnalistas ? (
                <div className="text-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">Cargando datos por analista...</p>
                </div>
              ) : errorAnalistas ? (
                <div className="text-center py-8">
                  <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-red-500" />
                  <p className="text-sm font-semibold text-red-800 mb-2">Error al cargar datos por analista</p>
                  <p className="text-xs text-red-600 mb-4">
                    {errorAnalistasDetalle instanceof Error
                      ? errorAnalistasDetalle.message
                      : 'No se pudieron cargar los datos. Por favor, intenta nuevamente.'}
                  </p>
                  <Button size="sm" variant="outline" onClick={() => refetchAnalistas()}>
                    Reintentar
                  </Button>
                </div>
              ) : !porAnalista || porAnalista.length === 0 ? (
                <div className="text-center py-8">
                  <Users className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">No hay datos de analistas disponibles</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {porAnalista.map((analista, index) => {
                    const estaExpandido = analistasExpandidos.has(analista.nombre)
                    const clientes = clientesPorAnalista[analista.nombre] || []
                    const cargando = cargandoClientesAnalista[analista.nombre] || false
                    const busqueda = busquedaPorAnalista[analista.nombre] || ''

                    // Filtrar clientes según búsqueda
                    const clientesFiltrados = busqueda.trim()
                      ? clientes.filter(cliente =>
                          cliente.cedula.toLowerCase().includes(busqueda.toLowerCase()) ||
                          cliente.nombres.toLowerCase().includes(busqueda.toLowerCase())
                        )
                      : clientes

                    // Ordenar por total adeudado de mayor a menor
                    const clientesOrdenados = [...clientesFiltrados].sort((a, b) =>
                      (b.total_adeudado || 0) - (a.total_adeudado || 0)
                    )

                    return (
                      <div key={index} className="border rounded-lg overflow-hidden">
                        {/* Header del analista */}
                        <div className="p-4 bg-gray-50 hover:bg-gray-100 transition-colors">
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => toggleAnalista(analista.nombre)}
                                  className="p-1 h-auto"
                                >
                                  {estaExpandido ? (
                                    <ChevronUp className="h-5 w-5" />
                                  ) : (
                                    <ChevronDown className="h-5 w-5" />
                                  )}
                                </Button>
                                <div>
                                  <h3 className="font-semibold text-lg">{analista.nombre}</h3>
                                  <p className="text-sm text-gray-600">
                                    {analista.cantidad_clientes} clientes atrasados con al menos 1 cuota vencida
                                  </p>
                                </div>
                              </div>
                            </div>
                            <div className="text-right mr-4">
                              <p className="text-2xl font-bold text-red-600">
                                ${analista.monto_total.toLocaleString('es-VE')}
                              </p>
                              <p className="text-xs text-gray-500">Monto total adeudado</p>
                            </div>
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => exportarClientesAnalista(analista.nombre)}
                              >
                                <Download className="h-4 w-4 mr-2" />
                                Exportar
                              </Button>
                            </div>
                          </div>
                        </div>

                        {/* Contenido expandible con clientes */}
                        {estaExpandido && (
                          <div className="p-4 border-t">
                            {cargando ? (
                              <div className="text-center py-8">
                                <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2 text-muted-foreground" />
                                <p className="text-sm text-muted-foreground">Cargando clientes...</p>
                              </div>
                            ) : clientes.length === 0 ? (
                              <div className="text-center py-8">
                                <Users className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                                <p className="text-sm text-muted-foreground">No hay clientes atrasados para este analista</p>
                              </div>
                            ) : (
                              <div className="space-y-4">
                                {/* Búsqueda de clientes */}
                                <div className="relative">
                                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                  <Input
                                    type="text"
                                    placeholder="Buscar cliente por nombre o cédula..."
                                    value={busqueda}
                                    onChange={(e) => setBusquedaPorAnalista(prev => ({ ...prev, [analista.nombre]: e.target.value }))}
                                    className="pl-10"
                                  />
                                </div>

                                {/* Información de resultados */}
                                {busqueda.trim() && (
                                  <div className="text-sm text-muted-foreground">
                                    Mostrando {clientesOrdenados.length} de {clientes.length} clientes
                                  </div>
                                )}

                                {/* Tabla de clientes */}
                                {clientesOrdenados.length === 0 && busqueda.trim() ? (
                                  <div className="text-center py-8">
                                    <Search className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                                    <p className="text-sm text-muted-foreground">
                                      No se encontraron clientes que coincidan con "{busqueda}"
                                    </p>
                                  </div>
                                ) : (
                                  <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                      <thead>
                                        <tr className="border-b bg-gray-50">
                                          <th className="text-left p-2 font-semibold">Cédula</th>
                                          <th className="text-left p-2 font-semibold">Nombres</th>
                                          <th className="text-left p-2 font-semibold">Analista</th>
                                          <th className="text-left p-2 font-semibold">Teléfono</th>
                                          <th className="text-right p-2 font-semibold">Cuotas Vencidas</th>
                                          <th className="text-right p-2 font-semibold">Total Adeudado</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {clientesOrdenados.map((cliente, idx) => {
                                          const estaEditando = editandoAnalista === cliente.prestamo_id
                                          const estaGuardando = guardandoAnalista === cliente.prestamo_id
                                          // Obtener el analista del cliente o usar el analista del grupo
                                          const analistaCliente = cliente.analista || analista.nombre
                                          return (
                                            <tr key={`${cliente.prestamo_id}-${idx}`} className="border-b hover:bg-gray-50 transition-colors group">
                                              <td className="p-2 font-mono text-xs">{cliente.cedula}</td>
                                              <td className="p-2">{cliente.nombres}</td>
                                              <td className="p-2">
                                                {estaEditando ? (
                                                  <div className="flex items-center gap-2">
                                                    <Select
                                                      value={analistaTemporal}
                                                      onValueChange={setAnalistaTemporal}
                                                      disabled={estaGuardando}
                                                    >
                                                      <SelectTrigger className="w-[200px] h-8">
                                                        <SelectValue placeholder="Seleccionar analista" />
                                                      </SelectTrigger>
                                                      <SelectContent>
                                                        {usuariosData?.map((usuario: any) => (
                                                          <SelectItem key={usuario.id} value={usuario.email}>
                                                            {usuario.email}
                                                          </SelectItem>
                                                        ))}
                                                      </SelectContent>
                                                    </Select>
                                                    <Button
                                                      size="sm"
                                                      variant="ghost"
                                                      onClick={() => guardarAnalista(cliente.prestamo_id)}
                                                      disabled={estaGuardando}
                                                      className="h-8 w-8 p-0"
                                                    >
                                                      {estaGuardando ? (
                                                        <Loader2 className="h-4 w-4 animate-spin" />
                                                      ) : (
                                                        <Save className="h-4 w-4 text-green-600" />
                                                      )}
                                                    </Button>
                                                    <Button
                                                      size="sm"
                                                      variant="ghost"
                                                      onClick={cancelarEdicionAnalista}
                                                      disabled={estaGuardando}
                                                      className="h-8 w-8 p-0"
                                                    >
                                                      <X className="h-4 w-4 text-red-600" />
                                                    </Button>
                                                  </div>
                                                ) : (
                                                  <div className="flex items-center gap-2">
                                                    <span className="text-sm">{analistaCliente || 'N/A'}</span>
                                                    <Button
                                                      size="sm"
                                                      variant="ghost"
                                                      onClick={() => iniciarEdicionAnalista(cliente.prestamo_id, analistaCliente || '')}
                                                      className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity hover:opacity-100"
                                                      title="Editar analista"
                                                    >
                                                      <Edit className="h-3 w-3" />
                                                    </Button>
                                                  </div>
                                                )}
                                              </td>
                                              <td className="p-2">{cliente.telefono || 'N/A'}</td>
                                              <td className="p-2 text-right">
                                                <Badge variant="outline" className="bg-red-50 text-red-700">
                                                  {cliente.cuotas_vencidas}
                                                </Badge>
                                              </td>
                                              <td className="p-2 text-right font-semibold text-red-600">
                                                ${(cliente.total_adeudado || 0).toLocaleString('es-VE')}
                                              </td>
                                            </tr>
                                          )
                                        })}
                                      </tbody>
                                    </table>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab Informes */}
        <TabsContent value="informes" className="space-y-4">
          <InformesCobranzas />
        </TabsContent>
      </Tabs>
    </div>
  )
}

