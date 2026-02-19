import { useState, useEffect } from 'react'
import { FileText, Save, RotateCcw, Copy, Edit, Trash2, Loader2, AlertCircle } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import { Badge } from '../../components/ui/badge'
import { toast } from 'sonner'
import { apiClient } from '../../services/api'

interface Variable {
  id: number
  variable: string
  descripcion: string
  activo: boolean
  orden: number
}

export function PromptConfigTab() {
  const [promptPersonalizado, setPromptPersonalizado] = useState('')
  const [cargandoPrompt, setCargandoPrompt] = useState(true)
  const [guardandoPrompt, setGuardandoPrompt] = useState(false)
  const [tienePromptPersonalizado, setTienePromptPersonalizado] = useState(false)
  const [mostrarPlaceholders, setMostrarPlaceholders] = useState(true)
  const [variablesPersonalizadas, setVariablesPersonalizadas] = useState<Variable[]>([])
  const [cargandoVariables, setCargandoVariables] = useState(false)
  const [mostrarGestionVariables, setMostrarGestionVariables] = useState(false)
  const [nuevaVariable, setNuevaVariable] = useState({ variable: '', descripcion: '' })
  const [creandoVariable, setCreandoVariable] = useState(false)
  const [editandoVariable, setEditandoVariable] = useState<number | null>(null)
  const [variableEditada, setVariableEditada] = useState({ variable: '', descripcion: '' })

  useEffect(() => {
    cargarPrompt()
    cargarVariables()
  }, [])

  const cargarPrompt = async () => {
    setCargandoPrompt(true)
    try {
      const data = await apiClient.get<{
        prompt_personalizado: string
        tiene_prompt_personalizado: boolean
        usando_prompt_default: boolean
      }>('/api/v1/configuracion/ai/prompt')

      setPromptPersonalizado(data.prompt_personalizado || '')
      setTienePromptPersonalizado(data.tiene_prompt_personalizado)
    } catch (error) {
      console.error('Error cargando prompt:', error)
      toast.error('Error cargando prompt')
    } finally {
      setCargandoPrompt(false)
    }
  }

  const handleGuardarPrompt = async () => {
    setGuardandoPrompt(true)
    try {
      await apiClient.put('/api/v1/configuracion/ai/prompt', {
        prompt: promptPersonalizado
      })
      toast.success('âœ… Prompt personalizado guardado exitosamente')
      await cargarPrompt()
    } catch (error: any) {
      console.error('Error guardando prompt:', error)
      const errorDetail = error?.response?.data?.detail || error?.message || 'Error guardando prompt'
      toast.error(errorDetail)
    } finally {
      setGuardandoPrompt(false)
    }
  }

  const handleRestaurarDefault = async () => {
    if (!confirm('¿Estás seguro de restaurar el prompt por defecto? Se perderá el prompt personalizado.')) {
      return
    }

    setGuardandoPrompt(true)
    try {
      await apiClient.put('/api/v1/configuracion/ai/prompt', {
        prompt: ''
      })
      toast.success('âœ… Prompt restaurado al valor por defecto')
      await cargarPrompt()
    } catch (error: any) {
      console.error('Error restaurando prompt:', error)
      toast.error('Error restaurando prompt')
    } finally {
      setGuardandoPrompt(false)
    }
  }

  const cargarVariables = async () => {
    setCargandoVariables(true)
    try {
      const data = await apiClient.get<{
        variables: Variable[]
        total: number
      }>('/api/v1/configuracion/ai/prompt/variables')
      setVariablesPersonalizadas(data.variables || [])
    } catch (error) {
      console.error('Error cargando variables:', error)
    } finally {
      setCargandoVariables(false)
    }
  }

  const handleCrearVariable = async () => {
    if (!nuevaVariable.variable.trim() || !nuevaVariable.descripcion.trim()) {
      toast.error('Variable y descripción son requeridos')
      return
    }

    let variable = nuevaVariable.variable.trim()
    if (!variable.startsWith('{') || !variable.endsWith('}')) {
      variable = `{${variable.replace(/[{}]/g, '')}}`
    }

    setCreandoVariable(true)
    try {
      await apiClient.post('/api/v1/configuracion/ai/prompt/variables', {
        variable,
        descripcion: nuevaVariable.descripcion.trim(),
        activo: true,
        orden: variablesPersonalizadas.length,
      })
      toast.success('Variable creada exitosamente')
      setNuevaVariable({ variable: '', descripcion: '' })
      await cargarVariables()
      await cargarPrompt()
    } catch (error: any) {
      console.error('Error creando variable:', error)
      toast.error(error?.response?.data?.detail || 'Error creando variable')
    } finally {
      setCreandoVariable(false)
    }
  }

  const handleActualizarVariable = async (id: number) => {
    if (!variableEditada.variable.trim() || !variableEditada.descripcion.trim()) {
      toast.error('Variable y descripción son requeridos')
      return
    }

    let variable = variableEditada.variable.trim()
    if (!variable.startsWith('{') || !variable.endsWith('}')) {
      variable = `{${variable.replace(/[{}]/g, '')}}`
    }

    try {
      await apiClient.put(`/api/v1/configuracion/ai/prompt/variables/${id}`, {
        variable,
        descripcion: variableEditada.descripcion.trim(),
      })
      toast.success('Variable actualizada exitosamente')
      setEditandoVariable(null)
      setVariableEditada({ variable: '', descripcion: '' })
      await cargarVariables()
      await cargarPrompt()
    } catch (error: any) {
      console.error('Error actualizando variable:', error)
      toast.error(error?.response?.data?.detail || 'Error actualizando variable')
    }
  }

  const handleEliminarVariable = async (id: number) => {
    if (!confirm('¿Estás seguro de eliminar esta variable?')) return

    try {
      await apiClient.delete(`/api/v1/configuracion/ai/prompt/variables/${id}`)
      toast.success('Variable eliminada exitosamente')
      await cargarVariables()
      await cargarPrompt()
    } catch (error: any) {
      console.error('Error eliminando variable:', error)
      toast.error(error?.response?.data?.detail || 'Error eliminando variable')
    }
  }

  const handleCopiarPlaceholders = () => {
    const placeholdersDefault = `{resumen_bd}
{info_cliente_buscado}
{datos_adicionales}
{info_esquema}
{contexto_documentos}`

    const placeholdersPersonalizados = variablesPersonalizadas
      .filter(v => v.activo)
      .map(v => v.variable)
      .join('\n')

    const todos = placeholdersDefault + (placeholdersPersonalizados ? '\n' + placeholdersPersonalizados : '')
    navigator.clipboard.writeText(todos)
    toast.success('Placeholders copiados al portapapeles')
  }

  if (cargandoPrompt) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Prompt Personalizado
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            {tienePromptPersonalizado
              ? 'âœ… Usando prompt personalizado'
              : 'â„¹ï¸ Usando prompt por defecto'}
          </p>
        </div>
        <div className="flex gap-2">
          {tienePromptPersonalizado && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleRestaurarDefault}
              disabled={guardandoPrompt}
            >
              <RotateCcw className="h-4 w-4 mr-2" />
              Restaurar Default
            </Button>
          )}
          <Button
            onClick={handleGuardarPrompt}
            disabled={guardandoPrompt}
          >
            {guardandoPrompt ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Guardando...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Guardar Prompt
              </>
            )}
          </Button>
        </div>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
        <div className="flex items-start gap-2">
          <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <div className="flex items-center justify-between mb-1">
              <p className="font-semibold text-amber-900">Placeholders Disponibles</p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setMostrarGestionVariables(!mostrarGestionVariables)}
                className="text-xs"
              >
                {mostrarGestionVariables ? 'Ocultar' : 'Gestionar Variables'}
              </Button>
            </div>
            <p className="text-sm text-amber-800 mb-2">
              El sistema reemplazará automáticamente estos placeholders con datos reales:
            </p>

            <div className="bg-white rounded p-3 font-mono text-xs space-y-1 mb-3">
              <div className="font-semibold text-amber-900 mb-1">Predeterminados:</div>
              <div><code className="text-blue-600">{'{resumen_bd}'}</code> - Resumen de la base de datos</div>
              <div><code className="text-blue-600">{'{info_cliente_buscado}'}</code> - Información del cliente si se busca</div>
              <div><code className="text-blue-600">{'{datos_adicionales}'}</code> - Cálculos y análisis adicionales</div>
              <div><code className="text-blue-600">{'{info_esquema}'}</code> - Esquema completo de la base de datos</div>
              <div><code className="text-blue-600">{'{contexto_documentos}'}</code> - Documentos de contexto adicionales</div>
            </div>

            {variablesPersonalizadas.length > 0 && (
              <div className="bg-white rounded p-3 font-mono text-xs space-y-1 mb-3">
                <div className="font-semibold text-green-700 mb-1">Personalizadas:</div>
                {variablesPersonalizadas.filter(v => v.activo).map((varItem) => (
                  <div key={varItem.id}>
                    <code className="text-green-600">{varItem.variable}</code> - {varItem.descripcion}
                  </div>
                ))}
              </div>
            )}

            {mostrarGestionVariables && (
              <div className="bg-white rounded-lg p-4 border border-amber-300 mt-3">
                <h4 className="font-semibold mb-3 flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Gestión de Variables Personalizadas
                </h4>

                <div className="border rounded-lg p-3 mb-4 space-y-3">
                  <h5 className="font-medium text-sm">Nueva Variable</h5>
                  <div>
                    <label className="text-xs font-medium block mb-1">Variable <span className="text-red-500">*</span></label>
                    <Input
                      value={nuevaVariable.variable}
                      onChange={(e) => setNuevaVariable(prev => ({ ...prev, variable: e.target.value }))}
                      placeholder="Ej: {mi_variable} o mi_variable"
                      className="font-mono text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium block mb-1">Descripción <span className="text-red-500">*</span></label>
                    <Input
                      value={nuevaVariable.descripcion}
                      onChange={(e) => setNuevaVariable(prev => ({ ...prev, descripcion: e.target.value }))}
                      placeholder="Describe qué contiene esta variable"
                      className="text-xs"
                    />
                  </div>
                  <Button
                    onClick={handleCrearVariable}
                    disabled={creandoVariable}
                    size="sm"
                    className="w-full"
                  >
                    {creandoVariable ? (
                      <>
                        <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                        Creando...
                      </>
                    ) : (
                      <>
                        <FileText className="h-3 w-3 mr-1" />
                        Agregar Variable
                      </>
                    )}
                  </Button>
                </div>

                {cargandoVariables ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                  </div>
                ) : variablesPersonalizadas.length > 0 ? (
                  <div className="space-y-2">
                    {variablesPersonalizadas.map((varItem) => (
                      <div key={varItem.id} className="border rounded p-2 hover:bg-gray-50">
                        {editandoVariable === varItem.id ? (
                          <div className="space-y-2">
                            <Input
                              value={variableEditada.variable}
                              onChange={(e) => setVariableEditada(prev => ({ ...prev, variable: e.target.value }))}
                              className="font-mono text-xs"
                              size={1}
                            />
                            <Input
                              value={variableEditada.descripcion}
                              onChange={(e) => setVariableEditada(prev => ({ ...prev, descripcion: e.target.value }))}
                              className="text-xs"
                              size={1}
                            />
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                onClick={() => handleActualizarVariable(varItem.id)}
                                className="text-xs h-7"
                              >
                                <Save className="h-3 w-3 mr-1" />
                                Guardar
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setEditandoVariable(null)}
                                className="text-xs h-7"
                              >
                                Cancelar
                              </Button>
                            </div>
                          </div>
                        ) : (
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <code className="text-green-600 font-mono text-xs">{varItem.variable}</code>
                              <Badge variant={varItem.activo ? "default" : "secondary"} className="text-xs ml-2">
                                {varItem.activo ? "Activo" : "Inactivo"}
                              </Badge>
                              <p className="text-xs text-gray-600 mt-1">{varItem.descripcion}</p>
                            </div>
                            <div className="flex items-center gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setEditandoVariable(varItem.id)
                                  setVariableEditada({ variable: varItem.variable, descripcion: varItem.descripcion })
                                }}
                                className="text-blue-600 hover:text-blue-700 h-7 w-7 p-0"
                              >
                                <Edit className="h-3 w-3" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleEliminarVariable(varItem.id)}
                                className="text-red-600 hover:text-red-700 h-7 w-7 p-0"
                              >
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            )}

            <Button
              variant="outline"
              size="sm"
              onClick={handleCopiarPlaceholders}
              className="mt-2"
            >
              <Copy className="h-4 w-4 mr-2" />
              Copiar Placeholders
            </Button>
          </div>
        </div>
      </div>

      <div>
        <label className="text-sm font-medium block mb-2">Prompt Personalizado</label>
        <Textarea
          value={promptPersonalizado}
          onChange={(e) => setPromptPersonalizado(e.target.value)}
          placeholder="Escribe tu prompt personalizado aquí. Asegúrate de incluir los placeholders requeridos."
          className="font-mono text-sm min-h-[400px]"
        />
        <p className="text-xs text-gray-500 mt-2">
          {promptPersonalizado.length} caracteres
        </p>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          ðŸ'¡ <strong>Tip:</strong> Puedes personalizar el comportamiento del AI ajustando el prompt.
          Los placeholders se reemplazarán automáticamente con datos reales del sistema.
        </p>
      </div>
    </div>
  )
}
