import tailwindcss from 'tailwindcss';
import autoprefixer from 'autoprefixer';
import removeTextSizeAdjust from './postcss-remove-text-size-adjust.js';

export default {
  plugins: [
    tailwindcss,
    // Plugin personalizado DEBE ir después de Tailwind pero antes de Autoprefixer
    // para procesar el CSS generado por Tailwind
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
