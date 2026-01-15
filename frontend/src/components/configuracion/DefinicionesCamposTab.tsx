import { useState, useEffect } from 'react'
import { Database, Plus, Edit, Trash2, Search, Filter, CheckCircle, XCircle, Loader2, Key, Hash } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toast } from 'sonner'
import { apiClient } from '@/services/api'

interface DefinicionCampo {
  id: number
  tabla: string
  campo: string
  definicion: string
  tipo_dato: string | null
  es_obligatorio: boolean
  tiene_indice: boolean
  es_clave_foranea: boolean
  tabla_referenciada: string | null
  campo_referenciado: string | null
  valores_posibles: string[]
  ejemplos_valores: string[]
  notas: string | null
  activo: boolean
  orden: number
  creado_en: string
  actualizado_en: string
}

export function DefinicionesCamposTab() {
  const [definiciones, setDefiniciones] = useState<DefinicionCampo[]>([])
  const [tablas, setTablas] = useState<string[]>([])
  const [cargando, setCargando] = useState(false)
  const [filtroTabla, setFiltroTabla] = useState<string>('todas')
  const [busqueda, setBusqueda] = useState('')
  const [mostrarFormulario, setMostrarFormulario] = useState(false)
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [guardando, setGuardando] = useState(false)

  const [formulario, setFormulario] = useState({
    tabla: '',
    campo: '',
    definicion: '',
    tipo_dato: '',
    es_obligatorio: false,
    tiene_indice: false,
    es_clave_foranea: false,
    tabla_referenciada: '',
    campo_referenciado: '',
    valores_posibles: '',
    ejemplos_valores: '',
    notas: '',
    activo: true,
    orden: 0,
  })

  useEffect(() => {
    cargarDefiniciones()
    cargarTablas()
  }, [])

  const cargarDefiniciones = async () => {
    setCargando(true)
    try {
      const response = await apiClient.get<{ definiciones: DefinicionCampo[], total: number }>(
        '/api/v1/configuracion/ai/definiciones-campos'
      )
      setDefiniciones(response.definiciones || [])
    } catch (error: any) {
      console.error('Error cargando definiciones:', error)
      toast.error('Error al cargar las definiciones de campos')
    } finally {
      setCargando(false)
    }
  }

  const cargarTablas = async () => {
    try {
      const response = await apiClient.get<{ tablas: string[], total: number }>(
        '/api/v1/configuracion/ai/definiciones-campos/tablas'
      )
      setTablas(response.tablas || [])
    } catch (error: any) {
      console.error('Error cargando tablas:', error)
    }
  }

  const handleGuardar = async () => {
    if (!formulario.tabla.trim() || !formulario.campo.trim() || !formulario.definicion.trim()) {
      toast.error('Tabla, campo y definición son obligatorios')
      return
    }

    setGuardando(true)
    try {
      const datos = {
        ...formulario,
        valores_posibles: formulario.valores_posibles.split('\n').filter(v => v.trim()),
        ejemplos_valores: formulario.ejemplos_valores.split('\n').filter(e => e.trim()),
        tipo_dato: formulario.tipo_dato || null,
        tabla_referenciada: formulario.tabla_referenciada || null,
        campo_referenciado: formulario.campo_referenciado || null,
        notas: formulario.notas || null,
      }

      if (editandoId) {
        await apiClient.put(`/api/v1/configuracion/ai/definiciones-campos/${editandoId}`, datos)
        toast.success('Definición actualizada exitosamente')
      } else {
        await apiClient.post('/api/v1/configuracion/ai/definiciones-campos', datos)
        toast.success('Definición creada exitosamente')
      }

      setMostrarFormulario(false)
      setEditandoId(null)
      resetearFormulario()
      cargarDefiniciones()
      cargarTablas()
    } catch (error: any) {
      console.error('Error guardando:', error)
      toast.error(error?.response?.data?.detail || 'Error al guardar la definición')
    } finally {
      setGuardando(false)
    }
  }

  const handleEditar = (definicion: DefinicionCampo) => {
    setFormulario({
      tabla: definicion.tabla,
      campo: definicion.campo,
      definicion: definicion.definicion,
      tipo_dato: definicion.tipo_dato || '',
      es_obligatorio: definicion.es_obligatorio,
      tiene_indice: definicion.tiene_indice,
      es_clave_foranea: definicion.es_clave_foranea,
      tabla_referenciada: definicion.tabla_referenciada || '',
      campo_referenciado: definicion.campo_referenciado || '',
      valores_posibles: definicion.valores_posibles.join('\n'),
      ejemplos_valores: definicion.ejemplos_valores.join('\n'),
      notas: definicion.notas || '',
      activo: definicion.activo,
      orden: definicion.orden,
    })
    setEditandoId(definicion.id)
    setMostrarFormulario(true)
  }

  const handleEliminar = async (id: number) => {
    if (!confirm('¿Estás seguro de eliminar esta definición?')) return

    try {
      await apiClient.delete(`/api/v1/configuracion/ai/definiciones-campos/${id}`)
      toast.success('Definición eliminada exitosamente')
      cargarDefiniciones()
    } catch (error: any) {
      console.error('Error eliminando:', error)
      toast.error(error?.response?.data?.detail || 'Error al eliminar la definición')
    }
  }

  const handleToggleActivo = async (definicion: DefinicionCampo) => {
    try {
      await apiClient.put(`/api/v1/configuracion/ai/definiciones-campos/${definicion.id}`, {
        activo: !definicion.activo,
      })
      toast.success(`Definición ${!definicion.activo ? 'activada' : 'desactivada'}`)
      cargarDefiniciones()
    } catch (error: any) {
      console.error('Error cambiando estado:', error)
      toast.error('Error al cambiar el estado')
    }
  }

  const resetearFormulario = () => {
    setFormulario({
      tabla: '',
      campo: '',
      definicion: '',
      tipo_dato: '',
      es_obligatorio: false,
      tiene_indice: false,
      es_clave_foranea: false,
      tabla_referenciada: '',
      campo_referenciado: '',
      valores_posibles: '',
      ejemplos_valores: '',
      notas: '',
      activo: true,
      orden: 0,
    })
  }

  const definicionesFiltradas = definiciones.filter(def => {
    const coincideBusqueda = !busqueda || 
      def.tabla.toLowerCase().includes(busqueda.toLowerCase()) ||
      def.campo.toLowerCase().includes(busqueda.toLowerCase()) ||
      def.definicion.toLowerCase().includes(busqueda.toLowerCase())
    const coincideTabla = filtroTabla === 'todas' || def.tabla === filtroTabla
    return coincideBusqueda && coincideTabla
  })

  const definicionesPorTabla = definicionesFiltradas.reduce((acc, def) => {
    if (!acc[def.tabla]) acc[def.tabla] = []
    acc[def.tabla].push(def)
    return acc
  }, {} as Record<string, DefinicionCampo[]>)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold flex items-center gap-2">
            <Database className="h-6 w-6 text-purple-600" />
            Catálogo de Campos
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            Define todos los campos de la base de datos con sus descripciones para entrenar acceso rápido
          </p>
        </div>
        <Button onClick={() => { resetearFormulario(); setMostrarFormulario(true); setEditandoId(null) }}>
          <Plus className="h-4 w-4 mr-2" />
          Agregar Campo
        </Button>
      </div>

      {/* Filtros */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Buscar por tabla, campo o definición..."
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={filtroTabla} onValueChange={setFiltroTabla}>
              <SelectTrigger className="w-48">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Tabla" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todas">Todas las tablas</SelectItem>
                {tablas.map(tabla => (
                  <SelectItem key={tabla} value={tabla}>{tabla}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Formulario */}
      {mostrarFormulario && (
        <Card className="border-purple-200">
          <CardContent className="pt-6">
            <h4 className="text-lg font-semibold mb-4">
              {editandoId ? 'Editar Definición' : 'Nueva Definición'}
            </h4>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium block mb-1">
                    Tabla <span className="text-red-500">*</span>
                  </label>
                  <Input
                    value={formulario.tabla}
                    onChange={(e) => setFormulario({ ...formulario, tabla: e.target.value })}
                    placeholder="Ej: clientes, prestamos, pagos"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium block mb-1">
                    Campo <span className="text-red-500">*</span>
                  </label>
                  <Input
                    value={formulario.campo}
                    onChange={(e) => setFormulario({ ...formulario, campo: e.target.value })}
                    placeholder="Ej: cedula, nombres, monto_pagado"
                  />
                </div>
              </div>

              <div>
                <label className="text-sm font-medium block mb-1">
                  Definición <span className="text-red-500">*</span>
                </label>
                <Textarea
                  value={formulario.definicion}
                  onChange={(e) => setFormulario({ ...formulario, definicion: e.target.value })}
                  placeholder="Describe qué almacena este campo y cómo se usa..."
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="text-sm font-medium block mb-1">Tipo de Dato</label>
                  <Input
                    value={formulario.tipo_dato}
                    onChange={(e) => setFormulario({ ...formulario, tipo_dato: e.target.value })}
                    placeholder="Ej: VARCHAR, INTEGER, DATE"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium block mb-1">Tabla Referenciada (FK)</label>
                  <Input
                    value={formulario.tabla_referenciada}
                    onChange={(e) => setFormulario({ ...formulario, tabla_referenciada: e.target.value })}
                    placeholder="Ej: clientes"
                    disabled={!formulario.es_clave_foranea}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium block mb-1">Campo Referenciado (FK)</label>
                  <Input
                    value={formulario.campo_referenciado}
                    onChange={(e) => setFormulario({ ...formulario, campo_referenciado: e.target.value })}
                    placeholder="Ej: id"
                    disabled={!formulario.es_clave_foranea}
                  />
                </div>
              </div>

              <div className="flex items-center gap-6">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formulario.es_obligatorio}
                    onChange={(e) => setFormulario({ ...formulario, es_obligatorio: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm">Obligatorio (NOT NULL)</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formulario.tiene_indice}
                    onChange={(e) => setFormulario({ ...formulario, tiene_indice: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm">Tiene Índice</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formulario.es_clave_foranea}
                    onChange={(e) => setFormulario({ ...formulario, es_clave_foranea: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm">Clave Foránea (FK)</span>
                </label>
              </div>

              <div>
                <label className="text-sm font-medium block mb-1">Valores Posibles (uno por línea)</label>
                <Textarea
                  value={formulario.valores_posibles}
                  onChange={(e) => setFormulario({ ...formulario, valores_posibles: e.target.value })}
                  placeholder="PENDIENTE&#10;PAGADO&#10;MORA"
                  rows={2}
                />
              </div>

              <div>
                <label className="text-sm font-medium block mb-1">Ejemplos de Valores (uno por línea)</label>
                <Textarea
                  value={formulario.ejemplos_valores}
                  onChange={(e) => setFormulario({ ...formulario, ejemplos_valores: e.target.value })}
                  placeholder="V123456789&#10;V987654321"
                  rows={2}
                />
              </div>

              <div>
                <label className="text-sm font-medium block mb-1">Notas Adicionales</label>
                <Textarea
                  value={formulario.notas}
                  onChange={(e) => setFormulario({ ...formulario, notas: e.target.value })}
                  placeholder="Información adicional sobre el campo..."
                  rows={2}
                />
              </div>

              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formulario.activo}
                    onChange={(e) => setFormulario({ ...formulario, activo: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm">Activo</span>
                </label>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => { setMostrarFormulario(false); resetearFormulario(); setEditandoId(null) }}>
                    Cancelar
                  </Button>
                  <Button onClick={handleGuardar} disabled={guardando}>
                    {guardando ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Guardando...
                      </>
                    ) : (
                      'Guardar'
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Lista de Definiciones */}
      {cargando ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
        </div>
      ) : definicionesFiltradas.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center py-12">
            <Database className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-600">
              {busqueda || filtroTabla !== 'todas' 
                ? 'No se encontraron definiciones con los filtros aplicados'
                : 'No hay definiciones de campos. Agrega la primera definición.'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {Object.entries(definicionesPorTabla).map(([tabla, defs]) => (
            <Card key={tabla}>
              <CardContent className="pt-6">
                <h4 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Database className="h-5 w-5 text-purple-600" />
                  Tabla: {tabla}
                  <Badge variant="secondary">{defs.length}</Badge>
                </h4>
                <div className="space-y-4">
                  {defs.map(def => (
                    <div key={def.id} className="border rounded-lg p-4 hover:bg-gray-50">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h5 className="font-semibold text-lg">{def.campo}</h5>
                            {def.activo ? (
                              <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                                <CheckCircle className="h-3 w-3 mr-1" />
                                Activo
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="bg-gray-50 text-gray-600 border-gray-200">
                                <XCircle className="h-3 w-3 mr-1" />
                                Inactivo
                              </Badge>
                            )}
                            {def.es_obligatorio && (
                              <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                                NOT NULL
                              </Badge>
                            )}
                            {def.tiene_indice && (
                              <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                                <Hash className="h-3 w-3 mr-1" />
                                Indexado
                              </Badge>
                            )}
                            {def.es_clave_foranea && (
                              <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                                <Key className="h-3 w-3 mr-1" />
                                FK → {def.tabla_referenciada}.{def.campo_referenciado}
                              </Badge>
                            )}
                          </div>
                          <p className="text-gray-700 mb-2">{def.definicion}</p>
                          <div className="flex flex-wrap gap-2 text-sm text-gray-600">
                            {def.tipo_dato && (
                              <Badge variant="secondary">Tipo: {def.tipo_dato}</Badge>
                            )}
                            {def.valores_posibles.length > 0 && (
                              <Badge variant="outline">
                                Valores: {def.valores_posibles.join(', ')}
                              </Badge>
                            )}
                            {def.ejemplos_valores.length > 0 && (
                              <Badge variant="outline">
                                Ejemplos: {def.ejemplos_valores.slice(0, 2).join(', ')}
                              </Badge>
                            )}
                          </div>
                          {def.notas && (
                            <div className="mt-2 text-sm text-gray-500 italic">
                              💡 {def.notas}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-2 ml-4">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleToggleActivo(def)}
                            title={def.activo ? 'Desactivar' : 'Activar'}
                          >
                            {def.activo ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEditar(def)}
                            title="Editar"
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEliminar(def.id)}
                            title="Eliminar"
                            className="text-red-600 hover:text-red-700"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
