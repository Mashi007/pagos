with open(r'C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\app\main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    # Mostrar contexto alrededor de app.include_router
    print('=== app.include_router (linea 116) ===')
    for i in range(114, 120):
        print(f'{i+1}: {lines[i].rstrip()}')
    
    print('\n=== @app.on_event startup (linea 207) ===')
    for i in range(206, 215):
        print(f'{i+1}: {lines[i].rstrip()}')
    
    print('\n=== @app.on_event shutdown (linea 277) ===')
    for i in range(276, 285):
        print(f'{i+1}: {lines[i].rstrip()}')
