import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const srcDir = path.join(__dirname, 'src');

const files = [];
function walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) walk(full);
    else if (/\.(ts|tsx)$/.test(e.name)) files.push(full);
  }
}
walk(srcDir);

const fixes = [
  [/Ã±/g, 'ñ'],
  [/Ã³/g, 'ó'],
  [/Ã­/g, 'í'],
  [/Ã©/g, 'é'],
  [/Ã¡/g, 'á'],
  [/Ãº/g, 'ú'],
  [/Ã“/g, 'Ó'],
  [/SesiÃ³n/g, 'Sesión'],
  [/â„¹ï¸\s*/g, ''],
  [/â†’/g, '→'],
  [/âœ…/g, '✅'],
  [/AUTOMÃ.TICO/g, 'AUTOMÁTICO'],
];

let n = 0;
for (const f of files) {
  let c = fs.readFileSync(f, 'utf8');
  let changed = false;
  for (const [re, repl] of fixes) {
    const next = c.replace(re, repl);
    if (next !== c) { c = next; changed = true; }
  }
  if (changed) {
    fs.writeFileSync(f, c, 'utf8');
    n++;
    console.log('Fixed:', path.relative(srcDir, f));
  }
}
console.log('Done. Fixed', n, 'files.');
