const fs = require('fs');

const filePath = 'Reportes.tsx';
const buffer = fs.readFileSync(filePath);
const content = buffer.toString('latin1');
const fixed = Buffer.from(content, 'utf8').toString('utf8');

fs.writeFileSync(filePath, content, 'utf8');
console.log('File re-encoded successfully');
