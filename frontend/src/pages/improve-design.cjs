const fs = require('fs');

const filePath = 'Reportes.tsx';
let content = fs.readFileSync(filePath, 'utf8');

// Replace the return statement with an improved structure
const oldReturn = `  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-8"
    >`;

const newReturn = `  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      {/* Header principal */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Centro de Reportes</h1>
        <p className="text-gray-600 mt-2">Genera y descarga reportes detallados del sistema. Datos en tiempo real desde la base de datos.</p>
      </div>`;

content = content.replace(oldReturn, newReturn);

// Remove the Card header with "Descargar reportes" title
content = content.replace(
  `      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center">
            <FileText className="mr-2 h-5 w-5" aria-hidden />
            Descargar reportes
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Haz clic en un icono para elegir años y meses, luego descarga el reporte en Excel.
          </p>
        </CardHeader>
        <CardContent>`,
  `      <Card className="shadow-sm">
        <CardContent className="pt-6">`
);

// Close the Card properly
content = content.replace(
  `        </CardContent>
      </Card>

      <DialogReporteFiltros`,
  `        </CardContent>
      </Card>

      <DialogReporteFiltros`
);

fs.writeFileSync(filePath, content, 'utf8');
console.log('Design improved: removed duplicate title and streamlined layout');
