import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Search, Plus, Trash2, Edit2, Save, X, Database, Link } from 'lucide-react'
import toast from 'react-hot-toast'
import { notificacionService, NotificacionVariable } from '@/services/notificacionService'

// Usar el tipo del servicio
type VariableConfig = NotificacionVariable

// Todos los campos disponibles en la base de datos relacionados con clientes
const CAMPOS_DISPONIBLES = {
  clientes: [
    { campo: 'id', descripcion: 'ID único del cliente' },
    { campo: 'cedula', descripcion: 'Cédula de identidad' },
    { campo: 'nombres', descripcion: 'Nombres completos' },
    { campo: 'telefono', descripcion: 'Teléfono de contacto' },
    { campo: 'email', descripcion: 'Correo electrónico' },
    { campo: 'direccion', descripcion: 'Dirección de residencia' },
    { campo: 'fecha_nacimiento', descripcion: 'Fecha de nacimiento' },
    { campo: 'ocupacion', descripcion: 'Ocupación del cliente' },
    { campo: 'estado', descripcion: 'Estado (ACTIVO, INACTIVO, FINALIZADO)' },
    { campo: 'activo', descripcion: 'Estado activo (true/false)' },
    { campo: 'fecha_registro', descripcion: 'Fecha de registro' },
    { campo: 'fecha_actualizacion', descripcion: 'Fecha de última actualización' },
    { campo: 'usuario_registro', descripcion: 'Usuario que registró' },
    { campo: 'notas', descripcion: 'Notas adicionales' },
  ],
  prestamos: [
    { campo: 'id', descripcion: 'ID del préstamo' },
    { campo: 'cliente_id', descripcion: 'ID del cliente' },
    { campo: 'cedula', descripcion: 'Cédula del cliente' },
    { campo: 'nombres', descripcion: 'Nombres del cliente' },
    { campo: 'valor_activo', descripcion: 'Valor del activo (vehículo)' },
    { campo: 'total_financiamiento', descripcion: 'Monto total financiado' },
    { campo: 'fecha_requerimiento', descripcion: 'Fecha requerida del préstamo' },
    { campo: 'modalidad_pago', descripcion: 'Modalidad (MENSUAL, QUINCENAL, SEMANAL)' },
    { campo: 'numero_cuotas', descripcion: 'Número total de cuotas' },
    { campo: 'cuota_periodo', descripcion: 'Monto de cuota por período' },
    { campo: 'tasa_interes', descripcion: 'Tasa de interés (%)' },
    { campo: 'fecha_base_calculo', descripcion: 'Fecha base para cálculo' },
    { campo: 'producto', descripcion: 'Producto financiero' },
    { campo: 'producto_financiero', descripcion: 'Producto financiero' },
    { campo: 'concesionario', descripcion: 'Concesionario' },
    { campo: 'analista', descripcion: 'Analista asignado' },
    { campo: 'modelo_vehiculo', descripcion: 'Modelo del vehículo' },
    { campo: 'estado', descripcion: 'Estado del préstamo' },
    { campo: 'usuario_proponente', descripcion: 'Usuario proponente' },
    { campo: 'usuario_aprobador', descripcion: 'Usuario aprobador' },
    { campo: 'fecha_registro', descripcion: 'Fecha de registro' },
    { campo: 'fecha_aprobacion', descripcion: 'Fecha de aprobación' },
  ],
  cuotas: [
    { campo: 'id', descripcion: 'ID de la cuota' },
    { campo: 'prestamo_id', descripcion: 'ID del préstamo' },
    { campo: 'numero_cuota', descripcion: 'Número de cuota' },
    { campo: 'fecha_vencimiento', descripcion: 'Fecha de vencimiento' },
    { campo: 'fecha_pago', descripcion: 'Fecha de pago' },
    { campo: 'monto_cuota', descripcion: 'Monto total de la cuota' },
    { campo: 'monto_capital', descripcion: 'Monto de capital' },
    { campo: 'monto_interes', descripcion: 'Monto de interés' },
    { campo: 'saldo_capital_inicial', descripcion: 'Saldo capital inicial' },
    { campo: 'saldo_capital_final', descripcion: 'Saldo capital final' },
    { campo: 'capital_pagado', descripcion: 'Capital pagado' },
    { campo: 'interes_pagado', descripcion: 'Interés pagado' },
    { campo: 'mora_pagada', descripcion: 'Mora pagada' },
    { campo: 'total_pagado', descripcion: 'Total pagado' },
    { campo: 'capital_pendiente', descripcion: 'Capital pendiente' },
    { campo: 'interes_pendiente', descripcion: 'Interés pendiente' },
    { campo: 'dias_mora', descripcion: 'Días de mora' },
    { campo: 'monto_mora', descripcion: 'Monto de mora' },
    { campo: 'tasa_mora', descripcion: 'Tasa de mora (%)' },
    { campo: 'dias_morosidad', descripcion: 'Días de morosidad' },
    { campo: 'monto_morosidad', descripcion: 'Monto de morosidad' },
    { campo: 'estado', descripcion: 'Estado de la cuota' },
  ],
  pagos: [
    { campo: 'id', descripcion: 'ID del pago' },
    { campo: 'cedula', descripcion: 'Cédula del cliente' },
    { campo: 'prestamo_id', descripcion: 'ID del préstamo' },
    { campo: 'numero_cuota', descripcion: 'Número de cuota' },
    { campo: 'fecha_pago', descripcion: 'Fecha de pago' },
    { campo: 'fecha_registro', descripcion: 'Fecha de registro' },
    { campo: 'monto_pagado', descripcion: 'Monto pagado' },
    { campo: 'numero_documento', descripcion: 'Número de documento' },
    { campo: 'institucion_bancaria', descripcion: 'Institución bancaria' },
    { campo: 'estado', descripcion: 'Estado del pago' },
    { campo: 'conciliado', descripcion: 'Si está conciliado' },
    { campo: 'fecha_conciliacion', descripcion: 'Fecha de conciliación' },
  ],
}

