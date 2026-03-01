const fs = require('fs');
const c = fs.readFileSync('Reportes.tsx', 'utf8');
const lines = c.split('\n');

for (let i = 110; i <= 140; i++) {
  if (i < lines.length) {
    const line = lines[i];
    const bytes = Buffer.from(line, 'utf8').toString('hex');
    console.log(`Line ${i+1}: ${line.substring(0, 60)}`);
    console.log(`  Bytes: ${bytes.substring(0, 100)}`);
  }
}
