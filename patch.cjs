const fs = require("fs");
const path = require("path");
const filePath = path.join("c:", "Users", "PORTATIL", "Documents", "BIBLIOTECA", "GitHub", "pagos", "frontend", "src", "components", "pagos", "CargaMasivaMenu.tsx");
let c = fs.readFileSync(filePath, "utf8");
c = c.replace(
  "import { Upload, FileSpreadsheet, CheckCircle, ChevronDown } from 'lucide-react'",
  "import { Upload, FileSpreadsheet, CheckCircle, ChevronDown, Mail } from 'lucide-react'"
);
c = c.replace(
  "import { ConciliacionExcelUploader } from './ConciliacionExcelUploader'",
  "import { ConciliacionExcelUploader } from './ConciliacionExcelUploader'\nimport toast from 'react-hot-toast'\nimport { pagoService } from '../../services/pagoService'"
);
const stateAndHandler = "\n  const [loadingGmail, setLoadingGmail] = useState(false)\n\n  async function handleGenerarExcelDesdeGmail() {\n    setIsOpen(false)\n    setLoadingGmail(true)\n    try {\n      await pagoService.runGmailNow()\n      await pagoService.downloadGmailExcel()\n      toast.success('Excel generado desde Gmail descargado.')\n    } catch (e) {\n      const msg = e?.message || 'Error al generar Excel desde Gmail.'\n      toast.error(msg)\n    } finally {\n      setLoadingGmail(false)\n    }\n  }\n";
c = c.replace(/const \[isOpen, setIsOpen\] = useState\(false\)\r?\n\r?\n  return/, "const [isOpen, setIsOpen] = useState(false)" + stateAndHandler + "\n  return");
const gmailButton = "\n            <button\n              className=\"w-full flex items-center px-3 py-2.5 text-sm rounded-md hover:bg-gray-100 transition-colors disabled:opacity-50\"\n              onClick={handleGenerarExcelDesdeGmail}\n              disabled={loadingGmail}\n            >\n              <Mail className=\"w-4 h-4 mr-2\" />\n              {loadingGmail ? 'Generando...' : 'Generar Excel desde Gmail'}\n            </button>";
c = c.replace(/(<CheckCircle className=\"w-4 h-4 mr-2\" \/>\s*\n\s*Conciliaci[^<]+<\/button>)\s*(<\/div>)/s, "$1" + gmailButton + "\n          $2");
fs.writeFileSync(filePath, c);
console.log("Done");
