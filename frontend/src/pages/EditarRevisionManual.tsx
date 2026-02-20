import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Loader2, Save, X, ArrowLeft, Check } from 'lucide-react'
import { toast } from 'sonner'
import { revisionManualService } from '../services/revisionManualService'

interface ClienteData {
  cliente_id: number
  nombres: string
  cedula: string
  telefono: string
  email: string
  direccion: string
  ocupacion: string
}

interface PrestamoData {
  prestamo_id: number
  total_financiamiento: number
  numero_cuotas: number
  tasa_interes: number
  producto: string
  observaciones: string
}

interface CuotaData {
  cuota_id: number
  numero_cuota: number
  monto: number
  fecha_vencimiento: string | null
  fecha_pago: string | null
  total_pagado: number
  estado: string
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
  const [cambios, setCambios] = useState({ cliente: false, prestamo: false, cuotas: false })

  const { isLoading, error } = useQuery({
    queryKey: ['revision-editar', prestamoId],
    queryFn: async () => {
      if (!prestamoId) throw new Error('ID de préstamo requerido')
      const data = await revisionManualService.getDetallePrestamoRevision(parseInt(prestamoId))
      setClienteData(data.cliente)
      setPrestamoData(data.prestamo)
      setCuotasData(data.cuotas)
      return data
    },
    enabled: !!prestamoId,
  })

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
        if (clienteData.direccion) clienteUpdate.direccion = clienteData.direccion
        if (clienteData.ocupacion) clienteUpdate.ocupacion = clienteData.ocupacion
        
