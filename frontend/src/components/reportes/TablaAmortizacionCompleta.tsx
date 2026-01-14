import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Search,
  Edit,
  Trash2,
  Save,
  X,
  FileText,
  User,
  DollarSign,
  Calendar,
  CreditCard,
  AlertCircle,
  CheckCircle2,
  Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { prestamoService } from '@/services/prestamoService'
import { cuotaService, type Cuota, type CuotaUpdate } from '@/services/cuotaService'
import { pagoService, type Pago } from '@/services/pagoService'
import { clienteService } from '@/services/clienteService'
import { usePrestamosByCedula } from '@/hooks/usePrestamos'
import { toast } from 'sonner'
import { formatCurrency, formatDate } from '@/utils'

interface ClienteInfo {
  id: number
  cedula: string
  nombres: string
  telefono: string
  email: string
}

interface PrestamoInfo {
  id: number
  total_financiamiento: number
  estado: string
  fecha_aprobacion: string | null
  numero_cuotas: number
  tasa_interes: number
}

export function TablaAmortizacionCompleta() {
  const [cedulaBuscar, setCedulaBuscar] = useState('')
  const [cedulaSeleccionada, setCedulaSeleccionada] = useState<string | null>(null)
  const [cuotaEditando, setCuotaEditando] = useState<Cuota | null>(null)
  const [pagoEditando, setPagoEditando] = useState<Pago | null>(null)
  const [mostrarDialogCuota, setMostrarDialogCuota] = useState(false)
  const [mostrarDialogPago, setMostrarDialogPago] = useState(false)
  const [mostrarDialogFecha, setMostrarDialogFecha] = useState(false)
  const [prestamoParaGenerar, setPrestamoParaGenerar] = useState<any>(null)
  const [fechaBaseCalculo, setFechaBaseCalculo] = useState<string>('')
  const queryClient = useQueryClient()

  // Buscar cliente por cédula
  const { data: clienteInfo, isLoading: loadingCliente } = useQuery({
    queryKey: ['cliente-cedula', cedulaSeleccionada],
    queryFn: async () => {
      if (!cedulaSeleccionada) return null
      try {
        const response = await clienteService.getClientes({ cedula: cedulaSeleccionada }, 1, 1)
        return response.data?.[0] || null
      } catch (error) {
        console.error('Error buscando cliente:', error)
        return null
      }
    },
    enabled: !!cedulaSeleccionada,
  })

  // Obtener préstamos por cédula usando hook
  const { data: prestamosData, isLoading: loadingPrestamos, error: errorPrestamos } = usePrestamosByCedula(cedulaSeleccionada || '')
  
  // Debug: Log para ver qué está pasando con los préstamos
  console.log('🔍 [TablaAmortizacion] Estado préstamos:', {
    cedulaSeleccionada,
    loadingPrestamos,
    errorPrestamos,
    prestamosData,
    prestamosLength: prestamosData?.length || 0,
    prestamoIds: prestamosData?.map(p => p.id) || []
  })
  
  // Asegurar que prestamos siempre sea un array
  const prestamos = prestamosData || []

  // Obtener cuotas de todos los préstamos (optimizado - una sola query)
  // Usar JSON.stringify para crear una key estable para React Query
  const prestamoIds = prestamosData?.map(p => p.id).sort((a, b) => a - b) || []
  const prestamoIdsKey = JSON.stringify(prestamoIds)
  const shouldFetchCuotas = !!cedulaSeleccionada && !!prestamosData && Array.isArray(prestamosData) && prestamosData.length > 0 && !loadingPrestamos
  
  console.log('🔍 [TablaAmortizacion] Condición para cargar cuotas:', {
    cedulaSeleccionada: !!cedulaSeleccionada,
    prestamosData: !!prestamosData,
    isArray: Array.isArray(prestamosData),
    prestamosLength: prestamosData?.length || 0,
    loadingPrestamos,
    shouldFetchCuotas,
    prestamoIds,
    prestamoIdsKey
  })
  
  const { data: todasLasCuotas, isLoading: loadingCuotas, error: errorCuotas } = useQuery({
    queryKey: ['cuotas-prestamos', prestamoIdsKey],
    queryFn: async () => {
      const ids = prestamosData?.map(p => p.id) || []
      if (!prestamosData || prestamosData.length === 0 || ids.length === 0) {
        console.log('⚠️ [TablaAmortizacion] No hay préstamos para cargar cuotas')
        return []
      }
      try {
        // Usar endpoint optimizado para múltiples préstamos
        console.log('📡 [TablaAmortizacion] Cargando cuotas para préstamos:', ids)
        const cuotas = await cuotaService.getCuotasMultiplesPrestamos(ids)
        console.log('✅ [TablaAmortizacion] Cuotas cargadas:', cuotas.length)
        return cuotas
      } catch (error) {
        console.error('❌ [TablaAmortizacion] Error obteniendo cuotas:', error)
        toast.error('Error al cargar cuotas. Algunos datos pueden estar incompletos.')
        return []
      }
    },
    enabled: shouldFetchCuotas,
    retry: 1, // Solo reintentar una vez
  })

  // Debug: Verificar cuando cambian los préstamos
  useEffect(() => {
    console.log('🔄 [TablaAmortizacion] useEffect - Prestamos cambiaron:', {
      cedulaSeleccionada,
      loadingPrestamos,
      prestamosData,
      prestamosLength: prestamosData?.length || 0,
      prestamoIds,
      shouldFetchCuotas,
      loadingCuotas,
      todasLasCuotasLength: todasLasCuotas?.length || 0
    })
  }, [cedulaSeleccionada, loadingPrestamos, prestamosData, prestamoIds, shouldFetchCuotas, loadingCuotas, todasLasCuotas])

  // Obtener pagos por cédula (manejar errores para que no fallen los reportes)
  const { data: pagosData, isLoading: loadingPagos, error: errorPagos } = useQuery({
    queryKey: ['pagos-cedula', cedulaSeleccionada],
    queryFn: async () => {
      try {
        return await pagoService.getAllPagos(1, 1000, { cedula: cedulaSeleccionada! })
      } catch (error) {
        console.error('Error obteniendo pagos:', error)
        toast.error('Error al cargar pagos. Algunos datos pueden estar incompletos.')
        // Retornar estructura vacía para que no falle el reporte
        return { pagos: [], total: 0, page: 1, pageSize: 1000 }
      }
    },
    enabled: !!cedulaSeleccionada,
    retry: 1, // Solo reintentar una vez
  })

  const pagos = pagosData?.pagos || []
  
  // Filtrar pagos activos y manejar valores nulos/vacíos en numero_documento
  const pagosFiltrados = pagos.filter(p => p.activo !== false).map(p => ({
    ...p,
    numero_documento: p.numero_documento || '', // Asegurar que nunca sea null/undefined
  }))

  // Mutaciones para editar
  const mutationActualizarCuota = useMutation({
    mutationFn: ({ cuotaId, data }: { cuotaId: number; data: CuotaUpdate }) =>
      cuotaService.updateCuota(cuotaId, data),
    onSuccess: (data, variables) => {
      toast.success('Cuota actualizada exitosamente')
      // Invalidar todas las queries relacionadas con cuotas para asegurar actualización
      queryClient.invalidateQueries({ queryKey: ['cuotas-prestamos'] })
      queryClient.invalidateQueries({ queryKey: ['cuotas'] })
      // También invalidar la query específica de esta cuota si existe
      queryClient.invalidateQueries({ queryKey: ['cuota', variables.cuotaId] })
      // Forzar refetch de las cuotas actuales para mostrar cambios inmediatos
      queryClient.refetchQueries({ queryKey: ['cuotas-prestamos', prestamoIdsKey] })
      setMostrarDialogCuota(false)
      setCuotaEditando(null)
    },
    onError: (error: any) => {
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error desconocido'
      toast.error(`Error al actualizar cuota: ${mensajeError}`)
      console.error('Error actualizando cuota:', error)
    },
  })

  const mutationEliminarCuota = useMutation({
    mutationFn: (cuotaId: number) => cuotaService.deleteCuota(cuotaId),
    onSuccess: () => {
      toast.success('Cuota eliminada exitosamente')
      queryClient.invalidateQueries({ queryKey: ['cuotas-prestamos'] })
    },
    onError: (error: any) => {
      toast.error(`Error al eliminar cuota: ${error?.message || 'Error desconocido'}`)
    },
  })

  // Función para confirmar eliminación
  const handleEliminarCuota = (cuotaId: number) => {
    if (!confirm('¿Está seguro de eliminar esta cuota? Esta acción no se puede deshacer.')) {
      return
    }
    mutationEliminarCuota.mutate(cuotaId)
  }

  const mutationActualizarPago = useMutation({
    mutationFn: ({ pagoId, data }: { pagoId: number; data: Partial<{
      monto_pagado: number
      numero_documento: string
      fecha_pago: string
      institucion_bancaria: string | null
    }> }) =>
      pagoService.updatePago(pagoId, data),
    onSuccess: () => {
      toast.success('Pago actualizado exitosamente')
      queryClient.invalidateQueries({ queryKey: ['pagos-cedula'] })
      setMostrarDialogPago(false)
      setPagoEditando(null)
    },
    onError: (error: any) => {
      toast.error(`Error al actualizar pago: ${error?.message || 'Error desconocido'}`)
    },
  })

  const mutationEliminarPago = useMutation({
    mutationFn: (pagoId: number) => pagoService.deletePago(pagoId),
    onSuccess: () => {
      toast.success('Pago eliminado exitosamente')
      queryClient.invalidateQueries({ queryKey: ['pagos-cedula'] })
    },
    onError: (error: any) => {
      toast.error(`Error al eliminar pago: ${error?.message || 'Error desconocido'}`)
    },
  })

  // Mutación para generar amortización
  const mutationGenerarAmortizacion = useMutation({
    mutationFn: (prestamoId: number) => prestamoService.generarAmortizacion(prestamoId),
    onSuccess: (data, prestamoId) => {
      toast.success(`Tabla de amortización generada exitosamente para el préstamo ${prestamoId}`)
      // Invalidar queries para recargar cuotas
      queryClient.invalidateQueries({ queryKey: ['cuotas-prestamos'] })
      queryClient.invalidateQueries({ queryKey: ['prestamos-cedula', cedulaSeleccionada] })
    },
    onError: (error: any) => {
      toast.error(`Error al generar amortización: ${error?.response?.data?.detail || error?.message || 'Error desconocido'}`)
    },
  })

  // Mutación para actualizar préstamo
  const mutationActualizarPrestamo = useMutation({
    mutationFn: ({ prestamoId, data }: { prestamoId: number; data: Partial<any> }) =>
      prestamoService.updatePrestamo(prestamoId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prestamos-cedula', cedulaSeleccionada] })
    },
  })

  // Función para abrir diálogo de fecha y generar cuotas
  const handleAbrirDialogoFecha = (prestamo: any) => {
    setPrestamoParaGenerar(prestamo)
    // Si ya tiene fecha_base_calculo, usarla como valor por defecto
    if (prestamo.fecha_base_calculo) {
      setFechaBaseCalculo(prestamo.fecha_base_calculo)
    } else {
      // Usar fecha de aprobación o fecha actual como sugerencia
      const fechaSugerida = prestamo.fecha_aprobacion 
        ? new Date(prestamo.fecha_aprobacion).toISOString().split('T')[0]
        : new Date().toISOString().split('T')[0]
      setFechaBaseCalculo(fechaSugerida)
    }
    setMostrarDialogFecha(true)
  }

  // Función para generar cuotas con fecha ingresada manualmente
  const handleGenerarCuotasConFecha = async () => {
    if (!prestamoParaGenerar || !fechaBaseCalculo) {
      toast.error('Por favor, ingrese una fecha válida')
      return
    }

    try {
      // Paso 1: Actualizar fecha_base_calculo en el préstamo
      if (!prestamoParaGenerar.fecha_base_calculo) {
        await mutationActualizarPrestamo.mutateAsync({
          prestamoId: prestamoParaGenerar.id,
          data: { fecha_base_calculo: fechaBaseCalculo }
        })
        toast.success('Fecha base de cálculo guardada')
      }

      // Paso 2: Generar las cuotas
      await mutationGenerarAmortizacion.mutateAsync(prestamoParaGenerar.id)
      
      // Paso 3: Aplicar pagos existentes a las cuotas generadas
      const pagosDelPrestamo = pagos.filter((p: Pago) => 
        p.prestamo_id === prestamoParaGenerar.id && 
        (p.conciliado || p.verificado_concordancia === 'SI')
      )

      if (pagosDelPrestamo.length > 0) {
        let pagosAplicados = 0
        for (const pago of pagosDelPrestamo) {
          try {
            await pagoService.aplicarPagoACuotas(pago.id)
            pagosAplicados++
          } catch (error) {
            console.error(`Error aplicando pago ${pago.id} a cuotas:`, error)
          }
        }
        if (pagosAplicados > 0) {
          toast.success(`${pagosAplicados} pago(s) aplicado(s) a las cuotas generadas`)
        }
      }

      // Cerrar diálogo y recargar datos
      setMostrarDialogFecha(false)
      setPrestamoParaGenerar(null)
      setFechaBaseCalculo('')
      
      queryClient.invalidateQueries({ queryKey: ['cuotas-prestamos'] })
      queryClient.invalidateQueries({ queryKey: ['prestamos-cedula', cedulaSeleccionada] })
      queryClient.invalidateQueries({ queryKey: ['pagos-cedula', cedulaSeleccionada] })
      
      toast.success('Tabla de amortización generada y pagos aplicados exitosamente')
    } catch (error: any) {
      toast.error(`Error: ${error?.response?.data?.detail || error?.message || 'Error desconocido'}`)
    }
  }

  // Función para generar cuotas para todos los préstamos sin cuotas
  const handleGenerarCuotasParaTodos = async () => {
    if (!prestamos || prestamos.length === 0) {
      toast.error('No hay préstamos para procesar')
      return
    }

    // Filtrar préstamos aprobados sin cuotas
    const prestamosSinCuotas = prestamos.filter((p: any) => {
      const tieneCuotas = todasLasCuotas && todasLasCuotas.length > 0 
        ? todasLasCuotas.some((c: Cuota) => c.prestamo_id === p.id)
        : false
      return p.estado === 'APROBADO' && !tieneCuotas
    })

    if (prestamosSinCuotas.length === 0) {
      toast.info('Todos los préstamos aprobados ya tienen cuotas generadas')
      return
    }

    // Si hay múltiples préstamos, procesar el primero y mostrar diálogo
    if (prestamosSinCuotas.length === 1) {
      handleAbrirDialogoFecha(prestamosSinCuotas[0])
    } else {
      // Para múltiples préstamos, procesar el primero
      handleAbrirDialogoFecha(prestamosSinCuotas[0])
      toast.info(`Se procesará el préstamo ${prestamosSinCuotas[0].id}. Los demás se pueden procesar después.`)
    }
  }

  // Función para confirmar eliminación de pago
  const handleEliminarPago = (pagoId: number) => {
    if (!confirm('¿Está seguro de eliminar este pago? Esta acción no se puede deshacer.')) {
      return
    }
    mutationEliminarPago.mutate(pagoId)
  }

  // Validación de cédula venezolana
  const validarCedula = (cedula: string): boolean => {
    if (!cedula || cedula.trim().length === 0) return false
    // Formato: V/E/J/P/G seguido de 6-12 dígitos
    return /^[VEJPG]\d{6,12}$/i.test(cedula.trim())
  }

  const handleBuscar = () => {
    const cedulaLimpia = cedulaBuscar.trim().toUpperCase()
    if (!cedulaLimpia) {
      toast.error('Por favor, ingrese una cédula')
      return
    }
    if (!validarCedula(cedulaLimpia)) {
      toast.error('Cédula inválida. Debe tener el formato V/E/J/P/G seguido de 6-12 dígitos')
      return
    }
    setCedulaSeleccionada(cedulaLimpia)
  }

  // Validadores
  const validarFecha = (fecha: string): boolean => {
    if (!fecha) return true // Fechas opcionales
    const fechaRegex = /^\d{4}-\d{2}-\d{2}$/
    if (!fechaRegex.test(fecha)) return false
    const fechaObj = new Date(fecha)
    return fechaObj instanceof Date && !isNaN(fechaObj.getTime())
  }

  const validarMonto = (valor: string): { valido: boolean; mensaje?: string } => {
    if (!valor || valor.trim() === '') return { valido: true } // Campos opcionales
    const numero = parseFloat(valor)
    if (isNaN(numero)) return { valido: false, mensaje: 'Debe ser un número válido' }
    if (numero < 0) return { valido: false, mensaje: 'No puede ser negativo' }
    // Validar máximo 2 decimales
    const partes = valor.split('.')
    if (partes.length === 2 && partes[1].length > 2) {
      return { valido: false, mensaje: 'Máximo 2 decimales permitidos' }
    }
    return { valido: true }
  }

  const formatearMonto = (valor: string): string => {
    if (!valor || valor.trim() === '') return ''
    const numero = parseFloat(valor)
    if (isNaN(numero)) return valor
    // Redondear a 2 decimales
    return numero.toFixed(2)
  }

  const handleEditarCuota = (cuota: Cuota) => {
    setCuotaEditando(cuota)
    setMostrarDialogCuota(true)
  }

  const handleEditarPago = (pago: Pago) => {
    setPagoEditando(pago)
    setMostrarDialogPago(true)
  }

  const getEstadoBadge = (estado: string) => {
    const estados: Record<string, { color: string; label: string }> = {
      PAGADO: { color: 'bg-green-500', label: 'Pagado' },
      PENDIENTE: { color: 'bg-yellow-500', label: 'Pendiente' },
      ATRASADO: { color: 'bg-red-500', label: 'Atrasado' },
      PARCIAL: { color: 'bg-blue-500', label: 'Parcial' },
      VENCIDA: { color: 'bg-red-500', label: 'Vencida' },
    }
    const config = estados[estado?.toUpperCase()] || { color: 'bg-gray-500', label: estado || 'N/A' }
    return <Badge className={`${config.color} text-white`}>{config.label}</Badge>
  }

  const totalFinanciamiento = prestamos?.reduce((sum, p) => sum + (p.total_financiamiento || 0), 0) || 0

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Tabla de Amortización por Cédula
          </CardTitle>
          <CardDescription>
            Busca una cédula para ver su tabla de amortización completa con opciones de edición y eliminación
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 mb-6">
            <Input
              placeholder="Ingresa la cédula del cliente"
              value={cedulaBuscar}
              onChange={(e) => setCedulaBuscar(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleBuscar()}
              className="max-w-md"
            />
            <Button onClick={handleBuscar} disabled={loadingCliente || loadingPrestamos}>
              <Search className="w-4 h-4 mr-2" />
              Buscar
            </Button>
          </div>

          {cedulaSeleccionada && (
            <>
              {/* Información del Cliente */}
              {(loadingCliente || loadingPrestamos) ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                  <span className="ml-2">Cargando información...</span>
                </div>
              ) : errorPrestamos ? (
                <Card className="mb-6">
                  <CardContent className="py-8 text-center">
                    <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
                    <p className="text-red-600 mb-2">Error al cargar los préstamos</p>
                    <p className="text-sm text-gray-600">
                      {errorPrestamos instanceof Error ? errorPrestamos.message : 'Error desconocido'}
                    </p>
                  </CardContent>
                </Card>
              ) : prestamos && prestamos.length === 0 && !loadingPrestamos ? (
                <Card className="mb-6">
                  <CardContent className="py-8 text-center">
                    <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-600 mb-2">No se encontraron préstamos para esta cédula</p>
                  </CardContent>
                </Card>
              ) : prestamos && prestamos.length > 0 ? (
                <>
                  {/* Tablas de Amortización agrupadas por préstamo */}
                  {loadingCuotas ? (
                    <Card className="mb-6">
                      <CardContent className="py-8 text-center">
                        <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-4" />
                        <p className="text-gray-600">Cargando tabla de amortización...</p>
                      </CardContent>
                    </Card>
                  ) : errorCuotas ? (
                    <Card className="mb-6">
                      <CardContent className="py-8 text-center">
                        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
                        <p className="text-red-600 mb-2">Error al cargar las cuotas</p>
                        <p className="text-sm text-gray-600">
                          {errorCuotas instanceof Error ? errorCuotas.message : 'Error desconocido'}
                        </p>
                      </CardContent>
                    </Card>
                  ) : todasLasCuotas && todasLasCuotas.length > 0 ? (
                    // Agrupar cuotas por préstamo y mostrar cada préstamo en su propia tabla
                    prestamos.map((prestamo: any) => {
                      const cuotasDelPrestamo = todasLasCuotas.filter((c: Cuota) => c.prestamo_id === prestamo.id)
                      
                      if (cuotasDelPrestamo.length === 0) {
                        return null
                      }

                      return (
                        <Card key={prestamo.id} className="mb-6 border-l-4 border-l-blue-500 shadow-md">
                          <CardHeader className="bg-gradient-to-r from-blue-50 to-transparent border-b">
                            <CardTitle className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <CreditCard className="w-5 h-5 text-blue-600" />
                                <div>
                                  <span className="text-lg font-bold">Préstamo #{prestamo.id}</span>
                                  {clienteInfo?.nombres && (
                                    <p className="text-sm text-gray-600 font-normal mt-1">{clienteInfo.nombres}</p>
                                  )}
                                </div>
                              </div>
                              <div className="text-right">
                                <p className="text-sm text-gray-600">Total Financiamiento</p>
                                <p className="text-xl font-bold text-blue-600">{formatCurrency(prestamo.total_financiamiento)}</p>
                              </div>
                            </CardTitle>
                          </CardHeader>
                          <CardContent className="pt-6">
                            <div className="overflow-x-auto">
                              <Table>
                                <TableHeader>
                                  <TableRow>
                                    <TableHead>Cuota #</TableHead>
                                    <TableHead>Fecha Vencimiento</TableHead>
                                    <TableHead>Monto Cuota</TableHead>
                                    <TableHead>Total Pagado</TableHead>
                                    <TableHead>Pendiente</TableHead>
                                    <TableHead>Estado</TableHead>
                                    <TableHead className="text-right">Acciones</TableHead>
                                  </TableRow>
                                </TableHeader>
                                <TableBody>
                                  {cuotasDelPrestamo.map((cuota) => (
                                    <TableRow key={cuota.id}>
                                      <TableCell className="font-semibold">{cuota.numero_cuota}</TableCell>
                                      <TableCell>{formatDate(cuota.fecha_vencimiento)}</TableCell>
                                      <TableCell>{formatCurrency(cuota.monto_cuota)}</TableCell>
                                      <TableCell className="font-semibold">{formatCurrency(cuota.total_pagado || 0)}</TableCell>
                                      <TableCell>{formatCurrency((cuota.monto_cuota || 0) - (cuota.total_pagado || 0))}</TableCell>
                                      <TableCell>{getEstadoBadge(cuota.estado)}</TableCell>
                                      <TableCell className="text-right">
                                        <div className="flex gap-2 justify-end">
                                          <Button
                                            size="sm"
                                            variant="outline"
                                            onClick={() => handleEditarCuota(cuota)}
                                            title="Editar Cuota"
                                          >
                                            <Edit className="w-4 h-4" />
                                          </Button>
                                          <Button
                                            size="sm"
                                            variant="outline"
                                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                            onClick={() => handleEliminarCuota(cuota.id)}
                                            title="Eliminar Cuota"
                                          >
                                            <Trash2 className="w-4 h-4" />
                                          </Button>
                                        </div>
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </div>
                          </CardContent>
                        </Card>
                      )
                    })
                  ) : (
                    <Card className="mb-6">
                      <CardContent className="py-8 text-center">
                        <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                        <p className="text-gray-600 mb-2">No se encontraron cuotas para los préstamos de este cliente</p>
                        <p className="text-sm text-gray-500 mb-4">
                          Los préstamos pueden no tener tabla de amortización generada.
                        </p>
                        {prestamos && prestamos.length > 0 && prestamos.some((p: any) => 
                          p.estado === 'APROBADO'
                        ) && (
                          <Button
                            onClick={handleGenerarCuotasParaTodos}
                            disabled={mutationGenerarAmortizacion.isPending || mutationActualizarPrestamo.isPending}
                            className="mt-2"
                          >
                            {mutationGenerarAmortizacion.isPending || mutationActualizarPrestamo.isPending ? (
                              <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                Generando...
                              </>
                            ) : (
                              <>
                                <FileText className="w-4 h-4 mr-2" />
                                Generar Tabla de Amortización
                              </>
                            )}
                          </Button>
                        )}
                        {prestamos && prestamos.length > 0 && !prestamos.some((p: any) => 
                          p.estado === 'APROBADO'
                        ) && (
                          <p className="text-sm text-yellow-600 mt-2">
                            Los préstamos necesitan estar aprobados para generar cuotas.
                          </p>
                        )}
                      </CardContent>
                    </Card>
                  )}
                </>
              ) : null}
            </>
          )}
        </CardContent>
      </Card>

      {/* Dialog Editar Cuota */}
      <Dialog open={mostrarDialogCuota} onOpenChange={setMostrarDialogCuota}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Editar Cuota #{cuotaEditando?.numero_cuota}</DialogTitle>
            <p className="text-sm text-gray-600 mb-4">Modifica los datos de la cuota. Los cambios se guardarán inmediatamente.</p>
          </DialogHeader>
          {cuotaEditando && (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                const formData = new FormData(e.currentTarget)
                
                // Validar fechas
                const fechaVencimiento = formData.get('fecha_vencimiento') as string
                const fechaPago = formData.get('fecha_pago') as string
                
                if (fechaVencimiento && !validarFecha(fechaVencimiento)) {
                  toast.error('Fecha de vencimiento inválida')
                  return
                }
                if (fechaPago && !validarFecha(fechaPago)) {
                  toast.error('Fecha de pago inválida')
                  return
                }

                // Validar y formatear montos
                const camposMonetarios = [
                  'monto_cuota', 'total_pagado'
                ]
                
                const data: CuotaUpdate = {}
                
                // Procesar fechas
                if (fechaVencimiento) {
                  data.fecha_vencimiento = fechaVencimiento
                }
                // Manejar fecha_pago: si está vacío, enviar null explícitamente
                if (fechaPago && fechaPago.trim() !== '') {
                  data.fecha_pago = fechaPago
                } else {
                  // Enviar null explícitamente para limpiar fecha_pago
                  data.fecha_pago = null
                }

                // Procesar montos con validación
                for (const campo of camposMonetarios) {
                  const valor = formData.get(campo) as string
                  if (valor && valor.trim() !== '') {
                    const validacion = validarMonto(valor)
                    if (!validacion.valido) {
                      toast.error(`${campo.replace(/_/g, ' ')}: ${validacion.mensaje}`)
                      return
                    }
                    const valorFormateado = formatearMonto(valor)
                    const valorNumerico = parseFloat(valorFormateado)
                    if (!isNaN(valorNumerico)) {
                      data[campo as keyof CuotaUpdate] = valorNumerico as any
                    }
                  }
                }

                // Procesar estado y observaciones
                const estado = formData.get('estado') as string
                if (estado) {
                  data.estado = estado
                }
                
                const observaciones = formData.get('observaciones') as string
                if (observaciones !== null) {
                  data.observaciones = observaciones || null
                }

                // Log para debugging (solo en desarrollo)
                if (process.env.NODE_ENV === 'development') {
                  console.log('📝 [EditarCuota] Datos a enviar:', {
                    cuotaId: cuotaEditando.id,
                    data,
                    dataKeys: Object.keys(data)
                  })
                }

                // Validar que haya al menos un campo para actualizar
                if (Object.keys(data).length === 0) {
                  toast.warning('No se han realizado cambios')
                  return
                }

                mutationActualizarCuota.mutate({ cuotaId: cuotaEditando.id, data })
              }}
              className="space-y-4"
            >
              {/* Fechas */}
              <div className="grid grid-cols-2 gap-4 border-b pb-4">
                <div>
                  <Label htmlFor="fecha_vencimiento">Fecha de Vencimiento *</Label>
                  <Input
                    id="fecha_vencimiento"
                    name="fecha_vencimiento"
                    type="date"
                    defaultValue={
                      typeof cuotaEditando.fecha_vencimiento === 'string'
                        ? cuotaEditando.fecha_vencimiento.split('T')[0]
                        : new Date(cuotaEditando.fecha_vencimiento).toISOString().split('T')[0]
                    }
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">Formato: YYYY-MM-DD</p>
                </div>
                <div>
                  <Label htmlFor="fecha_pago">Fecha de Pago</Label>
                  <Input
                    id="fecha_pago"
                    name="fecha_pago"
                    type="date"
                    defaultValue={
                      cuotaEditando.fecha_pago
                        ? typeof cuotaEditando.fecha_pago === 'string'
                          ? cuotaEditando.fecha_pago.split('T')[0]
                          : new Date(cuotaEditando.fecha_pago).toISOString().split('T')[0]
                        : ''
                    }
                  />
                  <p className="text-xs text-gray-500 mt-1">Formato: YYYY-MM-DD (opcional)</p>
                </div>
              </div>

              {/* Montos Base */}
              <div className="grid grid-cols-3 gap-4 border-b pb-4">
                <div>
                  <Label htmlFor="monto_cuota">Monto Cuota *</Label>
                  <Input
                    id="monto_cuota"
                    name="monto_cuota"
                    type="number"
                    step="0.01"
                    min="0"
                    defaultValue={cuotaEditando.monto_cuota}
                    required
                    onBlur={(e) => {
                      const valor = e.target.value
                      if (valor) {
                        const validacion = validarMonto(valor)
                        if (!validacion.valido) {
                          toast.error(validacion.mensaje || 'Valor inválido')
                          e.target.focus()
                        } else {
                          e.target.value = formatearMonto(valor)
                        }
                      }
                    }}
                  />
                  <p className="text-xs text-gray-500 mt-1">Máximo 2 decimales</p>
                </div>
              </div>

              {/* Montos Pagados */}
              <div className="grid grid-cols-1 gap-4 border-b pb-4">
                <div>
                  <Label htmlFor="total_pagado">Total Pagado</Label>
                  <Input
                    id="total_pagado"
                    name="total_pagado"
                    type="number"
                    step="0.01"
                    min="0"
                    defaultValue={cuotaEditando.total_pagado || 0}
                    onBlur={(e) => {
                      const valor = e.target.value
                      if (valor) {
                        const validacion = validarMonto(valor)
                        if (!validacion.valido) {
                          toast.error(validacion.mensaje || 'Valor inválido')
                          e.target.focus()
                        } else {
                          e.target.value = formatearMonto(valor)
                        }
                      }
                    }}
                  />
                  <p className="text-xs text-gray-500 mt-1">Máximo 2 decimales</p>
                </div>
              </div>

              {/* Estado y Observaciones */}
              <div className="grid grid-cols-1 gap-4">
                <div>
                  <Label htmlFor="estado">Estado</Label>
                  <select
                    id="estado"
                    name="estado"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    defaultValue={cuotaEditando.estado}
                  >
                    <option value="PENDIENTE">Pendiente</option>
                    <option value="PARCIAL">Parcial</option>
                    <option value="PAGADO">Pagado</option>
                    <option value="ATRASADO">Atrasado</option>
                    <option value="VENCIDA">Vencida</option>
                  </select>
                </div>
                <div>
                  <Label htmlFor="observaciones">Observaciones</Label>
                  <Textarea
                    id="observaciones"
                    name="observaciones"
                    defaultValue={cuotaEditando.observaciones || ''}
                    rows={3}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setMostrarDialogCuota(false)}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={mutationActualizarCuota.isPending}>
                  {mutationActualizarCuota.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Guardando...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4 mr-2" />
                      Guardar Cambios
                    </>
                  )}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {/* Dialog Editar Pago */}
      <Dialog open={mostrarDialogPago} onOpenChange={setMostrarDialogPago}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Editar Pago ID {pagoEditando?.id}</DialogTitle>
            <p className="text-sm text-gray-600 mb-4">Modifica los datos del pago. Los números científicos se normalizarán automáticamente.</p>
          </DialogHeader>
          {pagoEditando && (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                const formData = new FormData(e.currentTarget)
                
                // Normalizar número de documento si es científico o está vacío
                let numeroDocumento = (formData.get('numero_documento') as string)?.trim() || ''
                
                // Si está vacío, usar el valor actual o cadena vacía
                if (!numeroDocumento) {
                  numeroDocumento = pagoEditando.numero_documento || ''
                }
                
                // Normalizar formato científico si existe
                if (numeroDocumento && (/[eE]/.test(numeroDocumento))) {
                  try {
                    const numeroFloat = parseFloat(numeroDocumento)
                    if (!isNaN(numeroFloat)) {
                      numeroDocumento = Math.floor(numeroFloat).toString()
                      toast.info(`Número de documento normalizado: ${numeroDocumento}`)
                    }
                  } catch (e) {
                    console.error('Error normalizando número:', e)
                    toast.warning('Error al normalizar número científico. Se guardará tal como está.')
                  }
                }
                
                // Permitir guardar incluso si está vacío (no requerido)
                if (!numeroDocumento) {
                  numeroDocumento = '' // Permitir vacío
                }
                
                // Convertir fecha_pago a string si es Date
                let fechaPagoStr: string
                const fechaPagoForm = formData.get('fecha_pago') as string
                if (fechaPagoForm) {
                  fechaPagoStr = fechaPagoForm
                } else {
                  // Si no hay fecha del formulario, usar la fecha actual del pago
                  const fechaPagoActual = pagoEditando.fecha_pago
                  if (fechaPagoActual instanceof Date) {
                    fechaPagoStr = fechaPagoActual.toISOString().split('T')[0]
                  } else if (typeof fechaPagoActual === 'string') {
                    // Si ya es string, extraer solo la fecha (sin hora)
                    fechaPagoStr = fechaPagoActual.split('T')[0]
                  } else {
                    fechaPagoStr = new Date().toISOString().split('T')[0]
                  }
                }
                
                const data: Partial<{
                  monto_pagado: number
                  numero_documento: string
                  fecha_pago: string
                  institucion_bancaria: string | null
                }> = {
                  monto_pagado: parseFloat(formData.get('monto_pagado') as string) || pagoEditando.monto_pagado,
                  numero_documento: numeroDocumento,
                  fecha_pago: fechaPagoStr,
                  institucion_bancaria: (formData.get('institucion_bancaria') as string) || pagoEditando.institucion_bancaria || null,
                }
                mutationActualizarPago.mutate({ pagoId: pagoEditando.id, data })
              }}
              className="space-y-4"
            >
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="monto_pagado">Monto Pagado</Label>
                  <Input
                    id="monto_pagado"
                    name="monto_pagado"
                    type="number"
                    step="0.01"
                    defaultValue={pagoEditando.monto_pagado}
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="fecha_pago">Fecha de Pago</Label>
                  <Input
                    id="fecha_pago"
                    name="fecha_pago"
                    type="date"
                    defaultValue={
                      typeof pagoEditando.fecha_pago === 'string'
                        ? pagoEditando.fecha_pago.split('T')[0]
                        : new Date(pagoEditando.fecha_pago).toISOString().split('T')[0]
                    }
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="numero_documento">Número de Documento</Label>
                  <Input
                    id="numero_documento"
                    name="numero_documento"
                    defaultValue={pagoEditando.numero_documento || ''}
                    placeholder="Ingrese número de documento"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    {pagoEditando.numero_documento && /[eE]/.test(pagoEditando.numero_documento) ? (
                      <span className="text-yellow-600">
                        ⚠️ Formato científico detectado. Se normalizará automáticamente al guardar.
                      </span>
                    ) : (
                      'Los números científicos se normalizarán automáticamente'
                    )}
                    {!pagoEditando.numero_documento && (
                      <span className="text-gray-500"> Campo opcional. Puede dejarse vacío.</span>
                    )}
                  </p>
                </div>
                <div>
                  <Label htmlFor="institucion_bancaria">Institución Bancaria</Label>
                  <Input
                    id="institucion_bancaria"
                    name="institucion_bancaria"
                    defaultValue={pagoEditando.institucion_bancaria || ''}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setMostrarDialogPago(false)}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={mutationActualizarPago.isPending}>
                  {mutationActualizarPago.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Guardando...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4 mr-2" />
                      Guardar Cambios
                    </>
                  )}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {/* Dialog Ingresar Fecha Base de Cálculo */}
      <Dialog open={mostrarDialogFecha} onOpenChange={setMostrarDialogFecha}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Ingresar Fecha Base de Cálculo</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {prestamoParaGenerar && (
              <div className="bg-blue-50 p-3 rounded-md">
                <p className="text-sm text-gray-600">
                  <strong>Préstamo ID:</strong> {prestamoParaGenerar.id}
                </p>
                <p className="text-sm text-gray-600">
                  <strong>Monto:</strong> {formatCurrency(prestamoParaGenerar.total_financiamiento)}
                </p>
                <p className="text-sm text-gray-600">
                  <strong>Cuotas:</strong> {prestamoParaGenerar.numero_cuotas}
                </p>
              </div>
            )}
            <div>
              <Label htmlFor="fecha_base_calculo">Fecha Base de Cálculo *</Label>
              <Input
                id="fecha_base_calculo"
                type="date"
                value={fechaBaseCalculo}
                onChange={(e) => setFechaBaseCalculo(e.target.value)}
                required
                className="mt-1"
              />
              <p className="text-xs text-gray-500 mt-1">
                Esta fecha será guardada y usada para generar las cuotas del préstamo.
              </p>
            </div>
            {pagos && pagos.length > 0 && prestamoParaGenerar && (
              <div className="bg-yellow-50 p-3 rounded-md">
                <p className="text-sm text-yellow-800">
                  <strong>Nota:</strong> Se encontraron {pagos.filter((p: Pago) => 
                    p.prestamo_id === prestamoParaGenerar.id && 
                    (p.conciliado || p.verificado_concordancia === 'SI')
                  ).length} pago(s) conciliado(s) que se aplicarán automáticamente a las cuotas generadas.
                </p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button 
              type="button" 
              variant="outline" 
              onClick={() => {
                setMostrarDialogFecha(false)
                setPrestamoParaGenerar(null)
                setFechaBaseCalculo('')
              }}
            >
              Cancelar
            </Button>
            <Button 
              onClick={handleGenerarCuotasConFecha}
              disabled={!fechaBaseCalculo || mutationGenerarAmortizacion.isPending || mutationActualizarPrestamo.isPending}
            >
              {mutationGenerarAmortizacion.isPending || mutationActualizarPrestamo.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Procesando...
                </>
              ) : (
                <>
                  <FileText className="w-4 h-4 mr-2" />
                  Guardar Fecha y Generar Cuotas
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
