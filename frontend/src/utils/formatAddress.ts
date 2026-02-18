// Formateo de dirección (soporta JSON o texto plano)
interface DireccionJson {
  callePrincipal?: string | null
  calleTransversal?: string | null
  descripcion?: string | null
  parroquia?: string | null
  municipio?: string | null
  ciudad?: string | null
  estado?: string | null
}

export function formatAddress(direccion: string | null | undefined): string {
  if (!direccion || direccion.trim() === '') return '—'
  try {
    const trimmed = direccion.trim()
    if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || trimmed.startsWith('[')) {
      const parsed = JSON.parse(trimmed) as DireccionJson
      const parts: string[] = []
      if (parsed.callePrincipal) parts.push(parsed.callePrincipal)
      if (parsed.calleTransversal) parts.push(`y ${parsed.calleTransversal}`)
      if (parsed.descripcion) parts.push(parsed.descripcion)
      if (parsed.parroquia) parts.push(parsed.parroquia)
      if (parsed.municipio) parts.push(parsed.municipio)
      if (parsed.ciudad) parts.push(parsed.ciudad)
      if (parsed.estado) parts.push(parsed.estado)
      return parts.length > 0 ? parts.join(', ') : direccion
    }
    return direccion
  } catch {
    return direccion
  }
}
