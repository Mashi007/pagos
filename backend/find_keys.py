with open(r'C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\app\main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines, 1):
        if 'app.include_router' in line or '@app.on_event' in line or 'if __name__' in line:
            print(f'{i}: {line.rstrip()}')
