# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("frontend/src/components/prestamos/CrearPrestamoForm.tsx")
s = p.read_text(encoding="utf-8")

marker = """function fechaInputYmd(v: unknown): string {
  if (v == null || v === '') return ''

  const s = String(v)

  return s.length >= 10 ? s.slice(0, 10) : s
}

interface CrearPrestamoFormProps {"""

insert = """function fechaInputYmd(v: unknown): string {
  if (v == null || v === '') return ''

  const s = String(v)

  return s.length >= 10 ? s.slice(0, 10) : s
}

/** Texto de modelo guardado en BD/API (modelo_vehiculo o alias modelo). */
function modeloTextoDesdePrestamo(p?: Prestamo): string {
  if (!p) return ''
  const mv =
    p.modelo_vehiculo != null && String(p.modelo_vehiculo).trim() !== ''
      ? String(p.modelo_vehiculo).trim()
      : ''
  if (mv) return mv
  const m = (p as { modelo?: string | null }).modelo
  return m != null && String(m).trim() !== '' ? String(m).trim() : ''
}

interface CrearPrestamoFormProps {"""

if "function modeloTextoDesdePrestamo" not in s:
    assert marker in s, "marker1"
    s = s.replace(marker, insert, 1)

old_mi = """  const modeloInicial =
    prestamo?.modelo_vehiculo != null &&
    String(prestamo.modelo_vehiculo).trim() !== ''
      ? String(prestamo.modelo_vehiculo).trim()
      : ''

  const [formData, setFormData] = useState<Partial<PrestamoForm>>({"""

new_mi = """  const modeloInicial = modeloTextoDesdePrestamo(prestamo)

  const [formData, setFormData] = useState<Partial<PrestamoForm>>({"""

if "modeloTextoDesdePrestamo(prestamo)" not in s:
    assert old_mi in s, "modeloInicial"
    s = s.replace(old_mi, new_mi, 1)

old_va = """  const [valorActivo, setValorActivo] = useState<number>(
    prestamo?.valor_activo || 0
  )"""

new_va = """  const [valorActivo, setValorActivo] = useState<number>(() => {
    if (!prestamo) return 0
    const va = prestamo.valor_activo
    if (va == null) return 0
    const n = Number(va)
    return Number.isFinite(n) ? n : 0
  })"""

if "useState<number>(() => {" not in s or "const va = prestamo.valor_activo" not in s:
    assert old_va in s, "valorActivo"
    s = s.replace(old_va, new_va, 1)

needle = """  const { data: modelosVehiculos = [], error: errorModelos } =
    useModelosVehiculosActivos()

  const { user } = useSimpleAuth()"""

add_memo = """  const { data: modelosVehiculos = [], error: errorModelos } =
    useModelosVehiculosActivos()

  type ModeloCat = { id: number; modelo: string; precio?: number | null }

  const modelosParaSelect = useMemo((): ModeloCat[] => {
    const base = (modelosVehiculos || []) as ModeloCat[]
    const guardado = (formData.modelo_vehiculo || '').trim()
    if (
      guardado &&
      !base.some(m => String(m.modelo).trim() === guardado)
    ) {
      return [{ id: -1, modelo: guardado, precio: null }, ...base]
    }
    return base
  }, [modelosVehiculos, formData.modelo_vehiculo])

  const { user } = useSimpleAuth()"""

if "modelosParaSelect" not in s:
    assert needle in s, "modelos needle"
    s = s.replace(needle, add_memo, 1)

old_map = """                    <SelectContent>
                      {modelosVehiculos.map(modelo => (
                        <SelectItem key={modelo.id} value={modelo.modelo}>
                          {modelo.modelo}
                        </SelectItem>
                      ))}
                    </SelectContent>"""

new_map = """                    <SelectContent>
                      {modelosParaSelect.map(modelo => (
                        <SelectItem
                          key={
                            modelo.id === -1
                              ? `guardado-${modelo.modelo}`
                              : modelo.id
                          }
                          value={modelo.modelo}
                        >
                          {modelo.modelo}
                          {modelo.id === -1 ? ' (guardado)' : ''}
                        </SelectItem>
                      ))}
                    </SelectContent>"""

