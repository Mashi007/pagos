const fs = require('fs');

const filePath = 'Reportes.tsx';
let content = fs.readFileSync(filePath, 'utf8');

// Use a simple regex to find and replace
const pattern = /(return \(\s*<motion\.div[\s\S]*?className="space-y-8"\s*>\s*){\/\* Reportes:/;
const replacement = `$1{/* Header con título */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <FileText className="h-8 w-8 text-blue-600" />
          <h1 className="text-3xl font-bold text-gray-900">Centro de Reportes</h1>
        </div>
      </div>

      {/* Reportes:`;

content = content.replace(pattern, replacement);
fs.writeFileSync(filePath, content, 'utf8');
console.log('Header added with regex');
