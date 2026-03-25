import { useState, useEffect } from 'react'

import { motion } from 'framer-motion'

import { CheckCircle, XCircle, PlayCircle, RefreshCw } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import { Button } from '../components/ui/button'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'

import { Input } from '../components/ui/input'

import { Badge } from '../components/ui/badge'

import {
  validadoresService,
  ConfiguracionValidadores,
} from '../services/validadoresService'

export function Validadores() {
  const [campoTest, setCampoTest] = useState('')

  const [valorTest, setValorTest] = useState('')

  const [resultadoTest, setResultadoTest] = useState<any>(null)

  const [isLoading, setIsLoading] = useState(false)

  const [configuracion, setConfiguracion] =
    useState<ConfiguracionValidadores | null>(null)

  const [loadingConfig, setLoadingConfig] = useState(true)

  // Cargar configuración al montar el componente

  useEffect(() => {
    const cargarConfiguracion = async () => {
      try {
        const config = await validadoresService.obtenerConfiguracion()

        setConfiguracion(config)
      } catch (error) {
        console.error('Error cargando configuración:', error)
      } finally {
        setLoadingConfig(false)
      }
    }

    cargarConfiguracion()
  }, [])

  // Limpiar valor y resultado cuando cambia el campo a validar

  useEffect(() => {
    setValorTest('')

    setResultadoTest(null)
  }, [campoTest])

  const handleTestValidacion = async () => {
    setIsLoading(true)

    try {
      // Mapear campos del dropdown a nombres del backend

      const campoMapper: Record<string, string> = {
        cedula: 'cedula_venezuela',

        telefono_venezuela: 'telefono_venezuela',

        email: 'email',

        fecha: 'fecha',

        monto: 'monto',

        nombre: 'nombre',

        apellido: 'apellido',
      }

      const campoBackend = campoMapper[campoTest] || campoTest

      const resultado = await validadoresService.validarCampo(
        campoBackend,
        valorTest,
        'VENEZUELA'
      )

      setResultadoTest(resultado)
    } catch (error) {
      console.error('Error probando validador:', error)

      setResultadoTest({ error: 'Error al probar validador' })
    } finally {
      setIsLoading(false)
    }
  }

  const validadoresDisponibles = [
    {
      nombre: 'Cédula',

      campo: 'cedula',

      formato: 'V/E/J + 7-10 dígitos',

      ejemplo: 'V12345678',

      descripcion: 'Valida y formatea cédulas venezolanas',
    },

    {
      nombre: 'Teléfono',

      campo: 'telefono_venezuela',

      formato: '+58 + 10 dígitos (NO empieza por 0)',

      ejemplo: '+58 1234567890 o 1234567890',

      descripcion:
        'Valida y formatea teléfonos venezolanos. Se agrega +58 automáticamente. Cualquier orden válido de 10 dígitos (NO empieza por 0).',
    },

    {
      nombre: 'Email',

      campo: 'email',

      formato: 'usuario@dominio.com',

      ejemplo: 'usuario@ejemplo.com',

      descripcion: 'Valida formato RFC 5322, sin espacios/comas, minúsculas',
    },

    {
      nombre: 'Fecha',

      campo: 'fecha',

      formato: 'DD/MM/YYYY',

      ejemplo: '15/03/2024',

      descripcion: 'Valida fechas DD/MM/YYYY, auto-completado, año 4 dígitos',
    },

    {
      nombre: 'Monto',

      campo: 'monto',

      formato:
        'Formato europeo estricto: punto cada 3 desde derecha, coma decimal',

      ejemplo: '1.000,12 o 10.500,25',

      descripcion:
        'Sistema europeo estricto: punto (.) cada 3 dígitos desde la derecha para miles (obligatorio si > 999), coma (,) para decimales. Rango: 1-20000.',
    },

    {
      nombre: 'Nombre',

      campo: 'nombre',

      formato: '1-2 palabras, solo primera letra mayúscula',

      ejemplo: 'JUAN PEDRO -> Juan pedro',

      descripcion:
        'Auto-convierte a formato correcto. Solo la primera letra del texto en mayúscula, resto en minúscula.',
    },

    {
      nombre: 'Apellido',

      campo: 'apellido',

      formato: '1-2 palabras, solo primera letra mayúscula',

      ejemplo: 'PEREZ GONZALEZ -> Perez gonzalez',

      descripcion:
        'Auto-convierte a formato correcto. Solo la primera letra del texto en mayúscula, resto en minúscula.',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}

      <ModulePageHeader
        icon={CheckCircle}
        title="Validadores"
        description="Configuración y prueba de validadores del sistema"
      />

      {/* Sección: Probar Validadores */}

      <div className="grid gap-6 md:grid-cols-2">
        {/* Panel de prueba */}

        <Card>
          <CardHeader>
            <CardTitle>Probar Validador</CardTitle>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Campo a validar</label>

              <select
                className="w-full rounded-lg border px-3 py-2"
                value={campoTest}
                onChange={e => {
                  setCampoTest(e.target.value)

                  setValorTest('')

                  setResultadoTest(null)
                }}
              >
                <option value="">Seleccionar campo...</option>

                {validadoresDisponibles.map(v => (
                  <option key={v.campo} value={v.campo}>
                    {v.nombre} ({v.formato})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Valor a probar</label>

              <Input
                value={valorTest}
                onChange={e => setValorTest(e.target.value)}
                placeholder="Ingrese el valor..."
              />
            </div>

            <Button
              onClick={handleTestValidacion}
              disabled={!campoTest || !valorTest || isLoading}
              className="w-full"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Validando...
                </>
              ) : (
                <>
                  <PlayCircle className="mr-2 h-4 w-4" />
                  Probar Validación
                </>
              )}
            </Button>

            {resultadoTest && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-4"
              >
                <Card
                  className={
                    resultadoTest.validacion?.valido
                      ? 'border-green-500 bg-green-50'
                      : 'border-red-500 bg-red-50'
                  }
                >
                  <CardContent className="pt-4">
                    <div className="flex items-start space-x-3">
                      {resultadoTest.validacion?.valido ? (
                        <CheckCircle className="h-5 w-5 text-green-600" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-600" />
                      )}

                      <div className="flex-1">
                        <p className="font-medium">
                          {resultadoTest.validacion?.valido
                            ? 'âœ… Válido'
                            : 'âŒ Inválido'}
                        </p>

                        {resultadoTest.validacion?.error && (
                          <p className="mt-1 text-sm font-medium text-red-700">
                            <strong>Error:</strong>{' '}
                            {resultadoTest.validacion.error}
                          </p>
                        )}

                        {resultadoTest.validacion?.formato_esperado && (
                          <p className="mt-2 text-sm text-gray-700">
                            <strong>Formato esperado:</strong>{' '}
                            {resultadoTest.validacion.formato_esperado}
                          </p>
                        )}

                        {resultadoTest.validacion?.sugerencia && (
                          <p className="mt-2 rounded bg-blue-50 p-2 text-sm font-medium text-blue-700">
                            <strong>ðŸ'¡ Sugerencia:</strong>{' '}
                            {resultadoTest.validacion.sugerencia}
                          </p>
                        )}

                        {resultadoTest.validacion?.valor_formateado && (
                          <p className="mt-2 text-sm text-gray-600">
                            <strong>Valor formateado:</strong>{' '}
                            {resultadoTest.validacion.valor_formateado}
                          </p>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </CardContent>
        </Card>

        {/* Panel de validadores disponibles */}

        <Card>
          <CardHeader>
            <CardTitle>Validadores Disponibles</CardTitle>
          </CardHeader>

          <CardContent>
            <div className="space-y-3">
              {validadoresDisponibles.map(validador => (
                <motion.div
                  key={validador.campo}
                  whileHover={{ scale: 1.02 }}
                  className="cursor-pointer rounded-lg border p-3 transition-colors hover:border-primary"
                  onClick={() => {
                    setCampoTest(validador.campo)

                    setValorTest('')

                    setResultadoTest(null)
                  }}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-medium text-gray-900">
                        {validador.nombre}
                      </h4>

                      <p className="mt-1 text-sm text-gray-500">
                        {validador.descripcion}
                      </p>

                      <div className="mt-2 flex items-center space-x-4">
                        <Badge variant="outline" className="text-xs">
                          {validador.formato}
                        </Badge>

                        <span className="text-xs text-gray-400">
                          Ej: {validador.ejemplo}
                        </span>
                      </div>
                    </div>

                    <CheckCircle className="h-5 w-5 text-green-500" />
                  </div>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Sección: Configuración */}

      <div>
        <Card>
          <CardHeader>
            <CardTitle>Configuración de Validadores</CardTitle>
          </CardHeader>

          <CardContent>
            <div className="space-y-6">
              {/* País configurado */}

              <div>
                <h3 className="mb-3 font-medium text-gray-900">
                  País Configurado
                </h3>

                <Badge variant="outline" className="px-4 py-2 text-lg">
                  ðŸ‡»ðŸ‡ª Venezuela
                </Badge>
              </div>

              {/* Moneda configurada */}

              <div>
                <h3 className="mb-3 font-medium text-gray-900">Moneda</h3>

                <div className="flex gap-2">
                  <Badge variant="default" className="px-4 py-2 text-lg">
                    ðŸ'µ USD - Dólar Americano
                  </Badge>

                  <Badge variant="outline" className="px-4 py-2 text-lg">
                    ðŸ'° Bs. - Bolívares (Venezuela)
                  </Badge>
                </div>
              </div>

              {/* Endpoints disponibles */}

              <div>
                <h3 className="mb-3 font-medium text-gray-900">
                  Endpoints Disponibles
                </h3>

                <div className="space-y-2">
                  <div className="flex items-center justify-between rounded bg-gray-50 p-2">
                    <code className="text-xs">
                      POST /api/v1/validadores/validar-campo
                    </code>

                    <Badge>Validación en tiempo real</Badge>
                  </div>

                  <div className="flex items-center justify-between rounded bg-gray-50 p-2">
                    <code className="text-xs">
                      POST /api/v1/validadores/formatear-tiempo-real
                    </code>

                    <Badge>Formateo automático</Badge>
                  </div>

                  <div className="flex items-center justify-between rounded bg-gray-50 p-2">
                    <code className="text-xs">
                      GET /api/v1/validadores/configuracion
                    </code>

                    <Badge>Configuración</Badge>
                  </div>

                  <div className="flex items-center justify-between rounded bg-gray-50 p-2">
                    <code className="text-xs">
                      GET /api/v1/validadores/ejemplos-correccion
                    </code>

                    <Badge>Ejemplos</Badge>
                  </div>

                  <div className="flex items-center justify-between rounded bg-gray-50 p-2">
                    <code className="text-xs">
                      GET /api/v1/validadores/detectar-errores-masivo
                    </code>

                    <Badge variant="outline">Diagnóstico masivo</Badge>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default Validadores
