const fs = require('fs');

const filePath = 'Reportes.tsx';
let content = fs.readFileSync(filePath, 'utf8');

// Simply replace the CardHeader section with nothing, and add pt-6 to CardContent
content = content.replace(
  `        <CardHeader>
          <CardTitle className="flex items-center">
            <FileText className="mr-2 h-5 w-5" aria-hidden />
            Descargar reportes
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Haz clic en un icono para elegir años y meses, luego descarga el reporte en Excel.
          </p>
        </CardHeader>
        <CardContent>`,
  `        <CardContent className="pt-6">`
);

fs.writeFileSync(filePath, content, 'utf8');
console.log('Removed CardHeader with duplicate title');
