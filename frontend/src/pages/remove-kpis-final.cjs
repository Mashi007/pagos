const fs = require('fs');

const filePath = 'Reportes.tsx';
const lines = fs.readFileSync(filePath, 'utf8').split('\n');

let output = [];
let skipMode = false;
let skipLevel = 0;

for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  
  // Skip header section
  if (line.includes('flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between')) {
    skipMode = true;
    skipLevel = 1;
    continue;
  }
  
  // Skip KPI Cards section
  if (line.includes('KPI Cards: altura uniforme')) {
    skipMode = true;
    skipLevel = 1;
    continue;
  }
  
  // Count braces to know when to stop skipping
  if (skipMode) {
    const openBraces = (line.match(/{/g) || []).length;
    const closeBraces = (line.match(/}/g) || []).length;
    skipLevel += openBraces - closeBraces;
    
    if (skipLevel <= 0) {
      skipMode = false;
    }
    continue;
  }
  
  output.push(line);
}

fs.writeFileSync(filePath, output.join('\n'), 'utf8');
console.log('KPI sections removed');
