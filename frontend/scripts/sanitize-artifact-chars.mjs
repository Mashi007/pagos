/**
 * Reemplaza caracteres típicos de copiar/pegar o de salida de IA que rompen TS/JS
 * (comillas tipográficas, guiones Unicode, espacios invisibles, BOM duplicado).
 * Uso: node scripts/sanitize-artifact-chars.mjs [ruta opcional, default: ../src]
 */
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const rootDefault = path.join(__dirname, '..', 'src')
const targetRoot = path.resolve(process.argv[2] || rootDefault)

const replacements = [
  ['\uFEFF', ''],
  ['\u200B', ''],
  ['\u200C', ''],
  ['\u200D', ''],
  ['\u2060', ''],
  ['\u00A0', ' '],
  ['\u201C', '"'],
  ['\u201D', '"'],
  ['\u2018', "'"],
  ['\u2019', "'"],
  ['\u2013', '-'],
  ['\u2014', '-'],
]

const exts = new Set(['.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs'])

function walk(dir, out) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, e.name)
    if (e.isDirectory()) {
      if (e.name === 'node_modules' || e.name === 'dist') continue
      walk(full, out)
    } else if (exts.has(path.extname(e.name))) out.push(full)
  }
}

const files = []
if (fs.existsSync(targetRoot)) {
  const st = fs.statSync(targetRoot)
  if (st.isDirectory()) walk(targetRoot, files)
  else files.push(targetRoot)
} else {
  console.error('No existe:', targetRoot)
  process.exit(1)
}

let changedFiles = 0
for (const f of files) {
  let c = fs.readFileSync(f, 'utf8')
  const orig = c
  for (const [from, to] of replacements) {
    if (c.includes(from)) c = c.split(from).join(to)
  }
  if (c !== orig) {
    fs.writeFileSync(f, c, 'utf8')
    changedFiles++
    console.log('sanitized:', path.relative(path.join(__dirname, '..'), f))
  }
}
console.log('Done. Files changed:', changedFiles, '/', files.length)
