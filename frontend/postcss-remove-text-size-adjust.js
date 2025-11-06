/**
 * Plugin PostCSS personalizado para eliminar propiedades problemáticas
 * y corregir selectores mal formados
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
    Rule(rule) {
      // Detectar y corregir selectores mal formados
      if (rule.selector) {
        try {
          // Lista de pseudo-elementos válidos
          const validPseudoElements = ['before', 'after', 'first-line', 'first-letter', 
            'selection', 'placeholder', 'backdrop', 'marker', 'spelling-error', 'grammar-error'];
          
          // Detectar selectores problemáticos comunes
          let shouldRemove = false;
          let correctedSelector = rule.selector;
          
          // 1. Selectores con doble punto consecutivo (excepto en números como 1.5)
          if (correctedSelector.match(/\.\.(?!\d)/)) {
            correctedSelector = correctedSelector.replace(/\.\.(?!\d)/g, '.');
          }
          
          // 2. Selectores con pseudo-elementos inválidos (:: seguido de algo inválido)
          const pseudoElementMatch = correctedSelector.match(/::([a-zA-Z-]+)/);
          if (pseudoElementMatch) {
            const pseudoElement = pseudoElementMatch[1];
            if (!validPseudoElements.includes(pseudoElement) && 
                !pseudoElement.startsWith('-webkit-') && 
                !pseudoElement.startsWith('-moz-')) {
              // Pseudo-elemento inválido detectado
              shouldRemove = true;
            }
          }
          
          // 3. Selectores que empiezan con caracteres inválidos
          if (correctedSelector.match(/^[^a-zA-Z_.#\[:*-]/)) {
            shouldRemove = true;
          }
          
          // 4. Selectores con corchetes no balanceados
          const openBrackets = (correctedSelector.match(/\[/g) || []).length;
          const closeBrackets = (correctedSelector.match(/\]/g) || []).length;
          if (openBrackets !== closeBrackets) {
            shouldRemove = true;
          }
          
          // Aplicar corrección o eliminación
          if (shouldRemove) {
            // Solo loggear en desarrollo
            if (process.env.NODE_ENV === 'development') {
              console.warn(`[PostCSS] Selector mal formado eliminado: ${rule.selector}`);
            }
            rule.remove();
          } else if (correctedSelector !== rule.selector) {
            // Aplicar corrección si se hizo algún cambio
            rule.selector = correctedSelector;
          }
        } catch (e) {
          // Si hay un error al procesar el selector, ignorarlo silenciosamente
          // Esto previene que el build falle por selectores problemáticos
        }
      }
    },
  };
}

removeTextSizeAdjust.postcss = true;

