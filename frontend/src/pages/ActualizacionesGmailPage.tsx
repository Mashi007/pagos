/**
 * Actualizaciones > Gmail: re-escaneo manual por remitente.
 *
 * Permite acotar el pipeline Gmail vigente (mismo flujo que "Procesar manualmente" en /pagos)
 * a UN remitente, ignorando la regla global de "skip por etiqueta de usuario" SOLO para ese
 * remitente. Muestra los pagos detectados en tabla (banco, fecha pago, monto, serial, etc.)
 * con acciones Guardar / Editar / Eliminar, encadenadas a los endpoints canónicos:
 *  - Guardar: migra a pagos_con_errores y aplica `mover_a_pagos_normales` (cascada cuotas vigente).
 *  - Editar: PUT al sync_item (campos básicos); las reglas duras corren al guardar.
 *  - Eliminar: borra la fila local (sync_item + gmail_temporal asociados). No toca Gmail.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'

import {
  CheckCircle2,
  Loader2,
  Mail,
  Pencil,
  RefreshCw,
  Save,
  Trash2,
  X,
} from 'lucide-react'

import { toast } from 'sonner'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Button } from '../components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../components/ui/card'
import { Input } from '../components/ui/input'
import {
  pagoService,
  type GmailSyncItemUI,
} from '../services/pagoService'
import { useGmailPipeline } from '../hooks/useGmailPipeline'
import { getErrorMessage } from '../types/errors'

const QK_LIST = ['actualizaciones', 'gmail', 'sync-items'] as const

const PAGE_SIZE = 50

/** Devuelve la URL final del comprobante: si llega path relativo, se prefija con BASE_PATH. */
function urlComprobante(raw: string | null | undefined): string | null {
  const s = (raw || '').trim()
  if (!s) return null
  if (s.startsWith('http://') || s.startsWith('https://')) return s
  // path relativo: el apiClient añade base; aquí solo lo devolvemos tal cual.
  return s
}

function safeMonto(item: GmailSyncItemUI): string {
  const m = (item.monto || '').trim()
  return m || '-'
}

interface FilaEnEdicion {
  banco: string
  cedula: string
  fecha_pago: string
  monto: string
  numero_referencia: string
}

function filaInicialDesdeItem(item: GmailSyncItemUI): FilaEnEdicion {
  return {
    banco: item.banco || '',
    cedula: item.cedula || '',
    fecha_pago: item.fecha_pago || '',
    monto: item.monto || '',
    numero_referencia: item.numero_referencia || '',
  }
}

