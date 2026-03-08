const fs = require('fs');
const path = require('path');
const filePath = path.join(__dirname, 'src/components/pagos/CargaMasivaMenu.tsx');
let c = fs.readFileSync(filePath, 'utf8');

// 1. Add Mail to lucide-react import
c = c.replace(
  "import { Upload, FileSpreadsheet, CheckCircle, ChevronDown } from 'lucide-react'",
  "import { Upload, FileSpreadsheet, CheckCircle, ChevronDown, Mail } from 'lucide-react'"
);

// 2. Add toast and pagoService imports after ConciliacionExcelUploader
c = c.replace(
  "import { ConciliacionExcelUploader } from './ConciliacionExcelUploader'",
  "import { ConciliacionExcelUploader } from './ConciliacionExcelUploader'\nimport toast from 'react-hot-toast'\nimport { pagoService } from '../../services/pagoService'"
);

// 3. Add state and handler before return
const stateAndHandler = `
  const [loadingGmail, setLoadingGmail] = useState(false)

  async function handleGenerarExcelDesdeGmail() {
    setIsOpen(false)
    setLoadingGmail(true)
    try {
      await pagoService.runGmailNow()
      await pagoService.downloadGmailExcel()
      toast.success('Excel generado desde Gmail descargado.')
    } catch (e) {
      const msg = e?.message || 'Error al generar Excel desde Gmail.'
      toast.error(msg)
    } finally {
      setLoadingGmail(false)
    }
  }
`;
c = c.replace(
  /const \[isOpen, setIsOpen\] = useState\(false\)\r?\n\r?\n  return/,
  "const [isOpen, setIsOpen] = useState(false)" + stateAndHandler + "\n  return"
);

// 4. Add third button (Generar Excel desde Gmail) after Conciliacion button
const gmailButton = `
            <button
              className="w-full flex items-center px-3 py-2.5 text-sm rounded-md hover:bg-gray-100 transition-colors disabled:opacity-50"
              onClick={handleGenerarExcelDesdeGmail}
              disabled={loadingGmail}
            >
              <Mail className="w-4 h-4 mr-2" />
              {loadingGmail ? 'Generando...' : 'Generar Excel desde Gmail'}
            </button>`;
c = c.replace(
  /(<CheckCircle className="w-4 h-4 mr-2" \/>\s*\n\s*Conciliaci[^<]+<\/button>)\s*(<\/div>)/s,
  '$1' + gmailButton + '\n          $2'
);

fs.writeFileSync(filePath, c);
console.log('CargaMasivaMenu.tsx patched.');
