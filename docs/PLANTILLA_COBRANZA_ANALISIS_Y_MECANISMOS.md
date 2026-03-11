# Plantilla de Cobranza: Análisis, Dudas, Mapeo y Mecanismos

## 1. Análisis del texto de la plantilla

La plantilla es una **carta de cobranza formal** que:
- Saluda al cliente con tratamiento y nombre completo.
- Indica el número de crédito (préstamo) vigente.
- Lista las **cuotas vencidas sin pago** (con número, fecha de vencimiento y monto).
- Incluye párrafos estándar de recordatorio, cuentas de pago, plazo de 48 horas y exhortación a regularizar.
- Cierra con firma del Departamento de Cobranza y **fecha de emisión**.

**Sintaxis de variables:**
- Formato `{{TABLA.CAMPO}}` para valores simples (CLIENTES, PRESTAMOS, PAGOS, FECHA_CARTA).
- Bloque de iteración tipo Mustache/Handlebars: `{{#CUOTAS.VENCIMIENTOS}}` … `{{/CUOTAS.VENCIMIENTOS}}` con variables por ítem: `{{CUOTA.NUMERO}}`, `{{CUOTA.FECHA_VENCIMIENTO}}`, `{{CUOTA.MONTO}}`.

**Lógica de negocio:**
- Solo se envía la carta si existe **al menos una cuota** con `fecha_vencimiento <= FECHA_HOY` y **sin pago** (en nuestro modelo: `cuota.fecha_pago IS NULL`).
- Las cuotas a listar son las del **mismo préstamo** que se usa en la carta (filtro por `prestamo_id`).

---

## 2. Dudas y decisiones necesarias

| Duda | Opciones / Recomendación |
|------|---------------------------|
| **{{CLIENTES.TRATAMIENTO}}** | La tabla `clientes` **no tiene** campo `tratamiento` ni `genero`. Opciones: (A) Usar siempre "Sr/Sra." por defecto; (B) Añadir columna `genero` o `tratamiento` en `clientes` y mapear (Sr./Sra.). ¿Se desea añadir el campo en BD? |
| **{{CLIENTES.NOMBRE_COMPLETO}}** | En la BD actual, `clientes` tiene solo **`nombres`** (un solo campo). Se mapea a `clientes.nombres`. Si en el futuro hay `apellidos`, se podría concatenar `nombres + ' ' + apellidos`. |
| **{{PAGOS.ULTIMO_PAGO}}** | Aparece en la tabla de variables pero **no en el cuerpo** de la plantilla. Se puede mapear a la última `fecha_pago` del préstamo (MAX desde tabla `pagos` o desde aplicación a cuotas). ¿Debe mostrarse en la carta (ej. “Último pago registrado: …”)? |
| **Envío por cliente vs por cuota** | Hoy las notificaciones se envían **por ítem** (una cuota = un correo). Para la carta de cobranza lo natural es **un correo por préstamo** (o por cliente con un préstamo en mora) con **todas** las cuotas vencidas listadas. Se asume: agrupar por `prestamo_id` (o por cliente+préstamo), construir lista de cuotas vencidas y una sola carta por grupo. |
| **Tipo de plantilla** | La plantilla de cobranza puede ser un **tipo** nuevo (ej. `COBRANZA` o `CARTA_COBRANZA`) en `plantillas_notificacion`, para poder elegirla en la configuración de envíos cuando el flujo sea “cobranza” (p. ej. pestaña mora 90 o una futura pestaña “Carta cobranza”). |

---

## 3. Mapeo variables ↔ tablas reales

| Variable en plantilla | Tabla / Origen | Campo BD / Lógica |
|------------------------|----------------|---------------------|
| `{{CLIENTES.TRATAMIENTO}}` | clientes (o derivado) | No existe; valor por defecto `"Sr/Sra."` o desde futuro `clientes.genero` / `clientes.tratamiento` |
| `{{CLIENTES.NOMBRE_COMPLETO}}` | clientes | `clientes.nombres` |
| `{{PRESTAMOS.ID}}` | prestamos | `prestamos.id` |
| `{{FECHA_CARTA}}` | Sistema | Fecha actual del servidor (emisión de la carta) |
| `{{#CUOTAS.VENCIMIENTOS}}` … `{{/CUOTAS.VENCIMIENTOS}}` | cuotas | Lista de filas donde `cuotas.prestamo_id = prestamos.id` AND `cuotas.fecha_vencimiento <= HOY` AND `cuotas.fecha_pago IS NULL` ORDER BY `cuotas.fecha_vencimiento` ASC |
| `{{CUOTA.NUMERO}}` | cuotas (dentro del bloque) | `cuotas.numero_cuota` |
| `{{CUOTA.FECHA_VENCIMIENTO}}` | cuotas | `cuotas.fecha_vencimiento` (formato fecha legible) |
| `{{CUOTA.MONTO}}` | cuotas | `cuotas.monto_cuota` (en el modelo Python: `monto`) |
| `{{PAGOS.ULTIMO_PAGO}}` | pagos | Última `pagos.fecha_pago` del préstamo (opcional; no usado en el cuerpo actual) |

**Consulta sugerida para “cuotas vencidas sin pago” (por préstamo):**

```sql
SELECT c.id, c.numero_cuota, c.fecha_vencimiento, c.monto_cuota
FROM cuotas c
WHERE c.prestamo_id = :prestamo_id
  AND c.fecha_vencimiento <= CURRENT_DATE
  AND c.fecha_pago IS NULL
ORDER BY c.fecha_vencimiento ASC;
```

---

