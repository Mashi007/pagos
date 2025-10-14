import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Brain,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Users,
  DollarSign,
  BarChart3,
  PieChart,
  Target,
  Zap,
  Search,
  Filter,
  RefreshCw,
  Download,
  Eye,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Progress } from '@/components/ui/progress'
import { formatCurrency, formatDate } from '@/utils'

// Mock data para IA
const mockAnalisisIA = [
  {
    id: 'IA001',
    cliente: 'Juan Carlos Pérez González',
    cedula: 'V12345678',
    tipo: 'SCORING_CREDITICIO',
    score: 85,
    recomendacion: 'APROBAR',
    confianza: 92.5,
    fechaAnalisis: '2024-07-20',
    factores: ['Historial positivo', 'Ingresos estables', 'Referencias favorables'],
    riesgos: ['Ninguno identificado'],
    montoRecomendado: 25000,
    plazoRecomendado: 36,
  },
  {
    id: 'IA002',
    cliente: 'María Elena Rodríguez López',
    cedula: 'V87654321',
    tipo: 'SCORING_CREDITICIO',
    score: 72,
    recomendacion: 'APROBAR_CON_CONDICIONES',
    confianza: 78.3,
    fechaAnalisis: '2024-07-19',
    factores: ['Ingresos regulares', 'Antigüedad laboral'],
    riesgos: ['Historial crediticio limitado'],
    montoRecomendado: 18000,
    plazoRecomendado: 24,
  },
  {
    id: 'IA003',
    cliente: 'Carlos Alberto Martínez Silva',
    cedula: 'V11223344',
    tipo: 'ANALISIS_MORA',
    score: 35,
    recomendacion: 'RECHAZAR',
    confianza: 89.7,
    fechaAnalisis: '2024-07-18',
    factores: ['Historial de mora', 'Ingresos irregulares'],
    riesgos: ['Alto riesgo de incumplimiento', 'Deudas pendientes'],
    montoRecomendado: 0,
    plazoRecomendado: 0,
  },
]

const mockPredicciones = [
  {
    id: 'PRED001',
    tipo: 'FLUJO_CAJA',
    descripcion: 'Predicción de flujo de caja próximo mes',
    confianza: 87.5,
    fechaPrediccion: '2024-07-20',
    resultado: 'POSITIVO',
    valor: 125400,
    variacion: 5.2,
  },
  {
    id: 'PRED002',
    tipo: 'MOROSIDAD',
    descripcion: 'Predicción de tasa de morosidad',
    confianza: 82.1,
    fechaPrediccion: '2024-07-19',
    resultado: 'MEJORA',
    valor: 11.8,
    variacion: -2.3,
  },
  {
    id: 'PRED003',
    tipo: 'VENTAS',
    descripcion: 'Predicción de ventas del próximo trimestre',
    confianza: 75.8,
    fechaPrediccion: '2024-07-18',
    resultado: 'CRECIMIENTO',
    valor: 45,
    variacion: 12.5,
  },
]

const modelosIA = [
  {
    nombre: 'Scoring Crediticio',
    descripcion: 'Modelo para evaluar el riesgo crediticio de clientes',
    precision: 94.2,
    estado: 'ACTIVO',
    ultimaActualizacion: '2024-07-15',
    registrosEntrenamiento: 15420,
  },
  {
    nombre: 'Predicción de Mora',
    descripcion: 'Predice la probabilidad de mora de clientes',
    precision: 89.7,
    estado: 'ACTIVO',
    ultimaActualizacion: '2024-07-10',
    registrosEntrenamiento: 12350,
  },
  {
    nombre: 'Optimización de Cobranza',
    descripcion: 'Optimiza las estrategias de cobranza',
    precision: 91.3,
    estado: 'ENTRENANDO',
    ultimaActualizacion: '2024-07-20',
    registrosEntrenamiento: 8750,
  },
]

