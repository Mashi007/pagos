-- =============================================================================
-- Migración: FK auditoria.usuario_id debe apuntar a usuarios (no a users).
-- Error en producción: insert on "auditoria" violates foreign key constraint
-- "auditoria_usuario_id_fkey" - Key (usuario_id)=(2) is not present in "users".
-- La aplicación usa la tabla "usuarios" (modelo User); si la FK apunta a "users",
-- hay que reorientarla a "usuarios".
-- Ejecutar en la BD de producción (Render) una sola vez.
-- =============================================================================

-- Eliminar la FK que apunta a la tabla incorrecta (si existe)
ALTER TABLE auditoria
  DROP CONSTRAINT IF EXISTS auditoria_usuario_id_fkey;

-- Crear FK hacia la tabla que usa la app (usuarios)
ALTER TABLE auditoria
  ADD CONSTRAINT auditoria_usuario_id_fkey
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id);

-- Opcional: si en tu BD la tabla de usuarios se llama "users" y no "usuarios",
-- entonces en lugar de lo anterior haz que la FK apunte a users y asegúrate
-- de que exista al menos un usuario con el id que use el token (p. ej. id=2).
