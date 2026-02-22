const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, 'src', 'services', 'pagoService.ts');
let content = fs.readFileSync(filePath, 'utf8');

// Replace año and mojibake variants (aÃ±o, aA�o, etc.) with anio
content = content.replace(/año/g, 'anio');
content = content.replace(/aÃ±o/g, 'anio');
content = content.replace(/aA[\u0080-\uFFFF]+o/g, 'anio');

// Keep params.append('anio') - backend will accept 'anio' as query param

// Return type: API returns { año: number }; keep anio for type (callers use bracket notation if needed)

// Fix getUltimosPagos - add comma between }> and total
content = content.replace(
  /(total_prestamos: number\s*\n\s*)\}\>\s*\n\s*total: number/,
  '$1}>,\n    total: number'
);

fs.writeFileSync(filePath, content, 'utf8');
console.log('Done');
