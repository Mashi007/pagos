const fs = require('fs');

const filePath = 'Reportes.tsx';
let content = fs.readFileSync(filePath, 'utf8');

// Simple replacement using a simpler pattern
const oldPattern = `      className="space-y-8"
    >
      {/* Reportes: solo iconos`;

const newPattern = `      className="space-y-8"
    >
      {/* Header con título */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileText className="h-8 w-8 text-blue-600" />
          <h1 className="text-3xl font-bold text-gray-900">Centro de Reportes</h1>
        </div>
      </div>

      {/* Reportes: solo iconos`;

if (content.includes(oldPattern)) {
  content = content.replace(oldPattern, newPattern);
  fs.writeFileSync(filePath, content, 'utf8');
  console.log('Title header added successfully');
} else {
  console.log('Pattern not found');
}
