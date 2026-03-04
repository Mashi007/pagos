/**
 * Generador de Recibo de Pago en PDF (media carta / A5)
 * jsPDF 4.x – RapiCredit C.A. – Caracas, Venezuela
 */

export interface ReciboPrestamoData {
  id: number
  cedula: string
  nombres: string
  numero_cuotas: number
  total_financiamiento: number
  modalidad_pago: string
}

export interface ReciboCuotaData {
  id: number
  numero_cuota: number
  fecha_vencimiento: string
  fecha_pago?: string | null
  monto_cuota: number
  monto_capital?: number
  monto_interes?: number
  saldo_capital_final: number
  total_pagado: number
  pago_monto_conciliado?: number
  pago_id?: number | null
  pago_conciliado?: boolean
  estado: string
  numero_documento?: string | null
}

async function cargarLogoBase64(url: string): Promise<string | null> {
  try {
    const res = await fetch(url)
    if (!res.ok) return null
    const blob = await res.blob()
    return new Promise((resolve) => {
      const reader = new FileReader()
      reader.onloadend = () => resolve(reader.result as string)
      reader.onerror = () => resolve(null)
      reader.readAsDataURL(blob)
    })
  } catch {
    return null
  }
}

function formatFechaVE(fechaStr: string | null | undefined): string {
  if (!fechaStr) return '—'
  try {
    const d = new Date(fechaStr + 'T12:00:00')
    return d.toLocaleDateString('es-VE', { day: '2-digit', month: '2-digit', year: 'numeric' })
  } catch {
    return fechaStr
  }
}