        if (Object.keys(clienteUpdate).length > 0) {
          try {
            await revisionManualService.editarCliente(clienteData.cliente_id, clienteUpdate)
            savedSomething = true
          } catch (err: any) {
            errorOccurred = true
            const errorMsg = err?.response?.data?.detail || 'Error al guardar cliente'
            toast.error(`❌ Error en cliente: ${errorMsg}`)
            console.error('Error guardando cliente:', err)
          }
        }
      }

      // Solo guardar préstamo si hay cambios
      if (cambios.prestamo && prestamoData.prestamo_id) {
        const prestamoUpdate: Record<string, any> = {}
        if (prestamoData.total_financiamiento !== undefined && prestamoData.total_financiamiento > 0) {
          prestamoUpdate.total_financiamiento = prestamoData.total_financiamiento
        }
        if (prestamoData.numero_cuotas !== undefined && prestamoData.numero_cuotas > 0) {
          prestamoUpdate.numero_cuotas = prestamoData.numero_cuotas
        }
        if (prestamoData.tasa_interes !== undefined && prestamoData.tasa_interes >= 0) {
          prestamoUpdate.tasa_interes = prestamoData.tasa_interes
        }
        if (prestamoData.producto) prestamoUpdate.producto = prestamoData.producto
        if (prestamoData.observaciones) prestamoUpdate.observaciones = prestamoData.observaciones
        
        if (Object.keys(prestamoUpdate).length > 0) {
          try {
            await revisionManualService.editarPrestamo(prestamoData.prestamo_id, prestamoUpdate)
            savedSomething = true
          } catch (err: any) {
            errorOccurred = true
            const errorMsg = err?.response?.data?.detail || 'Error al guardar préstamo'
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
            if (cuota.fecha_pago) cuotaUpdate.fecha_pago = cuota.fecha_pago.split('T')[0]
            if (cuota.total_pagado !== undefined && cuota.total_pagado >= 0) {
              cuotaUpdate.total_pagado = cuota.total_pagado
            }
            if (cuota.estado) cuotaUpdate.estado = cuota.estado
            
            if (Object.keys(cuotaUpdate).length > 0) {
              try {
                await revisionManualService.editarCuota(cuota.cuota_id, cuotaUpdate)
                savedSomething = true
              } catch (err: any) {
                errorOccurred = true
                const errorMsg = err?.response?.data?.detail || 'Error al guardar cuota'
                toast.error(`❌ Error en cuota #${cuota.numero_cuota}: ${errorMsg}`)
                console.error(`Error guardando cuota ${cuota.numero_cuota}:`, err)
              }
            }
          }
        }
      }

      if (!errorOccurred && savedSomething) {
        toast.success('✅ Cambios parciales guardados en BD')
        setCambios({ cliente: false, prestamo: false, cuotas: false })
      } else if (errorOccurred) {
        toast.warning('⚠️ Algunos cambios no se guardaron. Revisa los errores arriba')
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
        if (clienteData.direccion) clienteUpdate.direccion = clienteData.direccion
        if (clienteData.ocupacion) clienteUpdate.ocupacion = clienteData.ocupacion
        
        if (Object.keys(clienteUpdate).length > 0) {
          try {
            await revisionManualService.editarCliente(clienteData.cliente_id, clienteUpdate)
          } catch (err: any) {
            throw new Error(`Error en cliente: ${err?.response?.data?.detail || 'Error desconocido'}`)
          }
        }
      }

      if (cambios.prestamo && prestamoData.prestamo_id) {
        const prestamoUpdate: Record<string, any> = {}
        if (prestamoData.total_financiamiento !== undefined && prestamoData.total_financiamiento > 0) {
          prestamoUpdate.total_financiamiento = prestamoData.total_financiamiento
        }
        if (prestamoData.numero_cuotas !== undefined && prestamoData.numero_cuotas > 0) {
          prestamoUpdate.numero_cuotas = prestamoData.numero_cuotas
        }
        if (prestamoData.tasa_interes !== undefined && prestamoData.tasa_interes >= 0) {
          prestamoUpdate.tasa_interes = prestamoData.tasa_interes
        }
        if (prestamoData.producto) prestamoUpdate.producto = prestamoData.producto
        if (prestamoData.observaciones) prestamoUpdate.observaciones = prestamoData.observaciones
        
        if (Object.keys(prestamoUpdate).length > 0) {
          try {
            await revisionManualService.editarPrestamo(prestamoData.prestamo_id, prestamoUpdate)
          } catch (err: any) {
            throw new Error(`Error en préstamo: ${err?.response?.data?.detail || 'Error desconocido'}`)
          }
        }
      }

      if (cambios.cuotas) {
        for (const cuota of cuotasData) {
          if (cuota.cuota_id) {
            const cuotaUpdate: Record<string, any> = {}
            if (cuota.fecha_pago) cuotaUpdate.fecha_pago = cuota.fecha_pago.split('T')[0]
            if (cuota.total_pagado !== undefined && cuota.total_pagado >= 0) {
              cuotaUpdate.total_pagado = cuota.total_pagado
            }
            if (cuota.estado) cuotaUpdate.estado = cuota.estado
            
            if (Object.keys(cuotaUpdate).length > 0) {
              try {
                await revisionManualService.editarCuota(cuota.cuota_id, cuotaUpdate)
              } catch (err: any) {
                throw new Error(`Error en cuota #${cuota.numero_cuota}: ${err?.response?.data?.detail || 'Error desconocido'}`)
              }
            }
          }
        }
      }

      // Finalizar revisión
      try {
        const res = await revisionManualService.finalizarRevision(parseInt(prestamoId))
        toast.success(res.mensaje)
        queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })

        // Pequeño delay antes de navegar para que el usuario vea el mensaje
        setTimeout(() => {
          navigate('/prestamos')
        }, 1500)
      } catch (err: any) {
        throw new Error(`Error al finalizar: ${err?.response?.data?.detail || 'Error desconocido'}`)
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
    navigate('/prestamos')
  }

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-red-600 mb-2">Error</h2>
          <p className="text-gray-600 mb-4">No se pudieron cargar los datos del préstamo</p>
          <Button onClick={() => navigate('/prestamos')}>Volver a Préstamos</Button>
        </div>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between sticky top-0 z-10 bg-white p-4 -mx-6 mb-4 shadow-sm">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCerrar}
            className="h-8 w-8 p-0"
            title="Volver sin guardar"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Revisión: {clienteData.nombres}
            </h1>
            <p className="text-sm text-gray-600">Edita los detalles del préstamo (cambios parciales permitidos)</p>
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
            className="bg-green-600 hover:bg-green-700 text-white gap-2"
            onClick={handleGuardarYCerrar}
            disabled={guardandoParcial || guardandoFinal}
            title="Guarda todos los cambios y finaliza la revisión"
          >
            {guardandoFinal ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
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
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Nombre</label>
                <input
                  type="text"
                  value={clienteData.nombres || ''}
                  onChange={(e) => {
                    setClienteData({ ...clienteData, nombres: e.target.value })
                    setCambios({ ...cambios, cliente: true })
                  }}
                  className="w-full border rounded px-3 py-2 mt-1"
                  placeholder="Ingresa nombre"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Cédula</label>
                <input
                  type="text"
                  value={clienteData.cedula || ''}
                  className="w-full border rounded px-3 py-2 mt-1 bg-gray-100 cursor-not-allowed"
                  disabled
                />
              </div>
              <div>
                <label className="text-sm font-medium">Teléfono</label>
                <input
                  type="text"
                  value={clienteData.telefono || ''}
                  onChange={(e) => {
                    setClienteData({ ...clienteData, telefono: e.target.value })
                    setCambios({ ...cambios, cliente: true })
                  }}
                  className="w-full border rounded px-3 py-2 mt-1"
                  placeholder="Ingresa teléfono"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Email</label>
                <input
                  type="email"
                  value={clienteData.email || ''}
                  onChange={(e) => {
                    setClienteData({ ...clienteData, email: e.target.value })
                    setCambios({ ...cambios, cliente: true })
                  }}
                  className="w-full border rounded px-3 py-2 mt-1"
                  placeholder="Ingresa email"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-sm font-medium">Dirección</label>
                <textarea
                  value={clienteData.direccion || ''}
                  onChange={(e) => {
                    setClienteData({ ...clienteData, direccion: e.target.value })
                    setCambios({ ...cambios, cliente: true })
                  }}
                  className="w-full border rounded px-3 py-2 mt-1"
                  placeholder="Ingresa dirección"
                  rows={2}
                />
              </div>
              <div>
                <label className="text-sm font-medium">Ocupación</label>
                <input
                  type="text"
                  value={clienteData.ocupacion || ''}
                  onChange={(e) => {
                    setClienteData({ ...clienteData, ocupacion: e.target.value })
                    setCambios({ ...cambios, cliente: true })
                  }}
                  className="w-full border rounded px-3 py-2 mt-1"
                  placeholder="Ingresa ocupación"
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
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Total Financiamiento</label>
                <input
                  type="number"
                  step="0.01"
                  value={prestamoData.total_financiamiento || ''}
                  onChange={(e) => {
                    setPrestamoData({ ...prestamoData, total_financiamiento: parseFloat(e.target.value) || 0 })
                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="w-full border rounded px-3 py-2 mt-1"
                  placeholder="0.00"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Número de Cuotas</label>
                <input
                  type="number"
                  value={prestamoData.numero_cuotas || ''}
                  onChange={(e) => {
                    setPrestamoData({ ...prestamoData, numero_cuotas: parseInt(e.target.value) || 0 })
                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="w-full border rounded px-3 py-2 mt-1"
                  placeholder="0"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Tasa de Interés (%)</label>
                <input
                  type="number"
                  step="0.01"
                  value={prestamoData.tasa_interes || ''}
                  onChange={(e) => {
                    setPrestamoData({ ...prestamoData, tasa_interes: parseFloat(e.target.value) || 0 })
                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="w-full border rounded px-3 py-2 mt-1"
                  placeholder="0.00"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Producto</label>
                <input
                  type="text"
                  value={prestamoData.producto || ''}
                  onChange={(e) => {
                    setPrestamoData({ ...prestamoData, producto: e.target.value })
                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="w-full border rounded px-3 py-2 mt-1"
                  placeholder="Ingresa producto"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-sm font-medium">Observaciones</label>
                <textarea
                  value={prestamoData.observaciones || ''}
                  onChange={(e) => {
                    setPrestamoData({ ...prestamoData, observaciones: e.target.value })
                    setCambios({ ...cambios, prestamo: true })
                  }}
                  className="w-full border rounded px-3 py-2 mt-1"
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
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {cuotasData.map((cuota, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-4 py-2 font-medium">{cuota.numero_cuota}</td>
                      <td className="px-4 py-2 text-right font-mono">${cuota.monto?.toFixed(2)}</td>
                      <td className="px-4 py-2 text-sm">
                        {cuota.fecha_vencimiento ? new Date(cuota.fecha_vencimiento).toLocaleDateString('es-ES') : 'N/A'}
                      </td>
                      <td className="px-4 py-2">
                        <input
                          type="date"
                          value={cuota.fecha_pago ? cuota.fecha_pago.split('T')[0] : ''}
                          onChange={(e) => {
                            const newCuotas = [...cuotasData]
                            newCuotas[idx] = { ...cuota, fecha_pago: e.target.value ? `${e.target.value}T00:00:00` : null }
                            setCuotasData(newCuotas)
                            setCambios({ ...cambios, cuotas: true })
                          }}
                          className="border rounded px-2 py-1 text-sm w-full"
                        />
                      </td>
                      <td className="px-4 py-2">
                        <input
                          type="number"
                          step="0.01"
                          value={cuota.total_pagado || ''}
                          onChange={(e) => {
                            const newCuotas = [...cuotasData]
                            newCuotas[idx] = { ...cuota, total_pagado: parseFloat(e.target.value) || 0 }
                            setCuotasData(newCuotas)
                            setCambios({ ...cambios, cuotas: true })
                          }}
                          className="border rounded px-2 py-1 text-sm w-20"
                          placeholder="0.00"
                        />
                      </td>
                      <td className="px-4 py-2">
                        <select
                          value={cuota.estado || 'pendiente'}
                          onChange={(e) => {
                            const newCuotas = [...cuotasData]
                            newCuotas[idx] = { ...cuota, estado: e.target.value }
                            setCuotasData(newCuotas)
                            setCambios({ ...cambios, cuotas: true })
                          }}
                          className="border rounded px-2 py-1 text-sm"
                        >
                          <option value="pendiente">Pendiente</option>
                          <option value="pagado">Pagado</option>
                          <option value="conciliado">Conciliado</option>
                        </select>
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
      <div className="flex gap-3 justify-end sticky bottom-6 bg-white p-4 -mx-6 shadow-lg rounded-t-lg">
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
          className="bg-green-600 hover:bg-green-700 text-white gap-2"
          onClick={handleGuardarYCerrar}
          disabled={guardandoParcial || guardandoFinal}
          title="Guarda todos los cambios y finaliza la revisión"
        >
          {guardandoFinal ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
          Guardar y Cerrar
        </Button>
      </div>
    </motion.div>
  )
}

export default EditarRevisionManual
