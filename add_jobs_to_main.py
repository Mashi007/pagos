#!/usr/bin/env python
# Script para agregar jobs a main.py

path = 'backend/app/main.py'

with open(path, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Buscar la posición del if __name__
insert_text = '''
# ============================================================================
# Background Jobs
# ============================================================================
from apscheduler.schedulers.background import BackgroundScheduler
from app.scripts.aplicar_pagos_pendientes_job import aplicar_pagos_pendientes

def iniciar_jobs():
    """Inicia jobs en background."""
    try:
        scheduler = BackgroundScheduler()
        # Job cada 5 minutos: aplicar pagos pendientes
        scheduler.add_job(
            aplicar_pagos_pendientes,
            'interval',
            minutes=5,
            id='aplicar_pagos_pendientes',
            max_instances=1
        )
        scheduler.start()
        logger.info("Background jobs iniciados: aplicar_pagos_pendientes cada 5 min")
    except Exception as e:
        logger.error(f"Error iniciando background jobs: {e}", exc_info=True)

# Iniciar jobs en startup
@app.on_event("startup")
async def startup_event():
    """Se ejecuta al iniciar la aplicación."""
    iniciar_jobs()


'''

# Insertar antes del if __name__
new_content = content.replace(
    'if __name__ == "__main__":',
    insert_text + 'if __name__ == "__main__":'
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Added background jobs to main.py")
