# FLUJO DE VALIDACIÓN: Rechazo de Documentos Duplicados

## Diagrama de Flujo - Pago Individual

```
POST /api/v1/pagos
│
├─ PagoCreate (payload)
│  ├─ cedula_cliente
│  ├─ prestamo_id
│  ├─ monto_pagado
│  ├─ numero_documento ◄─────────────────┐
│  └─ ...                                 │
│                                         │
├─ Normalizar documento                   │
│  ├─ _normalizar_numero_documento()      │
│  │  └─ "DOC-001" → "DOC001"             │
│  │                                      │
│  └─ _truncar_numero_documento()         │
│     └─ Limita a _MAX_LEN caracteres     │
│                                         │
├─ ¿Documento vacío?                      │
│  ├─ Sí → Permitir (skip validación)     │
│  └─ No → Continuar                      │
│                                         │
├─ ¿Documento existe en BD?               │
│  │ _numero_documento_ya_existe(db, doc) │
│  │                                      │
│  ├─ Sí → HTTPException(409 CONFLICT) ◄──┤
│  │                                      │
│  └─ No → Continuar                      │
│                                         │
├─ Crear Pago row                         │
│  ├─ cedula_cliente (uppercase)          │
│  ├─ numero_documento (normalizado)      │
│  ├─ estado = "PENDIENTE"                │
│  ├─ usuario_registro = current_user.email
│  └─ ...                                 │
│                                         │
├─ db.add() + db.commit()                 │
│                                         │
├─ Aplicar FIFO a cuotas (si aplica)      │
│                                         │
└─ RESPUESTA: 201 Created ✅              │
                                          │
                          [409 CONFLICT] ─┘
                          "Ya existe un pago con ese Nº de documento.
                           Regla general: no se aceptan duplicados."
```

---

## Diagrama de Flujo - Carga Masiva (FASE 0: Pre-check)

```
POST /api/v1/pagos/upload
│
├─ Validar archivo Excel/XLSX
│  └─ OK → Continuar
│
├─ Leer filas (skip header)
│  └─ Máximo 10,000 filas
│
├─ ════════════════════════════════════
│  FASE 0: PRE-CARGAR DOCUMENTOS BD
│  ════════════════════════════════════
│
├─ documentos_ya_en_bd = set()
│  │
│  └─ FOR cada Pago en BD:
│     ├─ Obtener numero_documento
│     ├─ Normalizar + Truncar
│     └─ Agregar a set()
│
├─ numeros_doc_en_lote = set()
│  │
│  └─ Vacío inicialmente (se llena durante iteración)
│
└─ → Continuar a FASE 1
```

---

## Diagrama de Flujo - Carga Masiva (FASE 1: Parsear Filas)

```
FASE 1: PARSEAR FILAS
│
├─ FilasParseadas = []
│
├─ FOR cada fila en rows:
│  │
│  ├─ Detectar formato (A/D/etc.)
│  │  ├─ cedula, prestamo_id, monto, fecha, numero_documento
│  │  └─ Agregar a FilasParseadas[]
│  │
│  └─ Capturar errores de parseo
│     └─ Guardar en pagos_con_error_list[]
│
└─ → Continuar a FASE 2
```

---

## Diagrama de Flujo - Carga Masiva (FASE 2: Validación + Creación)

