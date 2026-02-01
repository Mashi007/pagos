const fs = require('fs');
const path = require('path');

const srcDir = path.join(__dirname, 'src');
const replacements = [
  [String.fromCharCode(0xE2, 0x80, 0x9A, 0xEF, 0xB8, 0x8F), '\u2139\ufe0f'],
  [String.fromCharCode(0xE2, 0x9C, 0x85) + '"', '\u2705'],
  [String.fromCharCode(0xE2, 0x9C, 0x85), '\u2705'],
  [String.fromCharCode(0xF0, 0x9F, 0x93, 0x84), '\uD83D\uDCC4'],
  [String.fromCharCode(0xF0, 0x9F, 0x93, 0x85), '\uD83D\uDCC5'],
  [String.fromCharCode(0xF0, 0x9F, 0x93, 0x8A), '\uD83D\uDCCA'],
  [String.fromCharCode(0xF0, 0x9F, 0x93, 0x8B), '\uD83D\uDCCB'],
  [String.fromCharCode(0xF0, 0x9F, 0x92, 0xB0), '\uD83D\uDCB0'],
  [String.fromCharCode(0xF0, 0x9F, 0x92, 0xB5), '\uD83D\uDCB5'],
];

function walk(dir) {
  let results = [];
  const list = fs.readdirSync(dir);
  for (const file of list) {
    const full = path.join(dir, file);
    const stat = fs.statSync(full);
    if (stat && stat.isDirectory()) results = results.concat(walk(full));
    else if (/\.(ts|tsx)$/.test(file)) results.push(full);
  }
  return results;
}

const files = walk(srcDir);
let total = 0;
for (const file of files) {
  let content = fs.readFileSync(file, 'utf8');
  let changed = false;
  for (const [oldStr, newStr] of replacements) {
    if (content.includes(oldStr)) {
      content = content.split(oldStr).join(newStr);
      changed = true;
    }
  }
  if (changed) {
    fs.writeFileSync(file, content, 'utf8');
    console.log('Fixed:', path.basename(file));
    total++;
  }
}
console.log('Done. Fixed', total, 'files.');
