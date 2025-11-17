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
            'webkit-scrollbar', 'webkit-scrollbar-thumb', 'webkit-scrollbar-track',
            'webkit-scrollbar-button', 'webkit-scrollbar-corner'];

          // Detectar selectores problemáticos comunes
          let shouldRemove = false;
          let correctedSelector = rule.selector.trim();

          // Selectores de webkit-scrollbar son válidos incluso con pseudo-clases como :hover
          const isWebkitScrollbarSelector = correctedSelector.includes('webkit-scrollbar');

          // Validación básica: selector no puede estar vacío
          if (!correctedSelector || correctedSelector.length === 0) {
            rule.remove();
            return;
          }

          // 0. Detectar selectores con caracteres de control o no imprimibles
          if (/[\x00-\x1F\x7F-\x9F]/.test(correctedSelector)) {
            correctedSelector = correctedSelector.replace(/[\x00-\x1F\x7F-\x9F]/g, '');
            if (correctedSelector.length === 0) {
              rule.remove();
              return;
            }
          }

          // 1. Selectores con doble punto consecutivo (excepto en números como 1.5 o en clases como ..before)
          if (correctedSelector.match(/\.\.(?!\d|before|after|first-line|first-letter|selection|placeholder|backdrop|marker)/)) {
            correctedSelector = correctedSelector.replace(/\.\.(?!\d|before|after|first-line|first-letter|selection|placeholder|backdrop|marker)/g, '.');
          }

          // 1.1. Selectores con múltiples puntos consecutivos (más de 2)
          if (correctedSelector.match(/\.{3,}/)) {
            correctedSelector = correctedSelector.replace(/\.{3,}/g, '.');
          }

          // 1.2. Selectores que terminan con punto (inválido)
          if (correctedSelector.endsWith('.') && !correctedSelector.endsWith('::')) {
            correctedSelector = correctedSelector.slice(0, -1);
          }

          // 2. Selectores con pseudo-elementos inválidos (:: seguido de algo inválido)
          // ✅ EXCEPCIÓN: Selectores de webkit-scrollbar son válidos incluso con pseudo-clases
          if (!isWebkitScrollbarSelector) {
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
                  // Pseudo-elemento inválido detectado - intentar corregir o eliminar
                  // Si es un pseudo-elemento común mal escrito, intentar corregirlo
                  if (pseudoElement.toLowerCase() === 'webkit-scrollbar') {
                    // Ya está en la lista, no debería llegar aquí
                  } else {
                    shouldRemove = true;
                    break;
                  }
                }
              }
            }
          }

          // 2.1. Detectar pseudo-clases/pseudo-elementos con sintaxis incorrecta
          // Ejemplo: :::before (triple dos puntos) o :: :before (espacio)
          // ✅ EXCEPCIÓN: Selectores de webkit-scrollbar con :hover son válidos
          if (!isWebkitScrollbarSelector && (correctedSelector.match(/:::\w+/) || correctedSelector.match(/::\s+:/))) {
            shouldRemove = true;
          }

          // 3. Selectores que empiezan con caracteres inválidos (excepto los válidos)
          // Permitir: letras, números, _, ., #, [, :, *, -, @ (para @keyframes, etc.)
          if (correctedSelector.match(/^[^a-zA-Z0-9_.#\[:@*-]/)) {
            shouldRemove = true;
          }

          // 3.1. Selectores con espacios múltiples consecutivos (excepto dentro de strings)
          let inString = false;
          let stringChar = null;
          let hasMultipleSpaces = false;
          for (let i = 0; i < correctedSelector.length - 1; i++) {
            const char = correctedSelector[i];
            const nextChar = correctedSelector[i + 1];
            if ((char === '"' || char === "'") && (i === 0 || correctedSelector[i-1] !== '\\')) {
              if (!inString) {
                inString = true;
                stringChar = char;
              } else if (char === stringChar) {
                inString = false;
                stringChar = null;
              }
            } else if (!inString && char === ' ' && nextChar === ' ') {
              hasMultipleSpaces = true;
              break;
            }
          }
          if (hasMultipleSpaces) {
            // Normalizar espacios múltiples a uno solo (excepto dentro de strings)
            inString = false;
            stringChar = null;
            let normalized = '';
            let lastWasSpace = false;
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
                normalized += char;
                lastWasSpace = false;
              } else if (inString) {
                normalized += char;
                lastWasSpace = false;
              } else if (char === ' ') {
                if (!lastWasSpace) {
                  normalized += char;
                  lastWasSpace = true;
                }
              } else {
                normalized += char;
                lastWasSpace = false;
              }
            }
            correctedSelector = normalized.trim();
          }

          // 4. Selectores con corchetes no balanceados (para atributos)
          // También detectar selectores con corchetes escapados problemáticos como .after\:left-\[2px\]:after
          let bracketDepth = 0;
          inString = false;
          stringChar = null;
          let hasProblematicEscapedBrackets = false;

          // Detectar patrones problemáticos: corchetes escapados dentro de selectores escapados
          // Ejemplo: .after\:left-\[2px\]:after o .placeholder\:text-muted-foreground
          // Estos son válidos en Tailwind pero pueden causar warnings en algunos parsers
          const problematicPattern = /\\\[[^\]]*\\\]/;
          if (problematicPattern.test(correctedSelector)) {
            // Este es un selector válido de Tailwind con valores arbitrarios escapados
            // No es realmente un error, solo un warning del navegador
            // No lo eliminamos, solo lo marcamos para logging opcional
            hasProblematicEscapedBrackets = true;
          }

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
              // Solo contar corchetes no escapados
              if (char === '[' && (i === 0 || correctedSelector[i-1] !== '\\')) {
                bracketDepth++;
              }
              if (char === ']' && (i === 0 || correctedSelector[i-1] !== '\\')) {
                bracketDepth--;
              }
              if (bracketDepth < 0) {
                shouldRemove = true;
                break;
              }
            }
          }
          if (bracketDepth !== 0 && !hasProblematicEscapedBrackets) {
            // Solo marcar como problemático si NO es un patrón válido de Tailwind
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

          // 6. Detectar selectores con llaves no balanceadas (no deberían estar en selectores, pero por si acaso)
          let braceDepth = 0;
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
              if (char === '{') braceDepth++;
              if (char === '}') braceDepth--;
              if (braceDepth < 0) {
                shouldRemove = true;
                break;
              }
            }
          }
          if (braceDepth !== 0) {
            shouldRemove = true;
          }

          // 7. Validar que el selector no tenga comillas sin cerrar
          let quoteCount = 0;
          let lastQuote = null;
          for (let i = 0; i < correctedSelector.length; i++) {
            const char = correctedSelector[i];
            if ((char === '"' || char === "'") && (i === 0 || correctedSelector[i-1] !== '\\')) {
              if (lastQuote === null || lastQuote === char) {
                quoteCount++;
                lastQuote = char;
              }
            }
          }
          if (quoteCount % 2 !== 0) {
            // Comillas no balanceadas
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

