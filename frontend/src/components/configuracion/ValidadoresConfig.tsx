import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Play,
  RefreshCw,
  Phone,
  CreditCard,
  Calendar,
  Mail,
  Info,
  TestTube,
  CheckSquare,
  XSquare,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { configuracionService, ValidadoresConfig, PruebaValidadores } from '@/services/configuracionService'

export function ValidadoresConfig() {
  const [configuracion, setConfiguracion] = useState<ValidadoresConfig | null>(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Estado para pruebas
  const [pruebas, setPruebas] = useState<PruebaValidadores>({
    telefono: '',
    pais_telefono: 'VENEZUELA',
    cedula: '',
    pais_cedula: 'VENEZUELA',
    fecha: '',
    email: ''
  })
  const [resultadosPrueba, setResultadosPrueba] = useState<any>(null)
  const [ejecutandoPrueba, setEjecutandoPrueba] = useState(false)

  useEffect(() => {
    cargarConfiguracion()
  }, [])

  const cargarConfiguracion = async () => {
    try {
      setCargando(true)
      const config = await configuracionService.obtenerValidadores()
      setConfiguracion(config)
    } catch (err) {
      setError('Error al cargar la configuración de validadores')
      console.error('Error:', err)
    } finally {
      setCargando(false)
    }
  }

  const ejecutarPruebas = async () => {
    try {
      setEjecutandoPrueba(true)
      const datosPrueba = { ...pruebas }
      
      // Solo incluir campos que tengan valor
      Object.keys(datosPrueba).forEach(key => {
        if (!datosPrueba[key as keyof PruebaValidadores]) {
          delete datosPrueba[key as keyof PruebaValidadores]
        }
      })

      if (Object.keys(datosPrueba).length === 0) {
        setError('Por favor ingresa al menos un valor para probar')
        return
      }

      const resultados = await configuracionService.probarValidadores(datosPrueba)
      setResultadosPrueba(resultados)
    } catch (err) {
      setError('Error al ejecutar las pruebas')
      console.error('Error:', err)
    } finally {
      setEjecutandoPrueba(false)
    }
  }

  const limpiarPruebas = () => {
    setPruebas({
      telefono: '',
      pais_telefono: 'VENEZUELA',
      cedula: '',
      pais_cedula: 'VENEZUELA',
      fecha: '',
      email: ''
    })
    setResultadosPrueba(null)
  }

  if (cargando) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600">Cargando configuración...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center p-8">
        <AlertTriangle className="h-8 w-8 text-red-500" />
        <span className="ml-2 text-red-600">{error}</span>
        <Button onClick={cargarConfiguracion} variant="outline" className="ml-4">
          <RefreshCw className="h-4 w-4 mr-2" />
          Reintentar
        </Button>
      </div>
    )
  }

  if (!configuracion) {
    return null
  }

  const renderValidador = (tipo: string, config: any) => {
    const iconos = {
      telefono: Phone,
      cedula: CreditCard,
      fecha: Calendar,
      email: Mail
    }
    
    const IconComponent = iconos[tipo as keyof typeof iconos] || Info

    return (
      <Card key={tipo} className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center">
            <IconComponent className="mr-2 h-5 w-5" />
            {config.descripcion}
          </CardTitle>
          <CardDescription>
            {tipo === 'telefono' && 'Validación y formateo de números telefónicos'}
            {tipo === 'cedula' && 'Validación de cédulas por país'}
            {tipo === 'fecha' && 'Validación estricta de fechas'}
            {tipo === 'email' && 'Validación y normalización de emails'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Configuración específica por tipo */}
          {tipo === 'telefono' && config.paises_soportados?.venezuela && (
            <div className="bg-blue-50 p-4 rounded-lg">
              <h4 className="font-semibold text-blue-900 mb-2">🇻🇪 Venezuela</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <strong>Formato:</strong> {config.paises_soportados.venezuela.formato}
                </div>
                <div>
                  <strong>Requisitos:</strong>
                  <ul className="mt-1 space-y-1">
                    <li>• {config.paises_soportados.venezuela.requisitos.debe_empezar_por}</li>
                    <li>• {config.paises_soportados.venezuela.requisitos.longitud_total}</li>
                    <li>• {config.paises_soportados.venezuela.requisitos.primer_digito}</li>
                  </ul>
                </div>
              </div>
              
              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h5 className="font-medium text-green-700 mb-2">✅ Ejemplos Válidos</h5>
                  <ul className="text-sm space-y-1">
                    {config.paises_soportados.venezuela.ejemplos_validos.map((ejemplo, idx) => (
                      <li key={idx} className="font-mono bg-green-100 px-2 py-1 rounded">{ejemplo}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h5 className="font-medium text-red-700 mb-2">❌ Ejemplos Inválidos</h5>
                  <ul className="text-sm space-y-1">
                    {config.paises_soportados.venezuela.ejemplos_invalidos.map((ejemplo, idx) => (
                      <li key={idx} className="font-mono bg-red-100 px-2 py-1 rounded">{ejemplo}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {tipo === 'cedula' && config.paises_soportados?.venezuela && (
            <div className="bg-blue-50 p-4 rounded-lg">
              <h4 className="font-semibold text-blue-900 mb-2">🇻🇪 Venezuela</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <strong>Prefijos válidos:</strong> {config.paises_soportados.venezuela.prefijos_validos.join(', ')}
                </div>
                <div>
                  <strong>Longitud:</strong> {config.paises_soportados.venezuela.longitud}
                </div>
              </div>
              
              <div className="mt-4">
                <strong>Requisitos:</strong>
                <ul className="mt-1 space-y-1 text-sm">
                  <li>• {config.paises_soportados.venezuela.requisitos.prefijos}</li>
                  <li>• {config.paises_soportados.venezuela.requisitos.dígitos}</li>
                  <li>• {config.paises_soportados.venezuela.requisitos.longitud}</li>
                </ul>
              </div>
            </div>
          )}

          {tipo === 'fecha' && (
            <div className="bg-blue-50 p-4 rounded-lg">
              <h4 className="font-semibold text-blue-900 mb-2">📅 Formato DD/MM/YYYY</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <strong>Requisitos:</strong>
                  <ul className="mt-1 space-y-1">
                    <li>• {config.requisitos.dia}</li>
                    <li>• {config.requisitos.mes}</li>
                    <li>• {config.requisitos.año}</li>
                    <li>• {config.requisitos.separador}</li>
                  </ul>
                </div>
                <div>
                  <strong>Características:</strong>
                  <ul className="mt-1 space-y-1">
                    <li>• Validación estricta</li>
                    <li>• Verificación de fechas válidas</li>
                    <li>• Soporte para años bisiestos</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {tipo === 'email' && (
            <div className="bg-blue-50 p-4 rounded-lg">
              <h4 className="font-semibold text-blue-900 mb-2">📧 Validación RFC 5322</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <strong>Características:</strong>
                  <ul className="mt-1 space-y-1">
                    <li>• {config.caracteristicas.normalizacion}</li>
                    <li>• {config.caracteristicas.limpieza}</li>
                    <li>• {config.caracteristicas.validacion}</li>
                  </ul>
                </div>
                <div>
                  <strong>Dominios bloqueados:</strong>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {config.caracteristicas.dominios_bloqueados.slice(0, 3).map((dominio, idx) => (
                      <Badge key={idx} variant="destructive" className="text-xs">{dominio}</Badge>
                    ))}
                    {config.caracteristicas.dominios_bloqueados.length > 3 && (
                      <Badge variant="outline" className="text-xs">
                        +{config.caracteristicas.dominios_bloqueados.length - 3} más
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Configuración de comportamiento */}
          <div className="flex items-center space-x-4 text-sm">
            <Badge variant={config.auto_formateo ? "default" : "secondary"}>
              {config.auto_formateo ? "Auto-formateo" : "Sin auto-formateo"}
            </Badge>
            <Badge variant={config.validacion_tiempo_real ? "default" : "secondary"}>
              {config.validacion_tiempo_real ? "Validación en tiempo real" : "Validación manual"}
            </Badge>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Configuración de Validadores</h2>
          <p className="text-gray-600">Configuración y pruebas de los validadores del sistema</p>
        </div>
        <div className="flex space-x-2">
          <Button onClick={cargarConfiguracion} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Actualizar
          </Button>
        </div>
      </div>

      {/* Información general */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Info className="mr-2 h-5 w-5" />
            Información General
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <strong>Consultado por:</strong> {configuracion.consultado_por}
            </div>
            <div>
              <strong>Fecha consulta:</strong> {new Date(configuracion.fecha_consulta).toLocaleString()}
            </div>
            <div>
              <strong>Validadores disponibles:</strong> {Object.keys(configuracion.validadores_disponibles).length}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Validadores disponibles */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Validadores Disponibles</h3>
        <div className="space-y-4">
          {Object.entries(configuracion.validadores_disponibles).map(([tipo, config]) =>
            renderValidador(tipo, config)
          )}
        </div>
      </div>

      {/* Panel de pruebas */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <TestTube className="mr-2 h-5 w-5" />
            Panel de Pruebas
          </CardTitle>
          <CardDescription>
            Prueba los validadores con datos de ejemplo
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">Teléfono</label>
              <Input
                value={pruebas.telefono}
                onChange={(e) => setPruebas(prev => ({ ...prev, telefono: e.target.value }))}
                placeholder="1234567890"
              />
            </div>
            <div>
              <label className="text-sm font-medium">País (Teléfono)</label>
              <Select 
                value={pruebas.pais_telefono} 
                onValueChange={(value) => setPruebas(prev => ({ ...prev, pais_telefono: value }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="VENEZUELA">Venezuela</SelectItem>
                  <SelectItem value="DOMINICANA">República Dominicana</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">Cédula</label>
              <Input
                value={pruebas.cedula}
                onChange={(e) => setPruebas(prev => ({ ...prev, cedula: e.target.value }))}
                placeholder="V12345678"
              />
            </div>
            <div>
              <label className="text-sm font-medium">País (Cédula)</label>
              <Select 
                value={pruebas.pais_cedula} 
                onValueChange={(value) => setPruebas(prev => ({ ...prev, pais_cedula: value }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="VENEZUELA">Venezuela</SelectItem>
                  <SelectItem value="DOMINICANA">República Dominicana</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium">Fecha</label>
              <Input
                value={pruebas.fecha}
                onChange={(e) => setPruebas(prev => ({ ...prev, fecha: e.target.value }))}
                placeholder="DD/MM/YYYY"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Email</label>
              <Input
                value={pruebas.email}
                onChange={(e) => setPruebas(prev => ({ ...prev, email: e.target.value }))}
                placeholder="usuario@ejemplo.com"
              />
            </div>
          </div>

          <div className="flex space-x-2">
            <Button 
              onClick={ejecutarPruebas} 
              disabled={ejecutandoPrueba}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {ejecutandoPrueba ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              {ejecutandoPrueba ? 'Ejecutando...' : 'Ejecutar Pruebas'}
            </Button>
            <Button onClick={limpiarPruebas} variant="outline">
              Limpiar
            </Button>
          </div>

          {/* Resultados de pruebas */}
          {resultadosPrueba && (
            <div className="mt-6">
              <h4 className="font-semibold mb-3">Resultados de las Pruebas</h4>
              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">{resultadosPrueba.resumen.total_validados}</div>
                    <div className="text-sm text-gray-600">Total Validados</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">{resultadosPrueba.resumen.validos}</div>
                    <div className="text-sm text-gray-600">Válidos</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-red-600">{resultadosPrueba.resumen.invalidos}</div>
                    <div className="text-sm text-gray-600">Inválidos</div>
                  </div>
                </div>

                <div className="space-y-3">
                  {Object.entries(resultadosPrueba.resultados).map(([tipo, resultado]: [string, any]) => (
                    <div key={tipo} className="border rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <h5 className="font-medium capitalize">{tipo}</h5>
                        {resultado.valido ? (
                          <Badge className="bg-green-100 text-green-800">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Válido
                          </Badge>
                        ) : (
                          <Badge className="bg-red-100 text-red-800">
                            <XCircle className="h-3 w-3 mr-1" />
                            Inválido
                          </Badge>
                        )}
                      </div>
                      
                      <div className="text-sm space-y-1">
                        <div><strong>Original:</strong> {resultado.valor_original}</div>
                        {resultado.valor_formateado && (
                          <div><strong>Formateado:</strong> {resultado.valor_formateado}</div>
                        )}
                        {resultado.error && (
                          <div className="text-red-600"><strong>Error:</strong> {resultado.error}</div>
                        )}
                        {resultado.cambio_realizado && (
                          <div className="text-blue-600"><strong>Cambio aplicado:</strong> Sí</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Reglas de negocio */}
      <Card>
        <CardHeader>
          <CardTitle>Reglas de Negocio</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            {Object.entries(configuracion.reglas_negocio).map(([regla, descripcion]) => (
              <div key={regla} className="flex items-start space-x-2">
                <CheckSquare className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                <div>
                  <strong className="capitalize">{regla.replace(/_/g, ' ')}:</strong> {descripcion}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}
