import { useState } from 'react'

import { useParams, useNavigate } from 'react-router-dom'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import { motion } from 'framer-motion'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import { Button } from '../components/ui/button'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select'

import { Loader2, Save, X, ChevronLeft, Check } from 'lucide-react'

import { toast } from 'sonner'

import { revisionManualService } from '../services/revisionManualService'

import { useEstadosCliente } from '../hooks/useEstadosCliente'

import { useConcesionariosActivos } from '../hooks/useConcesionarios'

import { useAnalistasActivos } from '../hooks/useAnalistas'

import { useModelosVehiculosActivos } from '../hooks/useModelosVehiculos'

interface ClienteData {
  cliente_id: number

  nombres: string

  cedula: string

  telefono: string

  email: string

  direccion: string

  ocupacion: string

  estado: string

  fecha_nacimiento: string | null

  notas: string
}

interface PrestamoData {
  prestamo_id: number

  cliente_id?: number

  cedula: string

  nombres: string

  total_financiamiento: number

  numero_cuotas: number

  tasa_interes: number

  producto: string

  observaciones: string

  fecha_requerimiento: string | null

  modalidad_pago: string

  cuota_periodo: number

  fecha_base_calculo: string | null

  fecha_aprobacion: string | null

  estado: string

  concesionario: string

  analista: string

  modelo_vehiculo: string

  valor_activo: number | null

  usuario_proponente: string

  usuario_aprobador: string
}

interface CuotaData {
  cuota_id: number

  numero_cuota: number

  monto: number

  fecha_vencimiento: string | null

  fecha_pago: string | null

  total_pagado: number

  estado: string

  observaciones: string
}

