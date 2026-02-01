import { useState, useEffect } from 'react'
import { FileText, Save, RotateCcw, Loader2, AlertCircle, Copy, Edit, Trash2 } from 'lucide-react'
import { Card, CardContent } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import { Badge } from '../../components/ui/badge'
import { toast } from 'sonner'
import { apiClient } from '../../services/api'

export function PromptEditor() {
  const [promptPersonalizado, setPromptPersonalizado] = useState('')
  const [cargandoPrompt, setCargandoPrompt] = useState(true)
  const [guardandoPrompt, setGuardandoPrompt] = useState(false)
  const [tienePromptPersonalizado, setTienePromptPersonalizado] = useState(false)
  const [mostrarPlaceholders, setMostrarPlaceholders] = useState(true)

  // Estados para variables personalizadas
  const [variablesPersonalizadas, setVariablesPersonalizadas] = useState<Array<{
    id: number
    variable: string
    descripcion: string
    activo: boolean
    orden: number
  }>>([])
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
        variables_personalizadas?: Array<{
          id: number
          variable: string
          descripcion: string
          activo: boolean
          orden: number
        }>
      }>('/api/v1/configuracion/ai/prompt')

      setPromptPersonalizado(data.prompt_personalizado || '')
      setTienePromptPersonalizado(data.tiene_prompt_personalizado)
      if (data.variables_personalizadas) {
        setVariablesPersonalizadas(data.variables_personalizadas)
      }
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
    if (!confirm('Â¿EstÃ¡s seguro de restaurar el prompt por defecto? Se perderÃ¡ el prompt personalizado.')) {
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
        variables: Array<{
          id: number
          variable: string
          descripcion: string
          activo: boolean
          orden: number
        }>
        total: number
      }>('/api/v1/configuracion/ai/prompt/variables')
      setVariablesPersonalizadas(data.variables || [])
    } catch (error) {
      console.error('Error cargando variables:', error)
      // No mostrar error si la tabla no existe aÃºn
    } finally {
      setCargandoVariables(false)
    }
  }

  const handleCrearVariable = async () => {
    if (!nuevaVariable.variable.trim() || !nuevaVariable.descripcion.trim()) {
      toast.error('Variable y descripciÃ³n son requeridos')
      return
    }

    // Validar formato de variable
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
      await cargarPrompt() // Recargar para incluir nuevas variables
    } catch (error: any) {
      console.error('Error creando variable:', error)
      toast.error(error?.response?.data?.detail || 'Error creando variable')
    } finally {
      setCreandoVariable(false)
    }
  }

  const handleIniciarEdicionVariable = (variable: typeof variablesPersonalizadas[0]) => {
    setEditandoVariable(variable.id)
    setVariableEditada({ variable: variable.variable, descripcion: variable.descripcion })
  }

  const handleCancelarEdicionVariable = () => {
    setEditandoVariable(null)
    setVariableEditada({ variable: '', descripcion: '' })
  }

  const handleActualizarVariable = async (id: number) => {
    if (!variableEditada.variable.trim() || !variableEditada.descripcion.trim()) {
      toast.error('Variable y descripciÃ³n son requeridos')
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
    if (!confirm('Â¿EstÃ¡s seguro de eliminar esta variable?')) return

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

  const promptTemplate = `Eres un ANALISTA ESPECIALIZADO en prÃ©stamos y cobranzas con capacidad de anÃ¡lisis de KPIs operativos. Tu funciÃ³n es proporcionar informaciÃ³n precisa, anÃ¡lisis de tendencias y mÃ©tricas clave basÃ¡ndote EXCLUSIVAMENTE en los datos almacenados en las bases de datos del sistema.

ROL Y CONTEXTO:
- Eres un analista especializado en prÃ©stamos y cobranzas con capacidad de anÃ¡lisis de KPIs operativos
- Tu funciÃ³n es proporcionar informaciÃ³n precisa, anÃ¡lisis de tendencias y mÃ©tricas clave
- Basas tus respuestas EXCLUSIVAMENTE en los datos almacenados en las bases de datos del sistema
- Tienes acceso a informaciÃ³n en tiempo real de la base de datos del sistema
- Proporcionas anÃ¡lisis, estadÃ­sticas y recomendaciones basadas en datos reales
- Eres profesional, claro y preciso en tus respuestas
- Proporcionas respuestas accionables con contexto e interpretaciÃ³n

RESTRICCIÃ“N IMPORTANTE: Solo puedes responder preguntas relacionadas con la base de datos del sistema. Si recibes una pregunta que NO estÃ© relacionada con clientes, prÃ©stamos, pagos, cuotas, cobranzas, moras, estadÃ­sticas del sistema, o la fecha/hora actual, debes responder:

"Lo siento, el Chat AI solo responde preguntas sobre la base de datos del sistema (clientes, prÃ©stamos, pagos, cuotas, cobranzas, moras, estadÃ­sticas, etc.). Para preguntas generales, por favor usa el Chat de Prueba en la configuraciÃ³n de AI."

Tienes acceso a informaciÃ³n de la base de datos del sistema y a la fecha/hora actual. AquÃ­ tienes un resumen actualizado:

=== RESUMEN DE BASE DE DATOS ===
{resumen_bd}
{info_cliente_buscado}
{datos_adicionales}
{info_esquema}

[El sistema incluirÃ¡ automÃ¡ticamente el inventario completo de campos, mapeo semÃ¡ntico, y documentos de contexto]

=== DOCUMENTOS DE CONTEXTO ADICIONAL ===
{contexto_documentos}
NOTA: Si hay documentos de contexto arriba, Ãºsalos como informaciÃ³n adicional para responder preguntas. Los documentos pueden contener polÃ­ticas, procedimientos, o informaciÃ³n relevante sobre el sistema.

CAPACIDADES PRINCIPALES:
1. **Consulta de datos individuales**: InformaciÃ³n de prÃ©stamos, clientes y pagos especÃ­ficos
2. **AnÃ¡lisis de KPIs**: Morosidad, recuperaciÃ³n, cartera en riesgo, efectividad de cobranza
3. **AnÃ¡lisis de tendencias**: Comparaciones temporales (aumentos/disminuciones)
4. **Proyecciones operativas**: CuÃ¡nto se debe cobrar hoy, esta semana, este mes
5. **SegmentaciÃ³n**: AnÃ¡lisis por rangos de mora, montos, productos, zonas
6. **AnÃ¡lisis de Machine Learning**: PredicciÃ³n de morosidad, segmentaciÃ³n de clientes, detecciÃ³n de anomalÃ­as, clustering de prÃ©stamos

REGLAS FUNDAMENTALES:
1. **SOLO usa datos reales**: Accede a los Ã­ndices de las bases de datos y consulta los campos especÃ­ficos necesarios
2. **NUNCA inventes informaciÃ³n**: Si un dato no existe en la base de datos, indica claramente que no estÃ¡ disponible
3. **Muestra tus cÃ¡lculos**: Cuando calcules KPIs, indica la fÃ³rmula y los valores utilizados
4. **Compara con contexto**: Para tendencias, muestra perÃ­odo actual vs perÃ­odo anterior
5. **Respuestas accionables**: Incluye el "Â¿quÃ© significa esto?" cuando sea relevante
6. **SOLO responde preguntas sobre la base de datos del sistema relacionadas con cobranzas y prÃ©stamos**
7. Si la pregunta NO es sobre la BD, responde con el mensaje de restricciÃ³n mencionado arriba

PROCESO DE ANÃLISIS:
1. Identifica quÃ© mÃ©trica o anÃ¡lisis solicita el usuario
2. Determina quÃ© tabla(s), campo(s) y perÃ­odo de tiempo necesitas
3. Accede a los datos y realiza los cÃ¡lculos necesarios
4. Compara con perÃ­odos anteriores si es relevante
5. Presenta resultados con contexto y conclusiones claras

OBJETIVO:
Tu objetivo es ser el asistente analÃ­tico que permita tomar decisiones informadas sobre la gestiÃ³n de prÃ©stamos y cobranzas, proporcionando anÃ¡lisis precisos, tendencias claras y mÃ©tricas accionables basadas exclusivamente en los datos reales del sistema.

RECUERDA: Si la pregunta NO es sobre la base de datos, debes rechazarla con el mensaje de restricciÃ³n.`

  if (cargandoPrompt) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Prompt Personalizado
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            {tienePromptPersonalizado
              ? 'âœ… Usando prompt personalizado'
              : 'â„¹ï¸ Usando prompt por defecto'}
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
              El sistema reemplazarÃ¡ automÃ¡ticamente estos placeholders con datos reales:
            </p>

            {/* Placeholders predeterminados */}
            <div className="bg-white rounded p-3 font-mono text-xs space-y-1 mb-3">
              <div className="font-semibold text-amber-900 mb-1">Predeterminados:</div>
              <div><code className="text-blue-600">{'{resumen_bd}'}</code> - Resumen de la base de datos</div>
              <div><code className="text-blue-600">{'{info_cliente_buscado}'}</code> - InformaciÃ³n del cliente si se busca por cÃ©dula</div>
              <div><code className="text-blue-600">{'{datos_adicionales}'}</code> - CÃ¡lculos y anÃ¡lisis adicionales</div>
              <div><code className="text-blue-600">{'{info_esquema}'}</code> - Esquema completo de la base de datos</div>
              <div><code className="text-blue-600">{'{contexto_documentos}'}</code> - Documentos de contexto adicionales</div>
            </div>

            {/* Variables personalizadas */}
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

            {/* GestiÃ³n de Variables Personalizadas */}
            {mostrarGestionVariables && (
              <div className="bg-white rounded-lg p-4 border border-amber-300 mt-3">
                <h4 className="font-semibold mb-3 flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  GestiÃ³n de Variables Personalizadas
                </h4>

                {/* Formulario para nueva variable */}
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
                    <p className="text-xs text-gray-500 mt-1">Se agregarÃ¡n llaves automÃ¡ticamente si no las incluyes</p>
                  </div>
                  <div>
                    <label className="text-xs font-medium block mb-1">DescripciÃ³n <span className="text-red-500">*</span></label>
                    <Input
                      value={nuevaVariable.descripcion}
                      onChange={(e) => setNuevaVariable(prev => ({ ...prev, descripcion: e.target.value }))}
                      placeholder="Describe quÃ© contiene esta variable"
                      className="text-xs"
                    />
                  </div>
                  <Button
                    onClick={handleCrearVariable}
                    disabled={creandoVariable || !nuevaVariable.variable.trim() || !nuevaVariable.descripcion.trim()}
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

                {/* Tabla de variables existentes */}
                {cargandoVariables ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                  </div>
                ) : variablesPersonalizadas.length === 0 ? (
                  <div className="text-center py-4 text-gray-500 text-sm">
                    No hay variables personalizadas. Agrega una arriba.
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="text-xs font-semibold text-gray-700 mb-2">Variables Existentes:</div>
                    {variablesPersonalizadas.map((varItem) => (
                      <div key={varItem.id} className="border rounded p-2 hover:bg-gray-50">
                        {editandoVariable === varItem.id ? (
                          <div className="space-y-2">
                            <div>
                              <label className="text-xs font-medium block mb-1">Variable</label>
                              <Input
                                value={variableEditada.variable}
                                onChange={(e) => setVariableEditada(prev => ({ ...prev, variable: e.target.value }))}
                                className="font-mono text-xs"
                                size={1}
                              />
                            </div>
                            <div>
                              <label className="text-xs font-medium block mb-1">DescripciÃ³n</label>
                              <Input
                                value={variableEditada.descripcion}
                                onChange={(e) => setVariableEditada(prev => ({ ...prev, descripcion: e.target.value }))}
                                className="text-xs"
                                size={1}
                              />
                            </div>
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                onClick={() => handleActualizarVariable(varItem.id)}
                                disabled={!variableEditada.variable.trim() || !variableEditada.descripcion.trim()}
                                className="text-xs h-7"
                              >
                                <Save className="h-3 w-3 mr-1" />
                                Guardar
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={handleCancelarEdicionVariable}
                                className="text-xs h-7"
                              >
                                Cancelar
                              </Button>
                            </div>
                          </div>
                        ) : (
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <code className="text-green-600 font-mono text-xs">{varItem.variable}</code>
                                <Badge variant={varItem.activo ? "default" : "secondary"} className="text-xs">
                                  {varItem.activo ? "Activo" : "Inactivo"}
                                </Badge>
                              </div>
                              <p className="text-xs text-gray-600">{varItem.descripcion}</p>
                            </div>
                            <div className="flex items-center gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleIniciarEdicionVariable(varItem)}
                                className="text-blue-600 hover:text-blue-700 h-7 w-7 p-0"
                                title="Editar variable"
                              >
                                <Edit className="h-3 w-3" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleEliminarVariable(varItem.id)}
                                className="text-red-600 hover:text-red-700 h-7 w-7 p-0"
                                title="Eliminar variable"
                              >
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
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
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium">Prompt Personalizado</label>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setMostrarPlaceholders(!mostrarPlaceholders)}
            >
              {mostrarPlaceholders ? 'Ocultar' : 'Mostrar'} Template
            </Button>
          </div>
        </div>

        {mostrarPlaceholders && !tienePromptPersonalizado && (
          <div className="mb-4 p-4 bg-gray-50 border rounded-lg">
            <p className="text-sm font-medium mb-2">Template de Prompt (para referencia):</p>
            <Textarea
              value={promptTemplate}
              readOnly
              className="font-mono text-xs h-40"
              onClick={(e) => (e.target as HTMLTextAreaElement).select()}
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPromptPersonalizado(promptTemplate)}
              className="mt-2"
            >
              Usar como Base
            </Button>
          </div>
        )}

        <Textarea
          value={promptPersonalizado}
          onChange={(e) => setPromptPersonalizado(e.target.value)}
          placeholder="Escribe tu prompt personalizado aquÃ­. AsegÃºrate de incluir los placeholders: {resumen_bd}, {info_cliente_buscado}, {datos_adicionales}, {info_esquema}, {contexto_documentos}"
          className="font-mono text-sm min-h-[500px]"
        />
        <p className="text-xs text-gray-500 mt-2">
          {promptPersonalizado.length} caracteres. El prompt debe incluir los placeholders mencionados arriba.
        </p>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          ðŸ’¡ <strong>Tip:</strong> Puedes personalizar el comportamiento del AI ajustando el prompt.
          Los placeholders se reemplazarÃ¡n automÃ¡ticamente con datos reales del sistema.
          Si dejas el prompt vacÃ­o, se usarÃ¡ el prompt por defecto.
        </p>
      </div>
    </div>
  )
}
