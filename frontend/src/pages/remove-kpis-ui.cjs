const fs = require('fs');

const filePath = 'Reportes.tsx';
let content = fs.readFileSync(filePath, 'utf8');

// Only remove the visual KPI cards section and header, but keep the hooks and logic

// 1. Remove the header section with description and refresh button (everything between the first return and the KPI cards)
content = content.replace(
  /      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">[\s\S]*?<\/Button>\s*<\/div>\s*\n\s*{\/\* Mensaje de error si hay problema cargando datos \*\/}[\s\S]*?}\)[\s\n]*}\s*{\/\* KPI Cards:/,
  '      {/* KPI Cards:'
);

// 2. Remove the entire KPI Cards grid section (from <!-- KPI Cards --> to closing </div>)
content = content.replace(
  /{\/\* KPI Cards:[\s\S]*?<\/div>\s*<\/div>\s*\n\s*{\/\* Reportes:/,
  '{/* Reportes:'
);

fs.writeFileSync(filePath, content, 'utf8');
console.log('KPI UI sections removed successfully');
