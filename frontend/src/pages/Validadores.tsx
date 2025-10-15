import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Search,
  FileText,
  Settings,
  PlayCircle,
  RefreshCw,
  Download
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export function Validadores() {
  const [campoTest, setCampoTest] = useState('')
  const [valorTest, setValorTest] = useState('')
  const [resultadoTest, setResultadoTest] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleTestValidacion = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('/api/v1/validadores/validar-campo', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token') || sessionStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          campo: campoTest,
          valor: valorTest,
          pais: 'VENEZUELA'
        })
      })
      
      const data = await response.json()
      setResultadoTest(data)
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
      formato: 'V/E/J + 6-8 dígitos',
      ejemplo: 'V12345678',
      descripcion: 'Valida y formatea cédulas venezolanas'
    },
    {
      nombre: 'Teléfono',
      campo: 'telefono',
      formato: '+58 + 10 dígitos',
      ejemplo: '+58 424 1234567',
      descripcion: 'Valida y formatea teléfonos venezolanos'
    },
    {
      nombre: 'Email',
      campo: 'email',
      formato: 'usuario@dominio.com',
      ejemplo: 'usuario@ejemplo.com',
      descripcion: 'Valida formato RFC 5322 y normaliza'
    },
    {
      nombre: 'Fecha',
      campo: 'fecha_entrega',
      formato: 'DD/MM/YYYY',
      ejemplo: '15/03/2024',
      descripcion: 'Valida fechas con reglas de negocio'
    },
    {
      nombre: 'Monto',
      campo: 'total_financiamiento',
      formato: 'Número positivo',
      ejemplo: '25000.00',
      descripcion: 'Valida montos con límites'
    }
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Validadores</h1>
          <p className="text-gray-500 mt-1">
            Configuración y prueba de validadores del sistema
          </p>
        </div>
        <Button variant="outline">
          <Download className="w-4 h-4 mr-2" />
          Exportar Configuración
        </Button>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="probar" className="space-y-6">
        <TabsList>
          <TabsTrigger value="probar">
            <PlayCircle className="w-4 h-4 mr-2" />
            Probar Validadores
          </TabsTrigger>
          <TabsTrigger value="configuracion">
            <Settings className="w-4 h-4 mr-2" />
            Configuración
          </TabsTrigger>
          <TabsTrigger value="ejemplos">
            <FileText className="w-4 h-4 mr-2" />
            Ejemplos
          </TabsTrigger>
          <TabsTrigger value="diagnostico">
            <Search className="w-4 h-4 mr-2" />
            Diagnóstico
          </TabsTrigger>
        </TabsList>

        {/* Tab: Probar Validadores */}
        <TabsContent value="probar">
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
                    className="w-full px-3 py-2 border rounded-lg"
                    value={campoTest}
                    onChange={(e) => setCampoTest(e.target.value)}
                  >
                    <option value="">Seleccionar campo...</option>
                    {validadoresDisponibles.map((v) => (
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
                    onChange={(e) => setValorTest(e.target.value)}
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
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      Validando...
                    </>
                  ) : (
                    <>
                      <PlayCircle className="w-4 h-4 mr-2" />
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
                    <Card className={
                      resultadoTest.validacion?.valido 
                        ? "border-green-500 bg-green-50"
                        : "border-red-500 bg-red-50"
                    }>
                      <CardContent className="pt-4">
                        <div className="flex items-start space-x-3">
                          {resultadoTest.validacion?.valido ? (
                            <CheckCircle className="w-5 h-5 text-green-600" />
                          ) : (
                            <XCircle className="w-5 h-5 text-red-600" />
                          )}
                          <div className="flex-1">
                            <p className="font-medium">
                              {resultadoTest.validacion?.valido ? '✅ Válido' : '❌ Inválido'}
                            </p>
                            {resultadoTest.validacion?.mensaje && (
                              <p className="text-sm text-gray-600 mt-1">
                                {resultadoTest.validacion.mensaje}
                              </p>
                            )}
                            {resultadoTest.validacion?.valor_formateado && (
                              <p className="text-sm text-gray-600 mt-2">
                                <strong>Valor formateado:</strong> {resultadoTest.validacion.valor_formateado}
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
                  {validadoresDisponibles.map((validador) => (
                    <motion.div
                      key={validador.campo}
                      whileHover={{ scale: 1.02 }}
                      className="p-3 border rounded-lg hover:border-primary cursor-pointer transition-colors"
                      onClick={() => setCampoTest(validador.campo)}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="font-medium text-gray-900">{validador.nombre}</h4>
                          <p className="text-sm text-gray-500 mt-1">{validador.descripcion}</p>
                          <div className="flex items-center space-x-4 mt-2">
                            <Badge variant="outline" className="text-xs">
                              {validador.formato}
                            </Badge>
                            <span className="text-xs text-gray-400">
                              Ej: {validador.ejemplo}
                            </span>
                          </div>
                        </div>
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      </div>
                    </motion.div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Tab: Configuración */}
        <TabsContent value="configuracion">
          <Card>
            <CardHeader>
              <CardTitle>Configuración de Validadores</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {/* País configurado */}
                <div>
                  <h3 className="font-medium text-gray-900 mb-3">País Configurado</h3>
                  <Badge variant="outline" className="text-lg px-4 py-2">
                    🇻🇪 Venezuela
                  </Badge>
                </div>

                {/* Reglas de negocio */}
                <div>
                  <h3 className="font-medium text-gray-900 mb-3">Reglas de Negocio</h3>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-sm font-medium">Cédula Venezuela</p>
                      <p className="text-xs text-gray-600 mt-1">Prefijos V/E/J + 7-10 dígitos</p>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-sm font-medium">Teléfono Venezuela</p>
                      <p className="text-xs text-gray-600 mt-1">+58 + 10 dígitos (primer dígito no puede ser 0)</p>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-sm font-medium">Fecha formato</p>
                      <p className="text-xs text-gray-600 mt-1">DD/MM/YYYY (día 2 dígitos, mes 2 dígitos, año 4 dígitos)</p>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-sm font-medium">Email normalización</p>
                      <p className="text-xs text-gray-600 mt-1">Conversión automática a minúsculas (incluyendo @)</p>
                    </div>
                  </div>
                </div>

                {/* Endpoints disponibles */}
                <div>
                  <h3 className="font-medium text-gray-900 mb-3">Endpoints Disponibles</h3>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <code className="text-xs">POST /api/v1/validadores/validar-campo</code>
                      <Badge>Validación en tiempo real</Badge>
                    </div>
                    <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <code className="text-xs">POST /api/v1/validadores/formatear-tiempo-real</code>
                      <Badge>Formateo automático</Badge>
                    </div>
                    <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <code className="text-xs">GET /api/v1/validadores/configuracion</code>
                      <Badge>Configuración</Badge>
                    </div>
                    <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <code className="text-xs">GET /api/v1/validadores/ejemplos-correccion</code>
                      <Badge>Ejemplos</Badge>
                    </div>
                    <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <code className="text-xs">GET /api/v1/validadores/detectar-errores-masivo</code>
                      <Badge variant="outline">Diagnóstico masivo</Badge>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab: Ejemplos */}
        <TabsContent value="ejemplos">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Teléfono mal formateado</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <Badge variant="destructive">Incorrecto</Badge>
                    <p className="text-sm mt-1">4241234567</p>
                    <p className="text-xs text-gray-500">Sin código de país (+58)</p>
                  </div>
                  <div>
                    <Badge className="bg-green-600">Correcto</Badge>
                    <p className="text-sm mt-1">+58 424 1234567</p>
                    <p className="text-xs text-gray-500">Sistema auto-formatea al guardar</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Cédula sin letra</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <Badge variant="destructive">Incorrecto</Badge>
                    <p className="text-sm mt-1">12345678</p>
                    <p className="text-xs text-gray-500">Sin prefijo V/E</p>
                  </div>
                  <div>
                    <Badge className="bg-green-600">Correcto</Badge>
                    <p className="text-sm mt-1">V12345678</p>
                    <p className="text-xs text-gray-500">Admin edita y sistema valida</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Email mal formateado</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <Badge variant="destructive">Incorrecto</Badge>
                    <p className="text-sm mt-1">USUARIO@GMAIL.COM</p>
                    <p className="text-xs text-gray-500">Mayúsculas y formato incorrecto</p>
                  </div>
                  <div>
                    <Badge className="bg-green-600">Correcto</Badge>
                    <p className="text-sm mt-1">usuario@gmail.com</p>
                    <p className="text-xs text-gray-500">Normalizado automáticamente</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Fecha en formato incorrecto</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <Badge variant="destructive">Incorrecto</Badge>
                    <p className="text-sm mt-1">ERROR</p>
                    <p className="text-xs text-gray-500">Valor inválido</p>
                  </div>
                  <div>
                    <Badge className="bg-green-600">Correcto</Badge>
                    <p className="text-sm mt-1">15/03/2024</p>
                    <p className="text-xs text-gray-500">Admin selecciona en calendario</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Tab: Diagnóstico */}
        <TabsContent value="diagnostico">
          <Card>
            <CardHeader>
              <CardTitle>Diagnóstico de Datos</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-12">
                <AlertTriangle className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Diagnóstico Masivo
                </h3>
                <p className="text-gray-500 mb-6">
                  Detecta y corrige datos incorrectos en toda la base de datos
                </p>
                <Button size="lg">
                  <Search className="w-4 h-4 mr-2" />
                  Iniciar Diagnóstico
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

