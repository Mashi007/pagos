import { useState, useEffect, useRef } from 'react'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import { motion } from 'framer-motion'

import { useNavigate, useLocation, useSearchParams } from 'react-router-dom'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import { Button } from '../components/ui/button'

import {
  Loader2,
  Edit,
  AlertCircle,
  RefreshCw,
  Search,
  ChevronLeft,
  ChevronRight,
  Trash2,
  FileText,
  MoreHorizontal,
} from 'lucide-react'

import { Input } from '../components/ui/input'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog'

import { toast } from 'sonner'

import { revisionManualService } from '../services/revisionManualService'

import { EstadoRevisionIcon } from '../components/revision_manual/EstadoRevisionIcon'

import {
  invalidateListasNotificacionesMora,
  invalidatePagosPrestamosRevisionYCuotas,
} from '../constants/queryKeys'

interface PrestamoRevision {
  prestamo_id: number

  cliente_id: number

  cedula: string

  nombres: string

  total_prestamo: number

  total_abonos: number

  saldo: number

  cuotas_pagadas?: number | null

  cuotas_total?: number | null

  cuotas_vencidas: number

  cuotas_morosas: number

  estado_revision: string

  fecha_revision: string | null
}

interface ResumenRevision {
  total_prestamos: number

  prestamos_revisados: number

  prestamos_pendientes: number

  porcentaje_completado: number

  prestamos: PrestamoRevision[]
}

const PER_PAGE = 20

/** Máximo permitido por GET /revision-manual/prestamos (backend le=100). */
const PRESTAMOS_POR_CEDULA_PARA_MULTI_CREDITO = 100

const STORAGE_KEY = 'revision-manual-state'

function normalizarCedulaRevisionLista(c: string): string {
  return String(c ?? '')
    .trim()
    .replace(/-/g, '')
    .toUpperCase()
}

function etiquetaEstadoRevisionManual(estado: string): string {
  const e = (estado ?? '').trim().toLowerCase()
  if (e === 'revisado') return 'Revisado'
  if (e === 'revisando') return 'En revisión'
  if (e === 'pendiente') return 'Pendiente'
  if (e === 'en_espera') return 'En espera'
  if (e === 'rechazado') return 'Rechazado'
  return estado || '-'
}

function getStoredState(): {
  page: number
  filtro: 'todos' | 'pendientes' | 'revisados' | 'revisando'
  cedulaBuscar: string
} {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)

    if (!raw) return { page: 1, filtro: 'todos', cedulaBuscar: '' }

    const parsed = JSON.parse(raw)

    const filtros: Array<'todos' | 'pendientes' | 'revisados' | 'revisando'> = [
      'todos',
      'pendientes',
      'revisados',
      'revisando',
    ]

    return {
      page: Math.max(1, Number(parsed.page) || 1),

      filtro: filtros.includes(parsed.filtro) ? parsed.filtro : 'todos',

      cedulaBuscar:
        typeof parsed.cedulaBuscar === 'string' ? parsed.cedulaBuscar : '',
    }
  } catch {
    return { page: 1, filtro: 'todos', cedulaBuscar: '' }
  }
}

