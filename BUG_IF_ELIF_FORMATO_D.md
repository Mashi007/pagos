# Bug Crítico: Orden if-elif en Detección de Formatos

## Problema Descubierto

El endpoint `/api/v1/pagos/upload` **no estaba detectando correctamente el Formato D** (Cédula | Monto | Fecha | Documento) aunque técnicamente estaba en el código.

### Síntomas
- ❌ 0 pagos registrados
- ⚠️ 10 filas omitidas: "Comprueba que la columna 1 sea Cédula y la 4 sea Monto > 0"
- ⚠️ 9 filas con error
- ❌ Números gigantescos en la columna D interpretados como montos (740087406734393)

### Causa Raíz

La estructura lógica de los if-elif-else estaba **incorrecta**:

```python
# ❌ INCORRECTO (lo que estaba antes):
if Formato_D:          # if
    ...
if Formato_A:          # ← PROBLEMA: otro if, no elif!
    ...
elif Formato_B:        # Nunca se ejecuta porque A ya procesó
    ...
else:
    Formato_C
```

**Resultado**: 
1. Si Formato D falla en detectarse perfectamente (e.g., `row[1]` contiene algo inesperado), Formato A intenta capturarlo
2. Formato A verifica `_looks_like_documento(row[0])` en tu caso:
   - `row[0]` = `V18000758` (cédula) ❌ No es documento
   - Falla silenciosamente
3. Cae al `else` (Formato C) que espera: Cédula, ID_Préstamo, Fecha, **Monto**, Documento
4. Tu Formato D es: Cédula, **Monto**, Fecha, Documento
5. El Formato C interpreta tu Monto (96) como ID_Préstamo y tu Documento (numero gigante) como Monto
6. → ❌ Error 500 o filas omitidas

## Solución

Cambié la estructura a **if-elif-elif-else correcta**:

```python
# ✅ CORRECTO (después del fix):
if Formato_D:          # 1er intento: Cédula | Monto | Fecha | Documento
    ...
elif Formato_A:        # 2do intento: Documento | Cédula | Fecha | Monto
    ...
elif Formato_B:        # 3er intento: Fecha | Cédula | Monto | Documento
    ...
else:
    Formato_C          # Alternativa: Cédula | ID_Préstamo | Fecha | Monto | Documento
```

**Línea de código**:
```python
# Cambio:
- if len(row) >= 4 and _looks_like_documento(row[0]) and _looks_like_cedula(row[1]):
+ elif len(row) >= 4 and _looks_like_documento(row[0]) and _looks_like_cedula(row[1]):
```

## Por Qué Pasó Esto

Cuando agregué el Formato D recientemente, inserté un `if` al inicio. Pero **no convertí el Formato A a `elif`**. Esto significa que ambos formatos competían por detectar la fila, y el orden incorrecto de if-elif causaba la cascada de fallos.

## Prioridad Ahora Correcta

1. **Formato D (Principal)**: Cédula | Monto | Fecha | Documento ⭐
2. **Formato A**: Documento | Cédula | Fecha | Monto
3. **Formato B**: Fecha | Cédula | Monto | Documento
4. **Formato C**: Cédula | ID Préstamo | Fecha | Monto | Documento

## Resultado Esperado Ahora

Con tu Excel:
```
Cédula        | Monto | Fecha      | Nº Documento
V18000758     | 96    | 31-10-2025 | VE/505363358
V18000758     | 96    | 12-11-2025 | VE/490978173
...
```

**Deberías obtener:**
```json
{
  "message": "Carga finalizada",
  "registros_procesados": 20,
  "cuotas_aplicadas": 0,
  "filas_omitidas": 0,
  "errores": [],
  "errores_total": 0
}
```

## Archivos Modificados

- `backend/app/api/v1/endpoints/pagos.py`
  - Línea 505: Cambio de `if` a `elif` en Formato A
  
## Testing

Para verificar que funciona:

1. **Carga tu Excel** (20 filas de ejemplo)
2. **Espera respuesta 200 OK** con todos los registros procesados
3. **Verifica BD**: Los 20 pagos deben estar registrados
4. **Sin errores**: La sección `errores` debe estar vacía

## Lecciones Aprendidas

- ✅ Si-elif-else debe ser **exhaustivo y exclusivo**
- ✅ Primer formato detectado "gana" → ordenar por especificidad
- ✅ Al agregar formatos nuevos, revisar siempre la cadena completa
- ✅ Agregar tests para múltiples formatos en paralelo

## Próximas Mejoras

1. Agregar **logging detallado** que muestre qué formato se detectó
2. Agregar **unit tests** para cada formato
3. Documentar en UI qué formato se esperaba vs qué se detectó
4. Considerar un **modo debug** que muestra el parsing
