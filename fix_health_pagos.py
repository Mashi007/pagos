# -*- coding: utf-8 -*-
path = 'backend/app/api/v1/endpoints/health.py'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()
old = """        CRITICAL_TABLES = [
            "clientes",
            "prestamos",
            "cuotas",
            "pagos_whatsapp",
            "tickets",
        ]"""
new = """        CRITICAL_TABLES = [
            "clientes",
            "prestamos",
            "cuotas",
            "pagos",
            "pagos_con_errores",
            "revisar_pagos",
            "cuota_pagos",
            "pagos_whatsapp",
            "tickets",
        ]"""
if old in c:
    c = c.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print('CRITICAL_TABLES updated')
else:
    print('old not found')

# table_counts in detailed
old2 = 'table_counts = ["clientes", "prestamos", "cuotas", "pagos_whatsapp", "tickets"]'
new2 = 'table_counts = ["clientes", "prestamos", "cuotas", "pagos", "pagos_con_errores", "pagos_whatsapp", "tickets"]'
if old2 in c:
    c = c.replace(old2, new2)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print('table_counts updated')
