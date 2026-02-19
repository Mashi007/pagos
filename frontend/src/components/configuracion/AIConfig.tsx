import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import { apiClient } from '../../services/api'
import { type AIConfigState } from '../../types/aiConfig'
import { AIConfigMain } from './AIConfigMain'

export function AIConfig() {
  const [config, setConfig] = useState<AIConfigState>({
    modelo: 'openai/gpt-4o-mini',
    temperatura: '0.7',
    max_tokens: '1000',
    activo: 'false',
  })

  const [guardando, setGuardando] = useState(false)
  const [configuracionCorrecta, setConfiguracionCorrecta] = useState(false)
  const [verificandoConfig, setVerificandoConfig] = useState(false)

  useEffect(() => {
    cargarConfiguracion()
  }, [])

  const cargarConfiguracion = async () => {
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
      setConfig(configCargada)
      setConfiguracionCorrecta(!!data.configured && (data.activo || 'true').toLowerCase() === 'true')
    } catch (error) {
      console.error('Error cargando configuración de AI:', error)
      toast.error('Error cargando configuración')
    }
  }

  const verificarConfiguracion = async (guardarAutomaticamente: boolean = false) => {
    setVerificandoConfig(true)
    try {
      const resultado = await apiClient.post<{ success: boolean; message?: string }>(
        '/api/v1/configuracion/ai/probar',
        { pregunta: 'Verificar conexión con OpenRouter' }
      )
      const esValida = !!resultado.success
      setConfiguracionCorrecta(esValida)
      if (esValida && guardarAutomaticamente) {
        try {
          await apiClient.put('/api/v1/configuracion/ai/configuracion', {
            modelo: config.modelo,
            temperatura: config.temperatura,
            max_tokens: config.max_tokens,
            activo: config.activo,
          })
          toast.success('Configuración verificada y guardada')
          await cargarConfiguracion()
        } catch (_saveError: any) {
          toast.error('Error al guardar. Guarda manualmente.')
        }
      }
      return esValida
    } catch (error: any) {
      setConfiguracionCorrecta(false)
      return false
    } finally {
      setVerificandoConfig(false)
    }
  }

  const handleChange = (campo: keyof AIConfigState, valor: string) => {
    setConfig(prev => ({ ...prev, [campo]: valor }))
  }

  const handleGuardar = async () => {
    setGuardando(true)
    try {
      const tokenParaEnviar = config.openai_api_key && config.openai_api_key !== '***'
        ? config.openai_api_key
        : '***'
      await apiClient.put('/api/v1/configuracion/ai/configuracion', {
        modelo: config.modelo,
        temperatura: config.temperatura,
        max_tokens: config.max_tokens,
        activo: config.activo,
        openai_api_key: tokenParaEnviar,
      })
      toast.success('Configuración de AI guardada')
      await cargarConfiguracion()
      if (config.activo === 'true') setConfiguracionCorrecta(true)
    } catch (error: any) {
      console.error('Error guardando configuración:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error guardando configuración'
      toast.error(mensajeError)
    } finally {
      setGuardando(false)
    }
  }

  const handleVerificarYGuardar = async () => {
    await verificarConfiguracion(true)
  }

  return (
    <AIConfigMain
      config={config}
      onConfigChange={handleChange}
      onSave={handleGuardar}
      onVerifyAndSave={handleVerificarYGuardar}
      configuracionCorrecta={configuracionCorrecta}
      verificandoConfig={verificandoConfig}
      guardando={guardando}
    />
  )
}
