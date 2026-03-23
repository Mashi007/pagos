const fs = require('fs')
const s = fs.readFileSync(
  'c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/backend/app/api/v1/endpoints/pagos.py',
  'utf8'
)
const needle = '@router.post("/validar-filas-batch"'
const start = s.indexOf(needle)
console.log(s.slice(start, start + 2800))