export function EditarRevisionManual() {
  const { prestamoId } = useParams()

  const navigate = useNavigate()

  const queryClient = useQueryClient()

  const [clienteData, setClienteData] = useState<Partial<ClienteData>>({})

  const [prestamoData, setPrestamoData] = useState<Partial<PrestamoData>>({})

  const [cuotasData, setCuotasData] = useState<Partial<CuotaData>[]>([])

  const [guardandoParcial, setGuardandoParcial] = useState(false)

  const [guardandoFinal, setGuardandoFinal] = useState(false)

  const [cambios, setCambios] = useState({
    cliente: false,
    prestamo: false,
    cuotas: false,
  })

  const { isLoading, error } = useQuery({
    queryKey: ['revision-editar', prestamoId],

    queryFn: async () => {
      if (!prestamoId) throw new Error('ID de préstamo requerido')

      const data = await revisionManualService.getDetallePrestamoRevision(
        parseInt(prestamoId)
      )

      setClienteData(data.cliente)

      setPrestamoData(data.prestamo)

      setCuotasData(data.cuotas)

      return data
    },

    enabled: !!prestamoId,
  })

  // Estados de cliente desde BD (tabla estados_cliente)

  const { opciones: opcionesBD } = useEstadosCliente()

  const { data: concesionarios = [] } = useConcesionariosActivos()

  const { data: analistas = [] } = useAnalistasActivos()

  const { data: modelosVehiculos = [] } = useModelosVehiculosActivos()

  const opcionesBase = (
    opcionesBD.length > 0
      ? opcionesBD
      : [
          { valor: 'ACTIVO', etiqueta: 'Activo', orden: 1 },

          { valor: 'INACTIVO', etiqueta: 'Inactivo', orden: 2 },

          { valor: 'FINALIZADO', etiqueta: 'Finalizado', orden: 3 },

          { valor: 'LEGACY', etiqueta: 'Legacy', orden: 4 },
        ]
  ).map(e => ({ value: e.valor, label: e.etiqueta }))

  // Incluir estado actual del cliente si no está en la lista (valor legacy en BD)

  const estadoActual = clienteData.estado

  const opcionesEstado =
    estadoActual && !opcionesBase.some(e => e.value === estadoActual)
      ? [
          { value: estadoActual, label: `${estadoActual} (legacy)` },
          ...opcionesBase,
        ]
      : opcionesBase

  const handleGuardarParciales = async () => {
    if (!prestamoId) return

    // Validar si hay cambios

    if (!cambios.cliente && !cambios.prestamo && !cambios.cuotas) {
      toast.info('ℹ️ No hay cambios para guardar')

      return
    }

    setGuardandoParcial(true)

    try {
      let savedSomething = false

      let errorOccurred = false

      // Solo guardar cliente si hay cambios

      if (cambios.cliente && clienteData.cliente_id) {
        const clienteUpdate: Record<string, any> = {}

        if (clienteData.nombres) clienteUpdate.nombres = clienteData.nombres

        if (clienteData.telefono) clienteUpdate.telefono = clienteData.telefono

        if (clienteData.email) clienteUpdate.email = clienteData.email

        if (clienteData.direccion)
          clienteUpdate.direccion = clienteData.direccion

        if (clienteData.ocupacion)
          clienteUpdate.ocupacion = clienteData.ocupacion

        if (clienteData.estado) clienteUpdate.estado = clienteData.estado

        if (clienteData.fecha_nacimiento !== undefined)
          clienteUpdate.fecha_nacimiento = clienteData.fecha_nacimiento || null

        if (clienteData.notas !== undefined)
          clienteUpdate.notas = clienteData.notas

        if (Object.keys(clienteUpdate).length > 0) {
          try {
            await revisionManualService.editarCliente(
              clienteData.cliente_id,
              clienteUpdate
            )

            savedSomething = true
          } catch (err: any) {
            errorOccurred = true

            const errorMsg =
              err?.response?.data?.detail || 'Error al guardar cliente'

            toast.error(`❌ Error en cliente: ${errorMsg}`)

            console.error('Error guardando cliente:', err)
          }
        }
      }

      // Solo guardar préstamo si hay cambios

      if (cambios.prestamo && prestamoData.prestamo_id) {
        const prestamoUpdate: Record<string, any> = {}

        if (
          prestamoData.total_financiamiento !== undefined &&
          prestamoData.total_financiamiento >= 0
        )
          prestamoUpdate.total_financiamiento =
            prestamoData.total_financiamiento

        if (
          prestamoData.numero_cuotas !== undefined &&
          prestamoData.numero_cuotas >= 1
        )
          prestamoUpdate.numero_cuotas = prestamoData.numero_cuotas

        if (
          prestamoData.tasa_interes !== undefined &&
          prestamoData.tasa_interes >= 0
        )
          prestamoUpdate.tasa_interes = prestamoData.tasa_interes

        if (prestamoData.producto !== undefined)
          prestamoUpdate.producto = prestamoData.producto

        if (prestamoData.observaciones !== undefined)
          prestamoUpdate.observaciones = prestamoData.observaciones

        if (prestamoData.cedula !== undefined)
          prestamoUpdate.cedula = prestamoData.cedula

        if (prestamoData.nombres !== undefined)
          prestamoUpdate.nombres = prestamoData.nombres

        if (prestamoData.fecha_requerimiento !== undefined)
          prestamoUpdate.fecha_requerimiento =
            prestamoData.fecha_requerimiento || null

        if (prestamoData.modalidad_pago !== undefined)
          prestamoUpdate.modalidad_pago = prestamoData.modalidad_pago

        if (
          prestamoData.cuota_periodo !== undefined &&
          prestamoData.cuota_periodo >= 0
        )
          prestamoUpdate.cuota_periodo = prestamoData.cuota_periodo

        if (prestamoData.fecha_base_calculo !== undefined)
          prestamoUpdate.fecha_base_calculo =
            prestamoData.fecha_base_calculo || null

        if (prestamoData.fecha_aprobacion !== undefined)
          prestamoUpdate.fecha_aprobacion =
            prestamoData.fecha_aprobacion || null

        if (prestamoData.estado !== undefined)
          prestamoUpdate.estado = prestamoData.estado

        if (prestamoData.concesionario !== undefined)
          prestamoUpdate.concesionario = prestamoData.concesionario

        if (prestamoData.analista !== undefined)
          prestamoUpdate.analista = prestamoData.analista

        if (prestamoData.modelo_vehiculo !== undefined)
          prestamoUpdate.modelo_vehiculo = prestamoData.modelo_vehiculo

        if (
          prestamoData.valor_activo !== undefined &&
          prestamoData.valor_activo !== null
        )
          prestamoUpdate.valor_activo = prestamoData.valor_activo

        if (prestamoData.usuario_proponente !== undefined)
          prestamoUpdate.usuario_proponente = prestamoData.usuario_proponente

        if (prestamoData.usuario_aprobador !== undefined)
          prestamoUpdate.usuario_aprobador = prestamoData.usuario_aprobador

        if (Object.keys(prestamoUpdate).length > 0) {
          try {
            await revisionManualService.editarPrestamo(
              prestamoData.prestamo_id,
              prestamoUpdate
            )

            savedSomething = true
          } catch (err: any) {
            errorOccurred = true

            const errorMsg =
              err?.response?.data?.detail || 'Error al guardar préstamo'

            toast.error(`❌ Error en préstamo: ${errorMsg}`)

            console.error('Error guardando préstamo:', err)
          }
        }
      }

      // Guardar cuotas si hay cambios

      if (cambios.cuotas) {
        for (const cuota of cuotasData) {
          if (cuota.cuota_id) {
            const cuotaUpdate: Record<string, any> = {}

            if (cuota.fecha_pago)
              cuotaUpdate.fecha_pago = cuota.fecha_pago.split('T')[0]

            if (cuota.fecha_vencimiento)
              cuotaUpdate.fecha_vencimiento =
                cuota.fecha_vencimiento.split('T')[0]

            if (cuota.monto !== undefined && cuota.monto >= 0)
              cuotaUpdate.monto = cuota.monto

            if (cuota.total_pagado !== undefined && cuota.total_pagado >= 0)
              cuotaUpdate.total_pagado = cuota.total_pagado

            if (cuota.estado) cuotaUpdate.estado = cuota.estado

            if (cuota.observaciones !== undefined)
              cuotaUpdate.observaciones = cuota.observaciones

            if (Object.keys(cuotaUpdate).length > 0) {
              try {
                await revisionManualService.editarCuota(
                  cuota.cuota_id,
                  cuotaUpdate
                )

                savedSomething = true
              } catch (err: any) {
                errorOccurred = true

                const errorMsg =
                  err?.response?.data?.detail || 'Error al guardar cuota'

                toast.error(
                  `❌ Error en cuota #${cuota.numero_cuota}: ${errorMsg}`
                )

                console.error(
                  `Error guardando cuota ${cuota.numero_cuota}:`,
                  err
                )
              }
            }
          }
        }
      }

      if (!errorOccurred && savedSomething) {
        toast.success('✅ Cambios parciales guardados en BD')

        setCambios({ cliente: false, prestamo: false, cuotas: false })

        // Invalidar todas las vistas que muestran datos de préstamos, clientes y cuotas

        queryClient.invalidateQueries({
          queryKey: ['revision-manual-prestamos'],
        })

        queryClient.invalidateQueries({ queryKey: ['prestamos'] })

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
      } else if (errorOccurred) {
        toast.warning(
          '⚠️ Algunos cambios no se guardaron. Revisa los errores arriba'
        )
      }
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || 'Error desconocido'

      toast.error(`❌ Error general: ${errorMsg}`)

      console.error('Error general guardando:', err)
    } finally {
      setGuardandoParcial(false)
    }
  }

  const handleGuardarYCerrar = async () => {
    if (!prestamoId) return

    const confirmar = window.confirm(
      '⚠️ CONFIRMAR FINALIZACIÓN DE REVISIÓN\n\n' +
        '✓ Se guardarán todos los cambios pendientes\n' +
        '✓ El préstamo se marcará como REVISADO\n' +
        '✓ NO PODRÁS EDITAR ESTE PRÉSTAMO DE NUEVO\n\n' +
        '¿Estás completamente seguro?'
    )

    if (!confirmar) {
      toast.info('ℹ️ Finalización cancelada')

      return
    }

    setGuardandoFinal(true)

    try {
      // Guardar todos los cambios primero

      if (cambios.cliente && clienteData.cliente_id) {
        const clienteUpdate: Record<string, any> = {}

        if (clienteData.nombres) clienteUpdate.nombres = clienteData.nombres

        if (clienteData.telefono) clienteUpdate.telefono = clienteData.telefono

        if (clienteData.email) clienteUpdate.email = clienteData.email

        if (clienteData.direccion)
          clienteUpdate.direccion = clienteData.direccion

        if (clienteData.ocupacion)
          clienteUpdate.ocupacion = clienteData.ocupacion

        if (clienteData.estado) clienteUpdate.estado = clienteData.estado

        if (clienteData.fecha_nacimiento !== undefined)
          clienteUpdate.fecha_nacimiento = clienteData.fecha_nacimiento || null

        if (clienteData.notas !== undefined)
          clienteUpdate.notas = clienteData.notas

        if (Object.keys(clienteUpdate).length > 0) {
          try {
            await revisionManualService.editarCliente(
              clienteData.cliente_id,
              clienteUpdate
            )
          } catch (err: any) {
            throw new Error(
              `Error en cliente: ${err?.response?.data?.detail || 'Error desconocido'}`
            )
          }
        }
      }

      if (cambios.prestamo && prestamoData.prestamo_id) {
        const prestamoUpdate: Record<string, any> = {}

        if (
          prestamoData.total_financiamiento !== undefined &&
          prestamoData.total_financiamiento >= 0
        )
          prestamoUpdate.total_financiamiento =
            prestamoData.total_financiamiento

        if (
          prestamoData.numero_cuotas !== undefined &&
          prestamoData.numero_cuotas >= 1
        )
          prestamoUpdate.numero_cuotas = prestamoData.numero_cuotas

        if (
          prestamoData.tasa_interes !== undefined &&
          prestamoData.tasa_interes >= 0
        )
          prestamoUpdate.tasa_interes = prestamoData.tasa_interes

        if (prestamoData.producto !== undefined)
          prestamoUpdate.producto = prestamoData.producto

        if (prestamoData.observaciones !== undefined)
          prestamoUpdate.observaciones = prestamoData.observaciones

        if (prestamoData.cedula !== undefined)
          prestamoUpdate.cedula = prestamoData.cedula

        if (prestamoData.nombres !== undefined)
          prestamoUpdate.nombres = prestamoData.nombres

        if (prestamoData.fecha_requerimiento !== undefined)
          prestamoUpdate.fecha_requerimiento =
            prestamoData.fecha_requerimiento || null

        if (prestamoData.modalidad_pago !== undefined)
          prestamoUpdate.modalidad_pago = prestamoData.modalidad_pago

        if (
          prestamoData.cuota_periodo !== undefined &&
          prestamoData.cuota_periodo >= 0
        )
          prestamoUpdate.cuota_periodo = prestamoData.cuota_periodo

        if (prestamoData.fecha_base_calculo !== undefined)
          prestamoUpdate.fecha_base_calculo =
            prestamoData.fecha_base_calculo || null

        if (prestamoData.fecha_aprobacion !== undefined)
          prestamoUpdate.fecha_aprobacion =
            prestamoData.fecha_aprobacion || null

        if (prestamoData.estado !== undefined)
          prestamoUpdate.estado = prestamoData.estado

        if (prestamoData.concesionario !== undefined)
          prestamoUpdate.concesionario = prestamoData.concesionario

        if (prestamoData.analista !== undefined)
          prestamoUpdate.analista = prestamoData.analista

        if (prestamoData.modelo_vehiculo !== undefined)
          prestamoUpdate.modelo_vehiculo = prestamoData.modelo_vehiculo

        if (
          prestamoData.valor_activo !== undefined &&
          prestamoData.valor_activo !== null
        )
          prestamoUpdate.valor_activo = prestamoData.valor_activo

        if (prestamoData.usuario_proponente !== undefined)
          prestamoUpdate.usuario_proponente = prestamoData.usuario_proponente

        if (prestamoData.usuario_aprobador !== undefined)
          prestamoUpdate.usuario_aprobador = prestamoData.usuario_aprobador

        if (Object.keys(prestamoUpdate).length > 0) {
          try {
            await revisionManualService.editarPrestamo(
              prestamoData.prestamo_id,
              prestamoUpdate
            )
          } catch (err: any) {
            throw new Error(
              `Error en préstamo: ${err?.response?.data?.detail || 'Error desconocido'}`
            )
          }
        }
      }

      if (cambios.cuotas) {
        for (const cuota of cuotasData) {
          if (cuota.cuota_id) {
            const cuotaUpdate: Record<string, any> = {}

            if (cuota.fecha_pago)
              cuotaUpdate.fecha_pago = cuota.fecha_pago.split('T')[0]

            if (cuota.fecha_vencimiento)
              cuotaUpdate.fecha_vencimiento =
                cuota.fecha_vencimiento.split('T')[0]

            if (cuota.monto !== undefined && cuota.monto >= 0)
              cuotaUpdate.monto = cuota.monto

            if (cuota.total_pagado !== undefined && cuota.total_pagado >= 0)
              cuotaUpdate.total_pagado = cuota.total_pagado

            if (cuota.estado) cuotaUpdate.estado = cuota.estado

            if (cuota.observaciones !== undefined)
              cuotaUpdate.observaciones = cuota.observaciones

            if (Object.keys(cuotaUpdate).length > 0) {
              try {
                await revisionManualService.editarCuota(
                  cuota.cuota_id,
                  cuotaUpdate
                )
              } catch (err: any) {
                throw new Error(
                  `Error en cuota #${cuota.numero_cuota}: ${err?.response?.data?.detail || 'Error desconocido'}`
                )
              }
            }
          }
        }
      }

      // Finalizar revisión

      try {
        const res = await revisionManualService.finalizarRevision(
          parseInt(prestamoId)
        )

        toast.success(res.mensaje)

        // Invalidar todas las vistas para reflejar cambios en tablas originales

        queryClient.invalidateQueries({
          queryKey: ['revision-manual-prestamos'],
        })

        queryClient.invalidateQueries({ queryKey: ['prestamos'] })

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

        // Pequeño delay antes de navegar para que el usuario vea el mensaje

        setTimeout(() => {
          navigate('/revision-manual', { state: { fromFinalize: true } })
        }, 1500)
      } catch (err: any) {
        throw new Error(
          `Error al finalizar: ${err?.response?.data?.detail || 'Error desconocido'}`
        )
      }
    } catch (err: any) {
      const errorMsg = err.message || 'Error al guardar y cerrar'

      toast.error(`❌ ${errorMsg}`)

      console.error('Error finalizando:', err)
    } finally {
      setGuardandoFinal(false)
    }
  }

  const handleCerrar = () => {
    // Si hay cambios sin guardar, advertir

    if (cambios.cliente || cambios.prestamo || cambios.cuotas) {
      const confirmar = window.confirm(
        '⚠️ Tienes cambios sin guardar.\n\n' +
          'Si cierras ahora, se perderán todos los cambios realizados.\n' +
          '¿Estás seguro de que deseas cerrar sin guardar?'
      )

      if (!confirmar) return
    }

    // Invalidar para que al volver se muestren datos actualizados

    queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })

    queryClient.invalidateQueries({ queryKey: ['prestamos'] })

    queryClient.invalidateQueries({ queryKey: ['clientes'] })

    queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })

    navigate('/revision-manual')
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h2 className="mb-2 text-2xl font-bold text-red-600">Error</h2>

          <p className="mb-4 text-gray-600">
            No se pudieron cargar los datos del préstamo
          </p>

          <Button onClick={() => navigate('/revision-manual')}>
            Volver a Revisión Manual
          </Button>
        </div>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6 p-6"
    >
      {/* Header */}

      <div className="sticky top-0 z-10 -mx-6 mb-4 flex items-center justify-between bg-white p-4 shadow-sm">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCerrar}
            className="h-8 w-8 p-0"
            title="Volver sin guardar"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Revisión: {clienteData.nombres}
            </h1>

            <p className="text-sm text-gray-600">
              Edita los detalles del préstamo (cambios parciales permitidos)
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={handleGuardarParciales}
            disabled={guardandoParcial || guardandoFinal}
            className="gap-2"
            title="Guarda los cambios sin finalizar la revisión"
          >
            <Save className="h-4 w-4" />
            Guardar Parciales
          </Button>

          <Button
            className="gap-2 bg-green-600 text-white hover:bg-green-700"
            onClick={handleGuardarYCerrar}
            disabled={guardandoParcial || guardandoFinal}
            title="Guarda todos los cambios y finaliza la revisión"
          >
            {guardandoFinal ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Check className="h-4 w-4" />
            )}
            Guardar y Cerrar
          </Button>
        </div>
      </div>

      {/* Secciones */}

      <div className="grid gap-6">
        {/* Cliente */}

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              👤 Datos del Cliente
            </CardTitle>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="text-sm font-medium">Nombre</label>

                <input
                  type="text"
                  value={clienteData.nombres || ''}
                  onChange={e => {
                    setClienteData({ ...clienteData, nombres: e.target.value })

                    setCambios({ ...cambios, cliente: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                  placeholder="Ingresa nombre"
                />
              </div>

              <div>
                <label className="text-sm font-medium">Cédula</label>

                <input
                  type="text"
                  value={clienteData.cedula || ''}
                  className="mt-1 w-full cursor-not-allowed rounded border bg-gray-100 px-3 py-2"
                  disabled
                />
              </div>

              <div>
                <label className="text-sm font-medium">Teléfono</label>

                <input
                  type="text"
                  value={clienteData.telefono || ''}
                  onChange={e => {
                    setClienteData({ ...clienteData, telefono: e.target.value })

                    setCambios({ ...cambios, cliente: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                  placeholder="Ingresa teléfono"
                />
              </div>

              <div>
                <label className="text-sm font-medium">Email</label>

                <input
                  type="email"
                  value={clienteData.email || ''}
                  onChange={e => {
                    setClienteData({ ...clienteData, email: e.target.value })

                    setCambios({ ...cambios, cliente: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                  placeholder="Ingresa email"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="text-sm font-medium">Dirección</label>

                <textarea
                  value={clienteData.direccion || ''}
                  onChange={e => {
                    setClienteData({
                      ...clienteData,
                      direccion: e.target.value,
                    })

                    setCambios({ ...cambios, cliente: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                  placeholder="Ingresa dirección"
                  rows={2}
                />
              </div>

              <div>
                <label className="text-sm font-medium">Ocupación</label>

                <input
                  type="text"
                  value={clienteData.ocupacion || ''}
                  onChange={e => {
                    setClienteData({
                      ...clienteData,
                      ocupacion: e.target.value,
                    })

                    setCambios({ ...cambios, cliente: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                  placeholder="Ingresa ocupación"
                />
              </div>

              <div>
                <label className="text-sm font-medium">Estado</label>

                <select
                  value={clienteData.estado || ''}
                  onChange={e => {
                    setClienteData({ ...clienteData, estado: e.target.value })

                    setCambios({ ...cambios, cliente: true })
                  }}
                  className="mt-1 w-full rounded border bg-white px-3 py-2"
                >
                  <option value="">Seleccionar estado</option>

                  {opcionesEstado.map(est => (
                    <option key={est.value} value={est.value}>
                      {est.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-sm font-medium">Fecha Nacimiento</label>

                <input
                  type="date"
                  value={clienteData.fecha_nacimiento || ''}
                  onChange={e => {
                    setClienteData({
                      ...clienteData,
                      fecha_nacimiento: e.target.value || null,
                    })

                    setCambios({ ...cambios, cliente: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="text-sm font-medium">Notas</label>

                <textarea
                  value={clienteData.notas || ''}
                  onChange={e => {
                    setClienteData({ ...clienteData, notas: e.target.value })

                    setCambios({ ...cambios, cliente: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                  placeholder="Notas del cliente"
                  rows={2}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Préstamo */}

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              📋 Datos del Préstamo
            </CardTitle>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="text-sm font-medium">
                  Total Financiamiento
                </label>

                <input
                  type="number"
                  step="0.01"
                  value={prestamoData.total_financiamiento || ''}
                  onChange={e => {
                    setPrestamoData({
                      ...prestamoData,
                      total_financiamiento: parseFloat(e.target.value) || 0,
                    })

                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                  placeholder="0.00"
                />
              </div>

              <div>
                <label className="text-sm font-medium">Número de Cuotas</label>

                <input
                  type="number"
                  value={prestamoData.numero_cuotas || ''}
                  onChange={e => {
                    setPrestamoData({
                      ...prestamoData,
                      numero_cuotas: parseInt(e.target.value) || 0,
                    })

                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                  placeholder="0"
                />
              </div>

              <div>
                <label className="text-sm font-medium">
                  Tasa de Interés (%)
                </label>

                <input
                  type="number"
                  step="0.01"
                  value={prestamoData.tasa_interes || ''}
                  onChange={e => {
                    setPrestamoData({
                      ...prestamoData,
                      tasa_interes: parseFloat(e.target.value) || 0,
                    })

                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                  placeholder="0.00"
                />
              </div>

              <div>
                <label className="text-sm font-medium">Producto</label>

                <Select
                  value={prestamoData.producto || '-'}
                  onValueChange={v => {
                    setPrestamoData({
                      ...prestamoData,
                      producto: v === '-' ? '' : v,
                    })

                    setCambios({ ...cambios, prestamo: true })
                  }}
                >
                  <SelectTrigger className="mt-1 w-full">
                    <SelectValue placeholder="-" />
                  </SelectTrigger>

                  <SelectContent>
                    <SelectItem value="-">-</SelectItem>

                    {prestamoData.producto &&
                      !modelosVehiculos.some(
                        (m: any) => m.modelo === prestamoData.producto
                      ) && (
                        <SelectItem value={prestamoData.producto}>
                          {prestamoData.producto}
                        </SelectItem>
                      )}

                    {modelosVehiculos.map((m: any) => (
                      <SelectItem key={m.id} value={m.modelo}>
                        {m.modelo}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-sm font-medium">Cédula (préstamo)</label>

                <input
                  type="text"
                  value={prestamoData.cedula || ''}
                  onChange={e => {
                    setPrestamoData({ ...prestamoData, cedula: e.target.value })

                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                  placeholder="Cédula"
                />
              </div>

              <div>
                <label className="text-sm font-medium">
                  Nombres (préstamo)
                </label>

                <input
                  type="text"
                  value={prestamoData.nombres || ''}
                  onChange={e => {
                    setPrestamoData({
                      ...prestamoData,
                      nombres: e.target.value,
                    })

                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                  placeholder="Nombres"
                />
              </div>

              <div>
                <label className="text-sm font-medium">
                  Fecha Requerimiento
                </label>

                <input
                  type="date"
                  value={prestamoData.fecha_requerimiento || ''}
                  onChange={e => {
                    setPrestamoData({
                      ...prestamoData,
                      fecha_requerimiento: e.target.value || null,
                    })

                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                />
              </div>

              <div>
                <label className="text-sm font-medium">Modalidad Pago</label>

                <input
                  type="text"
                  value={prestamoData.modalidad_pago || ''}
                  onChange={e => {
                    setPrestamoData({
                      ...prestamoData,
                      modalidad_pago: e.target.value,
                    })

                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                  placeholder="MENSUAL, QUINCENAL, etc."
                />
              </div>

              <div>
                <label className="text-sm font-medium">Cuota Período</label>

                <input
                  type="number"
                  step="0.01"
                  value={prestamoData.cuota_periodo ?? ''}
                  onChange={e => {
                    setPrestamoData({
                      ...prestamoData,
                      cuota_periodo: parseFloat(e.target.value) || 0,
                    })

                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                  placeholder="0.00"
                />
              </div>

              <div>
                <label className="text-sm font-medium">
                  Fecha Base Cálculo
                </label>

                <input
                  type="date"
                  value={prestamoData.fecha_base_calculo || ''}
                  onChange={e => {
                    setPrestamoData({
                      ...prestamoData,
                      fecha_base_calculo: e.target.value || null,
                    })

                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                />
              </div>

              <div>
                <label className="text-sm font-medium">Fecha Aprobación</label>

                <input
                  type="date"
                  value={prestamoData.fecha_aprobacion || ''}
                  min={prestamoData.fecha_requerimiento || undefined}
                  onChange={e => {
                    setPrestamoData({
                      ...prestamoData,
                      fecha_aprobacion: e.target.value || null,
                    })

                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                  title={
                    prestamoData.fecha_requerimiento
                      ? 'Debe ser igual o posterior a la fecha de requerimiento'
                      : undefined
                  }
                />
              </div>

              <div>
                <label className="text-sm font-medium">Estado Préstamo</label>

                <input
                  type="text"
                  value={prestamoData.estado || ''}
                  onChange={e => {
                    setPrestamoData({ ...prestamoData, estado: e.target.value })

                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                  placeholder="DRAFT, APROBADO, RECHAZADO, etc."
                />
              </div>

              <div>
                <label className="text-sm font-medium">Concesionario</label>

                <Select
                  value={prestamoData.concesionario || '-'}
                  onValueChange={v => {
                    setPrestamoData({
                      ...prestamoData,
                      concesionario: v === '-' ? '' : v,
                    })

                    setCambios({ ...cambios, prestamo: true })
                  }}
                >
                  <SelectTrigger className="mt-1 w-full">
                    <SelectValue placeholder="-" />
                  </SelectTrigger>

                  <SelectContent>
                    <SelectItem value="-">-</SelectItem>

                    {prestamoData.concesionario &&
                      !concesionarios.some(
                        (c: any) => c.nombre === prestamoData.concesionario
                      ) && (
                        <SelectItem value={prestamoData.concesionario}>
                          {prestamoData.concesionario}
                        </SelectItem>
                      )}

                    {concesionarios.map((c: any) => (
                      <SelectItem key={c.id} value={c.nombre}>
                        {c.nombre}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-sm font-medium">Analista</label>

                <Select
                  value={prestamoData.analista || '-'}
                  onValueChange={v => {
                    setPrestamoData({
                      ...prestamoData,
                      analista: v === '-' ? '' : v,
                    })

                    setCambios({ ...cambios, prestamo: true })
                  }}
                >
                  <SelectTrigger className="mt-1 w-full">
                    <SelectValue placeholder="-" />
                  </SelectTrigger>

                  <SelectContent>
                    <SelectItem value="-">-</SelectItem>

                    {prestamoData.analista &&
                      !analistas.some(
                        (a: any) => a.nombre === prestamoData.analista
                      ) && (
                        <SelectItem value={prestamoData.analista}>
                          {prestamoData.analista}
                        </SelectItem>
                      )}

                    {analistas.map((a: any) => (
                      <SelectItem key={a.id} value={a.nombre}>
                        {a.nombre}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-sm font-medium">Modelo Vehículo</label>

                <Select
                  value={prestamoData.modelo_vehiculo || '-'}
                  onValueChange={v => {
                    setPrestamoData({
                      ...prestamoData,
                      modelo_vehiculo: v === '-' ? '' : v,
                    })

                    setCambios({ ...cambios, prestamo: true })
                  }}
                >
                  <SelectTrigger className="mt-1 w-full">
                    <SelectValue placeholder="-" />
                  </SelectTrigger>

                  <SelectContent>
                    <SelectItem value="-">-</SelectItem>

                    {prestamoData.modelo_vehiculo &&
                      !modelosVehiculos.some(
                        (m: any) => m.modelo === prestamoData.modelo_vehiculo
                      ) && (
                        <SelectItem value={prestamoData.modelo_vehiculo}>
                          {prestamoData.modelo_vehiculo}
                        </SelectItem>
                      )}

                    {modelosVehiculos.map((m: any) => (
                      <SelectItem key={m.id} value={m.modelo}>
                        {m.modelo}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-sm font-medium">Valor Activo</label>

                <input
                  type="number"
                  step="0.01"
                  value={prestamoData.valor_activo ?? ''}
                  onChange={e => {
                    const v = e.target.value

                    setPrestamoData({
                      ...prestamoData,
                      valor_activo: v === '' ? null : parseFloat(v) || 0,
                    })

                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                  placeholder="0.00"
                />
              </div>

              <div>
                <label className="text-sm font-medium">
                  Usuario Proponente
                </label>

                <input
                  type="text"
                  value={prestamoData.usuario_proponente || ''}
                  onChange={e => {
                    setPrestamoData({
                      ...prestamoData,
                      usuario_proponente: e.target.value,
                    })

                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                />
              </div>

              <div>
                <label className="text-sm font-medium">Usuario Aprobador</label>

                <input
                  type="text"
                  value={prestamoData.usuario_aprobador || ''}
                  onChange={e => {
                    setPrestamoData({
                      ...prestamoData,
                      usuario_aprobador: e.target.value,
                    })

                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="text-sm font-medium">Observaciones</label>

                <textarea
                  value={prestamoData.observaciones || ''}
                  onChange={e => {
                    setPrestamoData({
                      ...prestamoData,
                      observaciones: e.target.value,
                    })

                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="mt-1 w-full rounded border px-3 py-2"
                  placeholder="Ingresa observaciones"
                  rows={2}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Cuotas */}

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              💳 Cuotas/Pagos
            </CardTitle>
          </CardHeader>

          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left">Cuota</th>

                    <th className="px-4 py-2 text-right">Monto</th>

                    <th className="px-4 py-2 text-left">Vencimiento</th>

                    <th className="px-4 py-2 text-left">Fecha Pago</th>

                    <th className="px-4 py-2 text-right">Pagado</th>

                    <th className="px-4 py-2 text-left">Estado</th>

                    <th className="px-4 py-2 text-left">Observaciones</th>
                  </tr>
                </thead>

                <tbody className="divide-y">
                  {cuotasData.map((cuota, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-4 py-2 font-medium">
                        {cuota.numero_cuota}
                      </td>

                      <td className="px-4 py-2">
                        <input
                          type="number"
                          step="0.01"
                          value={cuota.monto ?? ''}
                          onChange={e => {
                            const newCuotas = [...cuotasData]

                            newCuotas[idx] = {
                              ...cuota,
                              monto: parseFloat(e.target.value) || 0,
                            }

                            setCuotasData(newCuotas)

                            setCambios({ ...cambios, cuotas: true })
                          }}
                          className="w-20 rounded border px-2 py-1 text-right text-sm"
                        />
                      </td>

                      <td className="px-4 py-2">
                        <input
                          type="date"
                          value={
                            cuota.fecha_vencimiento
                              ? cuota.fecha_vencimiento.split('T')[0]
                              : ''
                          }
                          onChange={e => {
                            const newCuotas = [...cuotasData]

                            newCuotas[idx] = {
                              ...cuota,
                              fecha_vencimiento: e.target.value
                                ? `${e.target.value}T00:00:00`
                                : null,
                            }

                            setCuotasData(newCuotas)

                            setCambios({ ...cambios, cuotas: true })
                          }}
                          className="w-full rounded border px-2 py-1 text-sm"
                        />
                      </td>

                      <td className="px-4 py-2">
                        <input
                          type="date"
                          value={
                            cuota.fecha_pago
                              ? cuota.fecha_pago.split('T')[0]
                              : ''
                          }
                          onChange={e => {
                            const newCuotas = [...cuotasData]

                            newCuotas[idx] = {
                              ...cuota,
                              fecha_pago: e.target.value
                                ? `${e.target.value}T00:00:00`
                                : null,
                            }

                            setCuotasData(newCuotas)

                            setCambios({ ...cambios, cuotas: true })
                          }}
                          className="w-full rounded border px-2 py-1 text-sm"
                        />
                      </td>

                      <td className="px-4 py-2">
                        <input
                          type="number"
                          step="0.01"
                          value={cuota.total_pagado || ''}
                          onChange={e => {
                            const newCuotas = [...cuotasData]

                            newCuotas[idx] = {
                              ...cuota,
                              total_pagado: parseFloat(e.target.value) || 0,
                            }

                            setCuotasData(newCuotas)

                            setCambios({ ...cambios, cuotas: true })
                          }}
                          className="w-20 rounded border px-2 py-1 text-sm"
                          placeholder="0.00"
                        />
                      </td>

                      <td className="px-4 py-2">
                        <select
                          value={cuota.estado || 'pendiente'}
                          onChange={e => {
                            const newCuotas = [...cuotasData]

                            newCuotas[idx] = {
                              ...cuota,
                              estado: e.target.value,
                            }

                            setCuotasData(newCuotas)

                            setCambios({ ...cambios, cuotas: true })
                          }}
                          className="rounded border px-2 py-1 text-sm"
                        >
                          <option value="pendiente">Pendiente</option>

                          <option value="pagado">Pagado</option>

                          <option value="conciliado">Conciliado</option>
                        </select>
                      </td>

                      <td className="px-4 py-2">
                        <input
                          type="text"
                          value={cuota.observaciones || ''}
                          onChange={e => {
                            const newCuotas = [...cuotasData]

                            newCuotas[idx] = {
                              ...cuota,
                              observaciones: e.target.value,
                            }

                            setCuotasData(newCuotas)

                            setCambios({ ...cambios, cuotas: true })
                          }}
                          className="w-32 rounded border px-2 py-1 text-sm"
                          placeholder="Obs."
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Botones inferiores sticky */}

      <div className="sticky bottom-6 -mx-6 flex justify-end gap-3 rounded-t-lg bg-white p-4 shadow-lg">
        <Button
          variant="outline"
          onClick={handleCerrar}
          className="gap-2"
          disabled={guardandoParcial || guardandoFinal}
          title="Cierra sin guardar cambios"
        >
          <X className="h-4 w-4" />
          Cerrar sin guardar
        </Button>

        <Button
          className="gap-2 bg-green-600 text-white hover:bg-green-700"
          onClick={handleGuardarYCerrar}
          disabled={guardandoParcial || guardandoFinal}
          title="Guarda todos los cambios y finaliza la revisión"
        >
          {guardandoFinal ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Check className="h-4 w-4" />
          )}
          Guardar y Cerrar
        </Button>
      </div>
    </motion.div>
  )
}

export default EditarRevisionManual
