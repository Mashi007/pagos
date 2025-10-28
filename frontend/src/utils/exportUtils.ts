/**
 * Utilidades para exportar tablas de amortización
 */

export interface Cuota {
  numero_cuota: number
  fecha_vencimiento: string
  monto_capital: number
  monto_interes: number
  monto_cuota: number
  saldo_capital_final: number
  estado: string
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
    // Importar dinámicamente xlsx
    const XLSXModule = await import('xlsx')
    const XLSX = XLSXModule as any
    
    // Crear datos para Excel
    const datos = cuotas.map(cuota => ({
      'Cuota': cuota.numero_cuota,
      'Fecha Vencimiento': cuota.fecha_vencimiento,
      'Capital': cuota.monto_capital,
      'Interés': cuota.monto_interes,
      'Total': cuota.monto_cuota,
      'Saldo Pendiente': cuota.saldo_capital_final,
      'Estado': cuota.estado,
    }))

    // Agregar resumen
    const totalCapital = cuotas.reduce((sum, c) => sum + c.monto_capital, 0)
    const totalInteres = cuotas.reduce((sum, c) => sum + c.monto_interes, 0)
    const totalGeneral = cuotas.reduce((sum, c) => sum + c.monto_cuota, 0)

    const resumen = [
      {},
      { 'Cuota': 'RESUMEN', 'Fecha Vencimiento': '', 'Capital': '', 'Interés': '', 'Total': '', 'Saldo Pendiente': '', 'Estado': '' },
      { 'Cuota': '', 'Fecha Vencimiento': '', 'Capital': totalCapital, 'Interés': totalInteres, 'Total': totalGeneral, 'Saldo Pendiente': '', 'Estado': '' },
    ]

    const todosLosDatos = [...datos, ...resumen]

    // Crear libro y hoja
    const ws = XLSX.utils.json_to_sheet(todosLosDatos)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'Tabla de Amortización')

    // Generar nombre del archivo
    const nombreArchivo = `Tabla_Amortizacion_${prestamo.cedula}_${prestamo.id}.xlsx`

    // Descargar
    XLSX.writeFile(wb, nombreArchivo)
  } catch (error) {
    console.error('Error al exportar a Excel:', error)
    alert('Error al exportar a Excel')
  }
}

/**
 * Exporta tabla de amortización a PDF (formato empresarial)
 */
export const exportarAPDF = (cuotas: Cuota[], prestamo: PrestamoInfo) => {
  // Importar dinámicamente jsPDF y jspdf-autotable
  Promise.all([import('jspdf'), import('jspdf-autotable')]).then((modules) => {
    const jsPDF = modules[0].default
    const autoTable = modules[1].default

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
    doc.text('INFORMACIÓN DEL PRÉSTAMO', 15, 55)

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
    
    // Preparar datos para la tabla
    const datosTabla = cuotas.map(cuota => [
      cuota.numero_cuota.toString(),
      cuota.fecha_vencimiento,
      `$${cuota.monto_capital.toFixed(2)}`,
      `$${cuota.monto_interes.toFixed(2)}`,
      `$${cuota.monto_cuota.toFixed(2)}`,
      `$${cuota.saldo_capital_final.toFixed(2)}`,
      cuota.estado
    ])

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
    doc.text('RESUMEN DE PRÉSTAMO', 15, resumenY + 7)

    const totalCapital = cuotas.reduce((sum, c) => sum + c.monto_capital, 0)
    const totalInteres = cuotas.reduce((sum, c) => sum + c.monto_interes, 0)
    const totalGeneral = cuotas.reduce((sum, c) => sum + c.monto_cuota, 0)

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
  }).catch(error => {
    console.error('Error al importar jsPDF:', error)
    alert('Error: Debes instalar las librerías. Ejecuta: npm install jspdf jspdf-autotable')
  })
}

