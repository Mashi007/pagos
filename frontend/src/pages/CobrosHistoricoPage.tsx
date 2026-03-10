/**
 * Histórico de pagos reportados por cliente (búsqueda por cédula).
 */
import React, { useState } from 'react'
import { historicoPorCliente, type HistoricoClienteItem } from '../services/cobrosService'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import toast from 'react-hot-toast'

export default function CobrosHistoricoPage() {
  const [cedula, setCedula] = useState('')
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<HistoricoClienteItem[]>([])
  const [cedulaBusqueda, setCedulaBusqueda] = useState('')

  const handleBuscar = async () => {
    if (!cedula.trim()) {
      toast.error('Ingrese la cédula.')
      return
    }
    setLoading(true)
    try {
      const res = await historicoPorCliente(cedula.trim())
      setItems(res.items)
      setCedulaBusqueda(res.cedula)
    } catch (e: any) {
      toast.error(e?.message || 'Error al buscar.')
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Histórico por cliente</h1>

      <Card>
        <CardHeader>
          <CardTitle>Buscar por cédula</CardTitle>
        </CardHeader>
        <CardContent className="flex gap-2">
          <Input
            placeholder="V12345678 o 12345678"
            value={cedula}
            onChange={(e) => setCedula(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleBuscar()}
            className="max-w-xs"
          />
          <Button onClick={handleBuscar} disabled={loading}>
            {loading ? 'Buscando...' : 'Buscar'}
          </Button>
        </CardContent>
      </Card>

      {cedulaBusqueda && (
        <Card>
          <CardHeader>
            <CardTitle>Pagos reportados — Cédula {cedulaBusqueda}</CardTitle>
          </CardHeader>
          <CardContent>
            {!items.length ? (
              <p className="text-gray-500">No hay registros para esta cédula.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-2">Referencia</th>
                      <th className="text-left py-2">Fecha pago</th>
                      <th className="text-left py-2">Fecha reporte</th>
                      <th className="text-right py-2">Monto</th>
                      <th className="text-left py-2">Estado</th>
                      <th className="text-left py-2">Recibo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((row) => (
                      <tr key={row.id} className="border-b">
                        <td className="py-2 font-mono">{row.referencia_interna}</td>
                        <td className="py-2">{row.fecha_pago ?? '—'}</td>
                        <td className="py-2">{new Date(row.fecha_reporte).toLocaleString()}</td>
                        <td className="py-2 text-right">{row.monto} {row.moneda}</td>
                        <td className="py-2">
                          <Badge variant={row.estado === 'aprobado' ? 'default' : row.estado === 'rechazado' ? 'destructive' : 'secondary'}>
                            {row.estado}
                          </Badge>
                        </td>
                        <td className="py-2">{row.tiene_recibo ? 'Sí' : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
