import { useState, useEffect } from 'react'
import { Save, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { Card, CardContent } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Badge } from '../../components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { toast } from 'sonner'
import { apiClient } from '../../services/api'
import { type AIConfigState } from '../../types/aiConfig'
import { OPENROUTER_MODELS } from '../../constants/aiModels'

interface ModelSelectionTabProps {
  config: AIConfigState
  onConfigChange: (campo: keyof AIConfigState, valor: string) => void
  onSave: () => Promise<void>
  onVerifyAndSave: () => Promise<void>
  configuracionCorrecta: boolean
  verificandoConfig: boolean
  guardando: boolean
}

export function ModelSelectionTab({
  config,
  onConfigChange,
  onSave,
  onVerifyAndSave,
  configuracionCorrecta,
  verificandoConfig,
  guardando,
}: ModelSelectionTabProps) {
  const [cargarConfiguracion, setCargarConfiguracion] = useState(false)
  const [mostrarToken, setMostrarToken] = useState(false)

  useEffect(() => {
    // Auto-load configuration on mount
    const loadConfig = async () => {
      try {
        const data = await apiClient.get<AIConfigState>('/api/v1/configuracion/ai/configuracion')
        const configCargada: AIConfigState = {
          configured: !!data.configured,
          provider: data.provider || 'openrouter',
          openai_api_key: data.openai_api_key ?? '',
          modelo_recomendado: data.modelo_recomendado || 'openai/gpt-4o-mini',
          modelo: data.modelo || 'openai/gpt-4o-mini',
          temperatura: data.temperatura || '0.7',
          max_tokens: data.max_tokens || '1000',
          activo: data.activo || 'false',
        }
        Object.entries(configCargada).forEach(([key, value]) => {
          onConfigChange(key as keyof AIConfigState, value)
        })
      } catch (error) {
        console.error('Error cargando configuración de AI:', error)
      }
    }

    if (!cargarConfiguracion) {
      loadConfig()
      setCargarConfiguracion(true)
    }
  }, [])

  return (
    <div className="space-y-4">
      {/* Estado: Configuración correcta */}
      {config.configured && configuracionCorrecta && (
        <div className="bg-white border-2 border-green-500 rounded-xl p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="flex flex-col items-center gap-1 flex-shrink-0">
              <div className="w-4 h-4 bg-green-500 rounded-full shadow-lg"></div>
              <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
              <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
            </div>
            <div className="flex-1">
              <p className="font-semibold text-gray-900">Configuración correcta</p>
              <p className="text-sm text-gray-600">
                OpenAI aceptó la conexión. Puedes usar AI para generar respuestas.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Estado: API Key no válida */}
      {config.configured && !configuracionCorrecta && !verificandoConfig && (
        <div className="bg-white border-2 border-amber-400 rounded-xl p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="flex flex-col items-center gap-1 flex-shrink-0">
              <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
              <div className="w-4 h-4 bg-amber-500 rounded-full shadow-lg"></div>
              <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
            </div>
            <div className="flex-1">
              <p className="font-semibold text-gray-900 mb-2">API Key no válida o no configurada</p>
              <div className="text-sm text-gray-600 space-y-1">
                <p>1. Ingresa tu API Key de OpenRouter en el campo de abajo (o obtén una en <a href="https://openrouter.ai/keys" target="_blank" rel="noopener noreferrer" className="underline text-blue-600">openrouter.ai/keys</a>)</p>
                <p>2. Activa el servicio AI y guarda</p>
                <p>3. El modelo recomendado es GPT-4o Mini (buen balance costo/velocidad)</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Estado: No configurado */}
      {!config.configured && (
        <div className="bg-white border-2 border-red-500 rounded-xl p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="flex flex-col items-center gap-1 flex-shrink-0">
              <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
              <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
              <div className="w-4 h-4 bg-red-500 rounded-full shadow-lg"></div>
            </div>
            <div className="flex-1">
              <p className="font-semibold text-gray-900">Configuración incompleta</p>
              <p className="text-sm text-gray-600">
                Ingresa tu API Key de OpenRouter en el campo de abajo y activa el servicio.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Toggle Activar/Desactivar AI */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <label className="text-sm font-semibold text-gray-900 block mb-1">Servicio de AI</label>
            <p className="text-xs text-gray-600">
              {config.activo === 'true'
                ? 'âœ… El sistema está usando AI para generar respuestas automáticas'
                : 'âš ï¸ El sistema NO usará AI. Activa el servicio para habilitar respuestas inteligentes.'}
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={config.activo === 'true'}
              onChange={async (e) => {
                const nuevoEstado = e.target.checked ? 'true' : 'false'
                onConfigChange('activo', nuevoEstado)
              }}
              className="sr-only peer toggle-input-peer"
            />
            <div className="toggle-switch-track-lg"></div>
            <span className="ml-3 text-sm font-medium text-gray-700">
              {config.activo === 'true' ? 'Activo' : 'Inactivo'}
            </span>
          </label>
        </div>
      </div>

      <Card className="shadow-sm border-gray-200">
        <CardContent className="pt-6 space-y-4">
          <div>
            <label className="text-sm font-medium block mb-2">API Key / Token (OpenRouter)</label>
            <Input
              type={mostrarToken ? 'text' : 'password'}
              autoComplete="off"
              value={config.openai_api_key === '***' ? '' : (config.openai_api_key ?? '')}
              onChange={(e) => onConfigChange('openai_api_key', e.target.value)}
              placeholder={config.openai_api_key === '***' ? '•••••••• (ya configurada — deja en blanco para no cambiar)' : 'Pega tu API key de OpenRouter'}
              className="font-mono text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">
              Obtén tu clave en <a href="https://openrouter.ai/keys" target="_blank" rel="noopener noreferrer" className="underline text-blue-600">openrouter.ai/keys</a>
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-sm font-medium block mb-2">Modelo (OpenRouter)</label>
              <Select value={config.modelo} onValueChange={(value) => onConfigChange('modelo', value)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {OPENROUTER_MODELS.map((m) => (
                    <SelectItem key={m.id} value={m.id}>
                      <span className="flex items-center gap-2">
                        {m.label}
                        {config.modelo_recomendado && m.id === config.modelo_recomendado && (
                          <Badge variant="secondary" className="text-xs">Recomendado</Badge>
                        )}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {config.modelo_recomendado && (
                <p className="text-xs text-gray-500 mt-1">Recomendado: GPT-4o Mini — buen balance costo y velocidad</p>
              )}
            </div>

            <div>
              <label className="text-sm font-medium block mb-2">Temperatura (0-2)</label>
              <Input
                type="number"
                step="0.1"
                min="0"
                max="2"
                value={config.temperatura}
                onChange={(e) => onConfigChange('temperatura', e.target.value)}
                placeholder="0.7"
              />
              <p className="text-xs text-gray-500 mt-1">Controla la creatividad. 0.7 es un buen balance.</p>
            </div>

            <div>
              <label className="text-sm font-medium block mb-2">Max Tokens (1-128000)</label>
              <Input
                type="number"
                min="1"
                max="128000"
                value={config.max_tokens}
                onChange={(e) => onConfigChange('max_tokens', e.target.value)}
                placeholder="1000"
              />
              <p className="text-xs text-gray-500 mt-1">Máximo de tokens en la respuesta.</p>
            </div>
          </div>

          <div className="flex gap-2 pt-4 border-t">
            <Button
              onClick={onSave}
              disabled={guardando}
              className={configuracionCorrecta && config.configured
                ? 'bg-green-600 hover:bg-green-700 text-white'
                : ''}
            >
              {guardando ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Guardando...
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  {configuracionCorrecta && config.configured
                    ? 'âœ… Guardar Configuración (Token Válido)'
                    : 'Guardar Configuración'}
                </>
              )}
            </Button>
            {config.configured && !configuracionCorrecta && (
              <Button
                onClick={onVerifyAndSave}
                disabled={verificandoConfig}
                variant="outline"
                className="border-blue-600 text-blue-600 hover:bg-blue-50"
              >
                {verificandoConfig ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Verificando...
                  </>
                ) : (
                  <>
                    <CheckCircle className="mr-2 h-4 w-4" />
                    Verificar y Guardar
                  </>
                )}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
