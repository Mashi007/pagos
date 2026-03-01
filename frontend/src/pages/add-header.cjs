const fs = require('fs');

const filePath = 'Reportes.tsx';
let content = fs.readFileSync(filePath, 'utf8');

// Use exact pattern from the file
const oldPattern = `return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-8"
    >
      {/* Reportes: solo iconos. Click = descarga Excel con distribuci\xf3n seg\xfan backend. */}`;

const newPattern = `return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-8"
    >
      {/* Header con título */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <FileText className="h-8 w-8 text-blue-600" />
          <h1 className="text-3xl font-bold text-gray-900">Centro de Reportes</h1>
        </div>
      </div>

      {/* Reportes: solo iconos. Click = descarga Excel con distribuci\xf3n seg\xfan backend. */}`;

content = content.replace(oldPattern, newPattern);
fs.writeFileSync(filePath, content, 'utf8');
console.log('Title header added');
