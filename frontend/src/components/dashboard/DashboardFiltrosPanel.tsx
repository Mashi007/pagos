import { useState } from 'react'
import { Filter, X, Calendar, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { useDashboardFiltros, type DashboardFiltros } from '@/hooks/useDashboardFiltros'

interface DashboardFiltrosPanelProps {
  filtros: DashboardFiltros
  setFiltros: (filtros: DashboardFiltros) => void
  periodo?: string
  setPeriodo?: (periodo: string) => void
  onRefresh?: () => void
  isRefreshing?: boolean
  opcionesFiltros?: {
    analistas?: string[]
    concesionarios?: string[]
    modelos?: string[]
  }
  loadingOpcionesFiltros?: boolean
  errorOpcionesFiltros?: boolean
}

export function DashboardFiltrosPanel({
  filtros,
  setFiltros,
  periodo = 'mes',
  setPeriodo,
  onRefresh,
  isRefreshing = false,
  opcionesFiltros,
  loadingOpcionesFiltros = false,
  errorOpcionesFiltros = false,
}: DashboardFiltrosPanelProps) {
  const [showFiltros, setShowFiltros] = useState(false)
  const { tieneFiltrosActivos, cantidadFiltrosActivos } = useDashboardFiltros(filtros)

  const handleLimpiarFiltros = () => {
    setFiltros({})
  }

  return (
    <div className="flex items-center space-x-3">
      {setPeriodo && (
        <Select value={periodo} onValueChange={setPeriodo}>
          <SelectTrigger className="w-[140px]">
            <Calendar className="mr-2 h-4 w-4" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="dia">Hoy</SelectItem>
            <SelectItem value="semana">Esta semana</SelectItem>
            <SelectItem value="mes">Este mes</SelectItem>
            <SelectItem value="año">Este año</SelectItem>
          </SelectContent>
        </Select>
      )}

      {/* Popover de Filtros */}
      <Popover open={showFiltros} onOpenChange={setShowFiltros}>
        <PopoverTrigger asChild>
          <Button variant="outline" size="sm">
            <Filter className="mr-2 h-4 w-4" />
            Filtros
            {tieneFiltrosActivos && (
              <Badge variant="secondary" className="ml-2">
                {cantidadFiltrosActivos}
              </Badge>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-96" align="end">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="font-semibold">Filtros Generales</h4>
              {tieneFiltrosActivos && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleLimpiarFiltros}
                >
                  <X className="h-4 w-4 mr-1" />
                  Limpiar
                </Button>
              )}
            </div>

            {/* Analista */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Analista</label>
              <Select
                value={filtros.analista ?? '__ALL__'}
                onValueChange={(value) =>
                  setFiltros({
                    ...filtros,
                    analista: value === '__ALL__' ? undefined : value,
                  })
                }
                disabled={loadingOpcionesFiltros}
              >
                <SelectTrigger>
                  <SelectValue
                    placeholder={
                      loadingOpcionesFiltros
                        ? 'Cargando...'
                        : errorOpcionesFiltros
                        ? 'Error al cargar'
                        : 'Todos los analistas'
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__ALL__">Todos los analistas</SelectItem>
                  {loadingOpcionesFiltros ? (
                    <SelectItem value="__ALL__" disabled>
                      Cargando opciones...
                    </SelectItem>
                  ) : opcionesFiltros?.analistas &&
                    opcionesFiltros.analistas.length > 0 ? (
                    opcionesFiltros.analistas.map((a: string) => (
                      <SelectItem key={a} value={a}>
                        {a}
                      </SelectItem>
                    ))
                  ) : (
                    <SelectItem value="__ALL__" disabled>
                      No hay opciones disponibles
                    </SelectItem>
                  )}
                </SelectContent>
              </Select>
            </div>

            {/* Concesionario */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Concesionario</label>
              <Select
                value={filtros.concesionario ?? '__ALL__'}
                onValueChange={(value) =>
                  setFiltros({
                    ...filtros,
                    concesionario: value === '__ALL__' ? undefined : value,
                  })
                }
                disabled={loadingOpcionesFiltros}
              >
                <SelectTrigger>
                  <SelectValue
                    placeholder={
                      loadingOpcionesFiltros
                        ? 'Cargando...'
                        : errorOpcionesFiltros
                        ? 'Error al cargar'
                        : 'Todos los concesionarios'
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__ALL__">Todos los concesionarios</SelectItem>
                  {loadingOpcionesFiltros ? (
                    <SelectItem value="__ALL__" disabled>
                      Cargando opciones...
                    </SelectItem>
                  ) : opcionesFiltros?.concesionarios &&
                    opcionesFiltros.concesionarios.length > 0 ? (
                    opcionesFiltros.concesionarios.map((c: string) => (
                      <SelectItem key={c} value={c}>
                        {c}
                      </SelectItem>
                    ))
                  ) : (
                    <SelectItem value="__ALL__" disabled>
                      No hay opciones disponibles
                    </SelectItem>
                  )}
                </SelectContent>
              </Select>
            </div>

            {/* Modelo */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Modelo</label>
              <Select
                value={filtros.modelo ?? '__ALL__'}
                onValueChange={(value) =>
                  setFiltros({
                    ...filtros,
                    modelo: value === '__ALL__' ? undefined : value,
                  })
                }
                disabled={loadingOpcionesFiltros}
              >
                <SelectTrigger>
                  <SelectValue
                    placeholder={
                      loadingOpcionesFiltros
                        ? 'Cargando...'
                        : errorOpcionesFiltros
                        ? 'Error al cargar'
                        : 'Todos los modelos'
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__ALL__">Todos los modelos</SelectItem>
                  {loadingOpcionesFiltros ? (
                    <SelectItem value="__ALL__" disabled>
                      Cargando opciones...
                    </SelectItem>
                  ) : opcionesFiltros?.modelos &&
                    opcionesFiltros.modelos.length > 0 ? (
                    opcionesFiltros.modelos.map((m: string) => (
                      <SelectItem key={m} value={m}>
                        {m}
                      </SelectItem>
                    ))
                  ) : (
                    <SelectItem value="__ALL__" disabled>
                      No hay opciones disponibles
                    </SelectItem>
                  )}
                </SelectContent>
              </Select>
            </div>

            {/* Rango de Fechas */}
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-2">
                <label className="text-sm font-medium">Fecha Desde</label>
                <Input
                  type="date"
                  value={filtros.fecha_inicio || ''}
                  onChange={(e) =>
                    setFiltros({
                      ...filtros,
                      fecha_inicio: e.target.value || undefined,
                    })
                  }
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Fecha Hasta</label>
                <Input
                  type="date"
                  value={filtros.fecha_fin || ''}
                  onChange={(e) =>
                    setFiltros({
                      ...filtros,
                      fecha_fin: e.target.value || undefined,
                    })
                  }
                />
              </div>
            </div>
          </div>
        </PopoverContent>
      </Popover>

      {onRefresh && (
        <Button
          variant="outline"
          size="sm"
          onClick={onRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          Actualizar
        </Button>
      )}
    </div>
  )
}

