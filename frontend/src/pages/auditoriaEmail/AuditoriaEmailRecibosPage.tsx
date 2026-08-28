import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table'
import { auditoriaEmailService } from '../../services/auditoriaEmailService'

export default function AuditoriaEmailRecibosPage() {
  const q = useQuery({
    queryKey: ['auditoria-email', 'recibos'],
    queryFn: () => auditoriaEmailService.recibos(0, 100),
  })
  const items = q.data?.items || []
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          Recibos extraídos ({q.data?.total ?? 0})
        </CardTitle>
      </CardHeader>
      <CardContent>
        {q.isLoading ? (
          <Loader2 className="h-5 w-5 animate-spin" />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Archivo</TableHead>
                  <TableHead>Cédula</TableHead>
                  <TableHead>Monto</TableHead>
                  <TableHead>Ruta</TableHead>
                  <TableHead>OCR</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={5}
                      className="py-6 text-center text-muted-foreground"
                    >
                      Sin recibos.
                    </TableCell>
                  </TableRow>
                ) : (
                  items.map(r => (
                    <TableRow key={String(r.id)}>
                      <TableCell>{String(r.filename || '—')}</TableCell>
                      <TableCell>{String(r.cedula || '—')}</TableCell>
                      <TableCell>{String(r.monto ?? '—')}</TableCell>
                      <TableCell>{String(r.route || '—')}</TableCell>
                      <TableCell>{String(r.ocrStatus || '—')}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
