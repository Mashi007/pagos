#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const filePath = 'Reportes.tsx';
console.log('Reading file...');

const buffer = fs.readFileSync(filePath);
const content = buffer.toString('utf8');

console.log('Original file size:', buffer.length);
console.log('UTF8 string length:', content.length);

// Fix corrupted encodings
let fixed = content
  .replace(/aÃ±os/g, 'años')
  .replace(/AÃ±os/g, 'Años')
  .replace(/Ã©/g, 'é')
  .replace(/Ã­/g, 'í')
  .replace(/Ã¡/g, 'á')
  .replace(/ÃÂ©/g, 'é')
  .replace(/ÃÂ­/g, 'í')
  .replace(/ÃÂ±/g, 'ñ')
  .replace(/Ã³/g, 'ó')
  .replace(/ÃÂ³/g, 'ó')
  .replace(/ÃÃ¡/g, 'á')
  .replace(/âœ"/g, '✓');

// 1. Add CheckCircle2 to imports
if (!fixed.includes('CheckCircle2')) {
  console.log('Adding CheckCircle2 import...');
  fixed = fixed.replace(
    '  Calculator,\n} from \'lucide-react\'',
    '  Calculator,\n  CheckCircle2,\n} from \'lucide-react\''
  );
}

// 2. Add CONCILIACION to tiposReporte array
if (!fixed.includes("{ value: 'CONCILIACION'")) {
  console.log('Adding CONCILIACION to tiposReporte...');
  fixed = fixed.replace(
    '  { value: \'CEDULA\', label: \'Por cédula\', icon: CreditCard },\n]',
    '  { value: \'CEDULA\', label: \'Por cédula\', icon: CreditCard },\n  { value: \'CONCILIACION\', label: \'Conciliación\', icon: CheckCircle2 },\n]'
  );
}

// 3. Add dialog state
if (!fixed.includes('const [dialogConciliacionAbierto')) {
  console.log('Adding dialogConciliacionAbierto state...');
  fixed = fixed.replace(
    '  const [dialogAbierto, setDialogAbierto] = useState(false)\n  const [reporteSeleccionado',
    '  const [dialogAbierto, setDialogAbierto] = useState(false)\n  const [dialogConciliacionAbierto, setDialogConciliacionAbierto] = useState(false)\n  const [reporteSeleccionado'
  );
}

// 4. Add CONCILIACION handling
if (!fixed.match(/if \(tipo === 'CONCILIACION'\)/)) {
  console.log('Adding CONCILIACION handling...');
  fixed = fixed.replace(
    '  const abrirDialogoReporte = (tipo: string) => {\n    if (tipo === \'MOROSIDAD\')',
    '  const abrirDialogoReporte = (tipo: string) => {\n    if (tipo === \'CONCILIACION\') {\n      setDialogConciliacionAbierto(true)\n      return\n    }\n    if (tipo === \'MOROSIDAD\')'
  );
}

// 5. Add DialogConciliacion component
if (!fixed.includes('<DialogConciliacion')) {
  console.log('Adding DialogConciliacion component...');
  fixed = fixed.replace(
    '        onConfirm={(filtros) => generarReporteContable(filtros)}\n      />\n    </motion.div>',
    '        onConfirm={(filtros) => generarReporteContable(filtros)}\n      />\n      <DialogConciliacion\n        open={dialogConciliacionAbierto}\n        onOpenChange={setDialogConciliacionAbierto}\n        onGuardar={() => {\n          queryClient.invalidateQueries({ queryKey: [\'reportes-resumen\'] })\n          queryClient.invalidateQueries({ queryKey: [\'kpis\'] })\n        }}\n      />\n    </motion.div>'
  );
}

fs.writeFileSync(filePath, fixed, 'utf8');
console.log('File updated successfully');
