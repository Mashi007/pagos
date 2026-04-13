import tailwindcss from 'tailwindcss';
import autoprefixer from 'autoprefixer';
import removeTextSizeAdjust from './postcss-remove-text-size-adjust.js';

export default {
  plugins: [
    tailwindcss,
    autoprefixer({
      overrideBrowserslist: [
        'defaults',
        'not IE 11',
        'not op_mini all',
      ],
      ignoreUnknownVersions: true,
    }),
    // Después de Autoprefixer: quita prefijos/propiedades que Firefox moderno rechaza en consola
    // (p. ej. -moz-column-gap) y sanea selectores del CSS ya expandido.
    removeTextSizeAdjust(),
  ],
}
