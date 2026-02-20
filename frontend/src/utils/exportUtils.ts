/**
 * Utilidades para exportar tablas de amortización
 */

import { toast } from 'sonner'

/** Mensaje cuando falla la carga dinámica del módulo (chunk 404 tras deploy) */
const MSJ_RECARGA = 'Recarga la página (F5) e intenta de nuevo. Si el problema persiste, contacta al administrador.'

export interface Cuota {
  numero_cuota: number
  fecha_vencimiento: string
  monto_capital?: number  // Opcional - puede no existir
  monto_interes?: number  // Opcional - puede no existir
  monto_cuota: number
  saldo_capital_inicial?: number
  saldo_capital_final: number
  estado: string
  total_pagado?: number
}

export interface PrestamoInfo {
  id: number
  cedula: string
  nombres: string
  total_financiamiento: number
  numero_cuotas: number
  modalidad_pago: string
  fecha_requerimiento: string
}

/**
 * Exporta tabla de amortización a Excel
 */
export const exportarAExcel = async (cuotas: Cuota[], prestamo: PrestamoInfo) => {
  try {
    // Importar dinámicamente exceljs
    const { createAndDownloadExcel } = await import('../types/exceljs')

    // Crear datos para Excel
    const datos = cuotas.map(cuota => {
      // Calcular monto_capital y monto_interes si no existen
      const saldoInicial = typeof cuota.saldo_capital_inicial === 'number' ? cuota.saldo_capital_inicial : 0
      const saldoFinal = typeof cuota.saldo_capital_final === 'number' ? cuota.saldo_capital_final : 0
      const montoCuota = typeof cuota.monto_cuota === 'number' ? cuota.monto_cuota : 0
      
      const montoCapital = typeof cuota.monto_capital === 'number' && !isNaN(cuota.monto_capital)
        ? cuota.monto_capital
        : Math.max(0, saldoInicial - saldoFinal)
      
      const montoInteres = typeof cuota.monto_interes === 'number' && !isNaN(cuota.monto_interes)
        ? cuota.monto_interes
        : Math.max(0, montoCuota - montoCapital)

      return {
        'Cuota': cuota.numero_cuota,
        'Fecha Vencimiento': cuota.fecha_vencimiento,
        'Capital': montoCapital,
        'Interés': montoInteres,
        'Total': montoCuota,
        'Saldo Pendiente': saldoFinal,
        'Estado': cuota.estado,
      }
    })

    // Agregar resumen
    const totalCapital = datos.reduce((sum, d) => sum + (d.Capital as number), 0)
    const totalInteres = datos.reduce((sum, d) => sum + (d.Interés as number), 0)
    const totalGeneral = datos.reduce((sum, d) => sum + (d.Total as number), 0)

    const resumen = [
      { 'Cuota': 'RESUMEN', 'Fecha Vencimiento': '', 'Capital': '', 'Interés': '', 'Total': '', 'Saldo Pendiente': '', 'Estado': '' },
      { 'Cuota': '', 'Fecha Vencimiento': '', 'Capital': totalCapital, 'Interés': totalInteres, 'Total': totalGeneral, 'Saldo Pendiente': '', 'Estado': '' },
    ]

    const todosLosDatos = [...datos, ...resumen]

    // Generar nombre del archivo
    const nombreArchivo = `Tabla_Amortizacion_${prestamo.cedula}_${prestamo.id}.xlsx`

    // Descargar usando exceljs
    await createAndDownloadExcel(todosLosDatos, 'Tabla de Amortización', nombreArchivo)
  } catch (error) {
    console.error('Error al exportar a Excel:', error)
    const isChunkError = error instanceof Error && (
      error.message.includes('dynamically imported') ||
      error.message.includes('Failed to fetch') ||
      error.message.includes('Loading chunk')
    )
    toast.error(isChunkError ? MSJ_RECARGA : 'Error al exportar a Excel')
  }
}

/**
 * Exporta tabla de amortización a PDF (formato empresarial)
 */
