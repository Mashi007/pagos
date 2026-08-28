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

export default function AuditoriaEmailBitacoraPage() {
  const q = useQuery({
    queryKey: ['auditoria-email', 'bitacora'],
    queryFn: () => auditoriaEmailService.bitacora(80),
  })
  const items = q.data?.items || []
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Bitácora de escaneos</CardTitle>
      </CardHeader>
      <CardContent>
        {q.isLoading ? (
          <Loader2 className="h-5 w-5 animate-spin" />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Fuente</TableHead>
                  <TableHead>Aceptados</TableHead>
                  <TableHead>Lotes</TableHead>
                  <TableHead>Creado</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={6}
                      className="py-6 text-center text-muted-foreground"
                    >
                      Sin corridas.
                    </TableCell>
                  </TableRow>
                ) : (
                  items.map(s => (
                    <TableRow key={s.id}>
                      <TableCell>{s.id}</TableCell>
                      <TableCell>{s.status}</TableCell>
                      <TableCell>{s.source}</TableCell>
                      <TableCell>
                        {s.processedTotal}/{s.maxMessages}
                      </TableCell>
                      <TableCell>{s.lotsDone}</TableCell>
                      <TableCell className="whitespace-nowrap text-xs">
                        {s.createdAt
                          ? new Date(s.createdAt).toLocaleString('es-VE')
                          : '—'}
                      </TableCell>
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
