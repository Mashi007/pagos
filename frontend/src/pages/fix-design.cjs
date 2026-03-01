const fs = require('fs');

const filePath = 'Reportes.tsx';
let content = fs.readFileSync(filePath, 'utf8');

// Find and replace the main return section structure
// Look for the pattern starting with the first non-restricted return

// First, replace the Card structure that contains "Descargar reportes"
content = content.replace(
  /      <Card className="shadow-sm">\s*<CardHeader>\s*<CardTitle className="flex items-center">\s*<FileText[^>]*\/>\s*Descargar reportes\s*<\/CardTitle>\s*<p className="text-sm text-muted-foreground">[^<]*<\/p>\s*<\/CardHeader>/,
  '      <Card className="shadow-sm">\n        <CardContent className="pt-6">'
);

fs.writeFileSync(filePath, content, 'utf8');
console.log('Card header removed');
