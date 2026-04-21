/**
 * VerificaciÃ³n post-build: asegura que dist/assets/ contiene todos los chunks
 * necesarios. Si faltan archivos, el build falla para detectar builds incompletos
 * (p. ej. timeout/OOM en Render).
 */
import { readdirSync, readFileSync, existsSync } from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const distPath = path.join(__dirname, 'dist')
const assetsPath = path.join(distPath, 'assets')

const MIN_JS_CHUNKS = 1 // Mínimo 1 chunk .js (entry; exceljs y demás van en el mismo bundle para evitar 404 en Render)

if (!existsSync(distPath)) {
  console.error('âŒ verify-build: dist/ no existe')
  process.exit(1)
}

if (!existsSync(assetsPath)) {
  console.error('âŒ verify-build: dist/assets/ no existe')
  process.exit(1)
}

const files = readdirSync(assetsPath)
const jsFiles = files.filter((f) => f.endsWith('.js'))
const cssFiles = files.filter((f) => f.endsWith('.css'))

if (jsFiles.length < MIN_JS_CHUNKS) {
  console.error(
    `âŒ verify-build: dist/assets/ tiene ${jsFiles.length} archivos .js (mÃ­nimo esperado: ${MIN_JS_CHUNKS}). Build posiblemente incompleto.`
  )
  console.error('   Archivos:', jsFiles.slice(0, 20).join(', '), jsFiles.length > 20 ? '...' : '')
  process.exit(1)
}

const indexPath = path.join(distPath, 'index.html')
if (!existsSync(indexPath)) {
  console.error('âŒ verify-build: dist/index.html no existe')
  process.exit(1)
}

for (const f of ['pagos-bootstrap.js', 'pagos-critical.css']) {
  const p = path.join(distPath, f)
  if (!existsSync(p)) {
    console.error(`âŒ verify-build: falta ${f} en dist/ (public shell para CSP sin inline)`)
    process.exit(1)
  }
}

const html = readFileSync(indexPath, 'utf8')
// Con base: '/pagos/', Vite genera src="/pagos/assets/index-xxx.js"; con base: '/' serÃ­a /assets/
const scriptMatch = html.match(/src="(\/pagos)?\/assets\/(index-[^"]+\.js)"/)
if (!scriptMatch) {
  console.error('âŒ verify-build: index.html no referencia el entry JS en /assets/ o /pagos/assets/')
  process.exit(1)
}

const entryJs = scriptMatch[2]
if (!jsFiles.includes(entryJs)) {
  console.error(`âŒ verify-build: index.html referencia ${entryJs} pero no existe en dist/assets/`)
  process.exit(1)
}

/** BFS sobre import("./chunk.js") desde el entry: detecta referencias a chunks ausentes (deploy incompleto → MIME text/html). */
const jsFilesSet = new Set(jsFiles)
const dynamicImportRe = /import\s*\(\s*["'](\.\/[^"']+\.js)["']\s*\)/g
function collectMissingDynamicChunks(startFile) {
  const queue = [startFile]
  const visited = new Set()
  const missing = []
  while (queue.length) {
    const f = queue.shift()
    if (visited.has(f)) continue
    visited.add(f)
    if (!jsFilesSet.has(f)) {
      missing.push(f)
      continue
    }
    let content
    try {
      content = readFileSync(path.join(assetsPath, f), 'utf8')
    } catch {
      missing.push(f)
      continue
    }
    dynamicImportRe.lastIndex = 0
    let m
    while ((m = dynamicImportRe.exec(content)) !== null) {
      const child = m[1].replace(/^\.\//, '')
      if (!visited.has(child)) queue.push(child)
    }
  }
  return missing
}

const missingDynamic = collectMissingDynamicChunks(entryJs)
if (missingDynamic.length) {
  console.error(
    `âŒ verify-build: chunks dinámicos referenciados pero no presentes en dist/assets/: ${missingDynamic.slice(0, 40).join(', ')}${missingDynamic.length > 40 ? ' ...' : ''}`
  )
  process.exit(1)
}

console.log(`âœ… verify-build: dist/assets/ tiene ${jsFiles.length} .js y ${cssFiles.length} .css`)
console.log(`âœ… verify-build: entry ${entryJs} existe`)
console.log(`âœ… verify-build: cadena import() dinámica desde entry OK (${jsFilesSet.size} archivos .js indexados)`)
process.exit(0)