export function RevisionManual() {
  const stored = getStoredState()

  const [filtro, setFiltro] = useState<
    'todos' | 'pendientes' | 'revisados' | 'revisando'
  >(stored.filtro)

  const [page, setPage] = useState(stored.page)

  const [cedulaBuscar, setCedulaBuscar] = useState(stored.cedulaBuscar)

  const [cedulaInput, setCedulaInput] = useState(stored.cedulaBuscar) // valor del input (para debounce o submit)

  const [prestamosOcultos, setPrestamosOcultos] = useState<Set<number>>(
    new Set()
  )

  const [elegirCreditoOpen, setElegirCreditoOpen] = useState(false)

  const [elegirCreditoPayload, setElegirCreditoPayload] = useState<{
    cedula: string
    nombres: string
    opciones: PrestamoRevision[]
    sugeridoId: number
  } | null>(null)

  const [resolviendoMultiCredito, setResolviendoMultiCredito] = useState(false)

  const timeoutsRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(
    new Map()
  )

  const queryClient = useQueryClient()

  const navigate = useNavigate()

  const location = useLocation()

  const [searchParams, setSearchParams] = useSearchParams()

  // ID del préstamo a resaltar (viene de ?prestamo_id=X al navegar desde Lista de Préstamos)
  const highlightPrestamoId = (() => {
    const raw = searchParams.get('prestamo_id')
    if (!raw) return null
    const n = parseInt(raw, 10)
    return isNaN(n) ? null : n
  })()

  const highlightRowRef = useRef<HTMLTableRowElement | null>(null)

  // Scroll automático a la fila resaltada cuando carga la lista
  useEffect(() => {
    if (highlightRowRef.current) {
      highlightRowRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      })
    }
  })

  // Al volver tras finalizar (Guardar y Cerrar), mostrar "Todos" para que el préstamo finalizado sea visible

  useEffect(() => {
    const state = location.state as { fromFinalize?: boolean } | null

    if (state?.fromFinalize) {
      setFiltro('todos')

      setPage(1)

      navigate(location.pathname, { replace: true, state: {} })
    }
  }, [location.state, location.pathname, navigate])

  // Persistir estado para mantener posición al volver de editar (Guardar y cerrar)

  useEffect(() => {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ page, filtro, cedulaBuscar })
    )
  }, [page, filtro, cedulaBuscar])

  // Limpiar timeouts al desmontar

  useEffect(() => {
    return () => {
      timeoutsRef.current.forEach(t => clearTimeout(t))

      timeoutsRef.current.clear()
    }
  }, [])

  const programarOcultarEn30s = (prestamoId: number) => {
    const existing = timeoutsRef.current.get(prestamoId)

    if (existing) clearTimeout(existing)

    const t = setTimeout(() => {
      setPrestamosOcultos(prev => new Set([...prev, prestamoId]))

      timeoutsRef.current.delete(prestamoId)
    }, 30000)

    timeoutsRef.current.set(prestamoId, t)
  }

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['revision-manual-prestamos', filtro, page, cedulaBuscar],

    queryFn: () =>
      revisionManualService.getPrestamosRevision(
        filtro,
        page,
        PER_PAGE,
        cedulaBuscar || undefined
      ),

    staleTime: 15 * 1000,

    refetchOnWindowFocus: true,
  })

  const handleConfirmarSi = async (prestamoId: number, nombres: string) => {
    const confirmar = window.confirm(
      `⚠️ CONFIRMAR REVISIÓN - ${nombres}\n\n` +
        '✓ Se marcarán TODOS los datos como correctos:\n' +
        '  - Datos del cliente\n' +
        '  - Datos del préstamo\n' +
        '  - Cuotas y pagos\n\n' +
        '✓ El préstamo desaparecerá de esta lista\n' +
        '✓ NO PODRÁS EDITAR ESTE PRÉSTAMO DE NUEVO\n\n' +
        '¿Confirmas que todo está correcto?'
    )

    if (!confirmar) {
      toast.info('ℹ️ Confirmación cancelada')

      return
    }

    try {
      const res =
        await revisionManualService.confirmarPrestamoRevisado(prestamoId)

      toast.success(`✅ ${res.mensaje}`)

      queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })
      void invalidateListasNotificacionesMora(queryClient)

      programarOcultarEn30s(prestamoId)
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || 'Error al confirmar'

      toast.error(`❌ ${errorMsg}`)

      console.error('Error confirmando:', err)
    }
  }

  const confirmarYIniciarRevision = async (
    prestamoId: number,
    nombres: string
  ) => {
    const confirmar = window.confirm(
      '⚠️ INICIAR EDICIÓN\n\n' +
        `Crédito seleccionado: préstamo #${prestamoId} - ${nombres}\n\n` +
        'Accederás a la interfaz de edición donde podrás:\n' +
        '✓ Editar datos del cliente\n' +
        '✓ Editar datos del préstamo\n' +
        '✓ Editar cuotas y pagos\n\n' +
        '✓ Puedes guardar cambios parciales (Guardar cambios)\n' +
        '✓ O finalizar la revisión (Guardar y Cerrar)\n\n' +
        '¿Deseas continuar?'
    )

    if (!confirmar) {
      toast.info('ℹ️ Edición cancelada')

      return
    }

    try {
      await revisionManualService.iniciarRevision(prestamoId)

      toast.info('ℹ️ Edición iniciada. Abriendo editor...')

      queryClient.invalidateQueries({
        queryKey: ['revision-manual-prestamos'],
      })
      void invalidateListasNotificacionesMora(queryClient)

      navigate(`/revision-manual/editar/${prestamoId}`)
    } catch (err: any) {
      const errorMsg =
        err?.response?.data?.detail || 'Error al iniciar revisión'

      toast.error(`❌ ${errorMsg}`)

      console.error('Error iniciando revisión:', err)
    }
  }

  const handleEditarNo = async (prestamoId: number) => {
    if (resolviendoMultiCredito) return

    const visibles = (data?.prestamos ?? []).filter(
      p => !prestamosOcultos.has(p.prestamo_id)
    )

    const fila = visibles.find(p => p.prestamo_id === prestamoId)
    const cedulaRaw = (fila?.cedula ?? '').trim()
    const nombresFila = fila?.nombres ?? ''

    if (!cedulaRaw) {
      await confirmarYIniciarRevision(prestamoId, nombresFila || 'Cliente')

      return
    }

    setResolviendoMultiCredito(true)

    try {
      const res = await revisionManualService.getPrestamosRevision(
        'todos',
        1,
        PRESTAMOS_POR_CEDULA_PARA_MULTI_CREDITO,
        cedulaRaw
      )

      const norm = normalizarCedulaRevisionLista(cedulaRaw)
      const mapa = new Map<number, PrestamoRevision>()

      for (const p of res.prestamos ?? []) {
        if (normalizarCedulaRevisionLista(p.cedula) === norm) {
          mapa.set(p.prestamo_id, p)
        }
      }

      const misma = [...mapa.values()].sort(
        (a, b) => a.prestamo_id - b.prestamo_id
      )

      if (misma.length === 0) {
        await confirmarYIniciarRevision(prestamoId, nombresFila || 'Cliente')

        return
      }

      if (misma.length === 1) {
        const unico = misma[0]
        await confirmarYIniciarRevision(
          unico.prestamo_id,
          unico.nombres || nombresFila || 'Cliente'
        )

        return
      }

      setElegirCreditoPayload({
        cedula: cedulaRaw,
        nombres: nombresFila || misma[0]?.nombres || 'Cliente',
        opciones: misma,
        sugeridoId: prestamoId,
      })
      setElegirCreditoOpen(true)
    } catch (e) {
      console.error('Error comprobando créditos por cédula:', e)
      toast.error(
        'No se pudo verificar si hay varios créditos. Se continúa con la fila seleccionada.'
      )
      await confirmarYIniciarRevision(prestamoId, nombresFila || 'Cliente')
    } finally {
      setResolviendoMultiCredito(false)
    }
  }

  const handleEliminar = async (prestamoId: number, nombres: string) => {
    const confirmar = window.confirm(
      `⚠️ ELIMINAR PRÉSTAMO - ${nombres}\n\n` +
        'Esta acción eliminará permanentemente:\n' +
        '  - El préstamo\n' +
        '  - Todas las cuotas asociadas\n' +
        '  - El registro de revisión manual\n\n' +
        '¿Estás seguro de que deseas eliminar?'
    )

    if (!confirmar) {
      toast.info('ℹ️ Eliminación cancelada')

      return
    }

    try {
      await revisionManualService.eliminarPrestamo(prestamoId)

      toast.success('✅ Préstamo eliminado')

      await invalidatePagosPrestamosRevisionYCuotas(queryClient, {
        skipNotificacionesMora: true,
      })

      queryClient.invalidateQueries({ queryKey: ['clientes'] })

      queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })

      queryClient.invalidateQueries({
        queryKey: ['kpis-principales-menu'],
        exact: false,
      })

      queryClient.invalidateQueries({
        queryKey: ['dashboard-menu'],
        exact: false,
      })

      void invalidateListasNotificacionesMora(queryClient)
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || 'Error al eliminar'

      toast.error(`❌ ${errorMsg}`)

      console.error('Error eliminando:', err)
    }
  }

  const datosVisibles = (data?.prestamos ?? []).filter(
    p => !prestamosOcultos.has(p.prestamo_id)
  )

  const totalPrestamos = data?.total_prestamos ?? 0

  const totalPages = Math.ceil(totalPrestamos / PER_PAGE) || 1

  const handleBuscarCedula = () => {
    setCedulaBuscar(cedulaInput.trim())

    setPage(1)
  }

  const handleLimpiarBusqueda = () => {
    setCedulaInput('')

    setCedulaBuscar('')

    setPage(1)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6 p-4 sm:p-6"
    >
      {/* Header */}

      <ModulePageHeader
        icon={FileText}
        title="Revisión Manual de Préstamos"
        description="Verifica y confirma los detalles de cada préstamo post-migración"
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              refetch()

              toast.info('Actualizando...')
            }}
            disabled={isLoading}
          >
            <RefreshCw
              className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`}
            />
            Actualizar
          </Button>
        }
      />

      {/* Barra de Progreso */}

      {data && (
        <Card className="border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Progreso de Revisión</CardTitle>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-700">
                  {data.prestamos_revisados} de {data.total_prestamos} préstamos
                  revisados
                </p>

                <p className="mt-1 text-xs text-gray-500">
                  Faltan: {data.prestamos_pendientes} préstamos por revisar
                </p>
              </div>

              <div className="text-3xl font-bold text-blue-600">
                {data.porcentaje_completado}%
              </div>
            </div>

            {/* Barra gráfica */}

            <div className="h-3 w-full overflow-hidden rounded-full bg-gray-200">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${data.porcentaje_completado}%` }}
                transition={{ duration: 0.5 }}
                className="h-full bg-gradient-to-r from-blue-500 to-indigo-600"
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filtros */}

      <div className="flex flex-wrap gap-2">
        <Button
          variant={filtro === 'todos' ? 'default' : 'outline'}
          size="sm"
          onClick={() => {
            setFiltro('todos')
            setPage(1)
          }}
        >
          Todos
        </Button>

        <Button
          variant={filtro === 'pendientes' ? 'default' : 'outline'}
          size="sm"
          onClick={() => {
            setFiltro('pendientes')
            setPage(1)
          }}
        >
          Pendientes ({data?.prestamos_pendientes || 0})
        </Button>

        <Button
          variant={filtro === 'revisando' ? 'default' : 'outline'}
          size="sm"
          onClick={() => {
            setFiltro('revisando')
            setPage(1)
          }}
        >
          🔄 Revisando
        </Button>

        <Button
          variant={filtro === 'revisados' ? 'default' : 'outline'}
          size="sm"
          onClick={() => {
            setFiltro('revisados')
            setPage(1)
          }}
        >
          ✓ Revisados ({data?.prestamos_revisados || 0})
        </Button>
      </div>

      {/* Búsqueda por cédula */}

      <Card className="border-blue-100 bg-blue-50/30">
        <CardContent className="pt-4">
          <div className="flex flex-col gap-3 sm:flex-row">
            <div className="flex flex-1 gap-2">
              <Search className="h-4 w-4 shrink-0 self-center text-gray-500" />

              <Input
                placeholder="Buscar por cédula para acceder a un caso específico..."
                value={cedulaInput}
                onChange={e => setCedulaInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleBuscarCedula()}
                className="max-w-md"
              />

              <Button
                size="sm"
                onClick={handleBuscarCedula}
                disabled={isLoading}
              >
                Buscar
              </Button>

              {cedulaBuscar && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handleLimpiarBusqueda}
                >
                  Limpiar
                </Button>
              )}
            </div>

            {cedulaBuscar && (
              <span className="self-center text-sm text-gray-600">
                Mostrando resultados para cédula:{' '}
                <strong>{cedulaBuscar}</strong>
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Tabla de Préstamos */}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5" />
            Lista de Préstamos
          </CardTitle>
        </CardHeader>

        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          ) : error ? (
            <div className="py-8 text-center text-red-600">
              <p>Error al cargar préstamos</p>
            </div>
          ) : datosVisibles.length === 0 ? (
            <div className="py-8 text-center text-gray-500">
              <p>No hay préstamos para mostrar</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left font-semibold">
                      Nombre
                    </th>

                    <th className="px-4 py-2 text-left font-semibold">
                      Cédula
                    </th>

                    <th className="px-4 py-2 text-right font-semibold">
                      Total Préstamo
                    </th>

                    <th className="px-4 py-2 text-right font-semibold">
                      Total Abonos
                    </th>

                    <th className="px-4 py-2 text-right font-semibold">
                      Saldo
                    </th>

                    <th
                      className="px-4 py-2 text-center font-semibold"
                      title="Pagadas / total de cuotas (misma regla que el detalle de amortización)"
                    >
                      Pagadas
                    </th>

                    <th className="px-4 py-2 text-center font-semibold">
                      Vencidas
                    </th>

                    <th className="px-4 py-2 text-center font-semibold">
                      Morosas
                    </th>

                    <th className="px-4 py-2 text-center font-semibold">
                      Estado
                    </th>

                    <th className="px-4 py-2 text-center font-semibold">
                      Acción
                    </th>

                    <th className="px-4 py-2 text-center font-semibold">
                      Decisión
                    </th>
                  </tr>
                </thead>

                <tbody className="divide-y">
                  {datosVisibles.map(prestamo => {
                    const isHighlighted =
                      highlightPrestamoId === prestamo.prestamo_id
                    return (
                      <motion.tr
                        key={prestamo.prestamo_id}
                        ref={isHighlighted ? highlightRowRef : undefined}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className={`transition ${isHighlighted ? 'bg-blue-50 ring-2 ring-inset ring-blue-400' : 'hover:bg-gray-50'}`}
                      >
                        <td className="px-4 py-3 font-medium">
                          {prestamo.nombres}
                        </td>

                        <td className="px-4 py-3 text-gray-600">
                          {prestamo.cedula}
                        </td>

                        <td className="px-4 py-3 text-right font-semibold">
                          $
                          {prestamo.total_prestamo.toLocaleString('es-ES', {
                            maximumFractionDigits: 2,
                          })}
                        </td>

                        <td className="px-4 py-3 text-right font-semibold text-green-600">
                          $
                          {prestamo.total_abonos.toLocaleString('es-ES', {
                            maximumFractionDigits: 2,
                          })}
                        </td>

                        <td className="px-4 py-3 text-right font-semibold text-orange-600">
                          $
                          {prestamo.saldo.toLocaleString('es-ES', {
                            maximumFractionDigits: 2,
                          })}
                        </td>

                        <td className="px-4 py-3 text-center text-gray-700">
                          {prestamo.cuotas_pagadas != null &&
                          prestamo.cuotas_total != null ? (
                            <span className="rounded bg-slate-100 px-2 py-1 text-xs font-semibold tabular-nums">
                              {prestamo.cuotas_pagadas} /{' '}
                              {prestamo.cuotas_total}
                            </span>
                          ) : (
                            <span className="text-xs text-gray-400">-</span>
                          )}
                        </td>

                        <td className="px-4 py-3 text-center">
                          <span
                            className={`rounded px-2 py-1 text-xs font-semibold ${prestamo.cuotas_vencidas > 0 ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100'}`}
                          >
                            {prestamo.cuotas_vencidas}
                          </span>
                        </td>

                        <td className="px-4 py-3 text-center">
                          <span
                            className={`rounded px-2 py-1 text-xs font-semibold ${prestamo.cuotas_morosas > 0 ? 'bg-red-100 text-red-800' : 'bg-gray-100'}`}
                          >
                            {prestamo.cuotas_morosas}
                          </span>
                        </td>

                        <td className="px-4 py-3 text-center">
                          {prestamo.estado_revision === 'revisado' && (
                            <span className="rounded bg-green-100 px-2 py-1 text-xs font-semibold text-green-800">
                              ✓ Revisado
                            </span>
                          )}

                          {prestamo.estado_revision === 'revisando' && (
                            <span className="rounded bg-yellow-100 px-2 py-1 text-xs font-semibold text-yellow-800">
                              🔄 Revisando
                            </span>
                          )}

                          {prestamo.estado_revision === 'pendiente' && (
                            <span className="rounded bg-blue-100 px-2 py-1 text-xs font-semibold text-blue-800">
                              Pendiente
                            </span>
                          )}

                          {prestamo.estado_revision === 'en_espera' && (
                            <span className="rounded bg-red-100 px-2 py-1 text-xs font-semibold text-red-800">
                              ⚠️ En Espera
                            </span>
                          )}
                        </td>

                        <td className="px-4 py-3 text-center">
                          <div className="flex items-center justify-center gap-2">
                            <EstadoRevisionIcon
                              prestamoId={prestamo.prestamo_id}
                              estadoActual={prestamo.estado_revision}
                              nombreCliente={prestamo.nombres}
                              onStateChange={() => {
                                queryClient.invalidateQueries({
                                  queryKey: ['revision-manual-prestamos'],
                                })
                              }}
                            />
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-7 w-7 p-0"
                              onClick={() => {
                                const opciones = `Opciones para ${prestamo.nombres}:\n\n1. Ver historial de cambios\n2. Enviar notificación\n3. Duplicar revisión\n4. Ver detalles completos\n5. Cancelar`
                                window.alert(opciones)
                              }}
                              title="Más opciones"
                            >
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </div>
                        </td>

                        <td className="px-4 py-3 text-center">
                          {prestamo.estado_revision === 'pendiente' && (
                            <div className="flex flex-wrap justify-center gap-2">
                              <Button
                                size="sm"
                                className="h-8 bg-green-600 px-2 text-xs text-white hover:bg-green-700"
                                onClick={() =>
                                  handleConfirmarSi(
                                    prestamo.prestamo_id,
                                    prestamo.nombres
                                  )
                                }
                              >
                                ✓ Sí
                              </Button>

                              <Button
                                size="sm"
                                className="h-8 bg-blue-600 px-2 text-xs text-white hover:bg-blue-700"
                                disabled={resolviendoMultiCredito}
                                onClick={() =>
                                  void handleEditarNo(prestamo.prestamo_id)
                                }
                              >
                                ✎ No
                              </Button>

                              <Button
                                size="sm"
                                variant="outline"
                                className="h-8 border-red-200 px-2 text-xs text-red-600 hover:border-red-300 hover:bg-red-50"
                                onClick={() =>
                                  handleEliminar(
                                    prestamo.prestamo_id,
                                    prestamo.nombres
                                  )
                                }
                              >
                                <Trash2 className="mr-1 h-3 w-3" />
                                Eliminar
                              </Button>
                            </div>
                          )}

                          {prestamo.estado_revision === 'revisando' && (
                            <div className="flex flex-wrap justify-center gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-8 text-xs text-blue-600"
                                onClick={() =>
                                  navigate(
                                    `/revision-manual/editar/${prestamo.prestamo_id}`
                                  )
                                }
                              >
                                <Edit className="mr-1 h-3 w-3" />
                                Continuar
                              </Button>

                              <Button
                                size="sm"
                                className="h-8 bg-blue-600 px-2 text-xs text-white hover:bg-blue-700"
                                disabled={resolviendoMultiCredito}
                                onClick={() =>
                                  void handleEditarNo(prestamo.prestamo_id)
                                }
                                title="Reiniciar edición"
                              >
                                ✎ No
                              </Button>

                              <Button
                                size="sm"
                                variant="outline"
                                className="h-8 border-red-200 text-xs text-red-600 hover:bg-red-50"
                                onClick={() =>
                                  handleEliminar(
                                    prestamo.prestamo_id,
                                    prestamo.nombres
                                  )
                                }
                              >
                                <Trash2 className="mr-1 h-3 w-3" />
                                Eliminar
                              </Button>
                            </div>
                          )}

                          {prestamo.estado_revision === 'revisado' && (
                            <span className="text-xs text-gray-500">
                              Finalizado
                            </span>
                          )}
                        </td>
                      </motion.tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Paginación */}

          {!isLoading && !error && totalPrestamos > 0 && (
            <div className="mt-4 flex flex-col items-center justify-between gap-4 border-t pt-4 sm:flex-row">
              <p className="text-sm text-gray-600">
                Mostrando <strong>{(page - 1) * PER_PAGE + 1}</strong> -{' '}
                <strong>{Math.min(page * PER_PAGE, totalPrestamos)}</strong> de{' '}
                <strong>{totalPrestamos}</strong> préstamos
              </p>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page <= 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                  Anterior
                </Button>

                <span className="px-3 py-1.5 text-sm font-medium text-gray-700">
                  Página {page} de {totalPages}
                </span>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                >
                  Siguiente
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog
        open={elegirCreditoOpen}
        onOpenChange={open => {
          setElegirCreditoOpen(open)

          if (!open) setElegirCreditoPayload(null)
        }}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Varios créditos para la misma cédula</DialogTitle>

            <DialogDescription>
              Esta cédula tiene más de un préstamo en la cola de revisión
              manual. Elija el crédito que va a abrir para no mezclar montos,
              cuotas ni pagos entre operaciones distintas.
            </DialogDescription>

            <div className="mt-3 space-y-2 text-sm text-gray-600">
              {elegirCreditoPayload ? (
                <p className="font-medium text-gray-800">
                  Cédula: {elegirCreditoPayload.cedula}
                  {elegirCreditoPayload.nombres ? (
                    <> · {elegirCreditoPayload.nombres}</>
                  ) : null}
                </p>
              ) : null}

              <p className="text-xs text-amber-800">
                Si hay más de {PRESTAMOS_POR_CEDULA_PARA_MULTI_CREDITO}{' '}
                préstamos para esta cédula, use la búsqueda por cédula y revise
                el listado completo.
              </p>
            </div>
          </DialogHeader>

          <div className="max-h-[min(360px,50vh)] space-y-2 overflow-y-auto pr-1">
            {elegirCreditoPayload?.opciones.map(op => {
              const esSugerido =
                op.prestamo_id === elegirCreditoPayload.sugeridoId

              return (
                <button
                  key={op.prestamo_id}
                  type="button"
                  className={`w-full rounded-lg border p-3 text-left text-sm transition-colors hover:bg-slate-50 ${
                    esSugerido
                      ? 'border-blue-400 bg-blue-50/80 ring-1 ring-blue-200'
                      : 'border-gray-200 bg-white'
                  }`}
                  onClick={() => {
                    const payload = elegirCreditoPayload

                    setElegirCreditoOpen(false)

                    setElegirCreditoPayload(null)

                    void confirmarYIniciarRevision(
                      op.prestamo_id,
                      op.nombres || payload?.nombres || 'Cliente'
                    )
                  }}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold text-gray-900">
                      Préstamo #{op.prestamo_id}
                    </span>

                    {esSugerido ? (
                      <span className="rounded bg-blue-600 px-2 py-0.5 text-xs font-medium text-white">
                        Fila desde la que hizo clic
                      </span>
                    ) : null}
                  </div>

                  <div className="mt-2 grid gap-1 text-xs text-gray-600 sm:grid-cols-2">
                    <span>
                      Total: $
                      {op.total_prestamo.toLocaleString('es-ES', {
                        maximumFractionDigits: 2,
                      })}
                    </span>

                    <span>
                      Saldo: $
                      {op.saldo.toLocaleString('es-ES', {
                        maximumFractionDigits: 2,
                      })}
                    </span>

                    <span>
                      Abonos: $
                      {op.total_abonos.toLocaleString('es-ES', {
                        maximumFractionDigits: 2,
                      })}
                    </span>

                    <span>
                      Revisión:{' '}
                      {etiquetaEstadoRevisionManual(op.estado_revision)}
                    </span>
                  </div>

                  {op.cuotas_pagadas != null && op.cuotas_total != null ? (
                    <p className="mt-1 text-xs text-gray-500">
                      Cuotas pagadas: {op.cuotas_pagadas} / {op.cuotas_total}
                    </p>
                  ) : null}
                </button>
              )
            })}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setElegirCreditoOpen(false)

                setElegirCreditoPayload(null)

                toast.info('ℹ️ Elija un crédito cuando esté listo.')
              }}
            >
              Cancelar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  )
}

export default RevisionManual
