const fs = require("fs");
const path = require("path");
const filePath = path.join(__dirname, "src", "components", "pagos", "CargaMasivaMenu.tsx");
let c = fs.readFileSync(filePath, "utf8");

// 1. Add useEffect to imports
c = c.replace(
  "import { useState } from 'react'",
  "import { useState, useEffect } from 'react'"
);

// 2. Add state for gmail status
c = c.replace(
  "const [loadingGmail, setLoadingGmail] = useState(false)\n\n  async function handleGenerarExcelDesdeGmail",
  `const [loadingGmail, setLoadingGmail] = useState(false)
  const [gmailStatus, setGmailStatus] = useState(null)

  useEffect(() => {
    if (!isOpen) return
    pagoService.getGmailStatus().then(setGmailStatus).catch(() => setGmailStatus(null))
  }, [isOpen])

  async function handleGenerarExcelDesdeGmail`
);

// 3. After success in handleGenerarExcelDesdeGmail, refresh status
c = c.replace(
  "await pagoService.downloadGmailExcel()\n      toast.success('Excel generado desde Gmail descargado.')",
  "await pagoService.downloadGmailExcel()\n      toast.success('Excel generado desde Gmail descargado.')\n      pagoService.getGmailStatus().then(setGmailStatus)"
);

// 4. Add status line before the buttons (after "Cargar desde archivo")
c = c.replace(
  "<p className=\"text-xs text-gray-500 px-2 py-1 mb-1\">Cargar desde archivo</p>\n          <div className=\"space-y-1\">",
  `<p className="text-xs text-gray-500 px-2 py-1 mb-1">Cargar desde archivo</p>
          {gmailStatus && (
            <p className="text-xs text-gray-600 px-2 py-1 mb-1 border-b border-gray-100">
              {gmailStatus.last_status === 'error' ? (
                <span className="text-amber-600">Ultima sync fallo</span>
              ) : gmailStatus.last_run ? (
                <>Ultima sync: {new Date(gmailStatus.last_run).toLocaleString('es-VE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })} – {gmailStatus.last_emails} correos, {gmailStatus.last_files} archivos</>
              ) : (
                <span className="text-gray-500">Sin sync aun</span>
              )}
            </p>
          )}
          <div className="space-y-1">`
);

fs.writeFileSync(filePath, c);
console.log("CargaMasivaMenu status: aplicado.");
