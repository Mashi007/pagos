const fs = require('fs');

const filePath = 'Reportes.tsx';
let content = fs.readFileSync(filePath, 'utf8');

// Fix corrupted encodings first
content = content.replace(/aA[^\w]+os/g, 'anos');
content = content.replace(/A[^\w]+os/g, 'Anos');

// 1. Add CheckCircle2 to imports
if (!content.includes('CheckCircle2')) {
  content = content.replace(
    "  Calculator,\n} from 'lucide-react'",
    "  Calculator,\n  CheckCircle2,\n} from 'lucide-react'"
  );
}

// 2. Add CONCILIACION to tiposReporte array
if (!content.includes("value: 'CONCILIACION'")) {
  content = content.replace(
    "  { value: 'CEDULA', label: 'Por cédula', icon: CreditCard },\n]",
    "  { value: 'CEDULA', label: 'Por cédula', icon: CreditCard },\n  { value: 'CONCILIACION', label: 'Conciliacion', icon: CheckCircle2 },\n]"
  );
}

// 3. Add dialog state
if (!content.includes('dialogConciliacionAbierto')) {
  content = content.replace(
    "  const [dialogAbierto, setDialogAbierto] = useState(false)\n  const [reporteSeleccionado",
    "  const [dialogAbierto, setDialogAbierto] = useState(false)\n  const [dialogConciliacionAbierto, setDialogConciliacionAbierto] = useState(false)\n  const [reporteSeleccionado"
  );
}

// 4. Add CONCILIACION handling in abrirDialogoReporte
if (!content.match(/if \(tipo === 'CONCILIACION'\)/)) {
  content = content.replace(
    "  const abrirDialogoReporte = (tipo: string) => {\n    if (tipo === 'MOROSIDAD')",
    "  const abrirDialogoReporte = (tipo: string) => {\n    if (tipo === 'CONCILIACION') {\n      setDialogConciliacionAbierto(true)\n      return\n    }\n    if (tipo === 'MOROSIDAD')"
  );
}

// 5. Add DialogConciliacion component
if (!content.includes('<DialogConciliacion')) {
  content = content.replace(
    "        onConfirm={(filtros) => generarReporteContable(filtros)}\n      />\n    </motion.div>",
    "        onConfirm={(filtros) => generarReporteContable(filtros)}\n      />\n      <DialogConciliacion\n        open={dialogConciliacionAbierto}\n        onOpenChange={setDialogConciliacionAbierto}\n        onGuardar={() => {\n          queryClient.invalidateQueries({ queryKey: ['reportes-resumen'] })\n          queryClient.invalidateQueries({ queryKey: ['kpis'] })\n        }}\n      />\n    </motion.div>"
  );
}

fs.writeFileSync(filePath, content, 'utf8');
console.log('All modifications applied successfully');