export function InteligenciaArtificial() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterTipo, setFilterTipo] = useState('Todos')
  const [filterRecomendacion, setFilterRecomendacion] = useState('Todos')
  const [selectedAnalisis, setSelectedAnalisis] = useState<string | null>(null)

  const filteredAnalisis = mockAnalisisIA.filter((analisis) => {
    const matchesSearch =
      analisis.cliente.toLowerCase().includes(searchTerm.toLowerCase()) ||
      analisis.cedula.includes(searchTerm) ||
      analisis.id.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesTipo = filterTipo === 'Todos' || analisis.tipo === filterTipo
    const matchesRecomendacion = filterRecomendacion === 'Todos' || analisis.recomendacion === filterRecomendacion
    return matchesSearch && matchesTipo && matchesRecomendacion
  })

  const totalAnalisis = mockAnalisisIA.length
  const aprobados = mockAnalisisIA.filter((a) => a.recomendacion === 'APROBAR').length
  const condicionales = mockAnalisisIA.filter((a) => a.recomendacion === 'APROBAR_CON_CONDICIONES').length
  const rechazados = mockAnalisisIA.filter((a) => a.recomendacion === 'RECHAZAR').length
  const promedioScore = mockAnalisisIA.reduce((sum, a) => sum + a.score, 0) / mockAnalisisIA.length

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600'
    if (score >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getScoreBadge = (score: number) => {
    if (score >= 80) return 'success'
    if (score >= 60) return 'warning'
    return 'destructive'
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Inteligencia Artificial</h1>
          <p className="text-gray-600">Análisis predictivo y automatización con IA.</p>
        </div>
        <div className="flex space-x-2">
          <Badge variant="secondary" className="bg-green-100 text-green-800">
            <Brain className="mr-1 h-3 w-3" /> IA ACTIVA
          </Badge>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Análisis</CardTitle>
            <Brain className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalAnalisis}</div>
            <p className="text-xs text-muted-foreground">Análisis realizados</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Score Promedio</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getScoreColor(promedioScore)}`}>
              {promedioScore.toFixed(1)}
            </div>
            <p className="text-xs text-muted-foreground">Puntuación media</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Aprobados</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{aprobados}</div>
            <p className="text-xs text-muted-foreground">Recomendaciones positivas</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Rechazados</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{rechazados}</div>
            <p className="text-xs text-muted-foreground">Alto riesgo</p>
          </CardContent>
        </Card>
      </div>

      {/* Predicciones */}
      <div className="grid gap-6 md:grid-cols-3">
        {mockPredicciones.map((prediccion) => (
          <Card key={prediccion.id}>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Zap className="mr-2 h-5 w-5" /> {prediccion.tipo.replace('_', ' ')}
              </CardTitle>
              <CardDescription>{prediccion.descripcion}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm">Confianza</span>
                  <span className="font-semibold">{prediccion.confianza}%</span>
                </div>
                <Progress value={prediccion.confianza} className="h-2" />
                <div className="flex justify-between items-center">
                  <span className="text-sm">Resultado</span>
                  <Badge
                    variant={
                      prediccion.resultado === 'POSITIVO' || prediccion.resultado === 'MEJORA' || prediccion.resultado === 'CRECIMIENTO'
                        ? 'success'
                        : 'warning'
                    }
                  >
                    {prediccion.resultado}
                  </Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm">Valor</span>
                  <span className="font-semibold">
                    {prediccion.tipo === 'FLUJO_CAJA' || prediccion.tipo === 'VENTAS' 
                      ? prediccion.tipo === 'FLUJO_CAJA' ? formatCurrency(prediccion.valor) : prediccion.valor
                      : `${prediccion.valor}%`
                    }
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm">Variación</span>
                  <span className={`font-semibold ${prediccion.variacion > 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {prediccion.variacion > 0 ? '+' : ''}{prediccion.variacion}%
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Modelos de IA */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Brain className="mr-2 h-5 w-5" /> Modelos de IA
          </CardTitle>
          <CardDescription>Estado y rendimiento de los modelos de inteligencia artificial.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            {modelosIA.map((modelo) => (
              <Card key={modelo.nombre} className="border">
                <CardContent className="p-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold">{modelo.nombre}</h3>
                      <Badge
                        variant={modelo.estado === 'ACTIVO' ? 'success' : 'warning'}
                      >
                        {modelo.estado}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-600">{modelo.descripcion}</p>
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Precisión</span>
                        <span className="font-semibold">{modelo.precision}%</span>
                      </div>
                      <Progress value={modelo.precision} className="h-2" />
                      <div className="text-xs text-gray-500">
                        Entrenado con {modelo.registrosEntrenamiento.toLocaleString()} registros
                      </div>
                      <div className="text-xs text-gray-500">
                        Última actualización: {formatDate(modelo.ultimaActualizacion)}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Análisis de IA */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Análisis de IA
            <div className="flex space-x-2">
              <Button variant="outline" size="sm">
                <RefreshCw className="mr-2 h-4 w-4" /> Ejecutar Análisis
              </Button>
              <Button variant="outline" size="sm">
                <Download className="mr-2 h-4 w-4" /> Exportar
              </Button>
            </div>
          </CardTitle>
          <CardDescription>Resultados de análisis de inteligencia artificial.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 mb-4">
            <Input
              placeholder="Buscar por cliente, cédula o ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="max-w-sm"
              leftIcon={<Search className="h-4 w-4 text-gray-400" />}
            />
            <Select value={filterTipo} onValueChange={setFilterTipo}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Tipo de análisis" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Todos">Todos los tipos</SelectItem>
                <SelectItem value="SCORING_CREDITICIO">Scoring Crediticio</SelectItem>
                <SelectItem value="ANALISIS_MORA">Análisis de Mora</SelectItem>
                <SelectItem value="OPTIMIZACION_COBRANZA">Optimización Cobranza</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filterRecomendacion} onValueChange={setFilterRecomendacion}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Recomendación" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Todos">Todas</SelectItem>
                <SelectItem value="APROBAR">Aprobar</SelectItem>
                <SelectItem value="APROBAR_CON_CONDICIONES">Con Condiciones</SelectItem>
                <SelectItem value="RECHAZAR">Rechazar</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Cliente</TableHead>
                <TableHead>Cédula</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Confianza</TableHead>
                <TableHead>Recomendación</TableHead>
                <TableHead>Monto Sugerido</TableHead>
                <TableHead>Fecha</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAnalisis.length > 0 ? (
                filteredAnalisis.map((analisis) => (
                  <TableRow key={analisis.id}>
                    <TableCell className="font-medium">{analisis.id}</TableCell>
                    <TableCell>{analisis.cliente}</TableCell>
                    <TableCell>{analisis.cedula}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{analisis.tipo.replace('_', ' ')}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={getScoreBadge(analisis.score)}>
                        {analisis.score}/100
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center">
                        <span className="text-sm">{analisis.confianza}%</span>
                        <Progress value={analisis.confianza} className="ml-2 h-1 w-12" />
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          analisis.recomendacion === 'APROBAR'
                            ? 'success'
                            : analisis.recomendacion === 'APROBAR_CON_CONDICIONES'
                              ? 'warning'
                              : 'destructive'
                        }
                      >
                        {analisis.recomendacion.replace('_', ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {analisis.montoRecomendado > 0 ? formatCurrency(analisis.montoRecomendado) : 'N/A'}
                    </TableCell>
                    <TableCell>{formatDate(analisis.fechaAnalisis)}</TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedAnalisis(analisis.id)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={10} className="text-center text-gray-500">
                    No se encontraron análisis de IA.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Detalle del Análisis */}
      {selectedAnalisis && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Brain className="mr-2 h-5 w-5" /> Detalle del Análisis - {selectedAnalisis}
            </CardTitle>
            <CardDescription>Información completa del análisis de IA.</CardDescription>
          </CardHeader>
          <CardContent>
            {(() => {
              const analisis = mockAnalisisIA.find(a => a.id === selectedAnalisis)
              if (!analisis) return null

              return (
                <div className="grid gap-6 md:grid-cols-2">
                  <div className="space-y-4">
                    <h3 className="font-semibold">Información del Cliente</h3>
                    <div className="bg-gray-50 p-4 rounded-lg space-y-2">
                      <div><strong>Cliente:</strong> {analisis.cliente}</div>
                      <div><strong>Cédula:</strong> {analisis.cedula}</div>
                      <div><strong>Tipo de Análisis:</strong> {analisis.tipo.replace('_', ' ')}</div>
                      <div><strong>Score:</strong> 
                        <Badge variant={getScoreBadge(analisis.score)} className="ml-2">
                          {analisis.score}/100
                        </Badge>
                      </div>
                      <div><strong>Confianza del Modelo:</strong> {analisis.confianza}%</div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h3 className="font-semibold">Recomendación</h3>
                    <div className="bg-gray-50 p-4 rounded-lg space-y-2">
                      <div><strong>Decisión:</strong> 
                        <Badge
                          variant={
                            analisis.recomendacion === 'APROBAR'
                              ? 'success'
                              : analisis.recomendacion === 'APROBAR_CON_CONDICIONES'
                                ? 'warning'
                                : 'destructive'
                          }
                          className="ml-2"
                        >
                          {analisis.recomendacion.replace('_', ' ')}
                        </Badge>
                      </div>
                      {analisis.montoRecomendado > 0 && (
                        <>
                          <div><strong>Monto Recomendado:</strong> {formatCurrency(analisis.montoRecomendado)}</div>
                          <div><strong>Plazo Recomendado:</strong> {analisis.plazoRecomendado} meses</div>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h3 className="font-semibold">Factores Positivos</h3>
                    <div className="bg-green-50 p-4 rounded-lg">
                      <ul className="space-y-1">
                        {analisis.factores.map((factor, index) => (
                          <li key={index} className="flex items-center">
                            <CheckCircle className="h-4 w-4 text-green-600 mr-2" />
                            {factor}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h3 className="font-semibold">Riesgos Identificados</h3>
                    <div className="bg-red-50 p-4 rounded-lg">
                      <ul className="space-y-1">
                        {analisis.riesgos.map((riesgo, index) => (
                          <li key={index} className="flex items-center">
                            <AlertTriangle className="h-4 w-4 text-red-600 mr-2" />
                            {riesgo}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )
            })()}
          </CardContent>
        </Card>
      )}
    </motion.div>
  )
}