export function GeneraVariables() {
  const [variables, setVariables] = useState<VariableConfig[]>([])
  const [loading, setLoading] = useState(false)
  const [busqueda, setBusqueda] = useState('')
  const [editando, setEditando] = useState<number | null>(null)
  const [nuevaVariable, setNuevaVariable] = useState<Partial<VariableConfig>>({
    nombre_variable: '',
    campo_bd: '',
    tabla: 'clientes',
    descripcion: '',
    activa: true,
  })

  const inicializarVariablesPrecargadas = async () => {
    try {
      await notificacionService.inicializarVariablesPrecargadas()
      // Recargar variables después de inicializar
      await cargarVariables()
    } catch (error: any) {
      // Si falla, no es crítico - las variables precargadas del frontend seguirán funcionando
      if (error?.response?.status !== 404) {
        console.warn('No se pudieron inicializar variables precargadas en BD:', error?.response?.data?.detail || error.message)
      }
    }
  }

  const cargarVariables = async () => {
    setLoading(true)
    try {
      const response = await notificacionService.listarVariables()
      setVariables(response || [])
    } catch (error: any) {
      // Si el endpoint no existe aún, usar lista vacía
      if (error?.response?.status !== 404) {
        toast.error(error?.response?.data?.detail || 'Error al cargar variables')
      }
      setVariables([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // Inicializar variables precargadas automáticamente al cargar el componente
    inicializarVariablesPrecargadas()
  }, [])

  const guardarVariable = async (variable: VariableConfig) => {
    try {
      if (variable.id) {
        await notificacionService.actualizarVariable(variable.id, variable)
        toast.success('Variable actualizada exitosamente')
      } else {
        await notificacionService.crearVariable(variable)
        toast.success('Variable creada exitosamente')
      }
      await cargarVariables()
      setEditando(null)
      setNuevaVariable({
        nombre_variable: '',
        campo_bd: '',
        tabla: 'clientes',
        descripcion: '',
        activa: true,
      })
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Error al guardar variable')
    }
  }

  const eliminarVariable = async (id: number) => {
    if (!window.confirm('¿Está seguro de eliminar esta variable?')) return

    try {
      await notificacionService.eliminarVariable(id)
      toast.success('Variable eliminada exitosamente')
      await cargarVariables()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Error al eliminar variable')
    }
  }

  const iniciarEdicion = (variable: VariableConfig) => {
    setEditando(variable.id!)
    setNuevaVariable(variable)
  }

  const cancelarEdicion = () => {
    setEditando(null)
    setNuevaVariable({
      nombre_variable: '',
      campo_bd: '',
      tabla: 'clientes',
      descripcion: '',
      activa: true,
    })
  }

  const variablesFiltradas = variables.filter(v =>
    v.nombre_variable.toLowerCase().includes(busqueda.toLowerCase()) ||
    v.campo_bd.toLowerCase().includes(busqueda.toLowerCase()) ||
    v.tabla.toLowerCase().includes(busqueda.toLowerCase()) ||
    (v.descripcion ?? '').toLowerCase().includes(busqueda.toLowerCase())
  )

  const camposTabla = nuevaVariable.tabla ? CAMPOS_DISPONIBLES[nuevaVariable.tabla as keyof typeof CAMPOS_DISPONIBLES] || [] : []

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5 text-blue-600" />
            Genera Variables {`{{variables}}`}
          </CardTitle>
          <CardDescription>
            Configure variables personalizadas que se relacionan con todos los campos disponibles en la base de datos.
            Estas variables pueden usarse en las plantillas de notificaciones usando la sintaxis {'{{nombre_variable}}'}.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Formulario para nueva variable */}
          <div className="border rounded-lg p-4 space-y-4 bg-gray-50">
            <h3 className="font-semibold text-sm">Nueva Variable</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-gray-600 mb-1 block">Nombre de Variable</label>
                <Input
                  value={nuevaVariable.nombre_variable || ''}
                  onChange={e => setNuevaVariable({ ...nuevaVariable, nombre_variable: e.target.value })}
                  placeholder="nombre_cliente"
                />
                <p className="text-xs text-gray-500 mt-1">Se usará como {'{{nombre_cliente}}'} en plantillas</p>
              </div>
              <div>
                <label className="text-sm text-gray-600 mb-1 block">Tabla</label>
                <select
                  value={nuevaVariable.tabla || 'clientes'}
                  onChange={e => {
                    setNuevaVariable({ ...nuevaVariable, tabla: e.target.value, campo_bd: '' })
                  }}
                  className="w-full border rounded px-3 py-2 text-sm"
                >
                  <option value="clientes">Clientes</option>
                  <option value="prestamos">Préstamos</option>
                  <option value="cuotas">Cuotas</option>
                  <option value="pagos">Pagos</option>
                </select>
              </div>
              <div>
                <label className="text-sm text-gray-600 mb-1 block">Campo de Base de Datos</label>
                <select
                  value={nuevaVariable.campo_bd || ''}
                  onChange={e => {
                    const campo = e.target.value
                    const campoInfo = camposTabla.find(c => c.campo === campo)
                    setNuevaVariable({
                      ...nuevaVariable,
                      campo_bd: campo,
                      descripcion: campoInfo?.descripcion || nuevaVariable.descripcion || '',
                    })
                  }}
                  className="w-full border rounded px-3 py-2 text-sm"
                >
                  <option value="">Seleccione un campo...</option>
                  {camposTabla.map(campo => (
                    <option key={campo.campo} value={campo.campo}>
                      {campo.campo} - {campo.descripcion}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm text-gray-600 mb-1 block">Descripción</label>
                <Input
                  value={nuevaVariable.descripcion || ''}
                  onChange={e => setNuevaVariable({ ...nuevaVariable, descripcion: e.target.value })}
                  placeholder="Descripción de la variable"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="activa"
                  checked={nuevaVariable.activa ?? true}
                  onChange={e => setNuevaVariable({ ...nuevaVariable, activa: e.target.checked })}
                />
                <label htmlFor="activa" className="text-sm">Variable activa</label>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => {
                  if (!nuevaVariable.nombre_variable || !nuevaVariable.campo_bd) {
                    toast.error('Complete todos los campos obligatorios')
                    return
                  }
                  guardarVariable(nuevaVariable as VariableConfig)
                }}
                disabled={!nuevaVariable.nombre_variable || !nuevaVariable.campo_bd}
              >
                <Plus className="h-4 w-4 mr-1" />
                {editando ? 'Actualizar' : 'Crear'} Variable
              </Button>
              {editando && (
                <Button variant="outline" onClick={cancelarEdicion}>
                  <X className="h-4 w-4 mr-1" />
                  Cancelar
                </Button>
              )}
            </div>
          </div>

          {/* Búsqueda */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              value={busqueda}
              onChange={e => setBusqueda(e.target.value)}
              placeholder="Buscar variables..."
              className="pl-10"
            />
          </div>

          {/* Lista de variables */}
          <div className="border rounded-lg overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Variable</TableHead>
                  <TableHead>Tabla</TableHead>
                  <TableHead>Campo BD</TableHead>
                  <TableHead>Descripción</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-4">
                      Cargando...
                    </TableCell>
                  </TableRow>
                ) : variablesFiltradas.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-4 text-gray-500">
                      {busqueda ? 'No se encontraron variables con ese criterio' : 'No hay variables configuradas. Cree una nueva variable.'}
                    </TableCell>
                  </TableRow>
                ) : (
                  variablesFiltradas.map(variable => (
                    <TableRow key={variable.id || variable.nombre_variable}>
                      <TableCell>
                        <code className="bg-gray-100 px-2 py-1 rounded text-sm">
                          {'{{'}{variable.nombre_variable}{'}}'}
                        </code>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{variable.tabla}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Link className="h-3 w-3 text-gray-400" />
                          <span className="text-sm font-mono">{variable.campo_bd}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-gray-600">
                        {variable.descripcion || '-'}
                      </TableCell>
                      <TableCell>
                        {variable.activa ? (
                          <Badge variant="success">Activa</Badge>
                        ) : (
                          <Badge variant="secondary">Inactiva</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => iniciarEdicion(variable)}
                            title="Editar"
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => variable.id && eliminarVariable(variable.id)}
                            title="Eliminar"
                          >
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Información de campos disponibles */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Campos Disponibles por Tabla</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {Object.entries(CAMPOS_DISPONIBLES).map(([tabla, campos]) => (
                  <div key={tabla} className="border rounded p-3">
                    <h4 className="font-semibold text-sm mb-2 capitalize">{tabla}</h4>
                    <ul className="space-y-1 text-xs text-gray-600">
                      {campos.map(campo => (
                        <li key={campo.campo} className="flex items-start gap-1">
                          <span className="font-mono text-xs">•</span>
                          <span className="text-xs">{campo.campo}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </CardContent>
      </Card>
    </div>
  )
}

