# -*- coding: utf-8 -*-
"""Fix modelo Select: Radix value undefined not ''; fallback from prestamo; normalized catalog match."""
from pathlib import Path

p = Path("frontend/src/components/prestamos/CrearPrestamoForm.tsx")
t = p.read_text(encoding="utf-8")

old_helper = """/** Texto de modelo guardado en BD/API (modelo_vehiculo o alias modelo). */
function modeloTextoDesdePrestamo(p?: Prestamo): string {
  if (!p) return ''
  const mv =
    p.modelo_vehiculo != null && String(p.modelo_vehiculo).trim() !== ''
      ? String(p.modelo_vehiculo).trim()
      : ''
  if (mv) return mv
  const m = (p as { modelo?: string | null }).modelo
  return m != null && String(m).trim() !== '' ? String(m).trim() : ''
}"""

new_helper = """/** Colapsa espacios para comparar modelo guardado vs catalogo. */
function normalizarTextoModelo(s: string): string {
  return String(s || '')
    .trim()
    .replace(/\\s+/g, ' ')
}

/** Texto de modelo guardado en BD/API (modelo_vehiculo, alias modelo o producto). */
function modeloTextoDesdePrestamo(p?: Prestamo): string {
  if (!p) return ''
  const mv =
    p.modelo_vehiculo != null && String(p.modelo_vehiculo).trim() !== ''
      ? String(p.modelo_vehiculo).trim()
      : ''
  if (mv) return mv
  const m = (p as { modelo?: string | null }).modelo
  if (m != null && String(m).trim() !== '') return String(m).trim()
  const prod = (p.producto || '').trim()
  if (prod) return prod
  return ''
}"""

if new_helper.split("normalizarTextoModelo")[0] not in t:
    assert old_helper in t, "helper block missing"
    t = t.replace(old_helper, new_helper, 1)

old_memo = """  type ModeloCat = { id: number; modelo: string; precio?: number | null }

  const modelosParaSelect = useMemo((): ModeloCat[] => {
    const base = (modelosVehiculos || []) as ModeloCat[]
    const guardado = (formData.modelo_vehiculo || '').trim()
    if (guardado && !base.some(m => String(m.modelo).trim() === guardado)) {
      return [{ id: -1, modelo: guardado, precio: null }, ...base]
    }
    return base
  }, [modelosVehiculos, formData.modelo_vehiculo])

  const { user } = useSimpleAuth()"""

new_memo = """  type ModeloCat = { id: number; modelo: string; precio?: number | null }

  /** Texto efectivo del modelo en edicion: formulario o lo que trae el prestamo (API). */
  const textoModeloGuardado = useMemo(() => {
    const fromForm = (formData.modelo_vehiculo || '').trim()
    if (fromForm) return fromForm
    return modeloTextoDesdePrestamo(prestamo).trim()
  }, [formData.modelo_vehiculo, prestamo])

  const { modelosParaSelect, valorSelectModelo } = useMemo(() => {
    const base = (modelosVehiculos || []) as ModeloCat[]
    const g = textoModeloGuardado
    if (!g) {
      return { modelosParaSelect: base, valorSelectModelo: undefined as string | undefined }
    }
    const gn = normalizarTextoModelo(g)
    const matchCat = base.find(
      m => normalizarTextoModelo(String(m.modelo)) === gn
    )
    if (matchCat) {
      return {
        modelosParaSelect: base,
        valorSelectModelo: matchCat.modelo,
      }
    }
    return {
      modelosParaSelect: [{ id: -1, modelo: g, precio: null }, ...base],
      valorSelectModelo: g,
    }
  }, [modelosVehiculos, textoModeloGuardado])

  const { user } = useSimpleAuth()"""

if "valorSelectModelo" not in t:
    assert old_memo in t, "modelosParaSelect memo missing"
    t = t.replace(old_memo, new_memo, 1)

old_select = """                  <Select
                    value={formData.modelo_vehiculo ?? ''}
                    onValueChange={value => {
                      setFormData({
                        ...formData,

                        modelo_vehiculo: value,
                      })

                      const modeloSel = modelosVehiculos.find(
                        (m: any) => m.modelo === value
                      )"""

new_select = """                  <Select
                    value={valorSelectModelo}
                    onValueChange={value => {
                      setFormData({
                        ...formData,

                        modelo_vehiculo: value,
                      })

                      const modeloSel =
                        modelosVehiculos.find((m: any) => m.modelo === value) ||
                        modelosParaSelect.find((m: any) => m.modelo === value)"""

if "valorSelectModelo" in t and "value={valorSelectModelo}" not in t:
    assert old_select in t, "Select modelo block missing"
    t = t.replace(old_select, new_select, 1)

# Alinear formData.modelo_vehiculo al texto canonico del catalogo cuando cargue el catalogo (evita value vs item mismatch)
align_snippet = """
  useEffect(() => {
    if (!prestamo?.id || !textoModeloGuardado) return
    const base = (modelosVehiculos || []) as ModeloCat[]
    if (!base.length) return
    const gn = normalizarTextoModelo(textoModeloGuardado)
    const matchCat = base.find(
      m => normalizarTextoModelo(String(m.modelo)) === gn
    )
    if (!matchCat) return
    setFormData(prev => {
      const cur = (prev.modelo_vehiculo || '').trim()
      if (normalizarTextoModelo(cur) === gn && cur === matchCat.modelo) {
        return prev
      }
      if (cur !== '' && normalizarTextoModelo(cur) !== gn) {
        return prev
      }
      return { ...prev, modelo_vehiculo: matchCat.modelo }
    })
  }, [prestamo?.id, modelosVehiculos, textoModeloGuardado])
"""

needle = "  const { user } = useSimpleAuth()\n\n  // Errores de carga"
if align_snippet.strip() not in t and needle in t:
    t = t.replace(needle, "  const { user } = useSimpleAuth()" + align_snippet + "\n  // Errores de carga", 1)

p.write_text(t, encoding="utf-8")
print("OK")
