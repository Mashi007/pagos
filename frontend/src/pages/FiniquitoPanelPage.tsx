import { useCallback, useEffect, useState } from 'react'

import { Link, useNavigate } from 'react-router-dom'

import {
  Eye,
  CheckCircle2,
  XCircle,
  Loader2,
  LogOut,
  FileText,
} from 'lucide-react'

import { toast } from 'sonner'

import { Button } from '../components/ui/button'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table'

import { Badge } from '../components/ui/badge'

import { FiniquitoRevisionDialog } from '../components/finiquito/FiniquitoRevisionDialog'

import {
  type FiniquitoCasoItem,
  finiquitoListarCasos,
  finiquitoPatchEstadoPublic,
  getFiniquitoAccessToken,
  setFiniquitoAccessToken,
} from '../services/finiquitoService'

import { PUBLIC_FLOW_SESSION_KEY } from '../config/env'

import { formatDate } from '../utils'

function textoUltimoPago(iso: string | null | undefined): string {
  if (iso == null || String(iso).trim() === '') return '-'
  try {
    return formatDate(String(iso))
  } catch {
    return String(iso)
  }
}

function etiquetaEstadoFiniquito(estado: string) {
  const e = (estado || '').toUpperCase()
  if (e === 'REVISION')
    return { label: 'Revisión', className: 'bg-amber-100 text-amber-900' }
  if (e === 'ACEPTADO')
    return { label: 'Aceptado', className: 'bg-emerald-100 text-emerald-900' }
  if (e === 'RECHAZADO')
    return { label: 'Rechazado', className: 'bg-red-100 text-red-900' }
  if (e === 'EN_PROCESO')
    return { label: 'En proceso', className: 'bg-sky-100 text-sky-950' }
  if (e === 'TERMINADO')
    return { label: 'Terminado', className: 'bg-emerald-200 text-emerald-950' }
  return { label: estado || '-', className: 'bg-slate-100 text-slate-800' }
}

export function FiniquitoPanelPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<FiniquitoCasoItem[]>([])
  const [loading, setLoading] = useState(true)
  const [revisionOpen, setRevisionOpen] = useState(false)
  const [revisionCasoId, setRevisionCasoId] = useState<number | null>(null)

  const salir = useCallback(() => {
    setFiniquitoAccessToken(null)
    navigate('/finiquitos', { replace: true })
  }, [navigate])

  const cargar = useCallback(async () => {
    if (!getFiniquitoAccessToken()) {
      navigate('/finiquitos/acceso', { replace: true })
      return
    }
    setLoading(true)
    try {
      const r = await finiquitoListarCasos()
      setItems(r.items || [])
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Error al cargar'
      toast.error(msg)
      if (msg.toLowerCase().includes('token')) {
        salir()
      }
    } finally {
      setLoading(false)
    }
  }, [navigate, salir])

  useEffect(() => {
    cargar()
  }, [cargar])

  useEffect(() => {
    sessionStorage.setItem(PUBLIC_FLOW_SESSION_KEY, '1')
    sessionStorage.setItem(
      PUBLIC_FLOW_SESSION_KEY + '_path',
      'finiquitos/panel'
    )
  }, [])

  const abrirRevision = (casoId: number) => {
    setRevisionCasoId(casoId)
    setRevisionOpen(true)
  }

  const aceptar = async (id: number) => {
    try {
      const r = await finiquitoPatchEstadoPublic(id, 'ACEPTADO')
      if (!r.ok) {
        toast.error(r.error || 'No se pudo aceptar')
        return
      }
      toast.success('Caso aceptado (desk).')
      cargar()
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error')
    }
  }

  const rechazar = async (id: number) => {
    try {
      const r = await finiquitoPatchEstadoPublic(id, 'RECHAZADO')
      if (!r.ok) {
        toast.error(r.error || 'No se pudo rechazar')
        return
      }
      toast.success('Caso rechazado; solo un administrador puede revertirlo.')
      cargar()
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error')
    }
  }

  return (
    <div className="min-h-[100dvh] bg-gradient-to-b from-slate-50 to-slate-100 p-4 sm:p-6">
      <div className="mx-auto max-w-6xl space-y-4">
        <ModulePageHeader
          icon={FileText}
          title="Finiquito"
          description="Préstamos con financiamiento = suma de abonos. El ojo abre el detalle del crédito: préstamo completo, plan de cuotas, préstamos y pagos por cédula. En Revisión puede aceptar o rechazar."
          actions={
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" asChild>
                <Link to="/finiquitos">Inicio Finiquito</Link>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="gap-1"
                onClick={salir}
              >
                <LogOut className="h-4 w-4" aria-hidden />
                Cerrar sesión
              </Button>
            </div>
          }
        />

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              Casos listos para finiquito
            </CardTitle>
            <CardDescription>
              Cada fila cumple total financiamiento = total abonos. Solo en
              estado Revisión puede aceptar (desk) o rechazar (revisión
              administrador).
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
              </div>
            ) : items.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">
                No hay casos materializados. El listado se actualiza en el
                servidor (p. ej. 02:00) cuando existan préstamos con la regla
                cumplida.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Cédula</TableHead>
                      <TableHead>Préstamo</TableHead>
                      <TableHead>Financiamiento</TableHead>
                      <TableHead>Abonos (suma)</TableHead>
                      <TableHead>Último pago</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead className="text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {items.map(row => (
                      <TableRow key={row.id}>
                        <TableCell className="font-medium">
                          {row.cedula}
                        </TableCell>
                        <TableCell>{row.prestamo_id}</TableCell>
                        <TableCell>{row.total_financiamiento}</TableCell>
                        <TableCell>{row.sum_total_pagado}</TableCell>
                        <TableCell
                          className="whitespace-nowrap text-sm text-slate-800"
                          title={
                            row.ultima_fecha_pago
                              ? `Pagos: ${row.ultima_fecha_pago}`
                              : undefined
                          }
                        >
                          {textoUltimoPago(row.ultima_fecha_pago)}
                        </TableCell>
                        <TableCell>
                          {(() => {
                            const t = etiquetaEstadoFiniquito(row.estado)
                            return (
                              <Badge className={`border-0 ${t.className}`}>
                                {t.label}
                              </Badge>
                            )
                          })()}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex flex-wrap justify-end gap-1">
                            <Button
                              size="icon"
                              variant="outline"
                              title="Ver préstamos y pagos (como en el sistema)"
                              onClick={() => abrirRevision(row.id)}
                            >
                              <Eye className="h-4 w-4" aria-hidden />
                            </Button>
                            {row.estado === 'REVISION' && (
                              <>
                                <Button
                                  size="icon"
                                  variant="outline"
                                  className="text-green-700"
                                  title="Aceptar"
                                  onClick={() => aceptar(row.id)}
                                >
                                  <CheckCircle2
                                    className="h-4 w-4"
                                    aria-hidden
                                  />
                                </Button>
                                <Button
                                  size="icon"
                                  variant="outline"
                                  className="text-red-700"
                                  title="Rechazar"
                                  onClick={() => rechazar(row.id)}
                                >
                                  <XCircle className="h-4 w-4" aria-hidden />
                                </Button>
                              </>
                            )}
                          </div>
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

      <FiniquitoRevisionDialog
        open={revisionOpen}
        casoId={revisionCasoId}
        onOpenChange={open => {
          setRevisionOpen(open)
          if (!open) setRevisionCasoId(null)
        }}
      />
    </div>
  )
}
