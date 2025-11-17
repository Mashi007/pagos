# 👨‍💼 GUÍA PARA ADMIN - APROBAR PRÉSTAMOS

## Estado Actual
- Tienes préstamos en estado **"Borrador"** (DRAFT)
- Como Admin, puedes aprobar directamente sin cambiar a "En Revisión"

---

## Proceso Paso a Paso

### 1️⃣ VER LOS PRÉSTAMOS EN BORRADOR

Desde la lista principal:
- Verás una tabla con todos los préstamos
- Los que están en "Borrador" tienen un badge gris

### 2️⃣ ABRIR EL PRÉSTAMO PARA EVALUAR

**Haz click en el icono de OJO (👁️)**
- Se abrirá un modal con los detalles completos
- Verás 3 pestañas:
  - **Detalles**: Información general
  - **Amortización**: Tabla de cuotas (vacía hasta aprobar)
  - **Auditoría**: Historial de cambios

### 3️⃣ EVALUAR EL RIESGO

Click en el botón **"Evaluar Riesgo"** o pestaña **"Evaluación de Riesgo"**.

Deberás completar estos campos:

#### 📊 INFORMACIÓN FINANCIERA
- **Ingresos Mensuales**: Ej: 1500
- **Gastos Fijos Mensuales**: Ej: 500
- **Enganche Pagado**: Ej: 300
- **Valor de la Garantía**: Ej: 4000

#### 📋 INFORMACIÓN LABORAL
- **Años en el Empleo**: Ej: 3
- **Tipo de Empleo**:
  - Formal (mejor puntuación)
  - Independiente
  - Contratado
  - Temporal

#### 💳 HISTORIAL CREDITICIO
- Excelente (sin atrasos en 2+ años)
- Bueno (algunos atrasos menores)
- Regular (atrasos significativos)
- Malo (múltiples incumplimientos)

### 4️⃣ VER RESULTADO DE LA EVALUACIÓN

El sistema calculará automáticamente:

#### 🎯 6 Criterios Evaluados (Puntuación máxima 100):
1. **Ratio de Endeudamiento** (25%) - Depende de ingresos/gastos/cuota
2. **Ratio de Cobertura** (20%) - Ingresos vs gastos fijos
3. **Historial Crediticio** (20%) - Basado en calificación
4. **Estabilidad Laboral** (15%) - Años en el empleo actual
5. **Tipo de Empleo** (10%) - Formal vs independiente
6. **Enganche y Garantías** (10%) - Porcentaje de enganche

#### 📈 RESULTADOS:
- **Puntuación Total**: 0-100 puntos
- **Clasificación de Riesgo**:
  - BAJO (80-100 puntos)
  - MODERADO (60-79 puntos)
  - ALTO (40-59 puntos)
  - CRÍTICO (<40 puntos)

#### 🎫 DECISIÓN FINAL:
- **APROBADO** (70+ puntos)
- **CONDICIONAL** (50-69 puntos)
- **REQUIERE_MITIGACION** (35-49 puntos)
- **RECHAZADO** (<35 puntos)

### 5️⃣ APROBAR EL PRÉSTAMO

Una vez evaluado, verás las **condiciones aplicadas**:

```json
{
  "tasa_interes_aplicada": 8.0,    // % según riesgo
  "plazo_maximo": 36,              // meses
  "enganche_minimo": 15.0,         // %
  "requisitos_adicionales": "..."
}
```

#### Haz click en:
- **"Aprobar Préstamo"** → Cambia estado a APROBADO
- **"Rechazar Préstamo"** → Cambia estado a RECHAZADO

### 6️⃣ CONFIRMAR APROBACIÓN

Al aprobar, el sistema:

✅ Recalcula las cuotas según plazo máximo
- **MENSUAL**: 36 cuotas por defecto
- **QUINCENAL**: 72 cuotas (36 × 2)
- **SEMANAL**: 144 cuotas (36 × 4)

✅ Asigna la tasa de interés según riesgo
- BAJO: 8%
- MODERADO: 12%
- ALTO: 18%
- CRÍTICO: 25%

✅ Genera la tabla de amortización
- Fechas de vencimiento
- Monto de capital e interés de cada cuota
- Saldo pendiente

✅ Crea registro de aprobación
- Guarda quién aprobó y cuándo
- Registra condiciones aplicadas

---

## Flujo Completo Visual

```
[LISTA DE PRÉSTAMOS]
       ↓
Click en 👁️ (Ver)
       ↓
[Modal de Detalles]
       ↓
Click "Evaluar Riesgo"
       ↓
[Formulario de Evaluación]
  Completa 6 criterios
       ↓
[Sistema Calcula Puntuación]
  - Puntuación: X/100
  - Riesgo: BAJO/MODERADO/ALTO/CRÍTICO
  - Decisión: APROBADO/CONDICIONAL/RECHAZADO
       ↓
[Mostrar Condiciones]
  - Tasa: X%
  - Plazo: X meses
  - Cuotas: X
       ↓
Click "Aprobar" o "Rechazar"
       ↓
┌─────────────────────┐
│  PRÉSTAMO APROBADO  │
│                     │
│ ✓ Estado: APROBADO │
│ ✓ Tasa: X%          │
│ ✓ Cuotas: X         │
│ ✓ Tabla generada    │
└─────────────────────┘
```

---

## Permisos de Admin

Como Admin puedes:
- ✅ Ver todos los préstamos (incluso de otros analistas)
- ✅ Editar cualquier préstamo (incluso aprobados/rechazados)
- ✅ Evaluar riesgo en cualquier momento
- ✅ Aprobar/rechazar directamente
- ✅ Cambiar condiciones (tasa, plazo, cuotas)
- ✅ Eliminar préstamos

**Los analistas NO pueden:**
- Ver evaluación de riesgo
- Aprobar préstamos
- Editar préstamos aprobados
- Cambiar estado a APROBADO

---

## Ejemplo Completo

### Escenario: Préstamo de Juan García

**Datos del Préstamo:**
- Monto: $2,000
- Modalidad: Quincenal
- Cuotas: 72 (por defecto)

**Evaluación:**
- Ingresos: $1,500/mes
- Gastos: $500/mes
- Años empleo: 3
- Tipo empleo: Formal
- Historial: Bueno
- Enganche: 10%

**Resultado:**
- **Puntuación: 75/100** → Riesgo: MODERADO
- **Tasa aplicada: 12%**
- **Plazo máximo: 30 meses**
- **Cuotas recalculadas: 60 quincenales** (30 × 2)
- **Decisión: APROBADO**

**Después de Aprobar:**
- Estado cambia a APROBADO
- Cuotas: 60 de $33.33 cada una
- Tasa: 12%
- Fecha base: Fecha de aprobación
- Tabla de amortización generada automáticamente

---

## Siguiente Paso

1. **Abre el frontend**: Ve a la lista de préstamos
2. **Click en el icono de ojo** del préstamo en Borrador
3. **Busca el botón "Evaluar Riesgo"**
4. **Completa el formulario**
5. **Aprueba o rechaza**

¿Necesitas algo más específico?
