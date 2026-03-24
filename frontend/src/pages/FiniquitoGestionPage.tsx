import { useCallback, useEffect, useState } from 'react'

import { Link } from 'react-router-dom'

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
} from '../services/finiquitoService'

type FiltroEstado = 'TODOS' | 'REVISION' | 'ACEPTADO' | 'RECHAZADO'

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
      toast.success(
        `Refresco listo: elegibles ${r.elegibles ?? 0}, insertados ${r.insertados ?? 0}`
      )
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
          <h1 className="text-2xl font-bold text-gray-900">Finiquito - Administración</h1>
          <p className="text-sm text-gray-500">
            Vista inferior: casos rechazados. Puede mover a cualquier estado.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link to="/finiquitos">Portal público Finiquito</Link>
          </Button>
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
            Por defecto muestra rechazados. Puede ver todos o filtrar por estado.
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
                <SelectItem value="RECHAZADO">Rechazados (vista inferior)</SelectItem>
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
            <p className="py-8 text-center text-sm text-slate-500">Sin registros.</p>
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
                        <Select
                          onValueChange={v => cambiarEstado(row.id, v)}
                        >
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
