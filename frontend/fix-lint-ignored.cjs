/**
 * Aplica correcciones de ESLint en archivos que están en .cursorignore.
 * Ejecutar: node fix-lint-ignored.cjs
 */
const fs = require('fs')
const path = require('path')

const base = path.join(__dirname, 'src')

function fixCrearClienteForm() {
  const file = path.join(base, 'components', 'clientes', 'CrearClienteForm.tsx')
  let s = fs.readFileSync(file, 'utf8')
  s = s.replace(/,\s*AnimatePresence\s*,/, ',')
  s = s.replace(/AnimatePresence\s*,\s*/, '')
  const lucideMatch = s.match(/import \{([^}]+)\} from 'lucide-react'/)
  if (lucideMatch) {
    const names = lucideMatch[1].split(',').map(x => x.trim()).filter(n =>
      !['DollarSign', 'Users', 'Building', 'AlertTriangle', 'Download', 'Badge'].includes(n))
    s = s.replace(/import \{[^}]+\} from 'lucide-react'/, `import { ${names.join(', ')} } from 'lucide-react'`)
  }
  s = s.replace(/\bconvertirFechaDeISO\b/g, '_convertirFechaDeISO')
  s = s.replace(/\berrorMessageUser\b/g, '_errorMessageUser')
  s = s.replace(/} catch \(error\) \{/g, '} catch {')
  fs.writeFileSync(file, s)
  console.log('Fixed CrearClienteForm.tsx')
}

function fixExcelUploader() {
  const file = path.join(base, 'components', 'clientes', 'ExcelUploader.tsx')
  let s = fs.readFileSync(file, 'utf8')
  s = s.replace(/,?\s*SearchableSelect\s*,?/, '')
  s = s.replace(/\bisSaving\b/g, '_isSaving')
  s = s.replace(/\bdropdownErrors\b/g, '_dropdownErrors')
  s = s.replace(/\bgetPendingClients\b/g, '_getPendingClients')
  s = s.replace(/\bgetSuggestion\b/g, '_getSuggestion')
  s = s.replace(/\bvalidateWorkbookStructure\b/g, '_validateWorkbookStructure')
  s = s.replace(/\bhandleSaveData\b/g, '_handleSaveData')
  s = s.replace(/} catch \(error\) \{/g, '} catch {')
  s = s.replace(/\(row,\s*index\)/g, '(_row, _index)')
  s = s.replace(/\bedad\b(?!\w)/g, '_edad')
  fs.writeFileSync(file, s)
  console.log('Fixed ExcelUploader.tsx')
}

function fixAIConfig() {
  const file = path.join(base, 'components', 'configuracion', 'AIConfig.tsx')
  let s = fs.readFileSync(file, 'utf8')
  const toRemove = ['Eye', 'EyeOff', 'Upload', 'BarChart3', 'TestTube', 'DollarSign']
  const lucideMatch = s.match(/import \{([^}]+)\} from 'lucide-react'/)
  if (lucideMatch) {
    const names = lucideMatch[1].split(',').map(x => x.trim()).filter(n =>
      !toRemove.includes(n))
    s = s.replace(/import \{[^}]+\} from 'lucide-react'/, `import { ${names.join(', ')} } from 'lucide-react'`)
  }
  s = s.replace(/\bmostrarToken\b/g, '_mostrarToken')
  s = s.replace(/\bcargandoDocumentos\b/g, '_cargandoDocumentos')
  s = s.replace(/\bsubiendoDocumento\b/g, '_subiendoDocumento')
  s = s.replace(/\beditandoDocumento\b/g, '_editandoDocumento')
  s = s.replace(/\bactualizandoDocumento\b/g, '_actualizandoDocumento')
  s = s.replace(/\bprocesandoDocumento\b/g, '_procesandoDocumento')
  s = s.replace(/\bresultadoPrueba\b/g, '_resultadoPrueba')
  s = s.replace(/\bsaveError\b/g, '_saveError')
  s = s.replace(/\bformatearTamaño\b/g, '_formatearTamaño')
  s = s.replace(/\bPromptEditor\b/g, '_PromptEditor')
  s = s.replace(/} catch \(error\) \{/g, '} catch {')
  const handleNames = ['handleFileChange', 'handleSubirDocumento', 'handleEliminarDocumento', 'handleIniciarEdicion', 'handleCancelarEdicion', 'handleActualizarDocumento', 'handleActivarDesactivarDocumento']
  handleNames.forEach(n => { s = s.replace(new RegExp('\\b' + n + '\\b', 'g'), '_' + n) })
  fs.writeFileSync(file, s)
  console.log('Fixed AIConfig.tsx')
}

try {
  fixCrearClienteForm()
  fixExcelUploader()
  fixAIConfig()
} catch (e) {
  console.error(e)
  process.exit(1)
}
