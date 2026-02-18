import { useState, useRef } from 'react'
import {
  Plus,
  Zap,
  Download,
  Loader2,
} from 'lucide-react'
import { Card, CardContent } from '../../ui/card'
import { Button } from '../../ui/button'
import { Input } from '../../ui/input'
import { Textarea } from '../../ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select'
import { toast } from 'sonner'

export interface ConversationFormsProps {
  tablasYCampos: Record<string, string[]>
  cargandoTablasCampos: boolean
  ultimaActualizacion: string
  onCargarTablasCampos: () => Promise<void>
  onCreate: (pregunta: string, respuesta: string) => Promise<void>
  onMejorarPregunta: (pregunta: string) => Promise<string>
  onMejorarRespuesta: (respuesta: string) => Promise<string>
  onMejorarConversacion: (pregunta: string, respuesta: string) => Promise<{ pregunta: string; respuesta: string }>
}

export function ConversationForms({
  tablasYCampos,
  cargandoTablasCampos,
  ultimaActualizacion,
  onCargarTablasCampos,
  onCreate,
  onMejorarPregunta,
  onMejorarRespuesta,
  onMejorarConversacion,
}: ConversationFormsProps) {
  const [mostrarFormulario, setMostrarFormulario] = useState(false)
  const [pregunta, setPregunta] = useState('')
  const [respuesta, setRespuesta] = useState('')
  const [guardando, setGuardando] = useState(false)
  const [mejorando, setMejorando] = useState<'pregunta' | 'respuesta' | 'conversacion' | null>(null)

  const [tablaSeleccionada, setTablaSeleccionada] = useState<string>('')
  const [campoSeleccionado, setCampoSeleccionado] = useState<string>('')
  const [textareaActivo, setTextareaActivo] = useState<'pregunta' | 'respuesta' | null>(null)

  const preguntaTextareaRef = useRef<HTMLTextAreaElement>(null)
  const respuestaTextareaRef = useRef<HTMLTextAreaElement>(null)

  const camposDisponibles = tablaSeleccionada ? (tablasYCampos[tablaSeleccionada] || []) : []

  const insertarEnTextarea = (texto: string) => {
    let textarea: HTMLTextAreaElement | null = null
    let valor: string
    let setValue: (value: string) => void

    if (textareaActivo === 'pregunta' || document.activeElement === preguntaTextareaRef.current) {
      textarea = preguntaTextareaRef.current
      valor = pregunta
      setValue = setPregunta
    } else {
      textarea = respuestaTextareaRef.current
      valor = respuesta
      setValue = setRespuesta
    }

    if (!textarea) {
      toast.error('Por favor, haz clic en un campo de texto primero')
      return
    }

    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const nuevoValor = valor.substring(0, start) + texto + valor.substring(end)
    setValue(nuevoValor)

    setTimeout(() => {
      const nuevaPosicion = start + texto.length
      textarea?.setSelectionRange(nuevaPosicion, nuevaPosicion)
      textarea?.focus()
    }, 0)
  }

  const handleInsertarTabla = () => {
    if (!tablaSeleccionada) return
    insertarEnTextarea(`[${tablaSeleccionada}]`)
  }

  const handleInsertarCampo = () => {
    if (!campoSeleccionado) return
    insertarEnTextarea(`{${campoSeleccionado}}`)
  }

  const handleCrearConversacion = async () => {
    if (!pregunta.trim() || !respuesta.trim()) {
      toast.error('Por favor completa pregunta y respuesta')
      return
    }

    setGuardando(true)
    try {
      await onCreate(pregunta, respuesta)
      setPregunta('')
      setRespuesta('')
      setMostrarFormulario(false)
    } finally {
      setGuardando(false)
    }
  }

  const handleMejorarPregunta = async () => {
    if (!pregunta.trim()) {
      toast.error('Por favor ingresa una pregunta')
      return
    }

    setMejorando('pregunta')
    try {
      const mejorada = await onMejorarPregunta(pregunta)
      setPregunta(mejorada)
      toast.success('Pregunta mejorada')
    } finally {
      setMejorando(null)
    }
  }

  const handleMejorarRespuesta = async () => {
    if (!respuesta.trim()) {
      toast.error('Por favor ingresa una respuesta')
      return
    }

    setMejorando('respuesta')
    try {
      const mejorada = await onMejorarRespuesta(respuesta)
      setRespuesta(mejorada)
      toast.success('Respuesta mejorada')
    } finally {
      setMejorando(null)
    }
  }

  const handleMejorarConversacionCompleta = async () => {
    if (!pregunta.trim() || !respuesta.trim()) {
      toast.error('Por favor completa pregunta y respuesta')
      return
    }

    setMejorando('conversacion')
    try {
      const resultado = await onMejorarConversacion(pregunta, respuesta)
      setPregunta(resultado.pregunta)
      setRespuesta(resultado.respuesta)
      toast.success('Conversación mejorada')
    } finally {
      setMejorando(null)
    }
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <h4 className="font-semibold text-lg flex items-center gap-2">
              <Plus className="h-5 w-5" />
              Nueva Conversación
            </h4>
            <Button
              size="sm"
              variant={mostrarFormulario ? 'default' : 'outline'}
              onClick={() => setMostrarFormulario(!mostrarFormulario)}
            >
              {mostrarFormulario ? 'Ocultar' : 'Crear'}
            </Button>
          </div>

          {mostrarFormulario && (
            <div className="space-y-4 pt-4 border-t">
              {/* Table and Field Insertion */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <div className="flex items-center justify-between mb-3">
                  <h5 className="text-sm font-medium text-blue-900">Insertar Tabla o Campo</h5>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={onCargarTablasCampos}
                    disabled={cargandoTablasCampos}
                    className="shrink-0"
                  >
                    {cargandoTablasCampos ? (
                      <>
                        <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                        Cargando...
                      </>
                    ) : (
                      <>
                        <Download className="h-3 w-3 mr-1" />
                        Actualizar
                      </>
                    )}
                  </Button>
                </div>

                {ultimaActualizacion && (
                  <p className="text-xs text-gray-500 mb-3">
                    Última actualización: {new Date(ultimaActualizacion).toLocaleString('es-ES')}
                    ({Object.keys(tablasYCampos).length} tablas)
                  </p>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {/* Table Selector */}
                  <div className="space-y-2">
                    <label className="text-xs font-medium text-gray-600">Tabla</label>
                    <div className="flex gap-2">
                      <Select value={tablaSeleccionada} onValueChange={setTablaSeleccionada}>
                        <SelectTrigger className="flex-1">
                          <SelectValue placeholder="Selecciona una tabla" />
                        </SelectTrigger>
                        <SelectContent>
                          {Object.keys(tablasYCampos).length === 0 ? (
                            <div className="px-2 py-1.5 text-sm text-gray-500">
                              {cargandoTablasCampos ? 'Cargando tablas...' : 'No hay tablas disponibles'}
                            </div>
                          ) : (
                            Object.keys(tablasYCampos).map((tabla) => (
                              <SelectItem key={tabla} value={tabla}>
                                {tabla}
                              </SelectItem>
                            ))
                          )}
                        </SelectContent>
                      </Select>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={handleInsertarTabla}
                        disabled={!tablaSeleccionada}
                        className="shrink-0"
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Insertar
                      </Button>
                    </div>
                  </div>

                  {/* Field Selector */}
                  <div className="space-y-2">
                    <label className="text-xs font-medium text-gray-600">Campo</label>
                    <div className="flex gap-2">
                      <Select
                        value={campoSeleccionado}
                        onValueChange={setCampoSeleccionado}
                        disabled={!tablaSeleccionada}
                      >
                        <SelectTrigger className="flex-1">
                          <SelectValue
                            placeholder={
                              tablaSeleccionada ? 'Selecciona un campo' : 'Selecciona tabla primero'
                            }
                          />
                        </SelectTrigger>
                        <SelectContent>
                          {camposDisponibles.length === 0 ? (
                            <div className="px-2 py-1.5 text-sm text-gray-500">
                              {!tablaSeleccionada ? 'Selecciona una tabla primero' : 'No hay campos disponibles'}
                            </div>
                          ) : (
                            camposDisponibles.map((campo) => (
                              <SelectItem key={campo} value={campo}>
                                {campo}
                              </SelectItem>
                            ))
                          )}
                        </SelectContent>
                      </Select>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={handleInsertarCampo}
                        disabled={!campoSeleccionado}
                        className="shrink-0"
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Insertar
                      </Button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Question Input */}
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-2">Pregunta</label>
                <Textarea
                  ref={preguntaTextareaRef}
                  value={pregunta}
                  onChange={(e) => setPregunta(e.target.value)}
                  onFocus={() => setTextareaActivo('pregunta')}
                  placeholder="Ingresa la pregunta..."
                  rows={3}
                  className="text-sm"
                />
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handleMejorarPregunta}
                  disabled={mejorando !== null || !pregunta.trim()}
                  className="mt-2 gap-2"
                >
                  <Zap className="h-4 w-4" />
                  {mejorando === 'pregunta' ? 'Mejorando...' : 'Mejorar con IA'}
                </Button>
              </div>

              {/* Response Input */}
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-2">Respuesta</label>
                <Textarea
                  ref={respuestaTextareaRef}
                  value={respuesta}
                  onChange={(e) => setRespuesta(e.target.value)}
                  onFocus={() => setTextareaActivo('respuesta')}
                  placeholder="Ingresa la respuesta..."
                  rows={3}
                  className="text-sm"
                />
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handleMejorarRespuesta}
                  disabled={mejorando !== null || !respuesta.trim()}
                  className="mt-2 gap-2"
                >
                  <Zap className="h-4 w-4" />
                  {mejorando === 'respuesta' ? 'Mejorando...' : 'Mejorar con IA'}
                </Button>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2">
                <Button
                  onClick={handleCrearConversacion}
                  disabled={guardando || !pregunta.trim() || !respuesta.trim()}
                  className="flex-1"
                >
                  {guardando ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                      Guardando...
                    </>
                  ) : (
                    <>
                      <Plus className="h-4 w-4 mr-1" />
                      Crear Conversación
                    </>
                  )}
                </Button>
                <Button
                  variant="ghost"
                  onClick={handleMejorarConversacionCompleta}
                  disabled={mejorando !== null || !pregunta.trim() || !respuesta.trim()}
                  className="gap-2"
                >
                  <Zap className="h-4 w-4" />
                  {mejorando === 'conversacion' ? 'Mejorando...' : 'Mejorar Todo'}
                </Button>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
