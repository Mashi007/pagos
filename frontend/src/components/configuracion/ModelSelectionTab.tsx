import { useState, useEffect } from 'react'

import { Save, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'

import { Card, CardContent } from '../../components/ui/card'

import { Button } from '../../components/ui/button'

import { Input } from '../../components/ui/input'

import { Badge } from '../../components/ui/badge'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select'

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
        const data = await apiClient.get<AIConfigState>(
          '/api/v1/configuracion/ai/configuracion'
        )

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
        <div className="rounded-xl border-2 border-green-500 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="flex flex-shrink-0 flex-col items-center gap-1">
              <div className="h-4 w-4 rounded-full bg-green-500 shadow-lg"></div>

              <div className="h-4 w-4 rounded-full bg-gray-200"></div>

              <div className="h-4 w-4 rounded-full bg-gray-200"></div>
            </div>

            <div className="flex-1">
              <p className="font-semibold text-gray-900">
                Configuración correcta
              </p>

              <p className="text-sm text-gray-600">
                OpenAI aceptó la conexión. Puedes usar AI para generar
                respuestas.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Estado: API Key no válida */}

      {config.configured && !configuracionCorrecta && !verificandoConfig && (
        <div className="rounded-xl border-2 border-amber-400 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="flex flex-shrink-0 flex-col items-center gap-1">
              <div className="h-4 w-4 rounded-full bg-gray-200"></div>

              <div className="h-4 w-4 rounded-full bg-amber-500 shadow-lg"></div>

              <div className="h-4 w-4 rounded-full bg-gray-200"></div>
            </div>

            <div className="flex-1">
              <p className="mb-2 font-semibold text-gray-900">
                API Key no válida o no configurada
              </p>

              <div className="space-y-1 text-sm text-gray-600">
                <p>
                  1. Ingresa tu API Key de OpenRouter en el campo de abajo (o
                  obtén una en{' '}
                  <a
                    href="https://openrouter.ai/keys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 underline"
                  >
                    openrouter.ai/keys
                  </a>
                  )
                </p>

                <p>2. Activa el servicio AI y guarda</p>

                <p>
                  3. El modelo recomendado es GPT-4o Mini (buen balance
                  costo/velocidad)
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Estado: No configurado */}

      {!config.configured && (
        <div className="rounded-xl border-2 border-red-500 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="flex flex-shrink-0 flex-col items-center gap-1">
              <div className="h-4 w-4 rounded-full bg-gray-200"></div>

              <div className="h-4 w-4 rounded-full bg-gray-200"></div>

              <div className="h-4 w-4 rounded-full bg-red-500 shadow-lg"></div>
            </div>

            <div className="flex-1">
              <p className="font-semibold text-gray-900">
                Configuración incompleta
              </p>

              <p className="text-sm text-gray-600">
                Ingresa tu API Key de OpenRouter en el campo de abajo y activa
                el servicio.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Toggle Activar/Desactivar AI */}

      <div className="rounded-xl border border-blue-200 bg-blue-50 p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <label className="mb-1 block text-sm font-semibold text-gray-900">
              Servicio de AI
            </label>

            <p className="text-xs text-gray-600">
              {config.activo === 'true'
                ? 'âœ… El sistema está usando AI para generar respuestas automáticas'
                : 'âš ï¸ El sistema NO usará AI. Activa el servicio para habilitar respuestas inteligentes.'}
            </p>
          </div>

          <label className="relative inline-flex cursor-pointer items-center">
            <input
              type="checkbox"
              checked={config.activo === 'true'}
              onChange={async e => {
                const nuevoEstado = e.target.checked ? 'true' : 'false'

                onConfigChange('activo', nuevoEstado)
              }}
              className="toggle-input-peer peer sr-only"
            />

            <div className="toggle-switch-track-lg"></div>

            <span className="ml-3 text-sm font-medium text-gray-700">
              {config.activo === 'true' ? 'Activo' : 'Inactivo'}
            </span>
          </label>
        </div>
      </div>

      <Card className="border-gray-200 shadow-sm">
        <CardContent className="space-y-4 pt-6">
          <div>
            <label className="mb-2 block text-sm font-medium">
              API Key / Token (OpenRouter)
            </label>

            <Input
              type={mostrarToken ? 'text' : 'password'}
              autoComplete="off"
              value={
                config.openai_api_key === '***'
                  ? ''
                  : (config.openai_api_key ?? '')
              }
              onChange={e => onConfigChange('openai_api_key', e.target.value)}
              placeholder={
                config.openai_api_key === '***'
                  ? '•••••••• (ya configurada - deja en blanco para no cambiar)'
                  : 'Pega tu API key de OpenRouter'
              }
              className="font-mono text-sm"
            />

            <p className="mt-1 text-xs text-gray-500">
              Obtén tu clave en{' '}
              <a
                href="https://openrouter.ai/keys"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 underline"
              >
                openrouter.ai/keys
              </a>
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium">
                Modelo (OpenRouter)
              </label>

              <Select
                value={config.modelo}
                onValueChange={value => onConfigChange('modelo', value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>

                <SelectContent>
                  {OPENROUTER_MODELS.map(m => (
                    <SelectItem key={m.id} value={m.id}>
                      <span className="flex items-center gap-2">
                        {m.label}

                        {config.modelo_recomendado &&
                          m.id === config.modelo_recomendado && (
                            <Badge variant="secondary" className="text-xs">
                              Recomendado
                            </Badge>
                          )}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {config.modelo_recomendado && (
                <p className="mt-1 text-xs text-gray-500">
                  Recomendado: GPT-4o Mini - buen balance costo y velocidad
                </p>
              )}
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">
                Temperatura (0-2)
              </label>

              <Input
                type="number"
                step="0.1"
                min="0"
                max="2"
                value={config.temperatura}
                onChange={e => onConfigChange('temperatura', e.target.value)}
                placeholder="0.7"
              />

              <p className="mt-1 text-xs text-gray-500">
                Controla la creatividad. 0.7 es un buen balance.
              </p>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">
                Max Tokens (1-128000)
              </label>

              <Input
                type="number"
                min="1"
                max="128000"
                value={config.max_tokens}
                onChange={e => onConfigChange('max_tokens', e.target.value)}
                placeholder="1000"
              />

              <p className="mt-1 text-xs text-gray-500">
                Máximo de tokens en la respuesta.
              </p>
            </div>
          </div>

          <div className="flex gap-2 border-t pt-4">
            <Button
              onClick={onSave}
              disabled={guardando}
              className={
                configuracionCorrecta && config.configured
                  ? 'bg-green-600 text-white hover:bg-green-700'
                  : ''
              }
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
