import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useNavigate } from 'react-router-dom'

import { useState } from 'react'

import { CheckCircle, Loader2, RefreshCw } from 'lucide-react'

import { toast } from 'sonner'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'

import { Button } from '../components/ui/button'

import { Input } from '../components/ui/input'

import { Label } from '../components/ui/label'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table'

import { Card, CardContent } from '../components/ui/card'

import { revisionManualService } from '../services/revisionManualService'

import { getErrorMessage } from '../types/errors'

import { limpiarReturnRevisionSesion } from '../constants/revisionNavigation'

export default function AutorizacionesRevisionManualAdminPage() {
  const navigate = useNavigate()

  const queryClient = useQueryClient()

  const [prestamoIdReabrir, setPrestamoIdReabrir] = useState('')

  const q = useQuery({
    queryKey: ['revision-manual-autorizaciones-reapertura'],
    queryFn: () =>
      revisionManualService.getAutorizacionesReaperturaPendientes(),
  })

  const mutAprobar = useMutation({
    mutationFn: async (solicitudId: number) => {
      const notaRaw = window.prompt('Nota interna (opcional):', '')
      const nota =
        notaRaw != null && String(notaRaw).trim()
          ? String(notaRaw).trim().slice(0, 2000)
          : undefined
      return revisionManualService.aprobarSolicitudReapertura(solicitudId, {
        nota,
      })
    },
    onSuccess: data => {
      toast.success(data.mensaje || 'Solicitud aprobada')
      void queryClient.invalidateQueries({
        queryKey: ['revision-manual-autorizaciones-reapertura'],
      })
      void queryClient.invalidateQueries({
        queryKey: ['revision-manual-prestamos'],
      })
      const abrir = window.confirm(
        `¿Abrir ahora la revisión manual del préstamo #${data.prestamo_id}?`
      )
      if (abrir) {
        limpiarReturnRevisionSesion()
        navigate(`/revision-manual/editar/${data.prestamo_id}`)
      }
    },
    onError: (err: unknown) => {
      toast.error(getErrorMessage(err) || 'No se pudo aprobar la solicitud')
    },
  })

  const mutRechazar = useMutation({
    mutationFn: async (solicitudId: number) => {
      const notaRaw = window.prompt('Motivo del rechazo (opcional):', '')
      const nota =
        notaRaw != null && String(notaRaw).trim()
          ? String(notaRaw).trim().slice(0, 2000)
          : undefined
      return revisionManualService.rechazarSolicitudReapertura(solicitudId, {
        nota,
      })
    },
    onSuccess: data => {
      toast.message(data.mensaje || 'Solicitud rechazada')
      void queryClient.invalidateQueries({
        queryKey: ['revision-manual-autorizaciones-reapertura'],
      })
    },
    onError: (err: unknown) => {
      toast.error(getErrorMessage(err) || 'No se pudo rechazar la solicitud')
    },
  })

  const mutReabrirPorId = useMutation({
    mutationFn: async (prestamoId: number) =>
      revisionManualService.iniciarRevision(prestamoId),
    onSuccess: (_data, prestamoId) => {
      toast.success(
        'Revisión puesta en «En revisión». El operario puede editar de nuevo.'
      )
      setPrestamoIdReabrir('')
      void queryClient.invalidateQueries({
        queryKey: ['revision-manual-autorizaciones-reapertura'],
      })
      void queryClient.invalidateQueries({
        queryKey: ['revision-manual-prestamos'],
      })
      const abrir = window.confirm(
        `¿Abrir ahora la pantalla de edición del préstamo #${prestamoId}?`
      )
      if (abrir) {
        limpiarReturnRevisionSesion()
        navigate(`/revision-manual/editar/${prestamoId}`)
      }
    },
    onError: (err: unknown) => {
      toast.error(
        getErrorMessage(err) ||
          'No se pudo cambiar el estado. Compruebe el ID y que exista revisión manual.'
      )
    },
  })

  const items = q.data ?? []

  return (
    <div className="container mx-auto max-w-6xl space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Autorizaciones (revisión manual)"
        description="Solicitudes de operarios para reabrir préstamos en Visto (revisado). Solo administrador."
        icon={CheckCircle}
        actions={
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={q.isFetching}
            onClick={() => void q.refetch()}
          >
            {q.isFetching ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            Actualizar
          </Button>
        }
      />

      <Card>
        <CardContent className="space-y-4 pt-6">
          <div className="rounded-lg border border-dashed border-muted-foreground/30 bg-muted/30 p-4">
            <p className="text-sm font-medium text-foreground">
              Reabrir sin solicitud previa
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Si un préstamo está en Visto (revisado) y no hay fila en la cola,
              puede ponerlo en «En revisión» aquí. Los operarios, en cambio,
              deben usar Revisión manual: clic en el estado Revisado y enviar
              solicitud al administrador.
            </p>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-end">
              <div className="flex-1 space-y-1.5">
                <Label htmlFor="prestamo-id-reabrir">ID del préstamo</Label>
                <Input
                  id="prestamo-id-reabrir"
                  inputMode="numeric"
                  placeholder="Ej. 12345"
                  value={prestamoIdReabrir}
                  onChange={e =>
                    setPrestamoIdReabrir(e.target.value.replace(/\D/g, ''))
                  }
                />
              </div>
              <Button
                type="button"
                variant="secondary"
                disabled={
                  mutReabrirPorId.isPending ||
                  !prestamoIdReabrir.trim() ||
                  Number(prestamoIdReabrir) < 1
                }
                onClick={() => {
                  const id = Number(prestamoIdReabrir)
                  if (!Number.isFinite(id) || id < 1) {
                    toast.error('Indique un ID de préstamo válido')
                    return
                  }
                  mutReabrirPorId.mutate(id)
                }}
              >
                {mutReabrirPorId.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Aplicando…
                  </>
                ) : (
                  'Poner en revisión'
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          {q.isLoading ? (
            <div className="flex items-center justify-center gap-2 py-12 text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin" />
              Cargando solicitudes…
            </div>
          ) : q.isError ? (
            <p className="text-center text-destructive">
              {getErrorMessage(q.error) || 'No se pudo cargar la lista'}
            </p>
          ) : items.length === 0 ? (
            <div className="space-y-3 py-8 text-center text-muted-foreground">
              <p>No hay solicitudes pendientes de operarios.</p>
              <p className="mx-auto max-w-lg text-sm">
                Las solicitudes aparecen cuando un operario, con un préstamo en
                Visto, hace clic en el estado «Revisado» en la lista de Revisión
                manual y confirma enviar la petición al administrador. Si solo
                necesita reabrir usted mismo, use el bloque «Reabrir sin
                solicitud previa» arriba.
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Solicitud</TableHead>
                  <TableHead>Préstamo</TableHead>
                  <TableHead>Cliente</TableHead>
                  <TableHead>Fecha</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map(row => {
                  const quien =
                    `${row.solicitante_nombre} ${row.solicitante_apellido}`.trim()
                  const email = row.solicitante_email || ''
                  const textoSolicitud = `${quien} requiere autorización: préstamo #${row.prestamo_id}${email ? ` (${email})` : ''}`
                  return (
                    <TableRow key={row.id}>
                      <TableCell className="max-w-[280px] align-top text-sm">
                        <div className="font-medium leading-snug">
                          {textoSolicitud}
                        </div>
                        {row.mensaje ? (
                          <p className="mt-1 text-xs text-muted-foreground">
                            {row.mensaje}
                          </p>
                        ) : null}
                      </TableCell>
                      <TableCell className="align-top font-mono text-sm">
                        #{row.prestamo_id}
                      </TableCell>
                      <TableCell className="align-top text-sm">
                        <div>{row.nombres_cliente || '-'}</div>
                        <div className="text-xs text-muted-foreground">
                          {row.cedula || '-'}
                        </div>
                      </TableCell>
                      <TableCell className="align-top text-xs text-muted-foreground">
                        {row.creado_en
                          ? new Date(row.creado_en).toLocaleString()
                          : '-'}
                      </TableCell>
                      <TableCell className="space-y-2 text-right align-top">
                        <div className="flex flex-col items-end gap-2 sm:flex-row sm:justify-end">
                          <Button
                            type="button"
                            size="sm"
                            variant="default"
                            disabled={
                              mutAprobar.isPending || mutRechazar.isPending
                            }
                            onClick={() => mutAprobar.mutate(row.id)}
                          >
                            Aprobar y reabrir
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            disabled={
                              mutAprobar.isPending || mutRechazar.isPending
                            }
                            onClick={() => mutRechazar.mutate(row.id)}
                          >
                            Rechazar
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="secondary"
                            onClick={() => {
                              limpiarReturnRevisionSesion()
                              navigate(
                                `/revision-manual/editar/${row.prestamo_id}`
                              )
                            }}
                          >
                            Abrir revisión
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
