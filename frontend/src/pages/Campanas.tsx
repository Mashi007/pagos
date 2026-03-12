import { useState, useEffect } from 'react'
import { campanasService, type CampanaCrm, type ListCampanasResponse } from '../services/campanasService'
import { Button } from '../components/ui/button'
import { Mail, SendHorizontal, Eye, Plus, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'

export function CampanasPage() {
  const [list, setList] = useState<ListCampanasResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [estado, setEstado] = useState<string>('')
  const [showCreate, setShowCreate] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const res = await campanasService.list({ page, per_page: 20, estado: estado || undefined })
      setList(res)
    } catch (e: unknown) {
      toast.error((e as Error)?.message || 'Error al cargar campaÃ±as')
      setList({ items: [], paginacion: { page: 1, per_page: 20, total: 0, pages: 0 } })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [page, estado])

  const handleIniciarEnvio = async (c: CampanaCrm) => {
    if (c.estado !== 'borrador') return
    try {
      await campanasService.iniciarEnvio(c.id)
      toast.success('EnvÃ­o iniciado en segundo plano.')
      load()
    } catch (e: unknown) {
      toast.error((e as Error)?.message || 'Error al iniciar envÃ­o')
    }
  }

  const openPreview = async (id: number) => {
    try {
      const html = await campanasService.getPreviewHtml(id)
      const w = window.open('', '_blank')
      if (w) {
        w.document.write(html)
        w.document.close()
      }
    } catch (e: unknown) {
      toast.error((e as Error)?.message || 'Error al cargar vista previa')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-2xl font-semibold text-slate-800 flex items-center gap-2">
          <Mail className="h-7 w-7 text-blue-600" />
          CampaÃ±as CRM
        </h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            
              <Plus className="h-4 w-4 mr-1" />
            Nueva campa�a
          </Button>
        </div>
      </div>

      <div className="flex gap-2 flex-wrap">
        <select
          value={estado}
          onChange={(e) => { setEstado(e.target.value); setPage(1) }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Todos los estados</option>
          <option value="borrador">Borrador</option>
          <option value="enviando">Enviando</option>
          <option value="completada">Completada</option>
          <option value="cancelada">Cancelada</option>
        </select>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
        </div>
      ) : list && list.items.length === 0 ? (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-8 text-center text-slate-600">
          No hay campaÃ±as. Crea una desde Â«Nueva campaÃ±aÂ».
        </div>
      ) : list ? (
        <>
          <div className="rounded-lg border border-slate-200 overflow-hidden bg-white">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-600 uppercase">Nombre</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-600 uppercase">Estado</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-600 uppercase">Destinatarios</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-600 uppercase">Enviados / Fallidos</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-600 uppercase">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {list.items.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <span className="font-medium text-slate-800">{c.nombre}</span>
                      <div className="text-xs text-slate-500">{c.asunto}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                        c.estado === 'borrador' ? 'bg-amber-100 text-amber-800' :
                        c.estado === 'enviando' ? 'bg-blue-100 text-blue-800' :
                        c.estado === 'completada' ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-700'
                      }`}>
                        {c.estado}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-slate-600">{c.total_destinatarios}</td>
                    <td className="px-4 py-3 text-right text-slate-600">{c.enviados} / {c.fallidos}</td>
                    <td className="px-4 py-3 text-right">
                      {c.cuerpo_html && (
                        <Button variant="ghost" size="sm" className="mr-1" onClick={() => openPreview(c.id)}>
                          <Eye className="h-4 w-4" /> Vista previa HTML
                      </Button>
                      )}
                      {c.estado === 'borrador' && c.total_destinatarios > 0 && (
                        <Button size="sm" onClick={() => handleIniciarEnvio(c)}>
                          <SendHorizontal className="h-4 w-4 mr-1" /> Iniciar envÃ­o
                      </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {list.paginacion.pages > 1 && (
            <div className="flex justify-center gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Anterior
            </Button>
              <span className="flex items-center px-3 text-sm text-slate-600">
                PÃ¡gina {list.paginacion.page} de {list.paginacion.pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= list.paginacion.pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Siguiente
            </Button>
            </div>
          )}
        </>
      ) : null}
    </div>
  )
}

export default CampanasPage
