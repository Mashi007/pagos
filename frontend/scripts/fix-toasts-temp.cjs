const fs = require('fs');
const path = require('path');
const filePath = path.join(__dirname, '../src/hooks/useExcelUploadPagos.ts');
let content = fs.readFileSync(filePath, 'utf8');

// 1
content = content.replace(/addToast\('error', 'Hay errores en esta fila\. Corr[^']*'\)/g, "addToast('error', 'Hay errores en esta fila.')");
// 2 - Cedula sin tilde (match Cedula or Cédula)
content = content.replace(/La C[e\xE9]dula/g, 'La Cedula');
// 3
content = content.replace(/addToast\('error', 'Sin conexi[^']*'\)/g, "addToast('error', 'Sin conexion')");
// 4
content = content.replace(/addToast\('warning', 'No hay pagos v[^']*'\)/g, "addToast('warning', 'No hay pagos validos')");
// 5
content = content.replace(/env[i\xED]e/g, 'envie');
// 6 - template literals: match addToast('TYPE',  + any chars until )
content = content.replace(/addToast\('success', [^]*\)/g, function(m){ return m.includes('Ã') ? "addToast('success', " + String.fromCharCode(36) + "{ok} pago(s) guardado(s) correctamente.)" : m; });
content = content.replace(/addToast\('warning', [^]*\)/g, function(m){ return m.includes('Ã') ? "addToast('warning', " + String.fromCharCode(36) + "{ok} guardado(s), " + String.fromCharCode(36) + "{fail} con errores.)" : m; });
content = content.replace(/addToast\('error', [^]*\)/g, function(m){ return m.includes('Ã') ? "addToast('error', Error al guardar.)" : m; });

fs.writeFileSync(filePath, content, 'utf8');
console.log('Done');