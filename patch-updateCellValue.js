const fs = require('fs');
const path = 'c:\\Users\\PORTATIL\\Documents\\BIBLIOTECA\\GitHub\\pagos\\frontend\\src\\hooks\\useExcelUploadPagos.ts';
let content = fs.readFileSync(path, 'utf8');

const oldBlock = `        // REGLA ESTRICTA: ningun documento duplicado; misma normalizacion que en validacion; no anadir vacios
        const documentosEnArchivo = new Set<string>()
        prev.forEach((other) => {
          if (other._rowIndex !== row._rowIndex) {
            const docNorm = (normalizarNumeroDocumento(other.numero_documento) || '').trim()
            if (docNorm) documentosEnArchivo.add(docNorm)
          }
        })
        if (field === 'numero_documento') {
          const validation = validatePagoField('numero_documento', (updated as any).numero_documento, { documentosEnArchivo })
          updated._validation = { ...r._validation, numero_documento: validation }
          updated._hasErrors = !validation.isValid
        } else {
          updated._validation = { ...r._validation, [field]: { isValid: true } }
          updated._hasErrors = !updated._validation.numero_documento?.isValid
        }
        return updated`;

const newBlock = `        // Documentos en otras filas (para detectar duplicados en archivo)
        const documentosEnArchivo = new Set<string>()
        prev.forEach((other) => {
          if (other._rowIndex !== row._rowIndex) {
            const docNorm = (normalizarNumeroDocumento(other.numero_documento) || '').trim()
            if (docNorm) documentosEnArchivo.add(docNorm)
          }
        })

        // Revalidar al editar: cedula, fecha, monto, documento
        let vCedula = updated._validation?.cedula ?? r._validation?.cedula
        let vFecha = updated._validation?.fecha_pago ?? r._validation?.fecha_pago
        let vMonto = updated._validation?.monto_pagado ?? r._validation?.monto_pagado
        let vDoc = updated._validation?.numero_documento ?? r._validation?.numero_documento

        if (field === 'cedula') {
          const allCedulas = new Set<string>()
          prev.forEach((other) => {
            const ced = (other._rowIndex === row._rowIndex
              ? String(value ?? '').trim().replace(/-/g, '').toUpperCase()
              : (other.cedula || '').trim().replace(/-/g, '').toUpperCase())
            if (ced && /^[VEJZ]\\d{6,11}$/.test(ced)) allCedulas.add(ced)
          })
          const cedulasInvalidas = new Set([...allCedulas].filter((c) => !cedulasExistentesBDRef.current.has(c)))
          vCedula = validatePagoField('cedula', (updated as any).cedula, { cedulasInvalidas })
        } else if (field === 'fecha_pago') {
          vFecha = validatePagoField('fecha_pago', (updated as any).fecha_pago)
        } else if (field === 'monto_pagado') {
          vMonto = validatePagoField('monto_pagado', (updated as any).monto_pagado)
        } else if (field === 'numero_documento') {
          vDoc = validatePagoField('numero_documento', (updated as any).numero_documento, {
            documentosEnArchivo,
            documentosDuplicadosBD: documentosDuplicadosBDRef.current,
          })
        }

        updated._validation = { ...r._validation, cedula: vCedula, fecha_pago: vFecha, monto_pagado: vMonto, numero_documento: vDoc }
        updated._hasErrors = !vCedula?.isValid || !vFecha?.isValid || !vMonto?.isValid || !vDoc?.isValid
        return updated`;

// Try with encoding variations
const patterns = [
  oldBlock,
  oldBlock.replace(/ningun/g, 'ning\u00fcn').replace(/normalizacion/g, 'normalizaci\u00f3n').replace(/validacion/g, 'validaci\u00f3n').replace(/anadir/g, 'a\u00f1adir').replace(/vacios/g, 'vac\u00edos'),
  content.match(/\/\/ REGLA ESTRICTA[\s\S]*?return updated\n\s+}\))[\s\S]*?}, \[\]\)/)?.[0]?.split('return updated')[0] + 'return updated'
];

let found = false;
for (const p of patterns) {
  if (content.includes(p.split('\n')[0])) {
    content = content.replace(p, newBlock);
    found = true;
    break;
  }
}

if (!found) {
  // Use regex to match
  const regex = /(\s+\/\/ REGLA ESTRICTA:[^\n]+\n\s+const documentosEnArchivo[\s\S]*?)if \(field === 'numero_documento'\) \{[\s\S]*?updated\._hasErrors = !validation\.isValid\s+\} else \{[\s\S]*?updated\._hasErrors = !updated\._validation\.numero_documento\?\.isValid\s+\}\s+return updated/;
  content = content.replace(regex, newBlock);
}

fs.writeFileSync(path, content);
console.log('Patch applied');
