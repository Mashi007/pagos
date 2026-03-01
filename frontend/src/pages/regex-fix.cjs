const fs = require('fs');

const filePath = 'Reportes.tsx';
let content = fs.readFileSync(filePath, 'utf8');

// Use regex to find and replace the CardHeader section
const pattern = /<Card className="shadow-sm">\s*<CardHeader>[\s\S]*?Descargar reportes[\s\S]*?<\/CardHeader>\s*<CardContent>/;

if (pattern.test(content)) {
  content = content.replace(
    pattern,
    `<Card className="shadow-sm">
        <CardContent className="pt-6">`
  );
  fs.writeFileSync(filePath, content, 'utf8');
  console.log('Replaced CardHeader section');
} else {
  console.log('Pattern not found');
}