export async function generarReciboPagoPDF(
  prestamo: ReciboPrestamoData,
  cuota: ReciboCuotaData
): Promise<void> {
  // ── Importar jsPDF dinámicamente (igual que exportUtils.ts) ──
  const jsPDFModule = await import('jspdf')
  const { jsPDF } = jsPDFModule

  // Página A5 vertical (148 × 210 mm) ≈ media carta
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a5' })
  const W = doc.internal.pageSize.getWidth()   // 148
  const mL = 10   // margen izquierdo
  const mR = 10   // margen derecho
  const cW = W - mL - mR  // ancho contenido
  const GREEN: [number, number, number] = [34, 139, 60]
  const BLUE: [number, number, number]  = [37, 99, 235]
  const AMBER: [number, number, number] = [161, 97, 7]
  let y = 10

  // ── ENCABEZADO VERDE ──────────────────────────────────────────
  doc.setFillColor(...GREEN)
  doc.rect(0, 0, W, 30, 'F')

  // Logo
  const logoUrl = `${window.location.origin}/pagos/logos/rAPI.png`
  const logo = await cargarLogoBase64(logoUrl)
  if (logo) {
    doc.addImage(logo, 'PNG', mL, 5, 28, 11)
  } else {
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(13)
    doc.setTextColor(255, 255, 255)
    doc.text('RAPICREDIT', mL, 13)
  }

  // Título del recibo
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(13)
  doc.setTextColor(255, 255, 255)
  doc.text('RECIBO DE PAGO', W - mR, 11, { align: 'right' })

  // Número de recibo y fecha de impresión
  const ahora = new Date()
  const fechaImpresion = ahora.toLocaleDateString('es-VE', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  })
  const horaImpresion = ahora.toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' })
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(7)
  doc.text(
    `No. RC-${cuota.pago_id ?? cuota.id}-C${cuota.numero_cuota}`,
    W - mR, 19, { align: 'right' }
  )
  doc.text(
    `Caracas, ${fechaImpresion}  ${horaImpresion}`,
    W - mR, 24, { align: 'right' }
  )

  y = 35

  // ── SECCIÓN: DATOS DEL CLIENTE ────────────────────────────────
  doc.setFillColor(242, 252, 244)
  doc.roundedRect(mL, y, cW, 22, 2, 2, 'F')
  doc.setDrawColor(...GREEN)
  doc.setLineWidth(0.4)
  doc.roundedRect(mL, y, cW, 22, 2, 2, 'S')

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(7)
  doc.setTextColor(...GREEN)
  doc.text('DATOS DEL CLIENTE', mL + 3, y + 5)

  const rowH = 5.5
  doc.setFontSize(9)

  const clientRows: [string, string][] = [
    ['Cédula:', prestamo.cedula],
    ['Nombre:', prestamo.nombres],
  ]
  clientRows.forEach(([lbl, val], i) => {
    const ry = y + 10 + i * rowH
    doc.setFont('helvetica', 'normal')
    doc.setTextColor(90)
    doc.text(lbl, mL + 3, ry)
    doc.setFont('helvetica', 'bold')
    doc.setTextColor(20)
    doc.text(val, mL + 24, ry)
  })
  y += 26

  // ── SECCIÓN: DATOS DEL PRÉSTAMO ───────────────────────────────
  doc.setFillColor(239, 246, 255)
  doc.roundedRect(mL, y, cW, 14, 2, 2, 'F')
  doc.setDrawColor(...BLUE)
  doc.roundedRect(mL, y, cW, 14, 2, 2, 'S')

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(7)
  doc.setTextColor(...BLUE)
  doc.text('DATOS DEL PRÉSTAMO', mL + 3, y + 5)

  doc.setFontSize(9)
  doc.setFont('helvetica', 'normal')
  doc.setTextColor(90)
  doc.text('Préstamo No.:', mL + 3, y + 11)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(20)
  doc.text(String(prestamo.id), mL + 30, y + 11)

  doc.setFont('helvetica', 'normal')
  doc.setTextColor(90)
  doc.text('Cuota:', mL + 60, y + 11)
  doc.setFont('helvetica', 'bold')
  doc.setTextColor(20)
  doc.text(`${cuota.numero_cuota} de ${prestamo.numero_cuotas}`, mL + 73, y + 11)
  y += 18

  // ── SECCIÓN: DETALLE DEL PAGO ─────────────────────────────────
  const totalPagado = Math.max(
    Number(cuota.total_pagado) || 0,
    Number(cuota.pago_monto_conciliado) || 0
  )
  const montoCapital = Number(cuota.monto_capital) || 0
  const montoInteres = Number(cuota.monto_interes) || 0

  const detalleRows: [string, string][] = [
    ['Fecha de pago:', formatFechaVE(cuota.fecha_pago)],
    ['Fecha vencimiento:', formatFechaVE(cuota.fecha_vencimiento)],
    ...(cuota.numero_documento
      ? [['No. Documento:', cuota.numero_documento] as [string, string]]
      : []),
    ['Capital pagado:', `$${montoCapital.toFixed(2)}`],
    ['Interés pagado:', `$${montoInteres.toFixed(2)}`],
    ['Saldo pendiente:', `$${Number(cuota.saldo_capital_final || 0).toFixed(2)}`],
  ]

  const detalleH = 12 + detalleRows.length * rowH + 12
  doc.setFillColor(255, 252, 240)
  doc.roundedRect(mL, y, cW, detalleH, 2, 2, 'F')
  doc.setDrawColor(...AMBER)
  doc.roundedRect(mL, y, cW, detalleH, 2, 2, 'S')

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(7)
  doc.setTextColor(...AMBER)
  doc.text('DETALLE DEL PAGO', mL + 3, y + 5)

  let dy = y + 11
  detalleRows.forEach(([lbl, val]) => {
    doc.setFontSize(8.5)
    doc.setFont('helvetica', 'normal')
    doc.setTextColor(90)
    doc.text(lbl, mL + 3, dy)
    doc.setFont('helvetica', 'bold')
    doc.setTextColor(20)
    doc.text(val, mL + cW - 3, dy, { align: 'right' })
    dy += rowH
  })

  // Línea separadora total
  doc.setDrawColor(...AMBER)
  doc.setLineWidth(0.5)
  doc.line(mL + 3, dy, mL + cW - 3, dy)
  dy += 4

  // TOTAL PAGADO grande
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(12)
  doc.setTextColor(40)
  doc.text('TOTAL PAGADO:', mL + 3, dy)
  doc.setTextColor(...GREEN)
  doc.text(`$${totalPagado.toFixed(2)}`, mL + cW - 3, dy, { align: 'right' })
  y += detalleH + 5

  // ── ESTADO ────────────────────────────────────────────────────
  const esConciliado = cuota.pago_conciliado === true
  const estadoColor: [number, number, number] = esConciliado ? GREEN : BLUE
  const estadoLabel = esConciliado ? '✓  CONCILIADO' : '✓  PAGADO'
  doc.setFillColor(...estadoColor)
  doc.roundedRect(mL, y, cW, 9, 2, 2, 'F')
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(10)
  doc.setTextColor(255)
  doc.text(estadoLabel, W / 2, y + 6.2, { align: 'center' })
  y += 13

  // ── ZONA FIRMA + SELLO ────────────────────────────────────────
  // Línea de firma (izquierda)
  const firmaX = mL
  const firmaY = y + 20
  doc.setDrawColor(150)
  doc.setLineWidth(0.4)
  doc.line(firmaX, firmaY, firmaX + 52, firmaY)
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(7.5)
  doc.setTextColor(60)
  doc.text('RAPICREDIT C.A.', firmaX + 26, firmaY + 4, { align: 'center' })
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(6.5)
  doc.setTextColor(100)
  doc.text('Autorizado por', firmaX + 26, firmaY + 8.5, { align: 'center' })

  // Sello circular (derecha)
  const cx = W - mR - 22
  const cy = y + 18
  const r = 18

  doc.setDrawColor(...GREEN)
  doc.setLineWidth(1.2)
  doc.circle(cx, cy, r)
  doc.setLineWidth(0.4)
  doc.circle(cx, cy, r - 2.5)

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(6.5)
  doc.setTextColor(...GREEN)
  doc.text('RAPICREDIT', cx, cy - 7, { align: 'center' })

  doc.setFont('helvetica', 'normal')
  doc.setFontSize(5)
  doc.text('SISTEMA DE GESTIÓN', cx, cy - 2, { align: 'center' })
  doc.text('DE CRÉDITOS', cx, cy + 2.5, { align: 'center' })

  doc.setDrawColor(...GREEN)
  doc.setLineWidth(0.3)
  doc.line(cx - 8, cy + 5.5, cx + 8, cy + 5.5)

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(5)
  doc.text('CARACAS, VEN.', cx, cy + 9, { align: 'center' })

  y += 45

  // ── PIE DE PÁGINA ─────────────────────────────────────────────
  doc.setFont('helvetica', 'italic')
  doc.setFontSize(6.5)
  doc.setTextColor(140)
  doc.text(
    'Este documento es un comprobante válido del pago de la cuota indicada.',
    W / 2, y, { align: 'center' }
  )
  doc.text(
    `Impreso el ${fechaImpresion} en Caracas, Venezuela.`,
    W / 2, y + 4.5, { align: 'center' }
  )

  // ── GUARDAR ───────────────────────────────────────────────────
  const filename = `Recibo_C${String(cuota.numero_cuota).padStart(2, '0')}_${prestamo.cedula}_Prestamo${prestamo.id}.pdf`
  doc.save(filename)
}
