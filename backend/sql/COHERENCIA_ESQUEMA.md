# Coherencia de estructura BD ↔ Modelos ↔ SQL

## Resumen

| Tabla                  | Modelo (Python)     | SQL (EJECUTAR_EN_DBEAVER) | COMPROBAR_BD.sql |
|------------------------|---------------------|----------------------------|------------------|
| pagos_whatsapp         | ✅ coherente        | ✅ añade link_imagen       | ✅ consultas 1,2,5 |
| pagos_informes         | ✅ coherente        | ✅ tabla + columnas + nullable | ✅ consultas 1,3,5,6 |
| conversacion_cobranza   | ✅ coherente        | ✅ tabla + columnas        | ✅ consultas 1,4,5 |

---

## 1. pagos_whatsapp

| Columna        | Modelo (PagosWhatsapp) | SQL / BD esperada |
|----------------|------------------------|-------------------|
| id             | Integer, PK            | SERIAL PRIMARY KEY |
| fecha          | DateTime, NOT NULL     | TIMESTAMP NOT NULL |
| cedula_cliente | String(20), nullable   | VARCHAR(20)       |
| imagen         | LargeBinary, NOT NULL  | BYTEA NOT NULL    |
| link_imagen    | Text, nullable         | TEXT (ADD COLUMN en script) |

**Nota:** La tabla base se crea con `pagos_whatsapp.sql` (id, fecha, cedula_cliente, imagen). `EJECUTAR_EN_DBEAVER.sql` solo añade `link_imagen` si no existe.

---

## 2. pagos_informes

| Columna              | Modelo (PagosInforme) | SQL (CREATE + ALTER) |
|----------------------|------------------------|------------------------|
| id                   | Integer, PK            | SERIAL PRIMARY KEY     |
| cedula               | String(20), NOT NULL   | VARCHAR(20) NOT NULL   |
| fecha_deposito        | String(50), nullable   | VARCHAR(50)            |
| nombre_banco          | String(255), nullable  | VARCHAR(255)           |
| numero_deposito       | String(100), nullable  | VARCHAR(100)           |
| numero_documento      | String(100), nullable  | VARCHAR(100)           |
| cantidad              | String(50), nullable   | VARCHAR(50)            |
| humano                | String(20), nullable   | VARCHAR(20)            |
| link_imagen           | Text, NOT NULL (modelo)| TEXT (script: nullable) |
| observacion           | Text, nullable         | TEXT                   |
| pagos_whatsapp_id     | Integer, FK, nullable  | INTEGER REFERENCES     |
| periodo_envio         | String(20), NOT NULL   | VARCHAR(20) NOT NULL   |
| fecha_informe         | DateTime, NOT NULL     | TIMESTAMP NOT NULL     |
| created_at            | DateTime, NOT NULL     | TIMESTAMP NOT NULL     |

**Columnas legacy (solo en BD, no en modelo):** `banco_entidad_financiera`, `cantidad_depositada`. El script las deja existir y pone `banco_entidad_financiera` nullable para evitar NotNullViolation. La app usa `nombre_banco`.

**Tipos en BD existente:** En algunas BD `fecha_deposito` y `fecha_informe` pueden ser `date` en lugar de `timestamp`/`varchar`; SQLAlchemy suele manejarlo. No afecta coherencia lógica.

---

## 3. conversacion_cobranza

| Columna                    | Modelo (ConversacionCobranza) | SQL (CREATE + ALTER) |
|----------------------------|-------------------------------|------------------------|
| id                         | Integer, PK                   | SERIAL PRIMARY KEY     |
| telefono                   | String(30), NOT NULL, unique   | VARCHAR(30) NOT NULL UNIQUE |
| cedula                     | String(20), nullable          | VARCHAR(20)            |
| nombre_cliente              | String(100), nullable         | VARCHAR(100) (ALTER)   |
| estado                     | String(30), NOT NULL         | VARCHAR(30) NOT NULL   |
| intento_foto                | Integer, NOT NULL            | INTEGER NOT NULL       |
| intento_confirmacion        | Integer, NOT NULL            | INTEGER NOT NULL (ALTER) |
| observacion                | Text, nullable               | TEXT (ALTER)            |
| pagos_informe_id_pendiente  | Integer, FK, nullable        | INTEGER REFERENCES (ALTER) |
| created_at                 | DateTime, NOT NULL           | TIMESTAMP NOT NULL     |
| updated_at                 | DateTime, NOT NULL           | TIMESTAMP NOT NULL     |

---

## Verificación

- **Modelos:** `app/models/pagos_whatsapp.py`, `pagos_informe.py`, `conversacion_cobranza.py`.
- **Script actualizar BD:** `sql/EJECUTAR_EN_DBEAVER.sql` (idempotente).
- **Script comprobar:** `sql/COMPROBAR_BD.sql` (6 consultas: tablas, columnas por tabla, resumen, columnas clave pagos_informes).

La estructura es coherente entre modelos Python, scripts SQL y consultas de comprobación.