if "modelosParaSelect.map" not in s:
    assert old_map in s, "select map"
    s = s.replace(old_map, new_map, 1)

old_fd = """                    {prestamo?.estado === 'DESISTIMIENTO' &&
                    prestamo?.fecha_desistimiento ? (
                      <p className="mt-2 text-xs text-slate-600">
                        Fecha de desistimiento:{' '}
                        {fechaInputYmd(prestamo.fecha_desistimiento)}
                      </p>
                    ) : null}"""

new_fd = """                    {prestamo?.fecha_desistimiento ? (
                      <p className="mt-2 text-xs text-slate-600">
                        Fecha de desistimiento registrada:{' '}
                        {fechaInputYmd(prestamo.fecha_desistimiento)}
                      </p>
                    ) : formData.estado === 'DESISTIMIENTO' ? (
                      <p className="mt-2 text-xs text-amber-700">
                        Al guardar se registrara la fecha de desistimiento en la base de datos.
                      </p>
                    ) : null}"""

if "Fecha de desistimiento registrada" not in s:
    assert old_fd in s, "fecha desist block"
    s = s.replace(old_fd, new_fd, 1)

anchor = """  const [showConfirmCreate, setShowConfirmCreate] = useState(false)

  const [showRechazarDialog, setShowRechazarDialog] = useState(false)"""

hydrate = """  const [showConfirmCreate, setShowConfirmCreate] = useState(false)

  useEffect(() => {
    if (!prestamo?.id) return
    const mv = modeloTextoDesdePrestamo(prestamo)
    setFormData({
      cedula: prestamo.cedula || '',
      total_financiamiento: Number(prestamo.total_financiamiento) || 0,
      modalidad_pago: prestamo.modalidad_pago || 'MENSUAL',
      fecha_requerimiento: fechaInputYmd(prestamo.fecha_requerimiento),
      fecha_aprobacion: prestamo.fecha_aprobacion
        ? fechaInputYmd(prestamo.fecha_aprobacion)
        : undefined,
      fecha_base_calculo: prestamo.fecha_base_calculo
        ? fechaInputYmd(prestamo.fecha_base_calculo)
        : undefined,
      tasa_interes:
        prestamo.tasa_interes != null ? Number(prestamo.tasa_interes) : undefined,
      producto: prestamo.producto || '',
      concesionario: prestamo.concesionario || '',
      analista: prestamo.analista || '',
      analista_id:
        prestamo.analista_id != null ? Number(prestamo.analista_id) : undefined,
      modelo_vehiculo: mv,
      estado: prestamo.estado,
      observaciones: prestamo.observaciones || '',
    })
    const va = prestamo.valor_activo
    setValorActivo(
      va != null && String(va).trim() !== '' and not Number.isNaN(Number(va))
        ? Number(va)
        : 0
    )
"""

# Oops I used Python 'and' - fix in file manually
hydrate = hydrate.replace(" and not ", " && !")

hydrate_cont = """    const n = prestamo.numero_cuotas
    setNumeroCuotas(n && Number(n) > 0 ? Number(n) : 12)
    const cpRaw = prestamo.cuota_periodo
    const cp = cpRaw != null && Number(cpRaw) > 0 ? Number(cpRaw) : 0
    if (cp > 0) {
      setCuotaPeriodo(cp)
    } else {
      const tf = Number(prestamo.total_financiamiento || 0)
      const nn = n && Number(n) > 0 ? Number(n) : 12
      setCuotaPeriodo(nn > 0 && tf > 0 ? Math.round((tf / nn) * 100) / 100 : 0)
    }
  }, [prestamo?.id])

  const [showRechazarDialog, setShowRechazarDialog] = useState(false)"""

full_hydrate = hydrate + hydrate_cont

if "if (!prestamo?.id) return" not in s or "modeloTextoDesdePrestamo(prestamo)" not in s.split("showConfirmCreate")[0]:
    pass

if "if (!prestamo?.id) return" not in s:
    assert anchor in s, "anchor hydrate"
    s = s.replace(anchor, full_hydrate, 1)

p.write_text(s, encoding="utf-8")
print("OK")
