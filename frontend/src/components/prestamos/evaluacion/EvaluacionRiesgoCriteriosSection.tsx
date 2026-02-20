import {
  Info,
  TrendingDown,
  AlertCircle,
  CheckCircle,
  MapPin,
  Users,
  Calendar,
  DollarSign,
} from 'lucide-react'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../../../components/ui/popover'
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card'
import { Button } from '../../../components/ui/button'
import { Input } from '../../../components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../../components/ui/select'
import type { EvaluacionFormData } from '../../../hooks/useEvaluacionRiesgo'
import type { Prestamo } from '../../../types'

interface EvaluacionRiesgoCriteriosSectionProps {
  showSection: string
  formData: EvaluacionFormData
  handleChange: <K extends keyof EvaluacionFormData>(
    field: K,
    value: EvaluacionFormData[K]
  ) => void
  prestamo: Prestamo
  clienteEdad: number
  resumenPrestamos: any
  bloqueadoPorMora: boolean
}

export function EvaluacionRiesgoCriteriosSection({
  showSection,
  formData,
  handleChange,
  prestamo,
  clienteEdad,
  resumenPrestamos,
  bloqueadoPorMora,
}: EvaluacionRiesgoCriteriosSectionProps) {
  const setFormData = (updates: Partial<EvaluacionFormData>) => {
    Object.entries(updates).forEach(([k, v]) =>
      handleChange(k as keyof EvaluacionFormData, v as never)
    )
  }
  const update = <K extends keyof EvaluacionFormData>(k: K, v: EvaluacionFormData[K]) =>
    setFormData({ [k]: v } as Partial<EvaluacionFormData>)

  if (showSection === 'situacion') {
    return (
      <Card className="border-purple-200">
        <CardHeader className="bg-purple-50">
          <CardTitle className="flex items-center gap-2 text-purple-700">
            <Info className="h-5 w-5" />
            Situación del Cliente
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4 space-y-3">
          {!resumenPrestamos && <p>Cargando resumen...</p>}
          {resumenPrestamos && !resumenPrestamos.tiene_prestamos && (
            <div className="p-3 rounded bg-green-50 border border-green-200 text-green-800">
              No tiene préstamos vigentes. Puede continuar con el análisis.
            </div>
          )}
          {resumenPrestamos && resumenPrestamos.tiene_prestamos && (
            <div className="space-y-3">
              <div className="p-3 rounded bg-yellow-50 border border-yellow-200 text-yellow-900">
                Préstamos vigentes: {resumenPrestamos.total_prestamos}. Saldo pendiente total: $
                {Number(resumenPrestamos.total_saldo_pendiente || 0).toFixed(2)}.
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left border-b">
                      <th className="py-2 pr-4">ID</th>
                      <th className="py-2 pr-4">Modelo</th>
                      <th className="py-2 pr-4">Financiamiento</th>
                      <th className="py-2 pr-4">Saldo</th>
                      <th className="py-2 pr-4">Cuotas en Mora</th>
                      <th className="py-2 pr-4">Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(resumenPrestamos.prestamos || []).map((p: any) => (
                      <tr key={p.id} className="border-b">
                        <td className="py-2 pr-4">{p.id}</td>
                        <td className="py-2 pr-4">{p.modelo_vehiculo}</td>
                        <td className="py-2 pr-4">${Number(p.total_financiamiento).toFixed(2)}</td>
                        <td className="py-2 pr-4">${Number(p.saldo_pendiente).toFixed(2)}</td>
                        <td className="py-2 pr-4">{p.cuotas_en_mora}</td>
                        <td className="py-2 pr-4">{p.estado}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {bloqueadoPorMora ? (
                <div className="p-3 rounded bg-red-50 border border-red-200 text-red-800">
                  Hay cuotas en mora. No se puede continuar hasta regularizar la situación.
                </div>
              ) : (
                <div className="p-3 rounded bg-blue-50 border border-blue-200 text-blue-800">
                  No hay cuotas en mora. Puede continuar con el análisis.
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    )
  }

  if (showSection === 'criterio1') {
    return (
      <Card className="border-blue-200">
        <CardHeader className="bg-blue-50">
          <CardTitle className="flex items-center gap-2 text-blue-700">
            <TrendingDown className="h-5 w-5" />
            CRITERIO 1: CAPACIDAD DE PAGO (29 puntos)
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4 space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Ingresos Mensuales (USD) *</label>
              <Input
                type="number"
                step="0.01"
                min={0}
                value={formData.ingresos_mensuales || ''}
                onChange={(e) => update('ingresos_mensuales', parseFloat(e.target.value) || 0)}
                required
              />
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="ghost" size="sm" className="h-6 mt-1 p-0 text-xs text-blue-600">
                    <Info className="h-3 w-3 mr-1" />
                    Ver escala
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-80">
                  <p className="text-sm font-semibold mb-2">Ratio de Endeudamiento:</p>
                  <ul className="text-xs space-y-1">
                    <li>- &lt; 25% → 14 puntos (Excelente)</li>
                    <li>- 25-35% → 11 puntos (Bueno)</li>
                    <li>- 35-50% → 6 puntos (Regular)</li>
                    <li>- &gt; 50% → 2 puntos (Malo)</li>
                  </ul>
                  <p className="text-sm font-semibold mb-2 mt-4">Ratio de Cobertura:</p>
                  <ul className="text-xs space-y-1">
                    <li>- &gt; 2.5x → 15 puntos (Excelente)</li>
                    <li>- 2.0-2.5x → 12 puntos (Bueno)</li>
                    <li>- 1.5-2.0x → 6 puntos (Regular)</li>
                    <li>- &lt; 1.5x → 0 puntos (RECHAZO)</li>
                  </ul>
                </PopoverContent>
              </Popover>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Gastos Fijos (USD) *</label>
              <Input
                type="number"
                step="0.01"
                min={0}
                value={formData.gastos_fijos_mensuales || ''}
                onChange={(e) => update('gastos_fijos_mensuales', parseFloat(e.target.value) || 0)}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Otras Deudas (USD) *</label>
              <Input
                type="number"
                step="0.01"
                min={0}
                value={formData.otras_deudas || ''}
                onChange={(e) => update('otras_deudas', parseFloat(e.target.value) || 0)}
                required
              />
              <p className="text-xs text-gray-500 mt-1">Sin incluir la cuota actual</p>
            </div>
          </div>
          <div className="bg-blue-50 p-3 rounded border border-blue-200">
            <p className="text-xs text-blue-700">
              <strong>Nota:</strong> La cuota del préstamo se toma automáticamente de la base de datos: $
              {prestamo.cuota_periodo || 0} USD
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (showSection === 'criterio2') {
    return (
      <Card className="border-yellow-200">
        <CardHeader className="bg-yellow-50">
          <CardTitle className="flex items-center gap-2 text-yellow-700">
            <AlertCircle className="h-5 w-5" />
            CRITERIO 2: ESTABILIDAD LABORAL (23 puntos)
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Meses de Trabajo *</label>
            <Input
              type="number"
              min={0}
              value={formData.meses_trabajo || ''}
              onChange={(e) => update('meses_trabajo', parseInt(e.target.value) || 0)}
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Escala: &gt; 24 meses → 9 pts, 12-24 → 7 pts, 6-12 → 4 pts, &lt; 6 → 0 pts
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Tipo de Empleo *</label>
            <Select value={formData.tipo_empleo} onValueChange={(v) => update('tipo_empleo', v)} required>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="empleado_formal">Empleado Formal (8 pts)</SelectItem>
                <SelectItem value="informal_estable">Informal Estable (&gt;1 año) (6 pts)</SelectItem>
                <SelectItem value="independiente_formal">Independiente Formal (RIF/NIT) (5 pts)</SelectItem>
                <SelectItem value="independiente_informal">Independiente Informal (3 pts)</SelectItem>
                <SelectItem value="sin_empleo">Sin Empleo Fijo (0 pts)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Sector Económico *</label>
            <Select value={formData.sector_economico} onValueChange={(v) => update('sector_economico', v)} required>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="gobierno_publico">Gobierno/Público (6 pts)</SelectItem>
                <SelectItem value="servicios_esenciales">Servicios Esenciales (5 pts)</SelectItem>
                <SelectItem value="comercio_establecido">Comercio Establecido (4 pts)</SelectItem>
                <SelectItem value="construccion_manufactura">Construcción/Manufactura (3 pts)</SelectItem>
                <SelectItem value="turismo_entretenimiento">Turismo/Entretenimiento (2 pts)</SelectItem>
                <SelectItem value="servicios_temporales">Servicios Temporales (1 pt)</SelectItem>
                <SelectItem value="agricultura_estacional">Agricultura Estacional (0 pts)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (showSection === 'criterio3') {
    return (
      <Card className="border-purple-200">
        <CardHeader className="bg-purple-50">
          <CardTitle className="flex items-center gap-2 text-purple-700">
            <CheckCircle className="h-5 w-5" />
            CRITERIO 3: REFERENCIAS PERSONALES (9 puntos)
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4 space-y-4">
          {[1, 2, 3].map((n) => (
            <div key={n} className="border rounded-lg p-4 bg-purple-50">
              <h4 className="font-medium text-sm mb-3">Referencia {n}</h4>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium mb-1">Observaciones</label>
                  <Input
                    type="text"
                    placeholder="Nombre, relación, etc."
                    value={
                      (formData as any)[`referencia${n}_observaciones`] || ''
                    }
                    onChange={(e) =>
                      update(`referencia${n}_observaciones` as keyof EvaluacionFormData, e.target.value)
                    }
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Calificación *</label>
                  <Select
                    value={(formData as any)[`referencia${n}_calificacion`]?.toString() ?? '0'}
                    onValueChange={(v) =>
                      update(`referencia${n}_calificacion` as keyof EvaluacionFormData, parseInt(v))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="3">3 - Recomendable</SelectItem>
                      <SelectItem value="2">2 - Dudosa</SelectItem>
                      <SelectItem value="1">1 - No recomendable</SelectItem>
                      <SelectItem value="0">0 - No contestó</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          ))}
          <div className="bg-purple-50 p-3 rounded border border-purple-200">
            <p className="text-xs text-purple-700">
              <strong>Escala:</strong> Calificación 3 → Recomendable (3 pts) | Calificación 2 → Dudosa (2 pts) |
              Calificación 1 → No recomendable (1 pt) | No contestó (0 pts)
              <br />
              <strong>Total máximo:</strong> 9 puntos (3 referencias x 3 pts c/u)
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (showSection === 'criterio4') {
    return (
      <Card className="border-green-200">
        <CardHeader className="bg-green-50">
          <CardTitle className="flex items-center gap-2 text-green-700">
            <MapPin className="h-5 w-5" />
            CRITERIO 4: ARRAIGO GEOGRÁFICO (7 puntos)
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Distancia al Trabajo (minutos) *</label>
            <Input
              type="number"
              min={0}
              value={formData.minutos_trabajo || ''}
              onChange={(e) => update('minutos_trabajo', parseInt(e.target.value) || 0)}
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              &lt; 30 min → 3 pts, 30-60 min → 2 pts, &gt; 60 min → 0 pts
            </p>
          </div>
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="familia_cercana"
                checked={formData.familia_cercana}
                onChange={(e) => update('familia_cercana', e.target.checked)}
                className="rounded border-gray-300"
              />
              <label htmlFor="familia_cercana" className="text-sm cursor-pointer">
                Familia cercana en la ciudad (4 pts)
              </label>
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="familia_pais"
                checked={formData.familia_pais}
                onChange={(e) => update('familia_pais', e.target.checked)}
                className="rounded border-gray-300"
              />
              <label htmlFor="familia_pais" className="text-sm cursor-pointer">
                Familia en el país (2 pts)
              </label>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (showSection === 'criterio5') {
    return (
      <Card className="border-indigo-200">
        <CardHeader className="bg-indigo-50">
          <CardTitle className="flex items-center gap-2 text-indigo-700">
            <Users className="h-5 w-5" />
            CRITERIO 5: PERFIL SOCIODEMOGRÁFICO (17 puntos)
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Situación de Vivienda Detallada *</label>
            <Select
              value={formData.tipo_vivienda_detallado}
              onValueChange={(v) => update('tipo_vivienda_detallado', v)}
              required
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="casa_propia_pagada">Casa Propia Pagada (6 pts)</SelectItem>
                <SelectItem value="casa_propia_hipoteca">Casa Propia con Hipoteca (5 pts)</SelectItem>
                <SelectItem value="casa_familiar">Casa Familiar/Heredada (5 pts)</SelectItem>
                <SelectItem value="alquiler_mas_3">Alquiler &gt;3 años (4 pts)</SelectItem>
                <SelectItem value="alquiler_1_3">Alquiler 1-3 años (3 pts)</SelectItem>
                <SelectItem value="alquiler_menos_1">Alquiler &lt;1 año (1 pt)</SelectItem>
                <SelectItem value="prestado">De Prestado (0.5 pts)</SelectItem>
                <SelectItem value="sin_vivienda">Sin Vivienda (0 pts)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="zona_urbana"
                checked={formData.zona_urbana}
                onChange={(e) => update('zona_urbana', e.target.checked)}
                className="rounded border-gray-300"
              />
              <label htmlFor="zona_urbana" className="text-sm cursor-pointer">
                Zona urbana consolidada (+0.5 pts)
              </label>
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="servicios_nombre"
                checked={formData.servicios_nombre}
                onChange={(e) => update('servicios_nombre', e.target.checked)}
                className="rounded border-gray-300"
              />
              <label htmlFor="servicios_nombre" className="text-sm cursor-pointer">
                Servicios a su nombre (+0.5 pts)
              </label>
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="zona_rural"
                checked={formData.zona_rural}
                onChange={(e) => update('zona_rural', e.target.checked)}
                className="rounded border-gray-300"
              />
              <label htmlFor="zona_rural" className="text-sm cursor-pointer">
                Zona rural/alejada (-0.5 pts)
              </label>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Personas en Casa</label>
              <Input
                type="number"
                min={1}
                value={formData.personas_casa || 1}
                onChange={(e) => update('personas_casa', parseInt(e.target.value) || 1)}
              />
              <p className="text-xs text-gray-500 mt-1">&gt; 5 personas → -0.5 pts</p>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Estado Civil *</label>
            <Select value={formData.estado_civil} onValueChange={(v) => update('estado_civil', v)} required>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="casado_mas_3">Casado/a &gt;3 años (3.5 pts)</SelectItem>
                <SelectItem value="casado_menos_3">Casado/a &lt;3 años (3.0 pts)</SelectItem>
                <SelectItem value="divorciado_con_hijos">Divorciado/a con hijos (2.5 pts)</SelectItem>
                <SelectItem value="soltero_con_pareja">Soltero/a con pareja (2.0 pts)</SelectItem>
                <SelectItem value="soltero_sin_pareja">Soltero/a sin pareja (1.5 pts)</SelectItem>
                <SelectItem value="divorciado_sin_hijos">Divorciado/a sin hijos (1.0 pt)</SelectItem>
                <SelectItem value="separado_reciente">Separado/a reciente (0 pts)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            {[
              { id: 'pareja_trabaja', key: 'pareja_trabaja' as const, label: 'Pareja trabaja (+1.0 pt)' },
              { id: 'pareja_aval', key: 'pareja_aval' as const, label: 'Pareja es aval (+1.5 pts)' },
              { id: 'pareja_desempleada', key: 'pareja_desempleada' as const, label: 'Pareja desempleada (-0.5 pts)' },
              { id: 'relacion_conflictiva', key: 'relacion_conflictiva' as const, label: 'Relación conflictiva (-1.0 pt)' },
            ].map(({ id, key, label }) => (
              <div key={id} className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id={id}
                  checked={formData[key]}
                  onChange={(e) => update(key, e.target.checked)}
                  className="rounded border-gray-300"
                />
                <label htmlFor={id} className="text-sm cursor-pointer">
                  {label}
                </label>
              </div>
            ))}
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Situación de Hijos *</label>
            <Select value={formData.situacion_hijos} onValueChange={(v) => update('situacion_hijos', v)} required>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1_2_menores">1-2 hijos menores (0-12) (5.0 pts)</SelectItem>
                <SelectItem value="1_2_mayores">1-2 hijos mayores (13+) (4.0 pts)</SelectItem>
                <SelectItem value="3_4_mixtos">3-4 hijos mixtos (3.0 pts)</SelectItem>
                <SelectItem value="sin_hijos_planea">Sin hijos, planea (2.5 pts)</SelectItem>
                <SelectItem value="5_mas">5+ hijos (1.5 pts)</SelectItem>
                <SelectItem value="sin_hijos_no_planea">Sin hijos, no planea (2.0 pts)</SelectItem>
                <SelectItem value="hijos_independientes">Hijos independientes (1.0 pt)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            {[
              { id: 'todos_estudian', key: 'todos_estudian' as const, label: 'Todos estudian (+0.5 pts)' },
              { id: 'viven_con_cliente', key: 'viven_con_cliente' as const, label: 'Viven con cliente (+0.5 pts)' },
              { id: 'necesidades_especiales', key: 'necesidades_especiales' as const, label: 'Necesidades especiales (-1.0 pt)' },
              { id: 'viven_con_ex', key: 'viven_con_ex' as const, label: 'Viven con ex (-0.5 pts)' },
              { id: 'embarazo_actual', key: 'embarazo_actual' as const, label: 'Embarazo actual (-0.5 pts)' },
            ].map(({ id, key, label }) => (
              <div key={id} className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id={id}
                  checked={formData[key]}
                  onChange={(e) => update(key, e.target.checked)}
                  className="rounded border-gray-300"
                />
                <label htmlFor={id} className="text-sm cursor-pointer">
                  {label}
                </label>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (showSection === 'criterio6') {
    const edad = clienteEdad || 0
    const años = Math.floor(edad)
    const meses = Math.round((edad - años) * 12)
    const mesesFinal = meses < 0 ? 0 : meses
    const edadDisplay = mesesFinal > 0 ? `${años} años y ${mesesFinal} meses` : `${años} años`

    return (
      <Card className="border-pink-200">
        <CardHeader className="bg-pink-50">
          <CardTitle className="flex items-center gap-2 text-pink-700">
            <Calendar className="h-5 w-5" />
            CRITERIO 6: EDAD DEL CLIENTE (10 puntos)
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Edad del Cliente (años y meses) *</label>
            <Input
              type="text"
              value={edadDisplay}
              disabled
              readOnly
              className="bg-gray-100 cursor-not-allowed font-semibold text-gray-700"
            />
            <p className="text-xs text-gray-500 mt-1">
              La edad se calcula automáticamente desde la fecha de nacimiento del cliente en la base de datos (no
              editable)
            </p>
            <div className="bg-pink-50 p-3 rounded border border-pink-200 mt-3">
              <p className="text-xs text-pink-700">
                <strong>Escala (10 puntos máx):</strong>
                <br />
                25-50 años → 10.0 pts (Óptimo) |
                <br />
                22-24 / 51-55 años → 8.0 pts (Muy bueno/Bueno) |
                <br />
                18-21 / 56-60 años → 6.0 pts (Regular) |
                <br />
                61-65 años → 3.0 pts (Bajo) |
                <br />
                &lt; 18 años → RECHAZO AUTOMÁTICO |
                <br />
                &gt; 65 años → 2.0 pts (Muy bajo)
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (showSection === 'criterio7') {
    const ingresos = formData.ingresos_mensuales || 0
    const gastosFijos = formData.gastos_fijos_mensuales || 0
    const otrasDeudas = formData.otras_deudas || 0
    const cuotaNueva = prestamo.cuota_periodo || 0
    const saldoResidual = ingresos - gastosFijos - otrasDeudas - cuotaNueva
    const porcentaje = ingresos > 0 ? (saldoResidual / ingresos) * 100 : 0
    let puntos = 0
    let categoria = ''
    let icono = ''
    if (porcentaje >= 15) {
      puntos = 5
      categoria = 'Holgado'
      icono = '[OK]'
    } else if (porcentaje >= 5) {
      puntos = 3
      categoria = 'Ajustado'
      icono = '[!]'
    } else {
      puntos = 0
      categoria = 'Insuficiente'
      icono = '[X]'
    }

    return (
      <Card className="border-red-200">
        <CardHeader className="bg-red-50">
          <CardTitle className="flex items-center gap-2 text-red-700">
            <DollarSign className="h-5 w-5" />
            CRITERIO 7: CAPACIDAD DE MANIOBRA (5 puntos)
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4 space-y-4">
          <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
            <h4 className="font-semibold text-blue-900 mb-2">¿Qué es la Capacidad de Maniobra?</h4>
            <p className="text-sm text-blue-800 mb-3">
              Es el saldo que le queda al cliente después de pagar todos sus gastos, deudas y la cuota del préstamo
              propuesto.
            </p>
            <div className="bg-white p-3 rounded border border-blue-100">
              <p className="text-xs font-mono text-gray-700">
                <strong>Fórmula:</strong>
                <br />
                Saldo Residual = Ingresos - Gastos Fijos - Otras Deudas - Cuota Nueva
              </p>
            </div>
          </div>
          <div className="bg-green-50 p-4 rounded-lg border border-green-200">
            <h4 className="font-semibold text-green-900 mb-3">PREVISUALIZACIÓN - CÁLCULO EN TIEMPO REAL</h4>
            <div className="bg-white p-3 rounded border border-green-100 mb-3">
              <div className="grid grid-cols-2 gap-2 text-sm mb-2">
                <div className="text-gray-600">• Ingresos Mensuales:</div>
                <div className="font-semibold">${ingresos.toFixed(2)}</div>
                <div className="text-gray-600">- Gastos Fijos:</div>
                <div className="font-semibold">-${gastosFijos.toFixed(2)}</div>
                <div className="text-gray-600">- Otras Deudas:</div>
                <div className="font-semibold">-${otrasDeudas.toFixed(2)}</div>
                <div className="text-gray-600">- Cuota Préstamo:</div>
                <div className="font-semibold">-${cuotaNueva.toFixed(2)}</div>
                <div className="border-t pt-2 font-bold text-green-700">• Saldo Residual:</div>
                <div className="border-t pt-2 font-bold text-green-700">${saldoResidual.toFixed(2)}</div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div className="bg-white p-3 rounded border">
                <div className="text-xs text-gray-600">% del Ingreso</div>
                <div className="text-2xl font-bold text-blue-600">{porcentaje.toFixed(2)}%</div>
              </div>
              <div className="bg-white p-3 rounded border">
                <div className="text-xs text-gray-600">Categoría</div>
                <div className="text-lg font-bold text-green-600">
                  {icono} {categoria}
                </div>
              </div>
            </div>
            <div className="bg-white p-3 rounded border text-center">
              <div className="text-xs text-gray-600 mb-1">PUNTOS QUE OBTENDRÍA:</div>
              <div className="text-3xl font-bold text-purple-600">{puntos} / 5 pts</div>
            </div>
            {saldoResidual < 0 && (
              <div className="bg-red-100 p-2 rounded border border-red-300 mt-3">
                <p className="text-xs text-red-800 font-semibold">
                  ⚠️ ALERTA: El cliente tendría un déficit de ${Math.abs(saldoResidual).toFixed(2)} USD mensual
                </p>
              </div>
            )}
          </div>
          <div className="bg-amber-50 p-3 rounded border border-amber-200">
            <p className="text-xs text-amber-800 font-semibold mb-2">[!] ESTE CRITERIO SE CALCULA AUTOMÁTICAMENTE</p>
            <p className="text-xs text-amber-700">
              La previsualización arriba usa los datos que ingresaste. Cuando hagas click en &quot;Evaluar Riesgo&quot;,
              el sistema calculará la capacidad de maniobra usando estos valores.
            </p>
          </div>
          <div className="bg-red-50 p-3 rounded border border-red-200">
            <p className="text-xs text-red-700">
              <strong>Escala de Puntuación (3 bandas):</strong>
              <br />
              [OK] &gt;=15% del ingreso → 5 pts (Holgado) - Margen suficiente para imprevistos
              <br />
              [!] 5%-14.9% del ingreso → 3 pts (Ajustado) - Margen mínimo
              <br />
              [X] &lt;5% o déficit → 0 pts (Insuficiente) - Sin margen, alto riesgo
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return null
}
