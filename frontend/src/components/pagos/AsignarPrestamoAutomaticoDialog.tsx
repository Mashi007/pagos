import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '../../components/ui/dialog'
import { Button } from '../../components/ui/button'
import { Badge } from '../../components/ui/badge'
import {
  AlertCircle,
  CheckCircle,
  Loader2,
  RefreshCw,
} from 'lucide-react'
import { pagoService } from '../../services/pagoService'
import { toast } from 'sonner'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table'

interface AsignarPrestamoAutomaticoDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onAsignacionCompleta?: () => void
}

export function AsignarPrestamoAutomaticoDialog({
  open,
  onOpenChange,
  onAsignacionCompleta,
}: AsignarPrestamoAutomaticoDialogProps) {
  const [loading, setLoading] = useState(false)
  const [asignando, setAsignando] = useState(false)
  const [sugerencias, setSugerencias] = useState<Array<{
    pago_id: number
    cedula_cliente: string
    fecha_pago: string | null
    monto_pagado: number
    numero_documento: string
    prestamo_sugerido: number | null
    num_creditos_activos: number
    acciones_necesarias: 'auto' | 'manual'
  }> | null>(null)
  const [resumen, setResumen] = useState<{
    total_pagos_sin_prestamo: number
    can_auto_asignar: number
    requieren_manual: number
  } | null>(null)
  const [resultado, setResultado] = useState<{
    asignados: number
    no_asignables: number
    mensaje: string
  } | null>(null)

  const handleCargarSugerencias = async () => {
    setLoading(true)
    try {
      const data = await pagoService.sugerirPagosConPréstamoFaltante(1, 100)
      setSugerencias(data.sugerencias)
      setResumen(data.resumen)
      setResultado(null)
    } catch (error) {
      toast.error('Error al cargar sugerencias')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleAsignarAutomatico = async () => {
    setAsignando(true)
    try {
      const data = await pagoService.asignarAutomáticamentePréstamos()
      setResultado({
        asignados: data.asignados,
        no_asignables: data.no_asignables,
        mensaje: data.mensaje,
      })
      toast.success(`Se asignaron ${data.asignados} pagos automáticamente`)
      onAsignacionCompleta?.()
    } catch (error) {
      toast.error('Error al asignar préstamos')
      console.error(error)
    } finally {
      setAsignando(false)
    }
  }

  const handleReiniciar = () => {
    setSugerencias(null)
    setResumen(null)
    setResultado(null)
  }

  const handleClose = () => {
    handleReiniciar()
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Auto-Asignar Préstamos a Pagos</DialogTitle>
          <DialogDescription>
            Identifica pagos sin crédito asignado y asigna automáticamente si el cliente tiene exactamente 1 crédito activo.
          </DialogDescription>
        </DialogHeader>

        {!resultado && !sugerencias && (
          <div className="space-y-4">
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
              <div className="flex gap-3">
                <AlertCircle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-amber-900">
                    Buscar pagos sin préstamo asignado
                  </p>
                  <p className="text-sm text-amber-700 mt-1">
                    Se identificarán los pagos que pueden asignarse automáticamente (cliente con exactamente 1 crédito activo) y los que requieren intervención manual.
                  </p>
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={handleClose}>
                Cancelar
              </Button>
              <Button onClick={handleCargarSugerencias} disabled={loading}>
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Cargar Sugerencias
              </Button>
            </DialogFooter>
          </div>
        )}

        {sugerencias && !resultado && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-lg border p-4 bg-blue-50">
                <p className="text-sm text-gray-600">Total sin Préstamo</p>
                <p className="text-2xl font-bold text-blue-600">
                  {resumen?.total_pagos_sin_prestamo || 0}
                </p>
              </div>
              <div className="rounded-lg border p-4 bg-green-50">
                <p className="text-sm text-gray-600">Pueden Auto-Asignarse</p>
                <p className="text-2xl font-bold text-green-600">
                  {resumen?.can_auto_asignar || 0}
                </p>
              </div>
              <div className="rounded-lg border p-4 bg-orange-50">
                <p className="text-sm text-gray-600">Requieren Manual</p>
                <p className="text-2xl font-bold text-orange-600">
                  {resumen?.requieren_manual || 0}
                </p>
              </div>
            </div>

            {sugerencias.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold mb-2">Primeras 10 sugerencias:</h3>
                <div className="rounded-lg border overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>ID Pago</TableHead>
                        <TableHead>Cédula</TableHead>
                        <TableHead>Créditos Activos</TableHead>
                        <TableHead>Sugerencia</TableHead>
                        <TableHead>Acción</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {sugerencias.slice(0, 10).map(sugerencia => (
                        <TableRow key={sugerencia.pago_id}>
                          <TableCell className="font-mono text-sm">
                            #{sugerencia.pago_id}
                          </TableCell>
                          <TableCell>{sugerencia.cedula_cliente}</TableCell>
                          <TableCell>{sugerencia.num_creditos_activos}</TableCell>
                          <TableCell>
                            {sugerencia.prestamo_sugerido ? (
                              <span className="text-sm">
                                Asignar a #{sugerencia.prestamo_sugerido}
                              </span>
                            ) : (
                              <span className="text-xs text-gray-500">
                                {sugerencia.num_creditos_activos === 0
                                  ? 'Sin créditos'
                                  : `${sugerencia.num_creditos_activos} créditos`}
                              </span>
                            )}
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant={
                                sugerencia.acciones_necesarias === 'auto'
                                  ? 'default'
                                  : 'secondary'
                              }
                              className="text-xs"
                            >
                              {sugerencia.acciones_necesarias === 'auto'
                                ? 'Auto'
                                : 'Manual'}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}

            <DialogFooter>
              <Button variant="outline" onClick={handleReiniciar}>
                Volver
              </Button>
              <Button
                onClick={handleAsignarAutomatico}
                disabled={asignando || (resumen?.can_auto_asignar || 0) === 0}
              >
                {asignando && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Asignar {resumen?.can_auto_asignar || 0} Préstamos
              </Button>
            </DialogFooter>
          </div>
        )}

        {resultado && (
          <div className="space-y-4">
            <div className="rounded-lg border border-green-200 bg-green-50 p-4">
              <div className="flex gap-3">
                <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-green-900">
                    Asignación Completada
                  </p>
                  <p className="text-sm text-green-700 mt-1">{resultado.mensaje}</p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-lg border p-4 bg-green-50">
                <p className="text-sm text-gray-600">Asignados</p>
                <p className="text-2xl font-bold text-green-600">
                  {resultado.asignados}
                </p>
              </div>
              <div className="rounded-lg border p-4 bg-orange-50">
                <p className="text-sm text-gray-600">Requieren Manual</p>
                <p className="text-2xl font-bold text-orange-600">
                  {resultado.no_asignables}
                </p>
              </div>
            </div>

            <DialogFooter>
              <Button onClick={handleClose}>Cerrar</Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
