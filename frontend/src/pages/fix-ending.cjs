const fs = require('fs');

const filePath = 'Reportes.tsx';
let content = fs.readFileSync(filePath, 'utf8');

// Make sure file ends with proper closing
if (!content.includes('export default Reportes')) {
  // Remove trailing whitespace
  content = content.trimEnd();
  
  // Add proper closing
  if (!content.endsWith('}')) {
    content += '\n  )\n}\n\nexport default Reportes\n';
  }
}

fs.writeFileSync(filePath, content, 'utf8');
console.log('File ending fixed');
