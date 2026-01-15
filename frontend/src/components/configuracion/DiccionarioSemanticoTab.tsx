import { useState, useEffect } from 'react'
import { BookOpen, Plus, Edit, Trash2, Search, Filter, CheckCircle, XCircle, Loader2, Info, Sparkles, Send, X } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { toast } from 'sonner'
import { apiClient } from '@/services/api'

interface DiccionarioSemantico {
  id: number
  palabra: string
  definicion: string
  categoria: string | null
  campo_relacionado: string | null
  tabla_relacionada: string | null
  sinonimos: string[]
  ejemplos_uso: string[]
  activo: boolean
  orden: number
  creado_en: string
  actualizado_en: string
}

export function DiccionarioSemanticoTab() {
  const [entradas, setEntradas] = useState<DiccionarioSemantico[]>([])
  const [cargando, setCargando] = useState(false)
  const [categorias, setCategorias] = useState<string[]>([])
  const [filtroCategoria, setFiltroCategoria] = useState<string>('todas')
  const [busqueda, setBusqueda] = useState('')
  const [mostrarFormulario, setMostrarFormulario] = useState(false)
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [guardando, setGuardando] = useState(false)
  
  // Estado para procesamiento con ChatGPT
  const [procesandoPalabra, setProcesandoPalabra] = useState<string | null>(null)
  const [mostrarModalProcesar, setMostrarModalProcesar] = useState(false)
  const [palabraProcesando, setPalabraProcesando] = useState<DiccionarioSemantico | null>(null)
  const [preguntaChatGPT, setPreguntaChatGPT] = useState<string>('')
  const [respuestaUsuario, setRespuestaUsuario] = useState<string>('')
  const [definicionMejorada, setDefinicionMejorada] = useState<string>('')
  const [procesando, setProcesando] = useState(false)

  const [formulario, setFormulario] = useState({
    palabra: '',
    definicion: '',
    categoria: '',
    campo_relacionado: '',
    tabla_relacionada: '',
    sinonimos: '',
    ejemplos_uso: '',
    activo: true,
    orden: 0,
  })

  useEffect(() => {
    cargarEntradas()
    cargarCategorias()
  }, [])

  const cargarEntradas = async () => {
    setCargando(true)
    try {
      const response = await apiClient.get<{ entradas: DiccionarioSemantico[], total: number }>(
        '/api/v1/configuracion/ai/diccionario-semantico'
      )
      setEntradas(response.data.entradas || [])
    } catch (error: any) {
      console.error('Error cargando diccionario:', error)
      toast.error('Error al cargar el diccionario semántico')
    } finally {
      setCargando(false)
    }
  }

  const cargarCategorias = async () => {
    try {
      const response = await apiClient.get<{ categorias: string[], total: number }>(
        '/api/v1/configuracion/ai/diccionario-semantico/categorias'
      )
      setCategorias(response.data.categorias || [])
    } catch (error: any) {
      console.error('Error cargando categorías:', error)
    }
  }

  const handleGuardar = async () => {
    if (!formulario.palabra.trim() || !formulario.definicion.trim()) {
      toast.error('Palabra y definición son obligatorios')
      return
    }

    setGuardando(true)
    try {
      const datos = {
        ...formulario,
        sinonimos: formulario.sinonimos.split('\n').filter(s => s.trim()),
        ejemplos_uso: formulario.ejemplos_uso.split('\n').filter(e => e.trim()),
        categoria: formulario.categoria || null,
        campo_relacionado: formulario.campo_relacionado || null,
        tabla_relacionada: formulario.tabla_relacionada || null,
      }

      if (editandoId) {
        await apiClient.put(`/api/v1/configuracion/ai/diccionario-semantico/${editandoId}`, datos)
        toast.success('Entrada actualizada exitosamente')
      } else {
        await apiClient.post('/api/v1/configuracion/ai/diccionario-semantico', datos)
        toast.success('Entrada creada exitosamente')
      }

      setMostrarFormulario(false)
      setEditandoId(null)
      resetearFormulario()
      cargarEntradas()
      cargarCategorias()
    } catch (error: any) {
      console.error('Error guardando:', error)
      toast.error(error?.response?.data?.detail || 'Error al guardar la entrada')
    } finally {
      setGuardando(false)
    }
  }

  const handleEditar = (entrada: DiccionarioSemantico) => {
    setFormulario({
      palabra: entrada.palabra,
      definicion: entrada.definicion,
      categoria: entrada.categoria || '',
      campo_relacionado: entrada.campo_relacionado || '',
      tabla_relacionada: entrada.tabla_relacionada || '',
      sinonimos: entrada.sinonimos.join('\n'),
      ejemplos_uso: entrada.ejemplos_uso.join('\n'),
      activo: entrada.activo,
      orden: entrada.orden,
    })
    setEditandoId(entrada.id)
    setMostrarFormulario(true)
  }

  const handleEliminar = async (id: number) => {
    if (!confirm('¿Estás seguro de eliminar esta entrada del diccionario?')) return

    try {
      await apiClient.delete(`/api/v1/configuracion/ai/diccionario-semantico/${id}`)
      toast.success('Entrada eliminada exitosamente')
      cargarEntradas()
    } catch (error: any) {
      console.error('Error eliminando:', error)
      toast.error(error?.response?.data?.detail || 'Error al eliminar la entrada')
    }
  }

  const handleToggleActivo = async (entrada: DiccionarioSemantico) => {
    try {
      await apiClient.put(`/api/v1/configuracion/ai/diccionario-semantico/${entrada.id}`, {
        activo: !entrada.activo,
      })
      toast.success(`Entrada ${!entrada.activo ? 'activada' : 'desactivada'}`)
      cargarEntradas()
    } catch (error: any) {
      console.error('Error cambiando estado:', error)
      toast.error('Error al cambiar el estado')
    }
  }

  const handleProcesarPalabra = async (entrada: DiccionarioSemantico) => {
    setPalabraProcesando(entrada)
    setMostrarModalProcesar(true)
    setPreguntaChatGPT('')
    setRespuestaUsuario('')
    setDefinicionMejorada('')
    setProcesando(true)

    try {
      const response = await apiClient.post<{
        success: boolean
        tipo: 'definicion_mejorada' | 'pregunta'
        definicion?: string
        pregunta?: string
        tokens_usados?: number
      }>('/api/v1/configuracion/ai/diccionario-semantico/procesar', {
        palabra: entrada.palabra,
        definicion_actual: entrada.definicion,
      })

      if (response.data.tipo === 'pregunta' && response.data.pregunta) {
        setPreguntaChatGPT(response.data.pregunta)
        toast.info('ChatGPT necesita más información')
      } else if (response.data.tipo === 'definicion_mejorada' && response.data.definicion) {
        setDefinicionMejorada(response.data.definicion)
        toast.success('Definición mejorada generada')
      }
    } catch (error: any) {
      console.error('Error procesando palabra:', error)
      toast.error(error?.response?.data?.detail || 'Error al procesar con ChatGPT')
    } finally {
      setProcesando(false)
    }
  }

  const handleEnviarRespuesta = async () => {
    if (!respuestaUsuario.trim() || !palabraProcesando) return

    setProcesando(true)
    try {
      const response = await apiClient.post<{
        success: boolean
        tipo: 'definicion_mejorada'
        definicion: string
        tokens_usados?: number
      }>('/api/v1/configuracion/ai/diccionario-semantico/procesar', {
        palabra: palabraProcesando.palabra,
        definicion_actual: palabraProcesando.definicion,
        respuesta_usuario: respuestaUsuario,
      })

      if (response.data.definicion) {
        setDefinicionMejorada(response.data.definicion)
        setPreguntaChatGPT('')
        setRespuestaUsuario('')
        toast.success('Definición mejorada generada')
      }
    } catch (error: any) {
      console.error('Error enviando respuesta:', error)
      toast.error(error?.response?.data?.detail || 'Error al procesar respuesta')
    } finally {
      setProcesando(false)
    }
  }

  const handleAplicarDefinicionMejorada = () => {
    if (!definicionMejorada || !palabraProcesando) return

    setFormulario({
      ...formulario,
      palabra: palabraProcesando.palabra,
      definicion: definicionMejorada,
      categoria: palabraProcesando.categoria || '',
      campo_relacionado: palabraProcesando.campo_relacionado || '',
      tabla_relacionada: palabraProcesando.tabla_relacionada || '',
      sinonimos: palabraProcesando.sinonimos.join('\n'),
      ejemplos_uso: palabraProcesando.ejemplos_uso.join('\n'),
      activo: palabraProcesando.activo,
      orden: palabraProcesando.orden,
    })
    setEditandoId(palabraProcesando.id)
    setMostrarFormulario(true)
    setMostrarModalProcesar(false)
    setDefinicionMejorada('')
    setPalabraProcesando(null)
    toast.success('Definición mejorada aplicada al formulario')
  }

  const resetearFormulario = () => {
    setFormulario({
      palabra: '',
      definicion: '',
      categoria: '',
      campo_relacionado: '',
      tabla_relacionada: '',
      sinonimos: '',
      ejemplos_uso: '',
      activo: true,
      orden: 0,
    })
  }

  const entradasFiltradas = entradas.filter(entrada => {
    const coincideBusqueda = !busqueda || 
      entrada.palabra.toLowerCase().includes(busqueda.toLowerCase()) ||
      entrada.definicion.toLowerCase().includes(busqueda.toLowerCase())
    const coincideCategoria = filtroCategoria === 'todas' || entrada.categoria === filtroCategoria
    return coincideBusqueda && coincideCategoria
  })

  const entradasPorCategoria = entradasFiltradas.reduce((acc, entrada) => {
    const cat = entrada.categoria || 'Sin categoría'
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(entrada)
    return acc
  }, {} as Record<string, DiccionarioSemantico[]>)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-blue-600" />
            Diccionario Semántico
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            Agrega palabras y definiciones para entrenar al AI a reconocer términos comunes
          </p>
        </div>
        <Button onClick={() => { resetearFormulario(); setMostrarFormulario(true); setEditandoId(null) }}>
          <Plus className="h-4 w-4 mr-2" />
          Agregar Palabra
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
                  placeholder="Buscar por palabra o definición..."
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={filtroCategoria} onValueChange={setFiltroCategoria}>
              <SelectTrigger className="w-48">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Categoría" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todas">Todas las categorías</SelectItem>
                {categorias.map(cat => (
                  <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Formulario */}
      {mostrarFormulario && (
        <Card className="border-blue-200">
          <CardContent className="pt-6">
            <h4 className="text-lg font-semibold mb-4">
              {editandoId ? 'Editar Entrada' : 'Nueva Entrada'}
            </h4>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium block mb-1">
                    Palabra <span className="text-red-500">*</span>
                  </label>
                  <Input
                    value={formulario.palabra}
                    onChange={(e) => setFormulario({ ...formulario, palabra: e.target.value })}
                    placeholder="Ej: cédula, pago, nombre"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium block mb-1">Categoría</label>
                  <Input
                    value={formulario.categoria}
                    onChange={(e) => setFormulario({ ...formulario, categoria: e.target.value })}
                    placeholder="Ej: identificacion, pagos"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-sm font-medium">
                    Definición <span className="text-red-500">*</span>
                  </label>
                  {formulario.palabra.trim() && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={async () => {
                        if (!formulario.palabra.trim()) {
                          toast.error('Primero ingresa una palabra')
                          return
                        }
                        setProcesando(true)
                        try {
                          const response = await apiClient.post<{
                            success: boolean
                            tipo: 'definicion_mejorada' | 'pregunta'
                            definicion?: string
                            pregunta?: string
                          }>('/api/v1/configuracion/ai/diccionario-semantico/procesar', {
                            palabra: formulario.palabra,
                            definicion_actual: formulario.definicion,
                          })

                          if (response.data.tipo === 'pregunta' && response.data.pregunta) {
                            // Abrir modal para pregunta
                            setPalabraProcesando({
                              id: 0,
                              palabra: formulario.palabra,
                              definicion: formulario.definicion,
                              categoria: formulario.categoria || null,
                              campo_relacionado: formulario.campo_relacionado || null,
                              tabla_relacionada: formulario.tabla_relacionada || null,
                              sinonimos: formulario.sinonimos.split('\n').filter(s => s.trim()),
                              ejemplos_uso: formulario.ejemplos_uso.split('\n').filter(e => e.trim()),
                              activo: formulario.activo,
                              orden: formulario.orden,
                              creado_en: '',
                              actualizado_en: '',
                            })
                            setPreguntaChatGPT(response.data.pregunta)
                            setMostrarModalProcesar(true)
                            toast.info('ChatGPT necesita más información')
                          } else if (response.data.tipo === 'definicion_mejorada' && response.data.definicion) {
                            setFormulario({ ...formulario, definicion: response.data.definicion })
                            toast.success('Definición mejorada aplicada')
                          }
                        } catch (error: any) {
                          console.error('Error procesando:', error)
                          toast.error(error?.response?.data?.detail || 'Error al procesar con ChatGPT')
                        } finally {
                          setProcesando(false)
                        }
                      }}
                      disabled={procesando}
                      className="text-blue-600 hover:text-blue-700"
                    >
                      {procesando ? (
                        <>
                          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                          Procesando...
                        </>
                      ) : (
                        <>
                          <Sparkles className="h-3 w-3 mr-1" />
                          Procesar con ChatGPT
                        </>
                      )}
                    </Button>
                  )}
                </div>
                <Textarea
                  value={formulario.definicion}
                  onChange={(e) => setFormulario({ ...formulario, definicion: e.target.value })}
                  placeholder="Describe qué significa esta palabra en el contexto del sistema..."
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium block mb-1">Campo Técnico Relacionado</label>
                  <Input
                    value={formulario.campo_relacionado}
                    onChange={(e) => setFormulario({ ...formulario, campo_relacionado: e.target.value })}
                    placeholder="Ej: cedula, nombres"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium block mb-1">Tabla Relacionada</label>
                  <Input
                    value={formulario.tabla_relacionada}
                    onChange={(e) => setFormulario({ ...formulario, tabla_relacionada: e.target.value })}
                    placeholder="Ej: clientes, pagos"
                  />
                </div>
              </div>

              <div>
                <label className="text-sm font-medium block mb-1">Sinónimos (uno por línea)</label>
                <Textarea
                  value={formulario.sinonimos}
                  onChange={(e) => setFormulario({ ...formulario, sinonimos: e.target.value })}
                  placeholder="documento&#10;DNI&#10;CI&#10;identificación"
                  rows={3}
                />
              </div>

              <div>
                <label className="text-sm font-medium block mb-1">Ejemplos de Uso (uno por línea)</label>
                <Textarea
                  value={formulario.ejemplos_uso}
                  onChange={(e) => setFormulario({ ...formulario, ejemplos_uso: e.target.value })}
                  placeholder="¿Cuál es el nombre del cliente con cédula V123456789?&#10;Buscar por documento V123456789"
                  rows={2}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={formulario.activo}
                      onChange={(e) => setFormulario({ ...formulario, activo: e.target.checked })}
                      className="rounded"
                    />
                    <span className="text-sm">Activo</span>
                  </label>
                </div>
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

      {/* Lista de Entradas */}
      {cargando ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      ) : entradasFiltradas.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center py-12">
            <BookOpen className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-600">
              {busqueda || filtroCategoria !== 'todas' 
                ? 'No se encontraron entradas con los filtros aplicados'
                : 'No hay entradas en el diccionario. Agrega la primera palabra.'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {Object.entries(entradasPorCategoria).map(([categoria, entradasCat]) => (
            <Card key={categoria}>
              <CardContent className="pt-6">
                <h4 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  {categoria}
                  <Badge variant="secondary">{entradasCat.length}</Badge>
                </h4>
                <div className="space-y-4">
                  {entradasCat.map(entrada => (
                    <div key={entrada.id} className="border rounded-lg p-4 hover:bg-gray-50">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h5 className="font-semibold text-lg">{entrada.palabra}</h5>
                            {entrada.activo ? (
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
                          </div>
                          <p className="text-gray-700 mb-2">{entrada.definicion}</p>
                          <div className="flex flex-wrap gap-2 text-sm text-gray-600">
                            {entrada.campo_relacionado && (
                              <Badge variant="secondary">Campo: {entrada.campo_relacionado}</Badge>
                            )}
                            {entrada.tabla_relacionada && (
                              <Badge variant="secondary">Tabla: {entrada.tabla_relacionada}</Badge>
                            )}
                            {entrada.sinonimos.length > 0 && (
                              <Badge variant="outline">
                                Sinónimos: {entrada.sinonimos.join(', ')}
                              </Badge>
                            )}
                          </div>
                          {entrada.ejemplos_uso.length > 0 && (
                            <div className="mt-2 text-sm text-gray-500">
                              <Info className="h-3 w-3 inline mr-1" />
                              Ejemplos: {entrada.ejemplos_uso.slice(0, 2).join('; ')}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-2 ml-4">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleProcesarPalabra(entrada)}
                            title="Procesar con ChatGPT"
                            className="text-blue-600 hover:text-blue-700"
                          >
                            <Sparkles className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleToggleActivo(entrada)}
                            title={entrada.activo ? 'Desactivar' : 'Activar'}
                          >
                            {entrada.activo ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEditar(entrada)}
                            title="Editar"
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEliminar(entrada.id)}
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

      {/* Modal de Procesamiento con ChatGPT */}
      <Dialog open={mostrarModalProcesar} onOpenChange={setMostrarModalProcesar}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-blue-600" />
              Procesar Palabra con ChatGPT
            </DialogTitle>
            <DialogDescription>
              {palabraProcesando && (
                <span className="font-semibold text-lg">{palabraProcesando.palabra}</span>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 mt-4">
            {/* Definición Actual */}
            {palabraProcesando && (
              <div className="bg-gray-50 p-4 rounded-lg">
                <h4 className="font-medium text-sm text-gray-700 mb-2">Definición Actual:</h4>
                <p className="text-gray-600">{palabraProcesando.definicion || '(sin definir)'}</p>
              </div>
            )}

            {/* Pregunta de ChatGPT */}
            {preguntaChatGPT && (
              <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg">
                <div className="flex items-start gap-2 mb-2">
                  <Sparkles className="h-5 w-5 text-blue-600 mt-0.5" />
                  <div className="flex-1">
                    <h4 className="font-medium text-sm text-blue-900 mb-2">ChatGPT pregunta:</h4>
                    <p className="text-blue-800">{preguntaChatGPT}</p>
                  </div>
                </div>
                <div className="mt-4">
                  <Textarea
                    value={respuestaUsuario}
                    onChange={(e) => setRespuestaUsuario(e.target.value)}
                    placeholder="Escribe tu respuesta aquí..."
                    rows={3}
                    className="mb-2"
                  />
                  <Button
                    onClick={handleEnviarRespuesta}
                    disabled={!respuestaUsuario.trim() || procesando}
                    className="w-full"
                  >
                    {procesando ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Procesando...
                      </>
                    ) : (
                      <>
                        <Send className="h-4 w-4 mr-2" />
                        Enviar Respuesta
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Definición Mejorada */}
            {definicionMejorada && (
              <div className="bg-green-50 border border-green-200 p-4 rounded-lg">
                <div className="flex items-start gap-2 mb-2">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <div className="flex-1">
                    <h4 className="font-medium text-sm text-green-900 mb-2">Definición Mejorada:</h4>
                    <p className="text-green-800 whitespace-pre-wrap">{definicionMejorada}</p>
                  </div>
                </div>
                <div className="mt-4 flex gap-2">
                  <Button
                    onClick={handleAplicarDefinicionMejorada}
                    className="flex-1 bg-green-600 hover:bg-green-700"
                  >
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Aplicar Definición
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setDefinicionMejorada('')
                      setPreguntaChatGPT('')
                      setRespuestaUsuario('')
                    }}
                  >
                    Descartar
                  </Button>
                </div>
              </div>
            )}

            {/* Loading */}
            {procesando && !preguntaChatGPT && !definicionMejorada && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
                <span className="ml-3 text-gray-600">Procesando con ChatGPT...</span>
              </div>
            )}

            {/* Botón Cerrar */}
            <div className="flex justify-end pt-4 border-t">
              <Button variant="outline" onClick={() => {
                setMostrarModalProcesar(false)
                setPreguntaChatGPT('')
                setRespuestaUsuario('')
                setDefinicionMejorada('')
                setPalabraProcesando(null)
              }}>
                Cerrar
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
