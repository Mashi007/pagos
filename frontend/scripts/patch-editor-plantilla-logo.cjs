/**
 * Parche: usar replaceBase64ImagesWithLogoUrl en EditorPlantillaHTML
 * para que al ingresar/pegar HTML con imagen base64 se guarde {{LOGO_URL}}.
 */
const fs = require('fs');
const path = require('path');
const file = path.join(__dirname, '../src/components/notificaciones/EditorPlantillaHTML.tsx');
let c = fs.readFileSync(file, 'utf8');

if (c.includes('replaceBase64ImagesWithLogoUrl')) {
  console.log('Already patched');
  process.exit(0);
}

// 1) Import
c = c.replace(
  "import { Save, Mail, Eye } from 'lucide-react'",
  "import { Save, Mail, Eye } from 'lucide-react'\nimport { replaceBase64ImagesWithLogoUrl } from '../../utils/plantillaHtmlLogo'"
);

// 2) Estado inicial
c = c.replace(
  "const [cuerpoHTML, setCuerpoHTML] = useState(plantilla?.cuerpo ?? '')",
  "const [cuerpoHTML, setCuerpoHTML] = useState(replaceBase64ImagesWithLogoUrl(plantilla?.cuerpo ?? ''))"
);

// 3) onChange del Textarea
c = c.replace(
  "onChange={(e) => setCuerpoHTML(e.target.value)}",
  "onChange={(e) => setCuerpoHTML(replaceBase64ImagesWithLogoUrl(e.target.value))}"
);

// 4) Payload guardar
c = c.replace(
  "cuerpo: cuerpoHTML.trim(),",
  "cuerpo: replaceBase64ImagesWithLogoUrl(cuerpoHTML).trim(),"
);

// 5) Enviar prueba
c = c.replace(
  "replaceBase64ImagesWithLogoUrl(cuerpoHTML).trim(),\n        undefined",
  "replaceBase64ImagesWithLogoUrl(cuerpoHTML).trim(),\n        undefined"
);
// Si ya se reemplazo el 4, el 5 puede ser solo el mensaje
c = c.replace(
  "asunto.trim() || 'Prueba de plantilla',\n        cuerpoHTML.trim(),",
  "asunto.trim() || 'Prueba de plantilla',\n        replaceBase64ImagesWithLogoUrl(cuerpoHTML).trim(),"
);

fs.writeFileSync(file, c);
console.log('Patched EditorPlantillaHTML.tsx');
