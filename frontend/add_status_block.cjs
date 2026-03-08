const fs = require("fs");
const path = require("path");
const filePath = path.join(__dirname, "src", "components", "pagos", "CargaMasivaMenu.tsx");
let c = fs.readFileSync(filePath, "utf8");

if (c.includes("gmailStatus.last_status")) {
  console.log("Status block already present");
  process.exit(0);
}

const insert = `
          {gmailStatus && (
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

const search = '<div className="space-y-1">';
const idx = c.indexOf(search);
if (idx === -1) {
  console.log("Target not found");
  process.exit(1);
}
c = c.slice(0, idx) + insert + c.slice(idx);
fs.writeFileSync(filePath, c);
console.log("Status block added.");
