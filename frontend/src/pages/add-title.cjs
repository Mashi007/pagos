const fs = require('fs');

const filePath = 'Reportes.tsx';
let content = fs.readFileSync(filePath, 'utf8');

// Find the return statement and add the title section after it
const newTitleSection = `  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-8"
    >
      {/* Header con título */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileText className="h-8 w-8 text-blue-600" />
          <h1 className="text-3xl font-bold text-gray-900">Centro de Reportes</h1>
        </div>
      </div>`;

// Replace the original return structure
content = content.replace(
  /  return \(\n    <motion\.div\n      initial=\{{ opacity: 0, y: 20 }}\n      animate=\{{ opacity: 1, y: 0 }}\n      transition=\{{ duration: 0\.3 }}\n      className="space-y-8"\n    >/,
  newTitleSection
);

fs.writeFileSync(filePath, content, 'utf8');
console.log('Title header added to Reportes page');
