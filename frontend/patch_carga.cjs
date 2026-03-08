const fs = require("fs");
const path = require("path");
const filePath = path.join(__dirname, "src", "components", "pagos", "CargaMasivaMenu.tsx");
let c = fs.readFileSync(filePath, "utf8");

// 1. Add status block after "Cargar desde archivo" if not present
const statusBlock = `          {gmailStatus && (
            <p className="text-xs text-gray-600 px-2 py-1 mb-1 border-b border-gray-100">
              {gmailStatus.last_status === 'error' ? (
                <span className="text-amber-600">Última sync falló</span>
              ) : gmailStatus.last_run ? (
                <>Última sync: {new Date(gmailStatus.last_run).toLocaleString('es-VE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })} – {gmailStatus.last_emails} correos, {gmailStatus.last_files} archivos</>
              ) : (
                <span className="text-gray-500">Sin sync aún</span>
              )}
            </p>
          )}
          `;
if (!c.includes("Última sync falló")) {
  c = c.replace(
    '<p className="text-xs text-gray-500 px-2 py-1 mb-1">Cargar desde archivo</p>\n          <div className="space-y-1">',
    '<p className="text-xs text-gray-500 px-2 py-1 mb-1">Cargar desde archivo</p>\n' + statusBlock + '<div className="space-y-1">'
  );
}

// 2. Add "puede tardar" toast at start of handleGenerarExcelDesdeGmail
if (!c.includes("Puede tardar 1-2 minutos")) {
  c = c.replace(
    "setLoadingGmail(true)\n    try {\n      await pagoService.runGmailNow()",
    "setLoadingGmail(true)\n    toast('Puede tardar 1-2 minutos según la cantidad de correos.', { duration: 3500, icon: '⏱️' })\n    try {\n      await pagoService.runGmailNow()"
  );
}

fs.writeFileSync(filePath, c);
console.log("CargaMasivaMenu: estado + puede tardar aplicados.");
