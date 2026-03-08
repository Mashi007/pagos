/**
 * Corrige mensajes corruptos (mojibake) y caracteres especiales en useExcelUploadPagos.ts
 * Ejecutar: node scripts/fix-encoding-toasts.js
 */
const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, '../src/hooks/useExcelUploadPagos.ts');
let content = fs.readFileSync(filePath, 'utf8');

// Patron mojibake tipico (UTF-8 mal interpretado)
const MOJI = /ÃƒÆ'Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ'Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢[^'`\)]*/g;

// 1. Hay errores en esta fila. (eliminar basura despues de "Corr")
content = content.replace(
  /addToast\('error', 'Hay errores en esta fila\. Corr[^']*'\)/g,
  "addToast('error', 'Hay errores en esta fila.')"
);

// 2. La Cedula (sin tilde)
content = content.replace(/La Cédula/g, 'La Cedula');

// 3. Sin conexion (todas las instancias con mojibake)
content = content.replace(
  /addToast\('error', 'Sin conexi[^']*'\)/g,
  "addToast('error', 'Sin conexion')"
);

// 4. No hay pagos validos
content = content.replace(
  /addToast\('warning', 'No hay pagos v[^']*'\)/g,
  "addToast('warning', 'No hay pagos validos')"
);

// 5. enviar sin tilde
content = content.replace(/envíe/g, 'envie');

// 6. Template literals corruptos - reemplazar por mensajes ASCII
content = content.replace(
  /addToast\('success', `[^`]*Ãƒ[^`]*`\)/g,
  "addToast('success', `${ok} pago(s) guardado(s) correctamente.`)"
);
content = content.replace(
  /addToast\('warning', `[^`]*Ãƒ[^`]*`\)/g,
  "addToast('warning', `${ok} guardado(s), ${fail} con errores.`)"
);
content = content.replace(
  /addToast\('error', `[^`]*Ãƒ[^`]*`\)/g,
  "addToast('error', `Error al guardar.`)"
);

// 7. Mensajes con variables - reemplazo mas amplio para los que tienen ${ok} ${fail}
content = content.replace(
  /if \(ok > 0 && fail === 0\) addToast\('success',[^;]+;/g,
  "if (ok > 0 && fail === 0) addToast('success', `${ok} pago(s) guardado(s) correctamente.`);"
);
content = content.replace(
  /else if \(ok > 0 && fail > 0\) addToast\('warning',[^;]+;/g,
  "else if (ok > 0 && fail > 0) addToast('warning', `${ok} guardado(s), ${fail} con errores.`);"
);
content = content.replace(
  /else if \(fail > 0\) addToast\('error',[^;]+;/g,
  "else if (fail > 0) addToast('error', `Error al guardar.`);"
);

fs.writeFileSync(filePath, content, 'utf8');
console.log('Fix encoding: done');
