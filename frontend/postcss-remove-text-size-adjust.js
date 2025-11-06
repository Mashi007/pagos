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
          // Lista de pseudo-elementos válidos (incluyendo variantes de navegador)
          const validPseudoElements = ['before', 'after', 'first-line', 'first-letter', 
            'selection', 'placeholder', 'backdrop', 'marker', 'spelling-error', 'grammar-error',
            'webkit-scrollbar', 'webkit-scrollbar-thumb', 'webkit-scrollbar-track'];
          
          // Detectar selectores problemáticos comunes
          let shouldRemove = false;
          let correctedSelector = rule.selector.trim();
          
          // Validación básica: selector no puede estar vacío
          if (!correctedSelector || correctedSelector.length === 0) {
            rule.remove();
            return;
          }
          
          // 1. Selectores con doble punto consecutivo (excepto en números como 1.5 o en clases como ..before)
          if (correctedSelector.match(/\.\.(?!\d|before|after|first-line|first-letter|selection|placeholder|backdrop|marker)/)) {
            correctedSelector = correctedSelector.replace(/\.\.(?!\d|before|after|first-line|first-letter|selection|placeholder|backdrop|marker)/g, '.');
          }
          
          // 2. Selectores con pseudo-elementos inválidos (:: seguido de algo inválido)
          const pseudoElementMatches = correctedSelector.match(/::([a-zA-Z-]+)/g);
          if (pseudoElementMatches) {
            for (const match of pseudoElementMatches) {
              const pseudoElement = match.replace('::', '');
              // Verificar si es un pseudo-elemento válido o un prefijo de navegador válido
              const isValid = validPseudoElements.includes(pseudoElement) || 
                            pseudoElement.startsWith('-webkit-') || 
                            pseudoElement.startsWith('-moz-') ||
                            pseudoElement.startsWith('webkit-') ||
                            pseudoElement.startsWith('moz-');
              if (!isValid) {
                // Pseudo-elemento inválido detectado
                shouldRemove = true;
                break;
              }
            }
          }
          
          // 3. Selectores que empiezan con caracteres inválidos (excepto los válidos)
          // Permitir: letras, números, _, ., #, [, :, *, -
          if (correctedSelector.match(/^[^a-zA-Z0-9_.#\[:*-]/)) {
            shouldRemove = true;
          }
          
          // 4. Selectores con corchetes no balanceados (para atributos)
          let bracketDepth = 0;
          let inString = false;
          let stringChar = null;
          for (let i = 0; i < correctedSelector.length; i++) {
            const char = correctedSelector[i];
            if ((char === '"' || char === "'") && (i === 0 || correctedSelector[i-1] !== '\\')) {
              if (!inString) {
                inString = true;
                stringChar = char;
              } else if (char === stringChar) {
                inString = false;
                stringChar = null;
              }
            } else if (!inString) {
              if (char === '[') bracketDepth++;
              if (char === ']') bracketDepth--;
              if (bracketDepth < 0) {
                shouldRemove = true;
                break;
              }
            }
          }
          if (bracketDepth !== 0) {
            shouldRemove = true;
          }
          
          // 5. Selectores con paréntesis no balanceados (para funciones CSS)
          let parenDepth = 0;
          inString = false;
          stringChar = null;
          for (let i = 0; i < correctedSelector.length; i++) {
            const char = correctedSelector[i];
            if ((char === '"' || char === "'") && (i === 0 || correctedSelector[i-1] !== '\\')) {
              if (!inString) {
                inString = true;
                stringChar = char;
              } else if (char === stringChar) {
                inString = false;
                stringChar = null;
              }
            } else if (!inString) {
              if (char === '(') parenDepth++;
              if (char === ')') parenDepth--;
              if (parenDepth < 0) {
                shouldRemove = true;
                break;
              }
            }
          }
          if (parenDepth !== 0) {
            shouldRemove = true;
          }
          
          // Aplicar corrección o eliminación
          if (shouldRemove) {
            // Solo loggear en desarrollo para no saturar los logs
            if (process.env.NODE_ENV === 'development') {
              console.warn(`[PostCSS] Selector mal formado eliminado: ${rule.selector.substring(0, 100)}${rule.selector.length > 100 ? '...' : ''}`);
            }
            rule.remove();
          } else if (correctedSelector !== rule.selector) {
            // Aplicar corrección si se hizo algún cambio
            rule.selector = correctedSelector;
          }
        } catch (e) {
          // Si hay un error al procesar el selector, eliminarlo silenciosamente
          // Esto previene que el build falle por selectores problemáticos
          // Solo loggear en desarrollo
          if (process.env.NODE_ENV === 'development') {
            console.warn(`[PostCSS] Error procesando selector, eliminando regla: ${e.message}`);
          }
          rule.remove();
        }
      }
    },
  };
}

removeTextSizeAdjust.postcss = true;

