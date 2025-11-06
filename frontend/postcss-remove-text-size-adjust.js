/**
 * Plugin PostCSS personalizado para eliminar propiedades text-size-adjust
 * que causan warnings en algunos navegadores
 */
export default function removeTextSizeAdjust() {
  return {
    postcssPlugin: 'postcss-remove-text-size-adjust',
    Declaration(decl) {
      // Eliminar propiedades text-size-adjust problemáticas
      if (
        decl.prop === '-webkit-text-size-adjust' ||
        decl.prop === '-moz-text-size-adjust' ||
        decl.prop === 'text-size-adjust'
      ) {
        decl.remove();
      }
    },
  };
}

removeTextSizeAdjust.postcss = true;

