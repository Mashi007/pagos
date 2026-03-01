const fs = require('fs');

const filePath = 'Reportes.tsx';
let content = fs.readFileSync(filePath, 'utf8');

// Only replace the CardHeader...CardContent section with just CardContent
// Be very specific about what we're replacing
const oldPattern = `      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center">
            <FileText className="mr-2 h-5 w-5" aria-hidden />
            Descargar reportes
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Haz clic en un icono para elegir años y meses, luego descarga el reporte en Excel.
          </p>
        </CardHeader>
        <CardContent>`;

const newPattern = `      <Card className="shadow-sm">
        <CardContent className="pt-6">`;

if (content.includes(oldPattern)) {
  content = content.replace(oldPattern, newPattern);
  fs.writeFileSync(filePath, content, 'utf8');
  console.log('Replaced CardHeader with duplicate title');
} else {
  console.log('Pattern not found');
}
