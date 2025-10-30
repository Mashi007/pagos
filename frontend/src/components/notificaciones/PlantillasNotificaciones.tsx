import { useEffect, useMemo, useRef, useState } from 'react'
import { notificacionService, NotificacionPlantilla } from '@/services/notificacionService'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card } from '@/components/ui/card'
import { Tabs } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { useSearchClientes } from '@/hooks/useClientes'
import { SearchableSelect } from '@/components/ui/searchable-select'

type EditorFocus = 'asunto' | 'encabezado' | 'cuerpo' | 'firma'

export function PlantillasNotificaciones() {
  const [plantillas, setPlantillas] = useState<NotificacionPlantilla[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<NotificacionPlantilla | null>(null)
  const [nombre, setNombre] = useState('')
  const [tipo, setTipo] = useState('')
  const [activa, setActiva] = useState(true)
  const [asunto, setAsunto] = useState('')
  const [encabezado, setEncabezado] = useState('')
  const [cuerpo, setCuerpo] = useState('')
  const [firma, setFirma] = useState('')
  const [variable, setVariable] = useState('')
  const [focus, setFocus] = useState<EditorFocus>('cuerpo')
  const [clienteIdPrueba, setClienteIdPrueba] = useState<number | ''>('')
  const [variablesPrueba, setVariablesPrueba] = useState<Record<string, any>>({})
  const asuntoRef = useRef<HTMLTextAreaElement | HTMLInputElement>(null)
  const encRef = useRef<HTMLTextAreaElement>(null)
  const cuerpoRef = useRef<HTMLTextAreaElement>(null)
  const firmaRef = useRef<HTMLTextAreaElement>(null)

  const cuerpoFinal = useMemo(() => {
    const parts = [encabezado, cuerpo, firma].filter(Boolean)
    return parts.join('\n\n')
  }, [encabezado, cuerpo, firma])

  const variablesSugeridas = [
    'nombre', 'monto', 'fecha_vencimiento', 'numero_cuota', 'credito_id', 'cedula', 'dias_atraso'
  ]

  const tiposSugeridos = [
    'PAGO_5_DIAS_ANTES', 'PAGO_3_DIAS_ANTES', 'PAGO_1_DIA_ANTES', 'PAGO_DIA_0', 'PAGO_1_DIA_ATRASADO', 'PAGO_3_DIAS_ATRASADO', 'PAGO_5_DIAS_ATRASADO'
  ]

  const cargar = async () => {
    setLoading(true)
    try {
      const data = await notificacionService.listarPlantillas(undefined, false)
      setPlantillas(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    cargar()
  }, [])

  const limpiar = () => {
    setSelected(null)
    setNombre('')
    setTipo('')
    setActiva(true)
    setAsunto('')
    setEncabezado('')
    setCuerpo('')
    setFirma('')
  }

  const seleccionar = (p: NotificacionPlantilla) => {
    setSelected(p)
    setNombre(p.nombre)
    setTipo(p.tipo)
    setActiva(Boolean(p.activa))
    setAsunto(p.asunto)
    setEncabezado('')
    setCuerpo(p.cuerpo)
    setFirma('')
  }

  const insertarVariable = () => {
    if (!variable) return
    const token = `{{${variable}}}`
    const insertInto = (el: HTMLTextAreaElement | HTMLInputElement | null, setter: (v: string) => void, current: string) => {
      if (!el) {
        setter(current + token)
        return
      }
      const start = (el as any).selectionStart ?? current.length
      const end = (el as any).selectionEnd ?? current.length
      const next = current.slice(0, start) + token + current.slice(end)
      setter(next)
      setTimeout(() => {
        try {
          (el as any).focus()
          ;(el as any).setSelectionRange(start + token.length, start + token.length)
        } catch {}
      }, 0)
    }

    if (focus === 'asunto') return insertarVariable(), insertInto(asuntoRef.current, setAsunto, asunto)
    if (focus === 'encabezado') return insertInto(encRef.current, setEncabezado, encabezado)
    if (focus === 'cuerpo') return insertInto(cuerpoRef.current, setCuerpo, cuerpo)
    if (focus === 'firma') return insertInto(firmaRef.current, setFirma, firma)
  }

  // Búsqueda clientes para prueba
  const [queryCliente, setQueryCliente] = useState('')
  const { data: resultadosClientes } = useSearchClientes(queryCliente)

  const aplicarFormato = (tag: 'b' | 'i' | 'u' | 'ul' | 'a') => {
    const wrap = (el: HTMLTextAreaElement | null, setter: (v: string) => void, current: string) => {
      if (!el) return
      const start = el.selectionStart ?? 0
      const end = el.selectionEnd ?? 0
      const selected = current.slice(start, end)
      let before = '', after = ''
      if (tag === 'a') {
        before = '<a href="https://">'
        after = '</a>'
      } else if (tag === 'ul') {
        const lines = selected || 'Elemento 1\nElemento 2'
        const wrapped = lines.split('\n').map(l => `<li>${l || 'Elemento'}</li>`).join('\n')
        const next = current.slice(0, start) + `<ul>\n${wrapped}\n</ul>` + current.slice(end)
        setter(next)
        return
      } else {
        before = `<${tag}>`
        after = `</${tag}>`
      }
      const next = current.slice(0, start) + before + (selected || 'texto') + after + current.slice(end)
      setter(next)
      setTimeout(() => {
        try { el.focus() } catch {}
      }, 0)
    }
    if (focus === 'encabezado') return wrap(encRef.current, setEncabezado, encabezado)
    if (focus === 'cuerpo') return wrap(cuerpoRef.current, setCuerpo, cuerpo)
    if (focus === 'firma') return wrap(firmaRef.current, setFirma, firma)
    if (focus === 'asunto') return // no aplicar html al asunto
  }

  const validarObligatorias = (): string | null => {
    // Reglas básicas por tipo
    const requeridasPorTipo: Record<string, string[]> = {
      'PAGO_5_DIAS_ANTES': ['nombre', 'monto', 'fecha_vencimiento'],
      'PAGO_3_DIAS_ANTES': ['nombre', 'monto', 'fecha_vencimiento'],
      'PAGO_1_DIA_ANTES': ['nombre', 'monto', 'fecha_vencimiento'],
      'PAGO_DIA_0': ['nombre', 'monto', 'fecha_vencimiento'],
      'PAGO_1_DIA_ATRASADO': ['nombre', 'monto', 'fecha_vencimiento', 'dias_atraso'],
      'PAGO_3_DIAS_ATRASADO': ['nombre', 'monto', 'fecha_vencimiento', 'dias_atraso'],
      'PAGO_5_DIAS_ATRASADO': ['nombre', 'monto', 'fecha_vencimiento', 'dias_atraso'],
    }
    const requeridas = requeridasPorTipo[tipo] || []
    const faltantes = requeridas.filter(v => !(`${asunto} ${cuerpoFinal}`).includes(`{{${v}}}`))
    if (faltantes.length) return `Faltan variables obligatorias: ${faltantes.join(', ')}`
    return null
  }

  const guardar = async () => {
    const error = validarObligatorias()
    if (error) {
      alert(error)
      return
    }

    const payload = {
      nombre,
      tipo,
      asunto,
      cuerpo: cuerpoFinal,
      activa,
    }

    if (selected?.id) {
      await notificacionService.actualizarPlantilla(selected.id, payload)
    } else {
      await notificacionService.crearPlantilla(payload)
    }
    await cargar()
    alert('Plantilla guardada')
  }

  const eliminar = async () => {
    if (!selected?.id) return
    if (!confirm('¿Eliminar plantilla?')) return
    await notificacionService.eliminarPlantilla(selected.id)
    limpiar()
    await cargar()
  }

  const exportar = async () => {
    if (!selected?.id) return
    const data = await notificacionService.exportarPlantilla(selected.id)
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `plantilla_${selected.nombre}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const enviarPrueba = async () => {
    if (!selected?.id) return alert('Selecciona o guarda la plantilla primero')
    if (!clienteIdPrueba) return alert('Indica un cliente de prueba')
    try {
      await notificacionService.enviarConPlantilla(selected.id, { cliente_id: Number(clienteIdPrueba), variables: variablesPrueba })
      alert('Prueba enviada')
    } catch (e) {
      alert('No se pudo enviar la prueba')
    }
  }

  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Plantillas</h2>
          <Button onClick={limpiar} variant="secondary">Nueva</Button>
        </div>
        <div className="border rounded-lg divide-y max-h-[70vh] overflow-auto">
          {loading && <div className="p-3 text-sm text-gray-500">Cargando...</div>}
          {!loading && plantillas.map(p => (
            <button key={p.id} onClick={() => seleccionar(p)} className={`w-full text-left p-3 hover:bg-gray-50 ${selected?.id===p.id?'bg-gray-50':''}`}>
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">{p.nombre}</div>
                  <div className="text-xs text-gray-500">{p.tipo}</div>
                </div>
                {p.activa ? <Badge variant="success">Activa</Badge> : <Badge variant="secondary">Inactiva</Badge>}
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="col-span-8 space-y-4">
        <Card className="p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm text-gray-600">Nombre</label>
              <Input value={nombre} onChange={e=>setNombre(e.target.value)} placeholder="Recordatorio de pago" />
            </div>
            <div>
              <label className="text-sm text-gray-600">Tipo (regla del programador)</label>
              <select value={tipo} onChange={e=>setTipo(e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
                <option value="">Seleccione...</option>
                {tiposSugeridos.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <input id="activa" type="checkbox" checked={activa} onChange={e=>setActiva(e.target.checked)} />
              <label htmlFor="activa" className="text-sm">Habilitar envío automático a las 3:00 AM</label>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="text-sm text-gray-600">Asunto</label>
              <Input ref={asuntoRef as any} value={asunto} onFocus={()=>setFocus('asunto')} onChange={e=>setAsunto(e.target.value)} placeholder="Asunto del correo" />
            </div>
            <div className="col-span-2">
              <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">Formato rápido (encabezado/cuerpo/firma):
                <Button size="sm" variant="ghost" onClick={()=>aplicarFormato('b')}>B</Button>
                <Button size="sm" variant="ghost" onClick={()=>aplicarFormato('i')}>I</Button>
                <Button size="sm" variant="ghost" onClick={()=>aplicarFormato('u')}>U</Button>
                <Button size="sm" variant="ghost" onClick={()=>aplicarFormato('ul')}>Lista</Button>
                <Button size="sm" variant="ghost" onClick={()=>aplicarFormato('a')}>Enlace</Button>
              </div>
            </div>
            <div>
              <label className="text-sm text-gray-600">Encabezado</label>
              <Textarea ref={encRef} value={encabezado} onFocus={()=>setFocus('encabezado')} onChange={e=>setEncabezado(e.target.value)} rows={4} placeholder="Encabezado" />
            </div>
            <div>
              <label className="text-sm text-gray-600">Firma</label>
              <Textarea ref={firmaRef} value={firma} onFocus={()=>setFocus('firma')} onChange={e=>setFirma(e.target.value)} rows={4} placeholder="Firma" />
            </div>
            <div className="col-span-2">
              <label className="text-sm text-gray-600">Cuerpo</label>
              <Textarea ref={cuerpoRef} value={cuerpo} onFocus={()=>setFocus('cuerpo')} onChange={e=>setCuerpo(e.target.value)} rows={10} placeholder="Contenido principal" />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Input value={variable} onChange={e=>setVariable(e.target.value)} placeholder="nombre, monto, fecha_vencimiento..." className="max-w-xs" />
            <Button onClick={insertarVariable}>Agrega</Button>
            <div className="text-xs text-gray-500">Sugeridas: {variablesSugeridas.map(v => `{{${v}}}`).join(', ')}</div>
          </div>

          <div className="flex gap-2">
            <Button onClick={guardar}>{selected ? 'Actualizar' : 'Guardar'}</Button>
            {selected && <Button variant="destructive" onClick={eliminar}>Eliminar</Button>}
            {selected && <Button variant="secondary" onClick={exportar}>Exportar</Button>}
          </div>
        </Card>

        <Card className="p-4 space-y-3">
          <h3 className="font-semibold">Vista previa</h3>
          <div className="border rounded p-3 bg-white">
            <div className="text-sm text-gray-600">Asunto:</div>
            <div className="font-medium mb-2">{asunto || '(sin asunto)'}</div>
            <hr />
            <pre className="whitespace-pre-wrap text-sm mt-2">{cuerpoFinal || '(sin contenido)'}</pre>
          </div>

          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="text-sm text-gray-600">Cliente de prueba</label>
              <SearchableSelect
                value={clienteIdPrueba ? String(clienteIdPrueba) : ''}
                onSearch={setQueryCliente}
                onChange={(val) => setClienteIdPrueba(val ? Number(val) : '')}
                options={(resultadosClientes || []).map((c: any) => ({
                  label: `${c.cedula} - ${c.nombres}`,
                  value: String(c.id ?? c.cliente_id ?? ''),
                }))}
                placeholder="Buscar por cédula o nombre..."
              />
            </div>
            <Button onClick={enviarPrueba}>Enviar prueba</Button>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default PlantillasNotificaciones


