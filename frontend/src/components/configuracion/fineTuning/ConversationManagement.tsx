import { useState } from 'react'
import {
  Heart,
  Edit,
  Save,
  Trash2,
  Download,
  Upload,
  MessageSquare,
} from 'lucide-react'
import { Card, CardContent } from '../../ui/card'
import { Button } from '../../ui/button'
import { Input } from '../../ui/input'
import { Textarea } from '../../ui/textarea'
import { Badge } from '../../ui/badge'
import { ConversacionAI } from '../../../services/aiTrainingService'
import { toast } from 'sonner'

export interface ConversationManagementProps {
  conversaciones: ConversacionAI[]
  cargando: boolean
  onRate: (conversacionId: number, calificacion: number, feedback: string) => Promise<void>
  onDelete: (conversacionId: number) => Promise<void>
  onEdit: (conversacionId: number, pregunta: string, respuesta: string) => Promise<void>
  onExport: () => void
  onImport: (event: React.ChangeEvent<HTMLInputElement>) => Promise<void>
  fileInputRef: React.RefObject<HTMLInputElement>
}

export function ConversationManagement({
  conversaciones,
  cargando,
  onRate,
  onDelete,
  onEdit,
  onExport,
  onImport,
  fileInputRef,
}: ConversationManagementProps) {
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [preguntaEditada, setPreguntaEditada] = useState('')
  const [respuestaEditada, setRespuestaEditada] = useState('')
  const [calificandoId, setCalificandoId] = useState<number | null>(null)
  const [calificacion, setCalificacion] = useState(0)
  const [feedback, setFeedback] = useState('')
  const [actualizando, setActualizando] = useState(false)

  const handleIniciarEdicion = (conversacion: ConversacionAI) => {
    setEditandoId(conversacion.id)
    setPreguntaEditada(conversacion.pregunta)
    setRespuestaEditada(conversacion.respuesta)
  }

  const handleCancelarEdicion = () => {
    setEditandoId(null)
    setPreguntaEditada('')
    setRespuestaEditada('')
  }

  const handleGuardarEdicion = async (conversacionId: number) => {
    setActualizando(true)
    try {
      await onEdit(conversacionId, preguntaEditada, respuestaEditada)
      handleCancelarEdicion()
    } finally {
      setActualizando(false)
    }
  }

  const handleCalificar = async (conversacionId: number) => {
    if (calificacion === 0) {
      toast.error('Por favor selecciona una calificación')
      return
    }

    try {
      await onRate(conversacionId, calificacion, feedback)
      setCalificandoId(null)
      setCalificacion(0)
      setFeedback('')
    } catch (error) {
      console.error('Error calificando:', error)
    }
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={onExport}
          disabled={conversaciones.length === 0}
          className="gap-2"
        >
          <Download className="h-4 w-4" />
          Exportar JSON
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => fileInputRef.current?.click()}
          className="gap-2"
        >
          <Upload className="h-4 w-4" />
          Importar JSON
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          onChange={onImport}
          style={{ display: 'none' }}
        />
      </div>

      {/* Conversations List */}
      {cargando ? (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center text-gray-500">Cargando conversaciones...</div>
          </CardContent>
        </Card>
      ) : conversaciones.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center text-gray-500">
              <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-40" />
              <p>No hay conversaciones registradas</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {conversaciones.map((conversacion) => (
            <Card key={conversacion.id} className="relative">
              <CardContent className="pt-4">
                {editandoId === conversacion.id ? (
                  // Edit mode
                  <div className="space-y-3">
                    <div>
                      <label className="text-sm font-medium text-gray-700 block mb-1">Pregunta</label>
                      <Textarea
                        value={preguntaEditada}
                        onChange={(e) => setPreguntaEditada(e.target.value)}
                        rows={2}
                        className="text-sm"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-700 block mb-1">Respuesta</label>
                      <Textarea
                        value={respuestaEditada}
                        onChange={(e) => setRespuestaEditada(e.target.value)}
                        rows={2}
                        className="text-sm"
                      />
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => handleGuardarEdicion(conversacion.id)}
                        disabled={actualizando}
                        className="flex-1"
                      >
                        <Save className="h-4 w-4 mr-1" />
                        Guardar
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={handleCancelarEdicion}
                        disabled={actualizando}
                        className="flex-1"
                      >
                        Cancelar
                      </Button>
                    </div>
                  </div>
                ) : calificandoId === conversacion.id ? (
                  // Rating mode
                  <div className="space-y-3">
                    <div>
                      <label className="text-sm font-medium text-gray-700 mb-2 block">
                        Calificación (1-5 estrellas)
                      </label>
                      <div className="flex gap-1">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <button
                            key={star}
                            onClick={() => setCalificacion(star)}
                            className={`text-2xl transition ${
                              star <= calificacion ? 'text-yellow-400' : 'text-gray-300'
                            }`}
                          >
                            ★
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-700 block mb-1">Feedback (opcional)</label>
                      <Textarea
                        value={feedback}
                        onChange={(e) => setFeedback(e.target.value)}
                        placeholder="Comentarios sobre la conversación..."
                        rows={2}
                        className="text-sm"
                      />
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => handleCalificar(conversacion.id)}
                        className="flex-1"
                      >
                        <Heart className="h-4 w-4 mr-1" />
                        Calificar
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setCalificandoId(null)
                          setCalificacion(0)
                          setFeedback('')
                        }}
                        className="flex-1"
                      >
                        Cancelar
                      </Button>
                    </div>
                  </div>
                ) : (
                  // Display mode
                  <div className="space-y-2">
                    <div>
                      <p className="text-xs text-gray-500 font-medium mb-1">PREGUNTA</p>
                      <p className="text-sm text-gray-900">{conversacion.pregunta}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 font-medium mb-1">RESPUESTA</p>
                      <p className="text-sm text-gray-900">{conversacion.respuesta}</p>
                    </div>
                    <div className="flex gap-2 items-center justify-between pt-2 border-t">
                      <div className="flex gap-2 items-center flex-wrap">
                        {conversacion.calificacion && (
                          <Badge variant="secondary" className="text-xs">
                            ★ {conversacion.calificacion}/5
                          </Badge>
                        )}
                        {conversacion.modelo_usado && (
                          <Badge variant="outline" className="text-xs">
                            {conversacion.modelo_usado}
                          </Badge>
                        )}
                      </div>
                      <div className="flex gap-1">
                        {!conversacion.calificacion && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setCalificandoId(conversacion.id)}
                            title="Calificar"
                          >
                            <Heart className="h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleIniciarEdicion(conversacion)}
                          title="Editar"
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onDelete(conversacion.id)}
                          title="Eliminar"
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
