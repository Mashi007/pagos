import { useCallback, useEffect, useState } from 'react'

import { Loader2, RefreshCw } from 'lucide-react'

import { toast } from 'sonner'

import { Button } from '../components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/card'
import { Label } from '../components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table'

import {
  type FiniquitoCasoItem,
  finiquitoAdminListar,
  finiquitoAdminPatchEstado,
  finiquitoAdminRefreshMaterializado,
  type FiniquitoRefreshStats,
} from '../services/finiquitoService'

type FiltroEstado = 'TODOS' | 'REVISION' | 'ACEPTADO' | 'RECHAZADO'

function mensajeListaVacia(filtro: FiltroEstado): string {
  if (filtro === 'RECHAZADO') {
    return 'No hay casos con estado Rechazado. El refresco puede indicar muchos «elegibles» y «insertados 0»: son préstamos que ya tenían fila en finiquito (se actualizaron, no se crearon nuevas). Cambie el filtro a Revisión o Todos para ver el resto.'
  }
  if (filtro === 'REVISION') {
    return 'No hay casos en Revisión. Pruebe Todos o ejecute «Refrescar materializado» si acaba de cargar datos.'
  }
  if (filtro === 'ACEPTADO') {
    return 'No hay casos aceptados con el filtro actual. Pruebe Todos o Revisión.'
  }
  return 'No hay casos en la tabla materializada. Ejecute «Refrescar materializado» o verifique préstamos saldados en el sistema.'
}

function textoToastRefresco(r: FiniquitoRefreshStats): {
  titulo: string
  descripcion: string
} {
  const ins = r.insertados ?? 0
  const act = r.actualizados ?? 0
  const eli = r.eliminados ?? 0
  const elg = r.elegibles ?? 0
  return {
    titulo: `Refresco: ${elg} elegibles · ${ins} nuevos · ${act} actualizados`,
    descripcion:
      ins === 0 && elg > 0
        ? 'Insertados 0 es normal si esos préstamos ya estaban en finiquito. La lista de abajo depende del filtro de bandeja (Rechazados solo muestra estado RECHAZADO).'
        : `Quitados del listado (ya no califican): ${eli}. Revise el filtro de bandeja si no ve filas.`,
  }
}

export function FiniquitoGestionPage() {
  const [filtro, setFiltro] = useState<FiltroEstado>('RECHAZADO')
  const [items, setItems] = useState<FiniquitoCasoItem[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const cargar = useCallback(async () => {
    setLoading(true)
    try {
      const estado = filtro === 'TODOS' ? undefined : filtro
      const r = await finiquitoAdminListar(estado)
      setItems(r.items || [])
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al cargar')
    } finally {
      setLoading(false)
    }
  }, [filtro])

  useEffect(() => {
    cargar()
  }, [cargar])

  const onRefreshJob = async () => {
    setRefreshing(true)
    try {
      const r = await finiquitoAdminRefreshMaterializado()
      const { titulo, descripcion } = textoToastRefresco(r)
      toast.success(titulo, { description: descripcion })
      cargar()
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al refrescar')
    } finally {
      setRefreshing(false)
    }
  }

  const cambiarEstado = async (id: number, estado: string) => {
    try {
      const r = await finiquitoAdminPatchEstado(id, estado)
      if (!r.ok) {
        toast.error(r.error || 'No se pudo actualizar')
        return
      }
      toast.success('Estado actualizado')
      cargar()
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error')
    }
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Finiquito - Administración
          </h1>
          <p className="text-sm text-gray-500">
            Vista inferior: casos rechazados. Puede mover a cualquier estado.
            Los colaboradores entran por la URL pública de finiquito (no por
            este menú).
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="secondary"
            disabled={refreshing}
            onClick={onRefreshJob}
            className="gap-2"
          >
            {refreshing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" aria-hidden />
            )}
            Refrescar materializado
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filtro</CardTitle>
          <CardDescription>
            Por defecto muestra rechazados. Puede ver todos o filtrar por
            estado. «Elegibles» en el refresco = préstamos cuya suma de cuotas
            pagadas iguala el financiamiento; no es el conteo de filas de esta
            tabla ni de rechazados.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="space-y-2">
            <Label>Bandeja</Label>
            <Select
              value={filtro}
              onValueChange={v => setFiltro(v as FiltroEstado)}
            >
              <SelectTrigger className="w-[220px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="RECHAZADO">
                  Rechazados (vista inferior)
                </SelectItem>
                <SelectItem value="REVISION">Revisión</SelectItem>
                <SelectItem value="ACEPTADO">Aceptados</SelectItem>
                <SelectItem value="TODOS">Todos</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button variant="outline" size="sm" onClick={() => cargar()}>
            Recargar lista
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
          ) : items.length === 0 ? (
            <p className="mx-auto max-w-xl py-8 text-center text-sm leading-relaxed text-slate-500">
              {mensajeListaVacia(filtro)}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID caso</TableHead>
                    <TableHead>Cédula</TableHead>
                    <TableHead>Préstamo</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead className="text-right">Nuevo estado</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map(row => (
                    <TableRow key={row.id}>
                      <TableCell>{row.id}</TableCell>
                      <TableCell>{row.cedula}</TableCell>
                      <TableCell>{row.prestamo_id}</TableCell>
                      <TableCell>{row.estado}</TableCell>
                      <TableCell className="text-right">
                        <Select onValueChange={v => cambiarEstado(row.id, v)}>
                          <SelectTrigger className="ml-auto w-[160px]">
                            <SelectValue placeholder="Cambiar..." />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="REVISION">Revisión</SelectItem>
                            <SelectItem value="ACEPTADO">Aceptado</SelectItem>
                            <SelectItem value="RECHAZADO">Rechazado</SelectItem>
                          </SelectContent>
                        </Select>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
