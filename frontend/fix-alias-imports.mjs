#!/usr/bin/env node
/**
 * Reemplaza todos los imports @/ por rutas relativas en frontend/src.
 * Así el build funciona en Render y Windows sin depender del alias de Vite.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const srcDir = path.join(__dirname, 'src');

function getAllFiles(dir, ext = ['.ts', '.tsx', '.js', '.jsx']) {
  let results = [];
  const list = fs.readdirSync(dir);
  for (const file of list) {
    const full = path.join(dir, file);
    const stat = fs.statSync(full);
    if (stat && stat.isDirectory()) {
      results = results.concat(getAllFiles(full, ext));
    } else if (ext.some(e => file.endsWith(e))) {
      results.push(full);
    }
  }
  return results;
}

function getRelativePrefix(filePath) {
  const dir = path.dirname(filePath);
  let relative = path.relative(dir, srcDir);
  relative = relative.split(path.sep).join('/');
  if (!relative || relative === '.') return './';
  return relative + '/';
}

const files = getAllFiles(srcDir);
let total = 0;
for (const file of files) {
  let content = fs.readFileSync(file, 'utf8');
  if (!content.includes('@/')) continue;
  const prefix = getRelativePrefix(file);
  const newContent = content.replace(/@\//g, prefix);
  if (newContent !== content) {
    fs.writeFileSync(file, newContent, 'utf8');
    total++;
    console.log('Fixed:', path.relative(srcDir, file));
  }
}
console.log('Done. Fixed', total, 'files.');
