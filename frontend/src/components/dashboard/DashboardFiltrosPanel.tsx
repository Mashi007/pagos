import { useState, useEffect } from 'react'
import { Filter, X, RefreshCw, Check } from 'lucide-react'
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
  periodo = 'año', // ✅ Por defecto: "Este año"
  setPeriodo,
  onRefresh,
  isRefreshing = false,
  opcionesFiltros,
  loadingOpcionesFiltros = false,
  errorOpcionesFiltros = false,
}: DashboardFiltrosPanelProps) {
  const [showFiltros, setShowFiltros] = useState(false)
  // ✅ Estado temporal para filtros antes de aplicar
  const [filtrosTemporales, setFiltrosTemporales] = useState<DashboardFiltros>(filtros)
  const { tieneFiltrosActivos, cantidadFiltrosActivos } = useDashboardFiltros(filtros)

  // ✅ Sincronizar filtros temporales cuando cambian los filtros reales (desde fuera) y se abre el popover
  useEffect(() => {
    if (showFiltros) {
      setFiltrosTemporales(filtros)
    }
  }, [filtros, showFiltros])

  const handleLimpiarFiltros = () => {
    console.log('🧹 Limpiando filtros...')
    const filtrosVacios: DashboardFiltros = {}
    setFiltrosTemporales(filtrosVacios)
    setFiltros(filtrosVacios)
    setShowFiltros(false) // Cerrar popover después de limpiar
  }

  // ✅ Función para aplicar filtros
  const handleAplicarFiltros = () => {
    console.log('✅ Aplicando filtros:', filtrosTemporales)
    setFiltros(filtrosTemporales)
    setShowFiltros(false) // Cerrar popover después de aplicar
  }

  return (
    <div className="flex items-center space-x-3">
      {/* Popover de Filtros */}
      <Popover
        open={showFiltros}
        onOpenChange={(open) => {
          setShowFiltros(open)
          // ✅ Cuando se abre el popover, sincronizar filtros temporales con los actuales
          if (open) {
            setFiltrosTemporales(filtros)
          }
        }}
      >
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
                value={filtrosTemporales.analista ?? '__ALL__'}
                onValueChange={(value) => {
                  const nuevoFiltro = {
                    ...filtrosTemporales,
                    analista: value === '__ALL__' ? undefined : value,
                  }
                  console.log('🔍 [Filtro Analista] Cambiando filtro temporal:', { anterior: filtrosTemporales.analista, nuevo: nuevoFiltro.analista, todosLosFiltros: nuevoFiltro })
                  setFiltrosTemporales(nuevoFiltro)
                }}
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
                value={filtrosTemporales.concesionario ?? '__ALL__'}
                onValueChange={(value) => {
                  const nuevoFiltro = {
                    ...filtrosTemporales,
                    concesionario: value === '__ALL__' ? undefined : value,
                  }
                  console.log('🔍 [Filtro Concesionario] Cambiando filtro temporal:', { anterior: filtrosTemporales.concesionario, nuevo: nuevoFiltro.concesionario, todosLosFiltros: nuevoFiltro })
                  setFiltrosTemporales(nuevoFiltro)
                }}
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
                value={filtrosTemporales.modelo ?? '__ALL__'}
                onValueChange={(value) => {
                  const nuevoFiltro = {
                    ...filtrosTemporales,
                    modelo: value === '__ALL__' ? undefined : value,
                  }
                  console.log('🔍 [Filtro Modelo] Cambiando filtro temporal:', { anterior: filtrosTemporales.modelo, nuevo: nuevoFiltro.modelo, todosLosFiltros: nuevoFiltro })
                  setFiltrosTemporales(nuevoFiltro)
                }}
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
                  value={filtrosTemporales.fecha_inicio || ''}
                  onChange={(e) => {
                    const nuevoFiltro = {
                      ...filtrosTemporales,
                      fecha_inicio: e.target.value || undefined,
                    }
                    console.log('🔍 [Filtro Fecha Inicio] Cambiando filtro temporal:', { anterior: filtrosTemporales.fecha_inicio, nuevo: nuevoFiltro.fecha_inicio, todosLosFiltros: nuevoFiltro })
                    setFiltrosTemporales(nuevoFiltro)
                  }}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Fecha Hasta</label>
                <Input
                  type="date"
                  value={filtrosTemporales.fecha_fin || ''}
                  onChange={(e) => {
                    const nuevoFiltro = {
                      ...filtrosTemporales,
                      fecha_fin: e.target.value || undefined,
                    }
                    console.log('🔍 [Filtro Fecha Fin] Cambiando filtro temporal:', { anterior: filtrosTemporales.fecha_fin, nuevo: nuevoFiltro.fecha_fin, todosLosFiltros: nuevoFiltro })
                    setFiltrosTemporales(nuevoFiltro)
                  }}
                />
              </div>
            </div>

            {/* ✅ Botón para Aplicar Filtros */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setFiltrosTemporales(filtros) // Resetear a filtros actuales
                  setShowFiltros(false) // Cerrar popover
                }}
              >
                Cancelar
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={handleAplicarFiltros}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                <Check className="mr-2 h-4 w-4" />
                Aplicar Filtros
              </Button>
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

