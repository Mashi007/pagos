import { useState, useEffect, useCallback } from 'react'





import { campanasService, type CampanaCrm, type ListCampanasResponse } from '../services/campanasService'





import { Button } from '../components/ui/button'





import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog'





import { Mail, Play, Eye, Plus, RefreshCw, FileText, Pause, Trash2, Calendar } from 'lucide-react'





import toast from 'react-hot-toast'











function fileToBase64(file: File): Promise<string> {





  return new Promise((resolve, reject) => {





    const reader = new FileReader()





    reader.onload = () => {





      const result = reader.result as string





      const base64 = result.indexOf(',') >= 0 ? result.split(',')[1] : result





      resolve(base64 || '')





    }





    reader.onerror = () => reject(reader.error)





    reader.readAsDataURL(file)





  })





}











export function CampanasPage() {





  const [list, setList] = useState<ListCampanasResponse | null>(null)





  const [loading, setLoading] = useState(true)





  const [page, setPage] = useState(1)





  const [estado, setEstado] = useState<string>('')





  const [showCreate, setShowCreate] = useState(false)





  const [previewTotal, setPreviewTotal] = useState<number>(0)





  const [createLoading, setCreateLoading] = useState(false)





  const [form, setForm] = useState({





    nombre: '',





    asunto: '',





    cuerpoTexto: '',





    cuerpoHtml: '',





    modoHtml: false,





    cc: '',





    adjunto: null as File | null,





    destinatariosClienteIds: '',





  })





  const [programarCampana, setProgramarCampana] = useState<CampanaCrm | null>(null)





  const [programarForm, setProgramarForm] = useState({ cada_dias: 0, cada_horas: 0 })





  const [programarLoading, setProgramarLoading] = useState(false)





  const [seleccionadosPreview, setSeleccionadosPreview] = useState<{





    total: number





    muestra: { email: string; cliente_id: number | null; nombres: string | null }[]





  } | null>(null)











  const load = async () => {





    setLoading(true)





    try {





      const res = await campanasService.list({ page, per_page: 20, estado: estado || undefined })





      setList(res)





    } catch (e: unknown) {





      toast.error((e as Error)?.message || 'Error al cargar campañas')





      setList({ items: [], paginacion: { page: 1, per_page: 20, total: 0, pages: 0 } })





    } finally {





      setLoading(false)





    }





  }











  useEffect(() => {





    load()





  }, [page, estado])











  const loadPreview = useCallback(async () => {





    try {





      const { total } = await campanasService.previewDestinatarios(1)





      setPreviewTotal(total)





    } catch {





      setPreviewTotal(0)





    }





  }, [])











  useEffect(() => {





    if (showCreate) {





      loadPreview()





      setForm({ nombre: '', asunto: '', cuerpoTexto: '', cuerpoHtml: '', modoHtml: false, cc: '', adjunto: null, destinatariosClienteIds: '' })





      setSeleccionadosPreview(null)





    }





  }, [showCreate, loadPreview])











  useEffect(() => {





    const ids = (form.destinatariosClienteIds || '').trim()





    if (!ids) {





      setSeleccionadosPreview(null)





      return





    }





    const t = setTimeout(async () => {





      try {





        const res = await campanasService.previewDestinatarios(500, ids)





        setSeleccionadosPreview({ total: res.total, muestra: res.muestra })





      } catch {





        setSeleccionadosPreview({ total: 0, muestra: [] })





      }





    }, 400)





    return () => clearTimeout(t)





  }, [form.destinatariosClienteIds])











  const handleCreateSubmit = async () => {





    const nombre = (form.nombre || '').trim()





    const asunto = (form.asunto || '').trim()





    if (!nombre) {





      toast.error('Escribe un nombre para la campaña.')





      return





    }





    if (!asunto) {





      toast.error('Escribe el asunto del correo.')





      return





    }





    setCreateLoading(true)





    try {





      const cuerpoTexto = form.modoHtml ? '' : (form.cuerpoTexto || '').trim()





      const cuerpoHtml = form.modoHtml ? (form.cuerpoHtml || form.cuerpoTexto || '').trim() || null : null





      const ccList = (form.cc || '')





        .split(/[\n,;]+/)





        .map((e) => e.trim())





        .filter((e) => e && e.includes('@'))





      let adjunto_nombre: string | null = null





      let adjunto_base64: string | null = null





      if (form.adjunto) {





        adjunto_nombre = form.adjunto.name





        adjunto_base64 = await fileToBase64(form.adjunto)





      }





      const idsStr = (form.destinatariosClienteIds || '').trim()





      const destinatarios_cliente_ids =





        idsStr === ''





          ? undefined





          : idsStr





              .split(/[\s,;]+/)





              .map((s) => parseInt(s, 10))





              .filter((n) => !Number.isNaN(n) && n > 0)





      await campanasService.create({





        nombre,





        asunto,





        cuerpo_texto: cuerpoTexto || (cuerpoHtml ? 'Contenido en HTML.' : ''),





        cuerpo_html: cuerpoHtml,





        cc_emails: ccList.length ? ccList : null,





        adjunto_nombre: adjunto_nombre || undefined,





        adjunto_base64: adjunto_base64 || undefined,





        destinatarios_cliente_ids: destinatarios_cliente_ids?.length ? destinatarios_cliente_ids : undefined,





      })





      toast.success('Campaña creada en borrador.')





      setShowCreate(false)





      load()





    } catch (e: unknown) {





      toast.error((e as Error)?.message || 'Error al crear la campaña.')





    } finally {





      setCreateLoading(false)





    }





  }











  const handleIniciarEnvio = async (c: CampanaCrm) => {





    if (c.estado !== 'borrador') return





    try {





      await campanasService.iniciarEnvio(c.id)





      toast.success('Envío iniciado en segundo plano.')





      load()





    } catch (e: unknown) {





      toast.error((e as Error)?.message || 'Error al iniciar envío')





    }





  }











  const handleParar = async (c: CampanaCrm) => {





    if (c.estado !== 'enviando') return





    try {





      await campanasService.parar(c.id)





      toast.success('Envío detenido.')





      load()





    } catch (e: unknown) {





      toast.error((e as Error)?.message || 'Error al parar')





    }





  }











  const handleEliminar = async (c: CampanaCrm) => {





    if (c.estado !== 'borrador' && c.estado !== 'cancelada') return





    if (!window.confirm(`¿Eliminar la campaña «${c.nombre}»?`)) return





    try {





      await campanasService.eliminar(c.id)





      toast.success('Campaña eliminada.')





      load()





    } catch (e: unknown) {





      toast.error((e as Error)?.message || 'Error al eliminar')





    }





  }











  const handleProgramarSubmit = async () => {





    if (!programarCampana) return





    const dias = programarForm.cada_dias || 0





    const horas = programarForm.cada_horas || 0





    if (!dias && !horas) {





      toast.error('Indica cada cuántos días o cada cuántas horas.')





      return





    }





    setProgramarLoading(true)





    try {





      await campanasService.programar(programarCampana.id, {





        cada_dias: dias || undefined,





        cada_horas: horas || undefined,





      })





      toast.success('Campaña programada. Se enviará en el intervalo indicado.')





      setProgramarCampana(null)





      load()





    } catch (e: unknown) {





      toast.error((e as Error)?.message || 'Error al programar')





    } finally {





      setProgramarLoading(false)





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





          Campañas CRM





        </h1>





        <div className="flex items-center gap-2">





          <Button variant="outline" size="sm" onClick={load} disabled={loading}>





            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />





            Actualizar





          </Button>





          <Button size="sm" onClick={() => setShowCreate(true)}>





            





              <Plus className="h-4 w-4 mr-1" />





            Nueva campaña





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





          <option value="programada">Programada</option>





          <option value="enviando">Enviando</option>





          <option value="completada">Completada</option>





          <option value="cancelada">Cancelada</option>





        </select>





      </div>











      <Dialog open={showCreate} onOpenChange={setShowCreate}>





        <DialogContent className="max-w-2xl">





          <DialogHeader>





            <DialogTitle>Nueva campaña (correo masivo)</DialogTitle>





            <p className="text-sm text-slate-600 mt-1">





              De: correo predeterminado del sistema.





            </p>





          </DialogHeader>





          <div className="space-y-4">





            <div>





              <label className="block text-sm font-medium text-slate-700 mb-1">Nombre de la campaña</label>





              <input





                type="text"





                value={form.nombre}





                onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))}





                placeholder="Ej. Promo marzo 2025"





                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"





              />





            </div>





            <div>





              <span className="text-slate-500 text-sm">De:</span>





              <span className="ml-2 text-slate-700 text-sm">Correo del sistema (Configuración &gt; Email)</span>





            </div>





            <div>





              <label className="block text-sm font-medium text-slate-700 mb-1">





                Para (destinatarios)





              </label>





              <input





                type="text"





                value={form.destinatariosClienteIds}





                onChange={(e) => setForm((f) => ({ ...f, destinatariosClienteIds: e.target.value }))}





                placeholder="Vacío = todos. O escribe IDs de cliente separados por coma (ej. 123 o 123, 456)"





                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"





              />





              <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50/80 p-3">





                <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">





                  Destinatarios





                </div>





                {form.destinatariosClienteIds.trim() === '' ? (





                  <p className="text-sm text-slate-600">





                    Todos los correos de tabla Clientes ({previewTotal} contactos)





                  </p>





                ) : seleccionadosPreview ? (





                  <>





                    <p className="text-sm text-slate-600 mb-2">





                      {seleccionadosPreview.total} contacto(s) seleccionado(s):





                    </p>





                    <ul className="max-h-40 overflow-y-auto space-y-1 text-sm text-slate-700">





                      {seleccionadosPreview.muestra.length === 0 ? (





                        <li className="text-amber-700">Ningún contacto con email válido para los IDs indicados.</li>





                      ) : (





                        seleccionadosPreview.muestra.map((d, i) => (





                          <li key={d.cliente_id ? i} className="flex items-center gap-2">





                            <span className="font-medium text-slate-800">{d.email}</span>





                            {d.nombres && <span className="text-slate-500">- {d.nombres}</span>}





                          </li>





                        ))





                      )}





                    </ul>





                  </>





                ) : (





                  <p className="text-sm text-slate-500">Cargando contactos seleccionados…</p>





                )}





              </div>





            </div>





            <div>





              <label className="block text-sm font-medium text-slate-700 mb-1">CC (copia, opcional)</label>





              <textarea





                value={form.cc}





                onChange={(e) => setForm((f) => ({ ...f, cc: e.target.value }))}





                placeholder="correo1@ejemplo.com, correo2@ejemplo.com"





                rows={2}





                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"





              />





            </div>





            <div>





              <label className="block text-sm font-medium text-slate-700 mb-1">Asunto</label>





              <input





                type="text"





                value={form.asunto}





                onChange={(e) => setForm((f) => ({ ...f, asunto: e.target.value }))}





                placeholder="Asunto del correo"





                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"





              />





            </div>





            <div>





              <div className="flex items-center gap-2 mb-1">





                <label className="block text-sm font-medium text-slate-700">Cuerpo del correo</label>





                <label className="flex items-center gap-1 text-sm text-slate-600">





                  <input





                    type="checkbox"





                    checked={form.modoHtml}





                    onChange={(e) => setForm((f) => ({ ...f, modoHtml: e.target.checked }))}





                  />





                  Usar HTML





                </label>





              </div>





              <textarea





                value={form.modoHtml ? form.cuerpoHtml : form.cuerpoTexto}





                onChange={(e) =>





                  setForm((f) =>





                    f.modoHtml ? { ...f, cuerpoHtml: e.target.value } : { ...f, cuerpoTexto: e.target.value }





                  )





                }





                placeholder={form.modoHtml ? 'Escribe HTML aquí...' : 'Texto del mensaje (o activa HTML para formato)'}





                rows={8}





                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm font-mono"





              />





            </div>





            <div>





              <label className="block text-sm font-medium text-slate-700 mb-1">Adjunto (un solo archivo, opcional)</label>





              <div className="flex items-center gap-2">





                <input





                  type="file"





                  accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"





                  onChange={(e) => setForm((f) => ({ ...f, adjunto: e.target.files?.[0] ?? null }))}





                  className="text-sm text-slate-600 file:mr-2 file:rounded file:border-0 file:bg-blue-50 file:px-3 file:py-1 file:text-blue-700"





                />





                {form.adjunto && (





                  <span className="text-sm text-slate-600 flex items-center gap-1">





                    <FileText className="h-4 w-4" />





                    {form.adjunto.name}





                  </span>





                )}





              </div>





            </div>





          </div>





          <DialogFooter>





            <Button variant="outline" onClick={() => setShowCreate(false)} disabled={createLoading}>





              Cancelar





            </Button>





            <Button onClick={handleCreateSubmit} disabled={createLoading}>





              {createLoading ? 'Creando…' : 'Crear campaña (borrador)'}





            </Button>





          </DialogFooter>





        </DialogContent>





      </Dialog>











      <Dialog open={!!programarCampana} onOpenChange={(open) => !open && setProgramarCampana(null)}>





        <DialogContent className="max-w-md">





          <DialogHeader>





            <DialogTitle>Programar envíos recurrentes</DialogTitle>





            <p className="text-sm text-slate-600 mt-1">





              {programarCampana?.nombre}. Indica cada cuántos días y/o horas se enviará la campaña.





            </p>





          </DialogHeader>





          <div className="space-y-4">





            <div>





              <label className="block text-sm font-medium text-slate-700 mb-1">Cada cuántos días (0 = no usar)</label>





              <input





                type="number"





                min={0}





                max={365}





                value={programarForm.cada_dias || ''}





                onChange={(e) => setProgramarForm((f) => ({ ...f, cada_dias: parseInt(e.target.value, 10) || 0 }))}





                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"





              />





            </div>





            <div>





              <label className="block text-sm font-medium text-slate-700 mb-1">Cada cuántas horas (0 = no usar)</label>





              <input





                type="number"





                min={0}





                max={8760}





                value={programarForm.cada_horas || ''}





                onChange={(e) => setProgramarForm((f) => ({ ...f, cada_horas: parseInt(e.target.value, 10) || 0 }))}





                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"





              />





            </div>





          </div>





          <DialogFooter>





            <Button variant="outline" onClick={() => setProgramarCampana(null)} disabled={programarLoading}>





              Cancelar





            </Button>





            <Button onClick={handleProgramarSubmit} disabled={programarLoading || (!programarForm.cada_dias && !programarForm.cada_horas)}>





              {programarLoading ? 'Programando…' : 'Programar'}





            </Button>





          </DialogFooter>





        </DialogContent>





      </Dialog>











      {loading ? (





        <div className="flex justify-center py-12">





          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />





        </div>





      ) : list && list.items.length === 0 ? (





        <div className="rounded-lg border border-slate-200 bg-slate-50 p-8 text-center text-slate-600">





          No hay campañas. Crea una desde «Nueva campaña».





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





                        c.estado === 'programada' ? 'bg-violet-100 text-violet-800' :





                        c.estado === 'completada' ? 'bg-green-100 text-green-800' :





                        c.estado === 'cancelada' ? 'bg-red-100 text-red-800' : 'bg-slate-100 text-slate-700'





                      }`}>





                        {c.estado}





                      </span>





                      {c.estado === 'programada' && (c.programado_cada_dias || c.programado_cada_horas) && (





                        <div className="text-xs text-slate-500 mt-0.5">





                          {[c.programado_cada_dias && `cada ${c.programado_cada_dias} día(s)`, c.programado_cada_horas && `cada ${c.programado_cada_horas} h`].filter(Boolean).join(' · ')}





                        </div>





                      )}





                    </td>





                    <td className="px-4 py-3 text-right text-slate-600">{c.total_destinatarios}</td>





                    <td className="px-4 py-3 text-right text-slate-600">{c.enviados} / {c.fallidos}</td>





                    <td className="px-4 py-3 text-right">





                      <div className="flex flex-wrap items-center justify-end gap-1">





                        {c.cuerpo_html && (





                          <Button variant="ghost" size="sm" onClick={() => openPreview(c.id)} title="Vista previa HTML">





                            <Eye className="h-4 w-4" />





                          </Button>





                        )}





                        {c.estado === 'enviando' && (





                          <Button variant="outline" size="sm" onClick={() => handleParar(c)} title="Parar envío">





                            <Pause className="h-4 w-4" /> Parar





                          </Button>





                        )}





                        {(c.estado === 'borrador' || c.estado === 'cancelada') && (





                          <Button variant="outline" size="sm" onClick={() => handleEliminar(c)} title="Eliminar campaña" className="text-red-600 hover:text-red-700">





                            <Trash2 className="h-4 w-4" /> Eliminar





                          </Button>





                        )}





                        {c.estado === 'borrador' && c.total_destinatarios > 0 && (





                          <>





                            <Button size="sm" onClick={() => handleIniciarEnvio(c)} title="Enviar ahora (una vez)">





                              <Play className="h-4 w-4" /> Play





                            </Button>





                            <Button variant="outline" size="sm" onClick={() => { setProgramarCampana(c); setProgramarForm({ cada_dias: 0, cada_horas: 0 }) }} title="Programar envíos recurrentes">





                              <Calendar className="h-4 w-4" /> Programar





                            </Button>





                          </>





                        )}





                      </div>





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





                Página {list.paginacion.page} de {list.paginacion.pages}





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





