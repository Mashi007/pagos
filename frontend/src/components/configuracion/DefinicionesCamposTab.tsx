import { useState, useEffect } from 'react'
import { Database, Plus, Edit, Trash2, Search, Filter, CheckCircle, XCircle, Loader2, Key, RefreshCw, FileText, ChevronDown, ChevronUp } from 'lucide-react'
import { Card, CardContent } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import { Badge } from '../../components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { toast } from 'sonner'
import { apiClient } from '../../services/api'

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

interface CampoDisponible {
  nombre: string
  tipo: string
  nullable: boolean
  es_obligatorio: boolean
  es_primary_key: boolean
  tiene_indice: boolean
  es_clave_foranea: boolean
  tabla_referenciada?: string
  campo_referenciado?: string
}

interface TablaCampos {
  [tabla: string]: CampoDisponible[]
}

export function DefinicionesCamposTab() {
  const [definiciones, setDefiniciones] = useState<DefinicionCampo[]>([])
  const [tablas, setTablas] = useState<string[]>([])
  const [camposDisponibles, setCamposDisponibles] = useState<TablaCampos>({})
  const [cargando, setCargando] = useState(false)
  const [sincronizando, setSincronizando] = useState(false)
  const [filtroTabla, setFiltroTabla] = useState<string>('todas')
  const [busqueda, setBusqueda] = useState('')
  const [mostrarFormulario, setMostrarFormulario] = useState(false)
  const [mostrarCamposDisponibles, setMostrarCamposDisponibles] = useState(false)
  const [mostrarMasOpciones, setMostrarMasOpciones] = useState(false)
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

  const [yaSincronizado, setYaSincronizado] = useState(false)

  useEffect(() => {
    cargarTodo()
  }, [])

  const cargarTodo = async () => {
    setCargando(true)
    try {
      // Primero cargar campos disponibles
      const camposCargados = await cargarCamposDisponibles()
      // Luego cargar definiciones
      const definicionesCargadas = await cargarDefiniciones()
      // Y tablas
      await cargarTablas()
      
      // Contar total de campos (sumar campos de todas las tablas)
      const totalCampos = Object.values(camposCargados).reduce((total, campos) => total + campos.length, 0)
      
      console.log(`ðŸ“Š Campos disponibles: ${totalCampos}, Definiciones existentes: ${definicionesCargadas.length}`)
      
      // Si no hay definiciones pero hay campos disponibles, sincronizar automáticamente
      if (definicionesCargadas.length === 0 && totalCampos > 0 && !yaSincronizado) {
        console.log('ðŸ”„ No hay definiciones precargadas. Sincronizando automáticamente...')
        setYaSincronizado(true)
        await handleSincronizarAutomatico()
      }
    } catch (error: any) {
      console.error('Error en cargarTodo:', error)
      toast.error('Error al cargar los datos')
    } finally {
      setCargando(false)
    }
  }

  const cargarDefiniciones = async () => {
    try {
      // Carga desde la tabla definiciones_campos (BD) vía API
      const response = await apiClient.get<{ definiciones: DefinicionCampo[], total: number }>(
        '/api/v1/configuracion/ai/definiciones-campos'
      )
      const definicionesCargadas = response.definiciones || []
      setDefiniciones(definicionesCargadas)
      return definicionesCargadas
    } catch (error: any) {
      console.error('Error cargando definiciones:', error)
      toast.error('Error al cargar las definiciones de campos')
      return []
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

  const cargarCamposDisponibles = async () => {
    try {
      const response = await apiClient.get<{ tablas_campos: TablaCampos, total_tablas: number }>(
        '/api/v1/configuracion/ai/tablas-campos'
      )
      const camposCargados = response.tablas_campos || {}
      setCamposDisponibles(camposCargados)
      
      // Log para debugging
      const totalCampos = Object.values(camposCargados).reduce((total, campos) => total + campos.length, 0)
      console.log(`ðŸ“‹ Campos disponibles cargados: ${totalCampos} campos en ${Object.keys(camposCargados).length} tablas`)
      
      return camposCargados
    } catch (error: any) {
      console.error('âŒ Error cargando campos disponibles:', error)
      toast.error('Error al cargar campos disponibles de la base de datos')
      return {}
    }
  }

  const handleSincronizarAutomatico = async () => {
    // Sincronización automática sin confirmación
    setSincronizando(true)
    try {
      const response = await apiClient.post<{
        mensaje: string
        campos_creados: number
        campos_actualizados: number
        campos_existentes: number
        total_procesados: number
      }>('/api/v1/configuracion/ai/definiciones-campos/sincronizar')
      
      toast.success(
        `âœ… Sincronización automática completada: ${response.campos_creados} campos precargados`
      )
      // Recargar todo después de sincronizar
      await cargarCamposDisponibles()
      await cargarDefiniciones()
      await cargarTablas()
    } catch (error: any) {
      console.error('Error sincronizando automáticamente:', error)
      toast.error(error?.response?.data?.detail || 'Error al sincronizar campos automáticamente')
    } finally {
      setSincronizando(false)
    }
  }

  const handleSincronizar = async () => {
    if (!confirm('¿Deseas sincronizar todos los campos de la base de datos? Esto creará definiciones para campos que no existen y actualizará información técnica de campos existentes sin sobrescribir definiciones personalizadas.')) {
      return
    }

    setSincronizando(true)
    try {
      const response = await apiClient.post<{
        mensaje: string
        campos_creados: number
        campos_actualizados: number
        campos_existentes: number
        total_procesados: number
      }>('/api/v1/configuracion/ai/definiciones-campos/sincronizar')
      
      toast.success(
        `Sincronización completada: ${response.campos_creados} creados, ${response.campos_actualizados} actualizados`
      )
      cargarDefiniciones()
      cargarTablas()
      cargarCamposDisponibles()
    } catch (error: any) {
      console.error('Error sincronizando:', error)
      toast.error(error?.response?.data?.detail || 'Error al sincronizar campos')
    } finally {
      setSincronizando(false)
    }
  }

  const handleSeleccionarCampo = (tabla: string, campo: CampoDisponible) => {
    // Verificar si ya existe definición
    const existe = definiciones.find(d => d.tabla === tabla && d.campo === campo.nombre)
    if (existe) {
      toast.info('Este campo ya tiene una definición. Puedes editarla.')
      handleEditar(existe)
      return
    }

    // Prellenar formulario con información del campo
    setFormulario({
      tabla: tabla,
      campo: campo.nombre,
      definicion: `Campo ${campo.nombre} de la tabla ${tabla}. Tipo: ${campo.tipo}. ${campo.es_obligatorio ? 'Obligatorio' : 'Opcional'}.`,
      tipo_dato: campo.tipo,
      es_obligatorio: campo.es_obligatorio,
      tiene_indice: campo.tiene_indice,
      es_clave_foranea: campo.es_clave_foranea,
      tabla_referenciada: campo.tabla_referenciada || '',
      campo_referenciado: campo.campo_referenciado || '',
      valores_posibles: '',
      ejemplos_valores: '',
      notas: '',
      activo: true,
      orden: 0,
    })
    setEditandoId(null)
    setMostrarFormulario(true)
    setMostrarCamposDisponibles(false)
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
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            onClick={handleSincronizar}
            disabled={sincronizando}
          >
            {sincronizando ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Sincronizando...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4 mr-2" />
                Sincronizar BD
              </>
            )}
          </Button>
          <Button 
            variant="outline" 
            onClick={() => setMostrarCamposDisponibles(!mostrarCamposDisponibles)}
          >
            <FileText className="h-4 w-4 mr-2" />
            {mostrarCamposDisponibles ? 'Ocultar' : 'Ver'} Campos Disponibles
          </Button>
          <Button onClick={() => { resetearFormulario(); setMostrarFormulario(true); setEditandoId(null) }}>
            <Plus className="h-4 w-4 mr-2" />
            Agregar Campo
          </Button>
        </div>
      </div>

      {/* Campos Disponibles */}
      {mostrarCamposDisponibles && (
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-lg font-semibold flex items-center gap-2">
                <Database className="h-5 w-5 text-blue-600" />
                Campos Disponibles en la Base de Datos
              </h4>
              <Badge variant="secondary">
                {Object.values(camposDisponibles).flat().length} campos totales
              </Badge>
            </div>
            <div className="space-y-4 max-h-96 overflow-y-auto">
              {Object.entries(camposDisponibles).map(([tabla, campos]) => (
                <div key={tabla} className="border rounded-lg p-3 bg-white">
                  <h5 className="font-semibold mb-2 text-sm text-gray-700">
                    Tabla: <span className="text-blue-600">{tabla}</span>
                    <Badge variant="outline" className="ml-2">{campos.length}</Badge>
                  </h5>
                  <div className="grid grid-cols-2 gap-2">
                    {campos.map(campo => {
                      const tieneDefinicion = definiciones.some(d => d.tabla === tabla && d.campo === campo.nombre)
                      return (
                        <button
                          key={campo.nombre}
                          onClick={() => handleSeleccionarCampo(tabla, campo)}
                          className={`text-left p-2 rounded border text-sm hover:bg-gray-50 transition-colors ${
                            tieneDefinicion 
                              ? 'border-green-300 bg-green-50' 
                              : 'border-gray-200'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-medium">{campo.nombre}</span>
                            {tieneDefinicion && (
                              <CheckCircle className="h-3 w-3 text-green-600" />
                            )}
                          </div>
                          <div className="text-xs text-gray-500 mt-1">
                            {campo.tipo}
                            {campo.es_obligatorio && ' • NOT NULL'}
                            {campo.tiene_indice && ' • Indexado'}
                            {campo.es_clave_foranea && ` • FK â†’ ${campo.tabla_referenciada}`}
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

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

      {/* Formulario simplificado */}
      {mostrarFormulario && (
        <Card className="border-purple-200">
          <CardContent className="pt-6">
            <h4 className="text-lg font-semibold mb-4">
              {editandoId ? 'Editar Definición' : 'Nueva Definición'}
            </h4>
            <div className="space-y-4">
              {/* Esencial: Tabla + Campo + Definición + Tipo */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium block mb-1">Tabla <span className="text-red-500">*</span></label>
                  <Select value={formulario.tabla} onValueChange={(v) => setFormulario({ ...formulario, tabla: v })}>
                    <SelectTrigger><SelectValue placeholder="Seleccionar tabla" /></SelectTrigger>
                    <SelectContent>
                      {Object.keys(camposDisponibles).map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-sm font-medium block mb-1">Campo <span className="text-red-500">*</span></label>
                  {formulario.tabla && camposDisponibles[formulario.tabla] ? (
                    <Select
                      value={formulario.campo}
                      onValueChange={(v) => {
                        const c = camposDisponibles[formulario.tabla].find(x => x.nombre === v)
                        if (c) handleSeleccionarCampo(formulario.tabla, c)
                      }}
                    >
                      <SelectTrigger><SelectValue placeholder="Seleccionar campo" /></SelectTrigger>
                      <SelectContent>
                        {camposDisponibles[formulario.tabla].map(c => (
                          <SelectItem key={c.nombre} value={c.nombre}>{c.nombre} ({c.tipo})</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      value={formulario.campo}
                      onChange={(e) => setFormulario({ ...formulario, campo: e.target.value })}
                      placeholder="Ej: cedula, estado"
                    />
                  )}
                </div>
              </div>

              <div>
                <label className="text-sm font-medium block mb-1">Definición <span className="text-red-500">*</span></label>
                <Textarea
                  value={formulario.definicion}
                  onChange={(e) => setFormulario({ ...formulario, definicion: e.target.value })}
                  placeholder="Qué almacena este campo y cómo se usa..."
                  rows={2}
                />
              </div>

              <div>
                <label className="text-sm font-medium block mb-1">Tipo de dato</label>
                <Input
                  value={formulario.tipo_dato}
                  onChange={(e) => setFormulario({ ...formulario, tipo_dato: e.target.value })}
                  placeholder="Ej: VARCHAR, INTEGER, DATE"
                />
              </div>

              {/* Más opciones (colapsable) */}
              <div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="text-gray-600 -ml-2"
                  onClick={() => setMostrarMasOpciones(!mostrarMasOpciones)}
                >
                  {mostrarMasOpciones ? <ChevronUp className="h-4 w-4 mr-1" /> : <ChevronDown className="h-4 w-4 mr-1" />}
                  Más opciones
                </Button>
                {mostrarMasOpciones && (
                  <div className="mt-3 pl-2 border-l-2 border-gray-200 space-y-3">
                    <div className="flex flex-wrap gap-4">
                      <label className="flex items-center gap-2">
                        <input type="checkbox" checked={formulario.es_obligatorio} onChange={(e) => setFormulario({ ...formulario, es_obligatorio: e.target.checked })} className="rounded" />
                        <span className="text-sm">Obligatorio</span>
                      </label>
                      <label className="flex items-center gap-2">
                        <input type="checkbox" checked={formulario.tiene_indice} onChange={(e) => setFormulario({ ...formulario, tiene_indice: e.target.checked })} className="rounded" />
                        <span className="text-sm">Tiene índice</span>
                      </label>
                      <label className="flex items-center gap-2">
                        <input type="checkbox" checked={formulario.es_clave_foranea} onChange={(e) => setFormulario({ ...formulario, es_clave_foranea: e.target.checked })} className="rounded" />
                        <span className="text-sm">Clave foránea</span>
                      </label>
                    </div>
                    {formulario.es_clave_foranea && (
                      <div className="grid grid-cols-2 gap-2">
                        <Input value={formulario.tabla_referenciada} onChange={(e) => setFormulario({ ...formulario, tabla_referenciada: e.target.value })} placeholder="Tabla referenciada" />
                        <Input value={formulario.campo_referenciado} onChange={(e) => setFormulario({ ...formulario, campo_referenciado: e.target.value })} placeholder="Campo referenciado" />
                      </div>
                    )}
                    <div>
                      <label className="text-sm text-gray-600 block mb-1">Valores posibles (uno por línea)</label>
                      <Textarea value={formulario.valores_posibles} onChange={(e) => setFormulario({ ...formulario, valores_posibles: e.target.value })} placeholder="PENDIENTE&#10;PAGADO&#10;MORA" rows={2} className="text-sm" />
                    </div>
                    <div>
                      <label className="text-sm text-gray-600 block mb-1">Ejemplos (uno por línea)</label>
                      <Textarea value={formulario.ejemplos_valores} onChange={(e) => setFormulario({ ...formulario, ejemplos_valores: e.target.value })} placeholder="Ej: V123456789" rows={1} className="text-sm" />
                    </div>
                    <div>
                      <label className="text-sm text-gray-600 block mb-1">Notas</label>
                      <Input value={formulario.notas} onChange={(e) => setFormulario({ ...formulario, notas: e.target.value })} placeholder="Notas opcionales" />
                    </div>
                    <label className="flex items-center gap-2">
                      <input type="checkbox" checked={formulario.activo} onChange={(e) => setFormulario({ ...formulario, activo: e.target.checked })} className="rounded" />
                      <span className="text-sm">Activo</span>
                    </label>
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button variant="outline" onClick={() => { setMostrarFormulario(false); resetearFormulario(); setEditandoId(null); setMostrarMasOpciones(false) }}>
                  Cancelar
                </Button>
                <Button onClick={handleGuardar} disabled={guardando}>
                  {guardando ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Guardando...</> : 'Guardar'}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Lista de Definiciones */}
      {cargando || sincronizando ? (
        <Card>
          <CardContent className="pt-6 text-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-purple-600 mx-auto mb-4" />
            <p className="text-gray-600">
              {sincronizando 
                ? 'Sincronizando campos de la base de datos... Esto puede tomar unos momentos.'
                : 'Cargando definiciones de campos...'}
            </p>
          </CardContent>
        </Card>
      ) : definicionesFiltradas.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center py-12">
            <Database className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-600 mb-2 font-medium">
              {busqueda || filtroTabla !== 'todas' 
                ? 'No se encontraron definiciones con los filtros aplicados'
                : 'No hay definiciones de campos precargadas'}
            </p>
            {!busqueda && filtroTabla === 'todas' && (
              <>
                <p className="text-sm text-gray-500 mb-4">
                  {Object.keys(camposDisponibles).length > 0 
                    ? `Se detectaron ${Object.values(camposDisponibles).reduce((total, campos) => total + campos.length, 0)} campos disponibles en ${Object.keys(camposDisponibles).length} tablas.`
                    : 'No se detectaron campos disponibles en la base de datos.'}
                </p>
                <Button 
                  onClick={handleSincronizar} 
                  disabled={sincronizando}
                  className="mt-2"
                >
                  {sincronizando ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Sincronizando...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Sincronizar BD Ahora
                    </>
                  )}
                </Button>
              </>
            )}
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
                                <Key className="h-3 w-3 mr-1" />
                                Indexado
                              </Badge>
                            )}
                            {def.es_clave_foranea && (
                              <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200">
                                <Key className="h-3 w-3 mr-1" />
                                FK â†’ {def.tabla_referenciada}.{def.campo_referenciado}
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
                              ðŸ’¡ {def.notas}
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
