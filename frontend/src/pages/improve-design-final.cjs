const fs = require('fs');

const filePath = 'Reportes.tsx';
let content = fs.readFileSync(filePath, 'utf8');

// Add the main header right after the motion.div opening (after the main return)
// Find the main return (not the restricted one) and add header
content = content.replace(
  /(\n  return \(\n    <motion\.div\n      initial=\{{ opacity: 0, y: 20 }}\n      animate=\{{ opacity: 1, y: 0 }}\n      transition=\{{ duration: 0\.3 }}\n      className="space-y-8"\n    >\n)(      {\/\* KPI Cards)/,
  `$1      {/* Header principal */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-gray-900">Centro de Reportes</h1>
        <p className="text-gray-600">Genera y descarga reportes detallados del sistema. Datos en tiempo real desde la base de datos.</p>
      </div>

$2`
);

// Remove the duplicate title in the Card
content = content.replace(
  /      <Card className="shadow-sm">\s*<CardHeader>\s*<CardTitle className="flex items-center">\s*<FileText[^\n]*\n[^\n]*Descargar reportes\s*<\/CardTitle>\s*<p className="text-sm text-muted-foreground">[^<]*<\/p>\s*<\/CardHeader>\s*<CardContent>/,
  '      <Card className="shadow-sm">\n        <CardContent>'
);

fs.writeFileSync(filePath, content, 'utf8');
console.log('Design improved: added header and removed duplicate title');
