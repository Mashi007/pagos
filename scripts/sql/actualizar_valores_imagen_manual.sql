-- ============================================================================
-- ACTUALIZAR VALORES MANUALMENTE EN abono_2026
-- ============================================================================
-- Script para actualizar valores de la imagen manualmente
-- 
-- INSTRUCCIONES:
-- 1. Modifica los valores en las queries UPDATE según tus datos
-- 2. Agrega más cédulas si es necesario
-- 3. Ejecuta el script completo
-- ============================================================================

-- ============================================================================
-- VALORES DE LA IMAGEN (Modifica estos valores según tus datos)
-- ============================================================================

-- Cédula: V14406409 → Valor imagen: 2350
UPDATE abono_2026 
SET abonos = 2350,
    fecha_actualizacion = CURRENT_TIMESTAMP
WHERE cedula = 'V14406409';

-- Cédula: V27223265 → Valor imagen: 864
UPDATE abono_2026 
SET abonos = 864,
    fecha_actualizacion = CURRENT_TIMESTAMP
WHERE cedula = 'V27223265';

-- Cédula: V23681759 → Valor imagen: 1120
UPDATE abono_2026 
SET abonos = 1120,
    fecha_actualizacion = CURRENT_TIMESTAMP
WHERE cedula = 'V23681759';

-- Cédula: V23107415 → Valor imagen: 730
UPDATE abono_2026 
SET abonos = 730,
    fecha_actualizacion = CURRENT_TIMESTAMP
WHERE cedula = 'V23107415';

-- ============================================================================
-- AGREGAR MÁS CÉDULAS AQUÍ (Copia y pega este bloque para cada cédula):
-- ============================================================================
/*
UPDATE abono_2026 
SET abonos = [VALOR_DE_LA_IMAGEN],
    fecha_actualizacion = CURRENT_TIMESTAMP
WHERE cedula = '[CEDULA]';
*/

-- ============================================================================
-- VERIFICAR VALORES ACTUALIZADOS
-- ============================================================================

SELECT 
    cedula,
    abonos AS valor_imagen,
    fecha_actualizacion
FROM abono_2026
WHERE cedula IN ('V14406409', 'V27223265', 'V23681759', 'V23107415')
ORDER BY cedula;
