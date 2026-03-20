with open(r'C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\app\main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    print('=== on_startup completo (lineas 207-277) ===')
    for i in range(206, 277):
        print(f'{i+1}: {lines[i].rstrip()}')