export const exportarAPDF = async (cuotas: Cuota[], prestamo: PrestamoInfo) => {
  try {
    // Importar dinámicamente jsPDF y jspdf-autotable
    const [jsPDFModule, autoTableModule] = await Promise.all([
      import('jspdf'),
      import('jspdf-autotable')
    ])

    // jspdf 4.x usa named export
    const { jsPDF } = jsPDFModule
    // jspdf-autotable 5.x usa default export
    const autoTable = autoTableModule.default

    // Crear nuevo documento PDF
    const doc = new jsPDF()

    // Colores empresariales
    const primaryColor = [59, 130, 246] as [number, number, number] // Blue-500
    const secondaryColor = [107, 114, 128] as [number, number, number] // Gray-500

    // ENCABEZADO EMPRESARIAL
    // Rectángulo de fondo
    doc.setFillColor(primaryColor[0], primaryColor[1], primaryColor[2])
    doc.rect(0, 0, 210, 40, 'F')

    // Logo/Título
    doc.setTextColor(255, 255, 255)
    doc.setFontSize(24)
    doc.setFont('helvetica', 'bold')
    doc.text('RapiCredit', 20, 20)
    doc.setFontSize(12)
    doc.setFont('helvetica', 'normal')
    doc.text('Sistema de Gestión de Préstamos', 20, 28)

    // Fecha del reporte
    doc.setFontSize(10)
    const fechaReporte = new Date().toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
    doc.text(fechaReporte, 160, 20, { align: 'right' })

    // INFORMACIÓN DEL CLIENTE
    doc.setFillColor(245, 245, 250)
    doc.rect(10, 45, 190, 40, 'F')

    doc.setFontSize(14)
    doc.setFont('helvetica', 'bold')
    doc.setTextColor(0, 0, 0)
    doc.text('INFORMACIÓN DEL PRÃ‰STAMO', 15, 55)

    doc.setFontSize(10)
    doc.setFont('helvetica', 'normal')
    doc.text(`Cliente: ${prestamo.nombres}`, 15, 65)
    doc.text(`Cédula: ${prestamo.cedula}`, 15, 70)
    doc.text(`Préstamo #${prestamo.id}`, 110, 65)
    doc.text(`Modalidad: ${prestamo.modalidad_pago}`, 110, 70)
    doc.text(`Total: $${prestamo.total_financiamiento.toFixed(2)}`, 110, 75)

    // TABLA DE AMORTIZACIÓN
    doc.setFontSize(12)
    doc.setFont('helvetica', 'bold')
    doc.text('TABLA DE AMORTIZACIÓN', 15, 92)

    // Preparar datos para la tabla y calcular totales
    let totalCapital = 0
    let totalInteres = 0
    let totalGeneral = 0
    
    const datosTabla = cuotas.map(cuota => {
      // Calcular monto_capital y monto_interes si no existen
      const saldoInicial = typeof cuota.saldo_capital_inicial === 'number' ? cuota.saldo_capital_inicial : 0
      const saldoFinal = typeof cuota.saldo_capital_final === 'number' ? cuota.saldo_capital_final : 0
      const montoCuota = typeof cuota.monto_cuota === 'number' ? cuota.monto_cuota : 0
      
      const montoCapital = typeof cuota.monto_capital === 'number' && !isNaN(cuota.monto_capital)
        ? cuota.monto_capital
        : Math.max(0, saldoInicial - saldoFinal)
      
      const montoInteres = typeof cuota.monto_interes === 'number' && !isNaN(cuota.monto_interes)
        ? cuota.monto_interes
        : Math.max(0, montoCuota - montoCapital)

      // Acumular totales
      totalCapital += montoCapital
      totalInteres += montoInteres
      totalGeneral += montoCuota

      return [
        cuota.numero_cuota.toString(),
        cuota.fecha_vencimiento,
        `$${montoCapital.toFixed(2)}`,
        `$${montoInteres.toFixed(2)}`,
        `$${montoCuota.toFixed(2)}`,
        `$${saldoFinal.toFixed(2)}`,
        cuota.estado
      ]
    })

    // Crear tabla con autoTable
    autoTable(doc, {
      startY: 95,
      head: [['Cuota', 'Fecha Vencimiento', 'Capital', 'Interés', 'Total', 'Saldo Pendiente', 'Estado']],
      body: datosTabla,
      theme: 'striped',
      headStyles: {
        fillColor: [primaryColor[0], primaryColor[1], primaryColor[2]],
        textColor: 255,
        fontStyle: 'bold'
      },
      alternateRowStyles: {
        fillColor: [245, 247, 250]
      },
      styles: {
        cellPadding: 3,
        fontSize: 8
      },
      columnStyles: {
        0: { cellWidth: 20, halign: 'center' },
        1: { cellWidth: 35 },
        2: { cellWidth: 25, halign: 'right' },
        3: { cellWidth: 25, halign: 'right' },
        4: { cellWidth: 25, halign: 'right' },
        5: { cellWidth: 35, halign: 'right' },
        6: { cellWidth: 30, halign: 'center' }
      }
    })

    // RESUMEN
    const finalY = (doc as any).lastAutoTable?.finalY || 150
    const resumenY = finalY + 10

    doc.setFillColor(primaryColor[0], primaryColor[1], primaryColor[2])
    doc.rect(10, resumenY, 190, 20, 'F')

    doc.setFontSize(11)
    doc.setFont('helvetica', 'bold')
    doc.setTextColor(255, 255, 255)
    doc.text('RESUMEN DE PRÃ‰STAMO', 15, resumenY + 7)

    // Los totales ya fueron calculados durante el mapeo de datosTabla

    doc.setFontSize(10)
    doc.setFont('helvetica', 'normal')
    doc.text(`Total Capital: $${totalCapital.toFixed(2)}`, 15, resumenY + 14)
    doc.text(`Total Intereses: $${totalInteres.toFixed(2)}`, 70, resumenY + 14)
    doc.text(`Monto Total: $${totalGeneral.toFixed(2)}`, 125, resumenY + 14)
    doc.text(`Cuotas: ${prestamo.numero_cuotas}`, 160, resumenY + 14)

    // FOOTER
    const pageCount = doc.getNumberOfPages()
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i)
      doc.setFontSize(8)
      doc.setTextColor(secondaryColor[0], secondaryColor[1], secondaryColor[2])
      doc.text(
        `RapiCredit - Sistema de Préstamos - Página ${i} de ${pageCount}`,
        105,
        290,
        { align: 'center' }
      )
      doc.text(
        `Documento generado el ${fechaReporte}`,
        105,
        293,
        { align: 'center' }
      )
    }

    // Generar nombre del archivo
    const nombreArchivo = `Tabla_Amortizacion_${prestamo.cedula}_${prestamo.id}.pdf`

    // Descargar
    doc.save(nombreArchivo)
  } catch (error) {
    console.error('Error al exportar a PDF:', error)
    const isChunkError = error instanceof Error && (
      error.message.includes('dynamically imported') ||
      error.message.includes('Failed to fetch') ||
      error.message.includes('Loading chunk')
    )
    toast.error(isChunkError ? MSJ_RECARGA : 'Error al exportar a PDF')
  }
}

