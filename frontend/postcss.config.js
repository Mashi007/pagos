import tailwindcss from 'tailwindcss';
import autoprefixer from 'autoprefixer';
import removeTextSizeAdjust from './postcss-remove-text-size-adjust.js';

export default {
  plugins: [
    tailwindcss,
    // Plugin personalizado para eliminar propiedades text-size-adjust problemáticas
    removeTextSizeAdjust(),
    autoprefixer({
      // Configuración para evitar propiedades problemáticas
      overrideBrowserslist: [
        'defaults',
        'not IE 11',
        'not op_mini all'
      ],
      // Excluir propiedades que causan errores en navegadores
      ignoreUnknownVersions: true,
    }),
  ],
}
