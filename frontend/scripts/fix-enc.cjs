const fs = require("fs");
const path = require("path");
const fp = path.join(__dirname, "../src/hooks/useExcelUploadPagos.ts");
let c = fs.readFileSync(fp, "utf8");

c = c.replace(/addToast\('error', 'Hay errores en esta fila\. Corr[^']*'\)/g, "addToast('error', 'Hay errores en esta fila.')");
c = c.replace(/La C[e\xE9]dula/g, "La Cedula");
c = c.replace(/addToast\('error', 'Sin conexi[^']*'\)/g, "addToast('error', 'Sin conexion')");
c = c.replace(/addToast\('warning', 'No hay pagos v[^']*'\)/g, "addToast('warning', 'No hay pagos validos')");
c = c.replace(/env[i\xED]e/g, "envie");

const d = String.fromCharCode(36);
c = c.replace(/addToast\('success', `(Ãƒ[^`]*)`\)/g, "addToast('success', `" + d + "{ok} pago(s) guardado(s) correctamente.`)");
c = c.replace(/addToast\('warning', `(Ãƒ[^`]*)`\)/g, "addToast('warning', `" + d + "{ok} guardado(s), " + d + "{fail} con errores.`)");
c = c.replace(/addToast\('error', `(Ãƒ[^`]*)`\)/g, "addToast('error', `Error al guardar.`)");

fs.writeFileSync(fp, c, "utf8");
console.log("Done");