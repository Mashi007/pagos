import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FileText,
  DollarSign,
  Eye,
  History,
  Loader2,
  Search,
} from 'lucide-react'
import toast from 'react-hot-toast'

import { CobranzaHistorialNotasDialog } from '../components/cobranzas/CobranzaHistorialNotasDialog'
import { CobranzaNegociacionDialog } from '../components/cobranzas/CobranzaNegociacionDialog'
import {
  buscarCobranzasPorCedula,
  type CobranzaBuscarResponse,
  type CobranzaPrestamoResumen,
} from '../services/cobranzaService'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table'
import { formatCurrency } from '../utils'

function modalidadLabel(v?: string | null): string {
  if (v === 'MENSUAL') return 'Mensual'
  if (v === 'QUINCENAL') return 'Quincenal'
  if (v === 'SEMANAL') return 'Semanal'
  return v || '-'
}

function estadoPrestamoBadge(estado: string) {
  const map: Record<string, string> = {
    APROBADO: 'bg-green-100 text-green-800',
    LIQUIDADO: 'bg-slate-100 text-slate-700',
    DRAFT: 'bg-gray-100 text-gray-700',
  }
  const labels: Record<string, string> = {
    APROBADO: 'Aprobado',
    LIQUIDADO: 'Liquidado',
    DRAFT: 'Borrador',
  }
  return (
    <Badge className={map[estado] || 'bg-blue-100 text-blue-800'}>
      {labels[estado] || estado}
    </Badge>
  )
}

export default function CobranzasPage() {
  const navigate = useNavigate()
  const [cedulaInput, setCedulaInput] = useState('')
  const [buscando, setBuscando] = useState(false)
  const [resultado, setResultado] = useState<CobranzaBuscarResponse | null>(null)
  const [aperturaToken, setAperturaToken] = useState(0)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [prestamoNegociacion, setPrestamoNegociacion] =
    useState<CobranzaPrestamoResumen | null>(null)
  const [historialOpen, setHistorialOpen] = useState(false)
  const [prestamoHistorial, setPrestamoHistorial] =
    useState<CobranzaPrestamoResumen | null>(null)

  const handleBuscar = async () => {
    if (!cedulaInput.trim()) {
      toast.error('Ingrese la cedula.')
      return
    }
    setBuscando(true)
    try {
      const res = await buscarCobranzasPorCedula(cedulaInput.trim())
      setResultado(res)
      if (!res.prestamos.length) {
        toast.error('No se encontraron prestamos para esta cedula.')
      }
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al buscar')
      setResultado(null)
    } finally {
      setBuscando(false)
    }
  }

  const abrirHistorial = (p: CobranzaPrestamoResumen) => {
    setPrestamoHistorial(p)
    setHistorialOpen(true)
  }

  const abrirNegociacion = (p: CobranzaPrestamoResumen) => {
    setPrestamoNegociacion(p)
    setAperturaToken(Date.now())
    setDialogOpen(true)
  }

  const verPrestamo = (p: CobranzaPrestamoResumen) => {
    navigate(`/prestamos?filtro_prestamo_id=${p.id}`)
  }

  const onCasoActualizado = (prestamoId: number, casoId: number) => {
    setResultado(prev => {
      if (!prev) return prev
      return {
        ...prev,
        prestamos: prev.prestamos.map(pr =>
          pr.id === prestamoId
            ? { ...pr, caso_id: casoId, caso_estado: 'ABIERTO' }
            : pr
        ),
      }
    })
    setPrestamoNegociacion(prev =>
      prev && prev.id === prestamoId ? { ...prev, caso_id: casoId } : prev
    )
    setPrestamoHistorial(prev =>
      prev && prev.id === prestamoId ? { ...prev, caso_id: casoId } : prev
    )
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Cobranzas</h1>
        <p className="mt-1 text-sm text-slate-600">
          Busque por cedula. Use el icono de historial para registrar notas y ver
          el historial del prestamo.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Search className="h-5 w-5" />
            Buscar por cedula
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Input
            placeholder="V6666666 o 32862424"
            value={cedulaInput}
            onChange={e => setCedulaInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleBuscar()}
            className="max-w-xs"
          />
          <Button onClick={handleBuscar} disabled={buscando}>
            {buscando ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Buscando...
              </>
            ) : (
              'Buscar'
            )}
          </Button>
        </CardContent>
      </Card>

      {resultado && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xl">
              Prestamos — {resultado.nombres || 'Cliente'}
            </CardTitle>
            <p className="text-sm text-slate-500">Cedula: {resultado.cedula}</p>
          </CardHeader>
          <CardContent>
            {resultado.prestamos.length === 0 ? (
              <p className="py-6 text-center text-slate-500">Sin prestamos.</p>
            ) : (
              <div className="overflow-hidden rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Modalidad</TableHead>
                      <TableHead>Cuotas</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead>Pendiente</TableHead>
                      <TableHead className="text-right">Accion</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {resultado.prestamos.map(p => (
                      <TableRow key={p.id}>
                        <TableCell>{modalidadLabel(p.modalidad_pago)}</TableCell>
                        <TableCell>{p.numero_cuotas ?? '-'}</TableCell>
                        <TableCell>{estadoPrestamoBadge(p.estado)}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <DollarSign className="h-4 w-4 shrink-0 text-amber-600" />
                            <span className="font-semibold text-amber-800">
                              {formatCurrency(p.saldo_pendiente)}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-blue-600 hover:bg-blue-50"
                              title="Ver prestamo"
                              onClick={() => verPrestamo(p)}
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-violet-600 hover:bg-violet-50"
                              title="Historial de notas"
                              onClick={() => abrirHistorial(p)}
                            >
                              <History className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-orange-600 hover:bg-orange-50"
                              title="Negociacion (ventana)"
                              onClick={() => abrirNegociacion(p)}
                            >
                              <FileText className="h-4 w-4" />
                            </Button>
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
      )}

      <CobranzaNegociacionDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        prestamo={prestamoNegociacion}
        aperturaToken={aperturaToken}
        onCasoActualizado={onCasoActualizado}
      />

      <CobranzaHistorialNotasDialog
        open={historialOpen}
        onOpenChange={setHistorialOpen}
        prestamo={prestamoHistorial}
        onCasoActualizado={onCasoActualizado}
      />
    </div>
  )
}