export default function ActualizacionesGmailPage() {
  const queryClient = useQueryClient()
  const [correoInput, setCorreoInput] = useState('')
  const [correoFiltro, setCorreoFiltro] = useState('')
  const [pagina, setPagina] = useState(1)
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [edicion, setEdicion] = useState<FilaEnEdicion | null>(null)

  const offset = (pagina - 1) * PAGE_SIZE

  // La tabla SOLO se llena cuando hay un correo: el módulo no expone el histórico global de la cola Gmail.
  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: [...QK_LIST, correoFiltro, pagina],
    queryFn: () =>
      pagoService.listGmailSyncItems({
        correo: correoFiltro,
        limit: PAGE_SIZE,
        offset,
      }),
    enabled: !!correoFiltro,
    refetchOnWindowFocus: false,
  })

  const { loading: ejecutandoPipeline, gmailStatus, run } = useGmailPipeline({
    onDone: () => {
      void queryClient.invalidateQueries({ queryKey: QK_LIST })
    },
  })

  const total = data?.total ?? 0
  const totalPaginas = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const items: GmailSyncItemUI[] = useMemo(() => data?.items ?? [], [data])

  const handleReescanear = useCallback(() => {
    const email = correoInput.trim().toLowerCase()
    if (!email || !email.includes('@')) {
      toast.error('Indica un correo válido (ej. cliente@dominio.com).')
      return
    }
    setCorreoFiltro(email)
    setPagina(1)
    void run('manual_redigitaliza_por_remitente', email)
  }, [correoInput, run])

  const handleLimpiar = useCallback(() => {
    setCorreoInput('')
    setCorreoFiltro('')
    setPagina(1)
  }, [])

  const guardarMutation = useMutation({
    mutationFn: (itemId: number) => pagoService.guardarGmailSyncItem(itemId),
    onSuccess: res => {
      toast.success(res.mensaje || 'Pago guardado.')
      void queryClient.invalidateQueries({ queryKey: QK_LIST })
    },
    onError: err => {
      toast.error(getErrorMessage(err) || 'No se pudo guardar')
    },
  })

  const eliminarMutation = useMutation({
    mutationFn: (itemId: number) => pagoService.deleteGmailSyncItem(itemId),
    onSuccess: () => {
      toast.success('Fila eliminada.')
      void queryClient.invalidateQueries({ queryKey: QK_LIST })
    },
    onError: err => {
      toast.error(getErrorMessage(err) || 'No se pudo eliminar')
    },
  })

  const editarMutation = useMutation({
    mutationFn: ({
      itemId,
      cambios,
    }: {
      itemId: number
      cambios: FilaEnEdicion
    }) => pagoService.editGmailSyncItem(itemId, cambios),
    onSuccess: () => {
      toast.success('Cambios guardados.')
      setEditandoId(null)
      setEdicion(null)
      void queryClient.invalidateQueries({ queryKey: QK_LIST })
    },
    onError: err => {
      toast.error(getErrorMessage(err) || 'No se pudo editar')
    },
  })

  const handleEditar = useCallback((item: GmailSyncItemUI) => {
    setEditandoId(item.id)
    setEdicion(filaInicialDesdeItem(item))
  }, [])

  const handleCancelarEdicion = useCallback(() => {
    setEditandoId(null)
    setEdicion(null)
  }, [])

  const handleGuardarEdicion = useCallback(() => {
    if (editandoId == null || edicion == null) return
    editarMutation.mutate({ itemId: editandoId, cambios: edicion })
  }, [editandoId, edicion, editarMutation])

  const handleEliminar = useCallback(
    (item: GmailSyncItemUI) => {
      const ok = window.confirm(
        `¿Eliminar la fila del comprobante ${item.numero_referencia || '(sin serial)'} (${item.banco || 'sin banco'})?\n\n` +
          'Esto borra la fila local (no toca Gmail). Si el correo se vuelve a escanear y la regla de etiqueta lo permite, podría reaparecer.'
      )
      if (!ok) return
      eliminarMutation.mutate(item.id)
    },
    [eliminarMutation]
  )

  const handleGuardar = useCallback(
    (item: GmailSyncItemUI) => {
      if (item.duplicado_en_pagos) {
        const ok = window.confirm(
          `El serial ${item.numero_referencia || '(s/r)'} ya existe en pagos (id ${item.pago_id_existente ?? '?'}). ` +
            '¿Eliminar esta fila de revisión? No se creará un duplicado en cartera.'
        )
        if (!ok) return
      }
      guardarMutation.mutate(item.id)
    },
    [guardarMutation]
  )

  // Refetch automático al terminar el pipeline (por si onDone no se disparó por backoff).
  useEffect(() => {
    if (!ejecutandoPipeline && gmailStatus?.last_status === 'success') {
      void queryClient.invalidateQueries({ queryKey: QK_LIST })
    }
  }, [ejecutandoPipeline, gmailStatus?.last_status, queryClient])

  const editingActive = editandoId != null && edicion != null

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Actualizaciones · Gmail"
        description="Re-escaneo manual por remitente. Indica un correo y se procesarán los mensajes de ese remitente que cumplan el criterio del pipeline (imagen/PDF en bandeja). Mismo flujo que «Procesar manualmente» en Pagos: para ese remitente concreto se omite la regla global de «skip por etiqueta de usuario» y se re-clasifica. Guardar aplica cascada de cuotas vigente."
        icon={Mail}
      />

      <Card>
        <CardHeader className="space-y-3">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <CardTitle className="text-lg">Re-escanear correos del remitente</CardTitle>
            <div className="text-xs text-muted-foreground">
              {gmailStatus?.last_status === 'running' ? (
                <span className="text-amber-700">Pipeline en curso…</span>
              ) : gmailStatus?.last_run ? (
                <span>
                  Última sync Gmail: {new Date(gmailStatus.last_run).toLocaleString()} ·{' '}
                  {gmailStatus.last_emails ?? 0} correo(s) ·{' '}
                  {gmailStatus.last_files ?? 0} archivo(s)
                </span>
              ) : (
                <span>Sin sync Gmail aún</span>
              )}
            </div>
          </div>
          <form
            onSubmit={e => {
              e.preventDefault()
              handleReescanear()
            }}
            className="flex flex-col gap-2 sm:flex-row sm:items-center"
          >
            <Input
              type="email"
              autoComplete="email"
              placeholder="correo@dominio.com"
              value={correoInput}
              onChange={e => setCorreoInput(e.target.value)}
              className="sm:max-w-md"
            />
            <div className="flex flex-wrap gap-2">
              <Button
                type="submit"
                disabled={ejecutandoPipeline || !correoInput.trim()}
                title="Lanza el pipeline Gmail acotado a este remitente. Saltea la regla de etiquetas SOLO para este correo."
              >
                {ejecutandoPipeline ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="mr-2 h-4 w-4" />
                )}
                Re-escanear este correo
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => void refetch()}
                disabled={!correoFiltro || isFetching}
                title="Refresca la tabla de este remitente (sin volver a Gmail)"
              >
                {isFetching ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="mr-2 h-4 w-4" />
                )}
                Refrescar tabla
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={handleLimpiar}
                disabled={!correoFiltro && !correoInput}
              >
                Limpiar
              </Button>
            </div>
          </form>
        </CardHeader>
        <CardContent>
          {!correoFiltro ? (
            <div className="rounded-md border border-dashed bg-muted/30 p-6 text-center text-sm text-muted-foreground">
              Indica un correo arriba y pulsa <strong>Re-escanear este correo</strong> para
              procesar los mensajes de ese remitente. La tabla solo muestra los comprobantes
              del remitente indicado: no se expone aquí la cola Gmail general.
            </div>
          ) : (
            <>
              <div className="mb-3 flex flex-col gap-1 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
                <span>Remitente: {correoFiltro}</span>
                <span>
                  {total} fila(s){' '}
                  {totalPaginas > 1
                    ? `· página ${pagina} de ${totalPaginas}`
                    : ''}
                </span>
              </div>

              <div className="overflow-x-auto rounded-md border">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-3 py-2">Fecha correo</th>
                  <th className="px-3 py-2">Imagen</th>
                  <th className="px-3 py-2">Banco</th>
                  <th className="px-3 py-2">Fecha pago</th>
                  <th className="px-3 py-2 text-right">Monto</th>
                  <th className="px-3 py-2">Serial</th>
                  <th className="px-3 py-2">¿En pagos?</th>
                  <th className="px-3 py-2 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td
                      colSpan={8}
                      className="px-3 py-6 text-center text-muted-foreground"
                    >
                      <Loader2 className="mr-2 inline h-4 w-4 animate-spin" />
                      Cargando…
                    </td>
                  </tr>
                ) : items.length === 0 ? (
                  <tr>
                    <td
                      colSpan={8}
                      className="px-3 py-6 text-center text-muted-foreground"
                    >
                      Sin filas para mostrar.{' '}
                      {correoFiltro
                        ? 'Prueba a re-escanear ese correo o quita el filtro.'
                        : 'Re-escanea un correo para llenar la tabla.'}
                    </td>
                  </tr>
                ) : (
                  items.map(item => {
                    const enEdicion = editingActive && editandoId === item.id
                    const dup = item.duplicado_en_pagos
                    return (
                      <tr
                        key={item.id}
                        className={`border-t ${dup ? 'bg-emerald-50/40' : ''}`}
                      >
                        <td className="px-3 py-2 align-top text-xs tabular-nums">
                          {item.fecha_correo || '-'}
                          {item.correo_origen ? (
                            <div className="mt-1 max-w-[14rem] truncate text-[10px] text-muted-foreground">
                              {item.correo_origen}
                            </div>
                          ) : null}
                        </td>
                        <td className="px-3 py-2 align-top">
                          {(() => {
                            const u = urlComprobante(item.comprobante_url)
                            if (!u) {
                              return (
                                <span className="inline-flex items-center rounded border border-dashed border-muted-foreground/40 px-2 py-1 text-[11px] text-muted-foreground">
                                  Sin imagen
                                </span>
                              )
                            }
                            return (
                              <a
                                href={u}
                                target="_blank"
                                rel="noreferrer"
                                title="Abrir comprobante"
                                className="inline-block"
                              >
                                <img
                                  src={u}
                                  alt="Comprobante"
                                  className="h-16 w-16 rounded border object-cover"
                                  loading="lazy"
                                  onError={(e) => {
                                    ;(e.currentTarget as HTMLImageElement).style.display =
                                      'none'
                                  }}
                                />
                              </a>
                            )
                          })()}
                        </td>
                        <td className="px-3 py-2 align-top">
                          {enEdicion ? (
                            <Input
                              value={edicion?.banco || ''}
                              onChange={e =>
                                setEdicion(
                                  prev =>
                                    prev && { ...prev, banco: e.target.value }
                                )
                              }
                              className="h-8 text-xs"
                            />
                          ) : (
                            item.banco || '-'
                          )}
                        </td>
                        <td className="px-3 py-2 align-top">
                          {enEdicion ? (
                            <Input
                              value={edicion?.fecha_pago || ''}
                              onChange={e =>
                                setEdicion(
                                  prev =>
                                    prev && {
                                      ...prev,
                                      fecha_pago: e.target.value,
                                    }
                                )
                              }
                              placeholder="dd/MM/yyyy o YYYY-MM-DD"
                              className="h-8 text-xs"
                            />
                          ) : (
                            item.fecha_pago || '-'
                          )}
                        </td>
                        <td className="px-3 py-2 text-right align-top tabular-nums">
                          {enEdicion ? (
                            <Input
                              value={edicion?.monto || ''}
                              onChange={e =>
                                setEdicion(
                                  prev =>
                                    prev && { ...prev, monto: e.target.value }
                                )
                              }
                              className="h-8 text-right text-xs"
                            />
                          ) : (
                            safeMonto(item)
                          )}
                        </td>
                        <td className="px-3 py-2 align-top">
                          {enEdicion ? (
                            <Input
                              value={edicion?.numero_referencia || ''}
                              onChange={e =>
                                setEdicion(
                                  prev =>
                                    prev && {
                                      ...prev,
                                      numero_referencia: e.target.value,
                                    }
                                )
                              }
                              className="h-8 text-xs"
                            />
                          ) : (
                            item.numero_referencia || '-'
                          )}
                        </td>
                        <td className="px-3 py-2 align-top text-xs">
                          {dup ? (
                            <span
                              className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-900"
                              title={`Ya existe en pagos (id ${item.pago_id_existente ?? '?'})`}
                            >
                              <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
                              Sí · pago {item.pago_id_existente ?? '?'}
                            </span>
                          ) : (
                            <span className="text-muted-foreground">No</span>
                          )}
                          {enEdicion && item.cedula != null ? (
                            <div className="mt-2">
                              <Input
                                value={edicion?.cedula || ''}
                                onChange={e =>
                                  setEdicion(
                                    prev =>
                                      prev && {
                                        ...prev,
                                        cedula: e.target.value,
                                      }
                                  )
                                }
                                placeholder="Cédula"
                                className="h-8 text-xs"
                              />
                            </div>
                          ) : null}
                        </td>
                        <td className="px-3 py-2 text-right align-top">
                          <div className="flex flex-wrap justify-end gap-1.5">
                            {enEdicion ? (
                              <>
                                <Button
                                  size="sm"
                                  onClick={handleGuardarEdicion}
                                  disabled={editarMutation.isPending}
                                  title="Guardar cambios en sync_item"
                                >
                                  {editarMutation.isPending ? (
                                    <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                                  ) : (
                                    <Save className="mr-1 h-3.5 w-3.5" />
                                  )}
                                  OK
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={handleCancelarEdicion}
                                  disabled={editarMutation.isPending}
                                >
                                  <X className="mr-1 h-3.5 w-3.5" />
                                  Cancelar
                                </Button>
                              </>
                            ) : (
                              <>
                                <Button
                                  size="sm"
                                  onClick={() => handleGuardar(item)}
                                  disabled={
                                    guardarMutation.isPending ||
                                    eliminarMutation.isPending
                                  }
                                  title="Migrar a pagos_con_errores y aplicar mover-a-pagos (cascada cuotas)"
                                >
                                  {guardarMutation.isPending ? (
                                    <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                                  ) : (
                                    <Save className="mr-1 h-3.5 w-3.5" />
                                  )}
                                  Guardar
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleEditar(item)}
                                  disabled={guardarMutation.isPending}
                                  title="Editar campos básicos antes de guardar"
                                >
                                  <Pencil className="mr-1 h-3.5 w-3.5" />
                                  Editar
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleEliminar(item)}
                                  disabled={eliminarMutation.isPending}
                                  title="Eliminar la fila local (no toca Gmail)"
                                >
                                  <Trash2 className="mr-1 h-3.5 w-3.5" />
                                  Eliminar
                                </Button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>

              {totalPaginas > 1 ? (
                <div className="mt-3 flex items-center justify-between text-xs">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setPagina(p => Math.max(1, p - 1))}
                    disabled={pagina <= 1 || isFetching}
                  >
                    Anterior
                  </Button>
                  <span className="text-muted-foreground">
                    Página {pagina} de {totalPaginas}
                  </span>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setPagina(p => Math.min(totalPaginas, p + 1))}
                    disabled={pagina >= totalPaginas || isFetching}
                  >
                    Siguiente
                  </Button>
                </div>
              ) : null}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