```
FASE 2: VALIDACIÓN + CREACIÓN
│
├─ FOR cada item en FilasParseadas:
│  │
│  ├─ Extraer datos
│  │  ├─ cedula, prestamo_id, monto, fecha, numero_documento
│  │  └─ Normalizar + Truncar numero_documento
│  │
│  ├─ key_doc = (numero_documento_norm or "").strip()
│  │
│  ├─ ══════════════════════════════════════
│  │  VALIDACIÓN 1: Duplicado en ARCHIVO
│  │  ══════════════════════════════════════
│  │
│  ├─ if key_doc and key_doc in numeros_doc_en_lote:
│  │  │
│  │  ├─ errores.append("Fila {i}: Nº documento duplicado en este archivo")
│  │  ├─ errores_detalle.append({...})
│  │  │
│  │  └─ continue ◄─── RECHAZADA (skip)
│  │
│  │
│  ├─ ══════════════════════════════════════
│  │  VALIDACIÓN 2: Duplicado en BD
│  │  ══════════════════════════════════════
│  │
│  ├─ if key_doc:
│  │  │
│  │  ├─ if key_doc in documentos_ya_en_bd:
│  │  │  │
│  │  │  ├─ errores.append("Fila {i}: Ya existe un pago...")
│  │  │  ├─ errores_detalle.append({...})
│  │  │  │
│  │  │  └─ continue ◄─── RECHAZADA (skip)
│  │  │
│  │  └─ numeros_doc_en_lote.add(key_doc) ◄─ Agregar al set para futuros checks
│  │
│  │
│  ├─ ══════════════════════════════════════
│  │  VALIDACIÓN 3: Préstamo obligatorio
│  │  ══════════════════════════════════════
│  │
│  ├─ if prestamo_id is None and cedula.strip():
│  │  ├─ count = db.query(Prestamo).filter(cliente.cedula == cedula).count()
│  │  └─ if count > 1: → continue (RECHAZADA)
│  │
│  │
│  ├─ ══════════════════════════════════════
│  │  CREAR PAGO (si pasa todas validaciones)
│  │  ══════════════════════════════════════
│  │
│  ├─ try:
│  │  │
│  │  ├─ p = Pago(
│  │  │  ├─ cedula_cliente = cedula.upper()
│  │  │  ├─ numero_documento = numero_doc_norm
│  │  │  ├─ estado = "PENDIENTE"
│  │  │  ├─ usuario_registro = current_user.email
│  │  │  └─ ...
│  │  │)
│  │  │
│  │  ├─ db.add(p)
│  │  ├─ registros += 1
│  │  │
│  │  └─ if prestamo_id: pagos_con_prestamo.append(p)
│  │
│  │
│  └─ except: → Guardar error
│
│
├─ db.flush()
│  └─ Asigna IDs a pagos insertados
│
│
├─ ════════════════════════════════════════
│  GUARDAR PAGOS CON ERRORES EN BD
│  ════════════════════════════════════════
│
├─ FOR cada pce_data en pagos_con_error_list:
│  │
│  ├─ pce = PagoConError(
│  │  ├─ cedula_cliente, monto, numero_documento
│  │  ├─ errores_descripcion = pce_data["errores"]
│  │  ├─ fila_origen = pce_data["fila_idx"]
│  │  └─ ...
│  │)
│  │
│  └─ db.add(pce)
│
│
├─ ════════════════════════════════════════
│  APLICAR PAGOS A CUOTAS (FIFO)
│  ════════════════════════════════════════
│
├─ FOR cada p en pagos_con_prestamo:
│  │
│  └─ _aplicar_pago_a_cuotas_interno(p, db)
│     ├─ Crear CuotaPago entries
│     └─ Actualizar p.estado = "PAGADO"
│
│
└─ RESPUESTA: 200 OK
   {
     "registros_creados": N,
     "registros_con_error": M,
     "errores": ["Fila X: ..."],
     "pagos_con_errores": [...]
   }
```

---

## Tabla de Decisiones (Validación)

```
┌──────────────────────────────────────────────────────────────────────┐
│ VALIDACIÓN: ¿Crear el Pago?                                          │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ 1. ¿numero_documento está vacío?                                      │
│    SÍ  → Permitir (skip validación, puede haber muchos sin doc)       │
│    NO  → Continuar paso 2                                             │
│                                                                       │
│ 2. ¿Documento ya existe en BD?                                        │
│    SÍ  → RECHAZAR (409 para individual, error en fila para bulk)      │
│    NO  → Continuar paso 3                                             │
│                                                                       │
│ 3. (Solo Bulk) ¿Documento ya aparece en este lote?                    │
│    SÍ  → RECHAZAR (fila rechazada, guardada en pagos_con_errores)     │
│    NO  → Continuar paso 4                                             │
│                                                                       │
│ 4. ¿prestamo_id está vacío?                                           │
│    SÍ  → ¿Cliente tiene más de 1 préstamo?                            │
│         SÍ  → RECHAZAR (debe especificar préstamo)                    │
│         NO  → Permitir (asignar único préstamo del cliente)           │
│    NO  → Continuar paso 5                                             │
│                                                                       │
│ 5. ¿Datos válidos (cédula, monto, fecha)?                             │
│    SÍ  → CREAR PAGO ✅                                                │
│    NO  → RECHAZAR (error de validación)                               │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Función: `_numero_documento_ya_existe()`

```python
def _numero_documento_ya_existe(
    db: Session, 
    numero_documento: Optional[str], 
    exclude_pago_id: Optional[int] = None
) -> bool:
    """
    Verifica si el documento ya existe en BD.
    
    Proceso:
    1. Normalizar número_documento
    2. Si resultado es None/empty → return False
    3. Query BD: SELECT id FROM Pago WHERE numero_documento = num
    4. (Opcional) Excluir un pago específico (para edición)
    5. return True si existe, False si no
    """
    
    # Paso 1: Normalizar
    num = _normalizar_numero_documento(numero_documento)
    
    # Paso 2: Si es vacío, permitir
    if not num:
        return False
    
    # Paso 3-4: Query BD
    q = select(Pago.id).where(Pago.numero_documento == num)
    
    # Opcional: Excluir pago específico (para edición inline)
    if exclude_pago_id is not None:
        q = q.where(Pago.id != exclude_pago_id)
    
    # Paso 5: Retornar resultado
    return db.scalar(q) is not None
