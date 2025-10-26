# PROCEDIMIENTO: MÓDULO CLIENTES - SISTEMA DE CRÉDITOS Y COBRANZA

## 📋 REGLAS BASE DEL SISTEMA

1. **Cédula de Identidad**: Mecanismo de articulación de tablas y trazabilidad (OBLIGATORIA)
2. **Nada Vacío**: Todos los campos deben tener valor para auditoría (NOT NULL con valores por defecto)
3. **Créditos y Cobranza**: Cédula es clave para rastrear pagos, préstamos, etc.

---

## 🎯 OBJETIVOS DEL MÓDULO CLIENTES

- Mantener interfaz actual del formulario "Nuevo Cliente"
- Mantener interfaz de "Carga Masiva"
- Implementar KPIs (4 tarjetas: Total, Activos, Inactivos, Finalizados)
- Añadir columna "Fecha Registro" al dashboard
- Ajustar endpoints backend para consistencia
- Aplicar validadores estrictos

---

## 🔄 ESTRUCTURA DE CAMPOS

### Campos de la Tabla `clientes`:

```sql
- id (INTEGER, PK)
- cedula (VARCHAR 20, NOT NULL) ⚠️ CLAVE DE ARTICULACIÓN
- nombres (VARCHAR 100, NOT NULL) ✅ UNIFICA nombres + apellidos
- telefono (VARCHAR 15, NOT NULL)
- email (VARCHAR 100, NOT NULL)
- direccion (TEXT, NOT NULL)
- fecha_nacimiento (DATE, NOT NULL)
- ocupacion (VARCHAR 100, NOT NULL)
- modelo_vehiculo (VARCHAR 100, NOT NULL) → Lista desplegable de Configuración
- concesionario (VARCHAR 100, NOT NULL) → Lista desplegable de Configuración
- analista (VARCHAR 100, NOT NULL) → Lista desplegable de Configuración
- estado (VARCHAR 20, NOT NULL, default 'ACTIVO') → ACTIVO/INACTIVO/FINALIZADO
- activo (BOOLEAN, NOT NULL, default TRUE)
- fecha_registro (TIMESTAMP, NOT NULL, default NOW())
- fecha_actualizacion (TIMESTAMP, NOT NULL, default NOW(), onupdate NOW()) ✅ AJUSTADO
- usuario_registro (VARCHAR 100, NOT NULL)
- notas (TEXT, NOT NULL, default 'NA') ✅ AJUSTADO
```

### Columnas DUPLICADAS ELIMINADAS:
- ❌ CEDULA IDENTIDAD (duplicado de `cedula`)
- ❌ nombre (duplicado de `nombres`)
- ❌ apellido (unificado en `nombres`)
- ❌ movil (duplicado de `telefono`)
- ❌ CORREO ELECTRONICO (duplicado de `email`)
- ❌ FECHA DE NACIMIENTO (duplicado de `fecha_nacimiento`)
- ❌ MODELO VEHICULO (duplicado de `modelo_vehiculo`)
- ❌ ESTADO DEL CASO (duplicado de `estado`)

---

## 📝 VALIDACIONES

### 1. NOMBRES (nombres + apellidos unificados)
- **Regla**: Mínimo 2 palabras, máximo 4 palabras
- **Autoformato**: Primera letra mayúscula
- **Ejemplos**:
  - ✅ "Juan Pérez" (2 palabras)
  - ✅ "Juan Carlos Pérez González" (4 palabras)
  - ❌ "Juan" (1 palabra) → Error
  - ❌ "Juan Carlos Pérez González Silva" (5 palabras) → Error

### 2. OCUPACION
- **Regla**: Máximo 2 palabras
- **Autoformato**: Primera letra mayúscula
- **Ejemplos**:
  - ✅ "Ingeniero"
  - ✅ "Gerente General"
  - ❌ "Ingeniero de Sistemas" (3 palabras) → Error

### 3. CÉDULA
- **Validador**: Aplicar reglas de validación existentes

### 4. TELÉFONO
- **Validador**: Aplicar reglas de validación existentes

### 5. EMAIL
- **Validador**: Aplicar reglas de validación existentes

### 6. FECHA DE NACIMIENTO
- **Validador**: Aplicar reglas de validación existentes

---

## 🔄 Sincronización Estado vs Activo

**Crear Cliente**:
- `activo` = TRUE (default)
- `estado` = "ACTIVO" (default)

