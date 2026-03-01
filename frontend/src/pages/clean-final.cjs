const fs = require('fs');

const filePath = 'Reportes.tsx';
const lines = fs.readFileSync(filePath, 'utf8').split('\n');

let output = [];
let skipMode = false;
let skipDepth = 0;

for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  
  // Start skipping at KPI Cards comment
  if (line.includes('KPI Cards: altura uniforme')) {
    skipMode = true;
    skipDepth = 0;
    continue;
  }
  
  // Also skip the CardHeader with "Descargar reportes"
  if (line.includes('<CardHeader>') && i > 300) {
    // Check if this is the one before CardTitle with Descargar reportes
    if (i + 2 < lines.length && lines[i + 2].includes('Descargar reportes')) {
      skipMode = true;
      skipDepth = 0;
      continue;
    }
  }
  
  if (skipMode) {
    // Count braces to track nesting
    const open = (line.match(/{/g) || []).length + (line.match(/<\w+/g) || []).length / 2;
    const close = (line.match(/}/g) || []).length + (line.match(/<\/\w+>/g) || []).length / 2;
    skipDepth += open - close;
    
    // Stop skipping when we reach depth 0 and find closing tag
    if (skipDepth <= 0 && (line.includes('</div>') || line.includes('</CardHeader>'))) {
      skipMode = false;
    }
    continue;
  }
  
  output.push(line);
}

fs.writeFileSync(filePath, output.join('\n'), 'utf8');
console.log('Removed KPI Cards section and Descargar reportes header');