```

---

## Normalización: `_normalizar_numero_documento()`

```
INPUT: "DOC-001"
  ↓
  Remover guiones, espacios, caracteres especiales
  ↓
  "DOC001"
  ↓
  Retornar

───────────────────────────────────────────

INPUT: "740087408305094"
  ↓
  No contiene caracteres especiales, mantener
  ↓
  "740087408305094"
  ↓
  Retornar

───────────────────────────────────────────

INPUT: "JPM99BMSWM4Y"
  ↓
  No contiene guiones, mantener
  ↓
  "JPM99BMSWM4Y"
  ↓
  Retornar

───────────────────────────────────────────

INPUT: None / "" / "nan" / "N/A"
  ↓
  Validar si es "vacío"
  ↓
  Retornar None
```

---

## Respuestas HTTP

### 201 Created - Pago Individual
```json
{
  "id": 1000,
  "cedula_cliente": "V99999999",
  "prestamo_id": 1,
  "monto_pagado": 12000,
  "numero_documento": "DOC001",
  "estado": "PENDIENTE",
  "usuario_registro": "itmaster@rapicreditca.com"
}
```

### 409 Conflict - Documento Duplicado
```json
{
  "detail": "Ya existe un pago con ese Nº de documento. Regla general: no se aceptan duplicados en documentos."
}
```

### 200 OK - Carga Masiva (con errores)
```json
{
  "registros_creados": 1,
  "registros_con_error": 1,
  "errores": [
    "Fila 2: Ya existe un pago con ese Nº de documento"
  ],
  "pagos_con_errores": [
    {
      "fila": 2,
      "cedula": "V99999999",
      "error": "Ya existe un pago con ese Nº de documento. Regla general: no se aceptan duplicados en documentos.",
      "datos": {
        "cedula": "V99999999",
        "prestamo_id": 1,
        "fecha_pago": "2026-03-15",
        "monto_pagado": 5000,
        "numero_documento": "DOC_ORIGINAL_001"
      }
    }
  ]
}
```

---

## Resumen Ejecutivo

```
┌─────────────────────────────────────────────┐
│ REGLA DE NEGOCIO:                           │
│ "No duplicados en documentos de pago"       │
├─────────────────────────────────────────────┤
│                                             │
│ ✅ Pago Individual:                         │
│    Documento duplicado → 409 CONFLICT       │
│                                             │
│ ✅ Carga Masiva:                            │
│    Duplicado BD → Fila rechazada            │
│    Duplicado archivo → Fila rechazada       │
│                                             │
│ ✅ Normalización:                           │
│    "DOC-001" = "DOC_001" = "DOC 001"        │
│                                             │
│ ✅ Trazabilidad:                            │
│    Rejections → pagos_con_errores          │
│                                             │
└─────────────────────────────────────────────┘
```

---

## Estado de Implementación

| Componente | Línea | Status | Verificado |
|-----------|-------|--------|-----------|
| `_numero_documento_ya_existe()` | 1416 | ✅ | Sí |
| `crear_pago()` individual | 1433 | ✅ | Sí |
| `upload_excel_pagos()` BD check | 724 | ✅ | Sí |
| `upload_excel_pagos()` archivo check | 718 | ✅ | Sí |
| Pre-check BD (FASE 0) | 668 | ✅ | Sí |
| Guardar pagos_con_errores | 770-786 | ✅ | Sí |

**Conclusión**: ✅ COMPLETAMENTE IMPLEMENTADO
