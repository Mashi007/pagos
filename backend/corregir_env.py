"""
Script temporal para corregir el archivo .env
- Lee el archivo con la codificación correcta
- Codifica correctamente la DATABASE_URL
- Guarda el archivo en UTF-8
"""
from pathlib import Path
from urllib.parse import urlparse, urlunparse, quote_plus

# Leer el archivo .env
env_file = Path('.env')

# Intentar diferentes codificaciones
encodings = ['latin-1', 'windows-1252', 'cp1252', 'utf-8']
content = None
used_encoding = None

for enc in encodings:
    try:
        content_bytes = env_file.read_bytes()
        content = content_bytes.decode(enc)
        if 'DATABASE_URL' in content:
            used_encoding = enc
            print(f"OK: Archivo leido con codificacion: {enc}")
            break
    except Exception as e:
        continue

if not content:
    print("❌ No se pudo leer el archivo .env")
    exit(1)

# Procesar líneas
lines = content.split('\n')
new_lines = []

for line in lines:
    if line.strip().startswith('DATABASE_URL='):
        # Extraer la URL
        url = line.split('=', 1)[1].strip()
        
        # Parsear y codificar correctamente
        try:
            parsed = urlparse(url)
            
            if parsed.password:
                # Codificar username y password
                username_encoded = quote_plus(parsed.username, safe='') if parsed.username else ''
                password_encoded = quote_plus(parsed.password, safe='')
                
                # Reconstruir netloc
                netloc = f"{username_encoded}:{password_encoded}@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
                
                # Reconstruir URL
                parsed = parsed._replace(netloc=netloc)
                url = urlunparse(parsed)
                
                print("OK: DATABASE_URL codificada correctamente")
                print(f"   Username: {parsed.username if parsed.username else 'N/A'}")
                print(f"   Password: {'*' * len(parsed.password) if parsed.password else 'N/A'}")
        
        except Exception as e:
            print(f"⚠️ Error al procesar DATABASE_URL: {e}")
            print(f"   Usando URL original")
        
        new_lines.append(f'DATABASE_URL={url}')
    else:
        new_lines.append(line)

# Guardar en UTF-8
new_content = '\n'.join(new_lines)
env_file.write_text(new_content, encoding='utf-8')

print(f"\nOK: Archivo .env corregido y guardado en UTF-8")
print(f"   Ubicación: {env_file.absolute()}")

