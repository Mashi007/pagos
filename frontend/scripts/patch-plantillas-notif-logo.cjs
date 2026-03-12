const fs = require('fs');
const path = require('path');
const file = path.join(__dirname, '../src/components/notificaciones/PlantillasNotificaciones.tsx');
let c = fs.readFileSync(file, 'utf8');

if (c.includes('replaceBase64ImagesWithLogoUrl')) {
  console.log('Already patched');
  process.exit(0);
}

// 1) Import
c = c.replace(
  "import { EditorPlantillaHTML } from './EditorPlantillaHTML'",
  "import { EditorPlantillaHTML } from './EditorPlantillaHTML'\nimport { replaceBase64ImagesWithLogoUrl } from '../../utils/plantillaHtmlLogo'"
);

// 2) cuerpoFinal: reemplazar base64 por {{LOGO_URL}} en el cuerpo que se guarda
c = c.replace(
  "const parts = [encabezado, cuerpo, firma].filter(Boolean)\n    return parts.join('\\n\\n')",
  "const parts = [encabezado, cuerpo, firma].filter(Boolean)\n    return replaceBase64ImagesWithLogoUrl(parts.join('\\n\\n'))"
);

// 3) Al cargar plantilla (seleccionar): mostrar cuerpo sin base64
c = c.replace(
  "setCuerpo(p.cuerpo)",
  "setCuerpo(replaceBase64ImagesWithLogoUrl(p.cuerpo || ''))"
);

fs.writeFileSync(file, c);
console.log('Patched PlantillasNotificaciones.tsx');