## 4. Mecanismos propuestos

### 4.1 Motor de sustitución en backend

- **Variables simples** `{{TABLA.CAMPO}}`:  
  Recibir un diccionario “contexto” con claves normalizadas (ej. `CLIENTES.NOMBRE_COMPLETO`, `PRESTAMOS.ID`, `FECHA_CARTA`) y reemplazar en asunto/cuerpo.
- **Bloque de iteración** `{{#CUOTAS.VENCIMIENTOS}}` … `{{/CUOTAS.VENCIMIENTOS}}`:  
  - Detectar el bloque en el texto.  
  - Para cada cuota en la lista (cuotas vencidas sin pago del préstamo): sustituir `{{CUOTA.NUMERO}}`, `{{CUOTA.FECHA_VENCIMIENTO}}`, `{{CUOTA.MONTO}}` y concatenar el fragmento.  
  - Reemplazar todo el bloque por esa concatenación.  
- Si la lista de cuotas vencidas está **vacía**, no enviar la carta (o no incluir el bloque y opcionalmente ocultar el párrafo de “pendientes de pago”).

### 4.2 Construcción del contexto por envío

- Desde los **filtros de las pestañas** (días 5, 3, 1, hoy, mora 90, etc.) ya se obtienen ítems (cliente + cuota(s)).  
- Para **carta de cobranza**: agrupar por `(cliente_id, prestamo_id)` (o por `prestamo_id`).  
- Por cada grupo:  
  - Obtener cliente y préstamo.  
  - Ejecutar la consulta de cuotas vencidas sin pago para ese `prestamo_id`.  
  - Armar contexto: `CLIENTES.*`, `PRESTAMOS.ID`, `FECHA_CARTA`, `CUOTAS.VENCIMIENTOS` (lista de objetos con NUMERO, FECHA_VENCIMIENTO, MONTO).  
  - Renderizar plantilla con el motor anterior y enviar **un** correo por grupo.

### 4.3 Reutilización de la plantilla

- La plantilla se guarda en **plantillas_notificacion** con tipo `COBRANZA` (o el que se defina).  
- En **Configuración → Plantillas** (y en Notificaciones → Configuración de envíos) se puede elegir esta plantilla para el caso “Cobranza”.  
- Al cargar las pestañas (días 5, 3, 1, hoy, mora 90), el backend ya filtra destinatarios; si se activa el envío de “Carta de cobranza”, se usa la misma base de datos (clientes, prestamos, cuotas, pagos) con la lógica agrupada y el nuevo formato de variables.

### 4.4 Ambiente de edición en frontend (Configuración → Plantillas)

- **Reorganizar** la pestaña **Plantillas** para que:  
  - Siga existiendo “Armar plantilla” y “Resumen” (por caso: 5 días, 3 días, hoy, mora 90, etc.).  
  - Se añada soporte explícito para **Plantilla de cobranza**: tipo `COBRANZA`, con documento de variables `{{TABLA.CAMPO}}` y bloque `{{#CUOTAS.VENCIMIENTOS}}`.  
- **Banco de variables** en el editor:  
  - Mostrar variables disponibles para cobranza: `{{CLIENTES.TRATAMIENTO}}`, `{{CLIENTES.NOMBRE_COMPLETO}}`, `{{PRESTAMOS.ID}}`, `{{FECHA_CARTA}}`, `{{#CUOTAS.VENCIMIENTOS}}` (con `{{CUOTA.NUMERO}}`, `{{CUOTA.FECHA_VENCIMIENTO}}`, `{{CUOTA.MONTO}}`), y opcionalmente `{{PAGOS.ULTIMO_PAGO}}`.  
  - Inserción por clic en el campo de cuerpo/asunto.  
- **Plantilla por defecto** de cobranza: poder cargar el texto completo que proporcionaste como plantilla inicial editables (asunto + cuerpo), de modo que sea reutilizable según lo que se cargue en las otras pestañas (misma BD y mismos filtros).

---

## 5. Resumen de tareas de implementación

1. **Backend**  
   - Extender (o añadir) función de sustitución para `{{TABLA.CAMPO}}` y para el bloque `{{#CUOTAS.VENCIMIENTOS}}` … `{{/CUOTAS.VENCIMIENTOS}}`.  
   - Construir contexto de cobranza por préstamo (cliente, prestamo_id, lista de cuotas vencidas, FECHA_CARTA).  
   - Añadir tipo `COBRANZA` (o `CARTA_COBRANZA`) a plantillas y usarlo al enviar cartas agrupadas por préstamo.

2. **Frontend**  
   - Reorganizar **Configuración → Plantillas** (tab=plantillas): mantener flujo actual y añadir soporte para plantilla de cobranza (tipo, variables, bloque).  
   - Incluir en el editor el banco de variables de cobranza y ambiente de edición claro (asunto + cuerpo con vista previa de variables).  
   - Opcional: botón “Cargar plantilla de cobranza por defecto” con el texto acordado.

3. **Datos**  
   - Mantener mapeo: CLIENTES → `clientes.nombres` (y tratamiento por defecto “Sr/Sra.”); PRESTAMOS → `prestamos.id`; CUOTAS → consulta de vencidas sin pago; FECHA_CARTA → fecha actual.  
   - Decidir si se agrega `tratamiento`/`genero` en `clientes` y si se usa `{{PAGOS.ULTIMO_PAGO}}` en el cuerpo.

Con esto, la plantilla de cobranza queda analizada, con dudas acotadas, variables compaginadas con tablas reales y mecanismos definidos para backend, envío y ambiente de edición.
