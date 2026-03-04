-- Direct SQL test for FK validation
-- This helps identify if the FK constraint is causing the 500 error

-- 1. Check if test client exists
SELECT COUNT(*) as clientes_test FROM public.clientes WHERE cedula LIKE 'V15%';

-- 2. Check if test payment cedula exists in clientes
SELECT cedula FROM public.clientes WHERE cedula = 'V151800';

-- 3. If no result above, the FK violation is the cause
-- Insert a test client directly to verify
INSERT INTO public.clientes (cedula, nombres, apellidos, email, telefono, direccion, fecha_nacimiento, ocupacion, estado, usuario_registro)
VALUES ('VTEST001', 'Test', 'User', 'test@example.com', '+584161234567', 'Test Street', '1990-01-01', 'Testing', 'ACTIVO', 'admin@test.com')
ON CONFLICT (cedula) DO NOTHING;

-- 4. Verify client was inserted
SELECT id, cedula, nombres FROM public.clientes WHERE cedula = 'VTEST001';

-- 5. Try to insert a payment with VTEST001
-- This should work if FK is set up correctly
INSERT INTO public.pagos (cedula, monto_pagado, fecha_pago, numero_documento, estado, usuario_registro)
VALUES ('VTEST001', 1000.00, NOW(), 'DOC-TEST-001', 'PENDIENTE', 'admin@test.com');

-- 6. Check if payment was inserted
SELECT id, cedula, monto_pagado FROM public.pagos WHERE numero_documento = 'DOC-TEST-001';

-- 7. Try to insert with invalid cedula (should fail if FK is enforced)
INSERT INTO public.pagos (cedula, monto_pagado, fecha_pago, numero_documento, estado, usuario_registro)
VALUES ('VINVALID', 1000.00, NOW(), 'DOC-INVALID-001', 'PENDIENTE', 'admin@test.com');
-- ^ This should give FK violation error

-- 8. Clean up
DELETE FROM public.pagos WHERE numero_documento LIKE 'DOC-TEST%' OR numero_documento LIKE 'DOC-INVALID%';
DELETE FROM public.clientes WHERE cedula = 'VTEST001';
