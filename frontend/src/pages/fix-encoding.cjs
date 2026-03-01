const fs = require('fs');

const filePath = 'Reportes.tsx';
let content = fs.readFileSync(filePath, 'utf8');

// Replace all double-encoded UTF-8 sequences
// c383c2b1 (Ã±) -> c3b1 (ñ)
// c383c2ad (Ã­) -> c3ad (í)  
// c383c2a9 (Ã©) -> c3a9 (é)

content = content.replace(/aÃ±os/g, 'años');
content = content.replace(/AÃ±os/g, 'Años');
content = content.replace(/perÃ­odo/g, 'período');
content = content.replace(/PrÃ©stamos/g, 'Préstamos');
content = content.replace(/ÃÂ©/g, 'é');
content = content.replace(/ÃÂ­/g, 'í');
content = content.replace(/ÃÂ±/g, 'ñ');

fs.writeFileSync(filePath, content, 'utf8');
console.log('Double-encoded UTF-8 sequences fixed');
