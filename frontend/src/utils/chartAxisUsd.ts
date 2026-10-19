/** Etiquetas compactas para ejes Y de gráficos en USD (evita `$1200000K` con montos grandes). */
export function formatChartAxisUsd(v: number): string {
  if (!Number.isFinite(v)) return ''
  const abs = Math.abs(v)
  if (abs >= 1_000_000_000) {
    return `$${(v / 1_000_000_000).toFixed(abs >= 10_000_000_000 ? 0 : 1)}B`
  }
  if (abs >= 1_000_000) {
    return `$${(v / 1_000_000).toFixed(abs >= 10_000_000 ? 0 : 1)}M`
  }
  if (abs >= 10_000) {
    return `$${(v / 1_000).toFixed(0)}k`
  }
  if (abs >= 1_000) {
    return `$${(v / 1_000).toFixed(1)}k`
  }
  return `$${Math.round(v)}`
}
