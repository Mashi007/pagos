import { useState, useEffect } from 'react'
import {
  Plus,
  Edit2,
  Trash2,
  Search,
  Save,
  X,
  Database,
  FileText,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { notificacionService, NotificacionVariable } from '@/services/notificacionService'
import { toast } from 'sonner'

const TABLAS_DISPONIBLES = [
  { value: 'clientes', label: 'Clientes' },
  { value: 'prestamos', label: 'Préstamos' },
  { value: 'cuotas', label: 'Cuotas' },
  { value: 'pagos', label: 'Pagos' },
]

const CAMPOS_DISPONIBLES: Record<string, Array<{ campo: string; descripcion: string }>> = {
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

export function GestionVariables() {
  const [variables, setVariables] = useState<NotificacionVariable[]>([])
  const [cargando, setCargando] = useState(false)
  const [busqueda, setBusqueda] = useState('')
  const [filtroTabla, setFiltroTabla] = useState<string>('')
  const [filtroActiva, setFiltroActiva] = useState<boolean | null>(null)

  // Estado para el diálogo de crear/editar
  const [dialogoAbierto, setDialogoAbierto] = useState(false)
  const [editando, setEditando] = useState(false)
  const [variableEditando, setVariableEditando] = useState<NotificacionVariable | null>(null)

  // Formulario
  const [nombreVariable, setNombreVariable] = useState('')
  const [tabla, setTabla] = useState('')
  const [campoBd, setCampoBd] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [activa, setActiva] = useState(true)

  // Diálogo de confirmación para eliminar
  const [dialogoEliminarAbierto, setDialogoEliminarAbierto] = useState(false)
  const [variableAEliminar, setVariableAEliminar] = useState<NotificacionVariable | null>(null)

  const cargarVariables = async () => {
    setCargando(true)
    try {
      const data = await notificacionService.listarVariables()
      setVariables(data)
    } catch (error: any) {
      console.error('Error cargando variables:', error)
      toast.error('Error al cargar variables')
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    cargarVariables()
  }, [])

  const abrirDialogoCrear = () => {
    setEditando(false)
    setVariableEditando(null)
    setNombreVariable('')
    setTabla('')
    setCampoBd('')
    setDescripcion('')
    setActiva(true)
    setDialogoAbierto(true)
  }

  // Obtener campos disponibles para la tabla seleccionada
  const camposDisponibles = tabla ? CAMPOS_DISPONIBLES[tabla] || [] : []

  // Manejar cambio de tabla - limpiar campo BD si cambia
  const handleTablaChange = (nuevaTabla: string) => {
    setTabla(nuevaTabla)
    // Si el campo BD actual no existe en la nueva tabla, limpiarlo
    if (campoBd && nuevaTabla) {
      const camposNuevaTabla = CAMPOS_DISPONIBLES[nuevaTabla] || []
      const campoExiste = camposNuevaTabla.some((c) => c.campo === campoBd)
      if (!campoExiste) {
        setCampoBd('')
      }
    } else {
      setCampoBd('')
    }
  }

  const abrirDialogoEditar = (variable: NotificacionVariable) => {
    setEditando(true)
    setVariableEditando(variable)
    setNombreVariable(variable.nombre_variable)
    setTabla(variable.tabla)
    setCampoBd(variable.campo_bd)
    setDescripcion(variable.descripcion || '')
    setActiva(variable.activa)
    setDialogoAbierto(true)
  }

  const cerrarDialogo = () => {
    setDialogoAbierto(false)
    setEditando(false)
    setVariableEditando(null)
    setNombreVariable('')
    setTabla('')
    setCampoBd('')
    setDescripcion('')
    setActiva(true)
  }

  const guardarVariable = async () => {
    // Validaciones
    if (!nombreVariable.trim()) {
      toast.error('El nombre de la variable es requerido')
      return
    }

    if (!tabla) {
      toast.error('La tabla es requerida')
      return
    }

    if (!campoBd.trim()) {
      toast.error('El campo de base de datos es requerido')
      return
    }

    // Validar formato del nombre de variable (solo letras, números y guiones bajos)
    if (!/^[a-z][a-z0-9_]*$/.test(nombreVariable.trim().toLowerCase())) {
      toast.error('El nombre de la variable solo puede contener letras minúsculas, números y guiones bajos, y debe empezar con letra')
      return
    }

    try {
      const datos: Partial<NotificacionVariable> = {
        nombre_variable: nombreVariable.trim().toLowerCase(),
        tabla: tabla,
        campo_bd: campoBd.trim(),
        descripcion: descripcion.trim() || null,
        activa: activa,
      }

      if (editando && variableEditando?.id) {
        await notificacionService.actualizarVariable(variableEditando.id, datos)
        toast.success('Variable actualizada exitosamente')
      } else {
        await notificacionService.crearVariable(datos)
        toast.success('Variable creada exitosamente')
      }

      cerrarDialogo()
      cargarVariables()
    } catch (error: any) {
      console.error('Error guardando variable:', error)
      const mensaje = error?.response?.data?.detail || error?.message || 'Error al guardar la variable'
      toast.error(mensaje)
    }
  }

  const confirmarEliminar = (variable: NotificacionVariable) => {
    setVariableAEliminar(variable)
    setDialogoEliminarAbierto(true)
  }

  const eliminarVariable = async () => {
    if (!variableAEliminar?.id) return

    try {
      await notificacionService.eliminarVariable(variableAEliminar.id)
      toast.success('Variable eliminada exitosamente')
      setDialogoEliminarAbierto(false)
      setVariableAEliminar(null)
      cargarVariables()
    } catch (error: any) {
      console.error('Error eliminando variable:', error)
      const mensaje = error?.response?.data?.detail || error?.message || 'Error al eliminar la variable'
      toast.error(mensaje)
    }
  }

  // Filtrar variables
  const variablesFiltradas = variables.filter((v) => {
    const coincideBusqueda =
      !busqueda ||
      v.nombre_variable.toLowerCase().includes(busqueda.toLowerCase()) ||
      v.tabla.toLowerCase().includes(busqueda.toLowerCase()) ||
      v.campo_bd.toLowerCase().includes(busqueda.toLowerCase()) ||
      (v.descripcion && v.descripcion.toLowerCase().includes(busqueda.toLowerCase()))

    const coincideTabla = !filtroTabla || v.tabla === filtroTabla
    const coincideActiva = filtroActiva === null || v.activa === filtroActiva

    return coincideBusqueda && coincideTabla && coincideActiva
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Database className="h-6 w-6" />
            Gestión de Variables Personalizadas
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Crea y gestiona variables personalizadas para usar en plantillas de notificaciones
          </p>
        </div>
        <Button onClick={abrirDialogoCrear}>
          <Plus className="h-4 w-4 mr-2" />
          Nueva Variable
        </Button>
      </div>

      {/* Filtros */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <Label htmlFor="busqueda">Buscar</Label>
              <div className="relative mt-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  id="busqueda"
                  placeholder="Buscar por nombre, tabla, campo..."
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div>
              <Label htmlFor="filtro-tabla">Filtrar por Tabla</Label>
              <Select value={filtroTabla} onValueChange={setFiltroTabla}>
                <SelectTrigger id="filtro-tabla" className="mt-1">
                  <SelectValue placeholder="Todas las tablas" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todas las tablas</SelectItem>
                  {TABLAS_DISPONIBLES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="filtro-activa">Filtrar por Estado</Label>
              <Select
                value={filtroActiva === null ? 'todas' : filtroActiva ? 'activa' : 'inactiva'}
                onValueChange={(value) => {
                  if (value === 'todas') setFiltroActiva(null)
                  else setFiltroActiva(value === 'activa')
                }}
              >
                <SelectTrigger id="filtro-activa" className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todas">Todas</SelectItem>
                  <SelectItem value="activa">Activas</SelectItem>
                  <SelectItem value="inactiva">Inactivas</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabla de Variables */}
      <Card>
        <CardHeader>
          <CardTitle>Variables Configuradas</CardTitle>
          <CardDescription>
            {variablesFiltradas.length} de {variables.length} variables
          </CardDescription>
        </CardHeader>
        <CardContent>
          {cargando ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          ) : variablesFiltradas.length === 0 ? (
            <div className="text-center py-12">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p className="text-gray-500">
                {variables.length === 0
                  ? 'No hay variables configuradas. Crea tu primera variable.'
                  : 'No se encontraron variables con los filtros aplicados.'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
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
                  {variablesFiltradas.map((variable) => (
                    <TableRow key={variable.id}>
                      <TableCell>
                        <div className="font-mono text-sm">
                          {`{{${variable.nombre_variable}}}`}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{variable.tabla}</Badge>
                      </TableCell>
                      <TableCell>
                        <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                          {variable.campo_bd}
                        </code>
                      </TableCell>
                      <TableCell>
                        <div className="max-w-xs truncate" title={variable.descripcion || ''}>
                          {variable.descripcion || (
                            <span className="text-gray-400 italic">Sin descripción</span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        {variable.activa ? (
                          <Badge variant="default" className="bg-green-600">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Activa
                          </Badge>
                        ) : (
                          <Badge variant="secondary">
                            <XCircle className="h-3 w-3 mr-1" />
                            Inactiva
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => abrirDialogoEditar(variable)}
                            title="Editar"
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => confirmarEliminar(variable)}
                            title="Eliminar"
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Diálogo de Crear/Editar */}
      <Dialog open={dialogoAbierto} onOpenChange={setDialogoAbierto}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editando ? 'Editar Variable' : 'Nueva Variable Personalizada'}
            </DialogTitle>
            <p className="text-sm text-gray-500 mt-1">
              {editando
                ? 'Modifica los datos de la variable personalizada'
                : 'Crea una nueva variable personalizada para usar en plantillas de notificaciones'}
            </p>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="nombre-variable">
                  Nombre de Variable <span className="text-red-500">*</span>
                </Label>
                <div className="relative">
                  <Input
                    id="nombre-variable"
                    placeholder="ej: resumen_bd"
                    value={nombreVariable}
                    onChange={(e) => setNombreVariable(e.target.value)}
                    disabled={editando}
                  />
                  <div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-xs text-gray-400">
                    {`{{${nombreVariable || 'variable'}}}`}
                  </div>
                </div>
                <p className="text-xs text-gray-500">
                  Solo letras minúsculas, números y guiones bajos. Se usará como {`{{${nombreVariable || 'variable'}}}`}
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="tabla">
                  Tabla <span className="text-red-500">*</span>
                </Label>
                <Select
                  value={tabla}
                  onValueChange={handleTablaChange}
                >
                  <SelectTrigger id="tabla">
                    <SelectValue placeholder="Selecciona una tabla" />
                  </SelectTrigger>
                  <SelectContent>
                    {TABLAS_DISPONIBLES.map((t) => (
                      <SelectItem key={t.value} value={t.value}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="campo-bd">
                Campo de Base de Datos <span className="text-red-500">*</span>
              </Label>
              {tabla ? (
                <>
                  <Select
                    value={campoBd}
                    onValueChange={setCampoBd}
                    disabled={!tabla}
                  >
                    <SelectTrigger id="campo-bd">
                      <SelectValue placeholder="Selecciona un campo" />
                    </SelectTrigger>
                    <SelectContent>
                      {camposDisponibles.map((campo) => (
                        <SelectItem key={campo.campo} value={campo.campo}>
                          <div className="flex flex-col">
                            <span className="font-mono text-sm">{campo.campo}</span>
                            <span className="text-xs text-gray-500">{campo.descripcion}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {campoBd && (
                    <p className="text-xs text-gray-500 mt-1">
                      {camposDisponibles.find((c) => c.campo === campoBd)?.descripcion}
                    </p>
                  )}
                </>
              ) : (
                <Input
                  id="campo-bd"
                  placeholder="Primero selecciona una tabla"
                  value={campoBd}
                  disabled
                />
              )}
              <p className="text-xs text-gray-500 mt-1">
                {tabla
                  ? `${camposDisponibles.length} campos disponibles en la tabla "${TABLAS_DISPONIBLES.find((t) => t.value === tabla)?.label}"`
                  : 'Selecciona una tabla para ver los campos disponibles'}
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="descripcion">Descripción</Label>
              <Textarea
                id="descripcion"
                placeholder="ej: Resumen de la base de datos"
                value={descripcion}
                onChange={(e) => setDescripcion(e.target.value)}
                rows={3}
              />
              <p className="text-xs text-gray-500">
                Descripción de qué representa esta variable
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="activa"
                checked={activa}
                onChange={(e) => setActiva(e.target.checked)}
                className="rounded border-gray-300"
              />
              <Label htmlFor="activa" className="cursor-pointer">
                Variable activa (disponible para usar en plantillas)
              </Label>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={cerrarDialogo}>
              <X className="h-4 w-4 mr-2" />
              Cancelar
            </Button>
            <Button onClick={guardarVariable}>
              <Save className="h-4 w-4 mr-2" />
              {editando ? 'Actualizar' : 'Guardar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Diálogo de Confirmación de Eliminación */}
      <Dialog open={dialogoEliminarAbierto} onOpenChange={setDialogoEliminarAbierto}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirmar Eliminación</DialogTitle>
            <p className="text-sm text-gray-500 mt-1">
              ¿Estás seguro de que deseas eliminar la variable{' '}
              <strong>{`{{${variableAEliminar?.nombre_variable}}}`}</strong>?
              <br />
              Esta acción no se puede deshacer.
            </p>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogoEliminarAbierto(false)}>
              Cancelar
            </Button>
            <Button variant="destructive" onClick={eliminarVariable}>
              <Trash2 className="h-4 w-4 mr-2" />
              Eliminar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