**Actualizar Cliente**:
- Campo `estado` editable (ACTIVO/INACTIVO/FINALIZADO)
- Campo `activo` NO visible en formulario
- **Sincronización automática backend**:
  ```python
  if estado == "ACTIVO":
      activo = True
  elif estado in ["INACTIVO", "FINALIZADO"]:
      activo = False
  ```

---

## 📊 KPIs (4 Tarjetas)

### Tarjeta 1: TOTAL CLIENTES
- **Color**: Azul (#3B82F6)
- **Icono**: Dos personas
- **Valor**: `COUNT(*) FROM clientes`
- **Badge**: "Base total"

### Tarjeta 2: CLIENTES ACTIVOS
- **Color**: Verde (#10B981)
- **Icono**: Persona con check
- **Valor**: `COUNT(*) WHERE activo = TRUE AND estado = 'ACTIVO'`
- **Badge**: Porcentaje de total

### Tarjeta 3: CLIENTES INACTIVOS
- **Color**: Naranja (#F97316)
- **Icono**: Persona con X
- **Valor**: `COUNT(*) WHERE activo = FALSE`
- **Badge**: Porcentaje de total

### Tarjeta 4: CLIENTES FINALIZADOS
- **Color**: Gris (#6B7280)
- **Icono**: Persona con menos
- **Valor**: `COUNT(*) WHERE estado = 'FINALIZADO'`
- **Badge**: Porcentaje de total

---

## 🗂️ Campos con Listas Desplegables (Strings desde Configuración)

### Modelo de Vehículo
- **Fuente**: Lista de `modelos_vehiculos` de Configuración
- **Tipo**: STRING (nombre del modelo)
- **Ejemplo**: "Toyota Corolla", "Ford Fiesta"

### Concesionario
- **Fuente**: Lista de `concesionarios` de Configuración
- **Tipo**: STRING (nombre del concesionario)
- **Ejemplo**: "CORPORACIÓN VENELJET, C.A."

### Analista
- **Fuente**: Lista de `analistas` de Configuración
- **Tipo**: STRING (nombre del analista)
- **Ejemplo**: "BELIANA YSABEL GONZÁLEZ CARVAJAL"

---

## 📅 Fecha en Dashboard

- **Columna**: "Fecha Registro"
- **Origen**: Campo `fecha_registro` de la BD
- **Formato**: DD/MM/YYYY
- **Default si NULL/Inválido**: "01/10/2025"

---

## 🔄 PROCESO DE UNIFICACIÓN nombres + apellidos

### Backend:
```python
# Cuando se crea/actualiza cliente
nombres_combinados = f"{nombres} {apellidos}".strip()
# Validar: 2-4 palabras
# Guardar en campo nombres
```

### Frontend:
```typescript
// Un solo campo "nombres" en el formulario
<nombres>: "Juan Carlos Pérez González" (hasta 4 palabras)
// Al enviar: se concatena nombres + apellidos antes de guardar
```

---

## 📋 CHECKLIST IMPLEMENTACIÓN

### Fase 1: Base de Datos ✅
- [x] Script SQL para eliminar columnas duplicadas
- [x] Script SQL para unificar nombres + apellidos
- [x] Script SQL para ajustar fecha_actualizacion
- [x] Script SQL para ajustar notas

### Fase 2: Backend
- [ ] Actualizar modelo Cliente (eliminar `apellidos`)
- [ ] Actualizar schemas
- [ ] Ajustar endpoint crear_cliente (unificar nombres)
- [ ] Ajustar endpoint actualizar_cliente (sincronizar estado/activo)
- [ ] Implementar paginación y orden por ID
- [ ] Endpoint para KPIs

### Fase 3: Frontend
- [ ] Actualizar CrearClienteForm (un solo campo nombres)
- [ ] Implementar validación 2-4 palabras
- [ ] Implementar validación ocupacion (max 2 palabras)
- [ ] Crear componente ClientesKPIs (4 tarjetas)
- [ ] Añadir columna "Fecha Registro" al dashboard
- [ ] Ajustar tarjeta de búsqueda (sin título)
- [ ] Conectar todo con React Query

---

## 🎯 NOTAS IMPORTANTES

1. **NO cambiar formulario actual** - Solo ajustar validaciones
2. **NO cambiar carga masiva** - Mantener como está
3. **Cédula es clave** - No duplicados
4. **Nada vacío** - Todos los campos deben tener valor
5. **Sincronización automática** - estado → activo en backend

