# Add GmailTemporal to pagos_gmail_sync.py
path = "app/models/pagos_gmail_sync.py"
import os
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(base, path)

with open(path, "r", encoding="utf-8") as f:
    c = f.read()

if "class GmailTemporal" in c:
    print("Model already has GmailTemporal")
    exit(0)

block = '''
class GmailTemporal(Base):
    """
    Tabla temporal para exportar a Excel. Cada procesamiento Gmail inserta aqui a continuacion.
    Al descargar el Excel se vacia esta tabla (TRUNCATE). No tiene FK a sync.
    """
    __tablename__ = "gmail_temporal"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    correo_origen = Column(String(255), nullable=False)
    asunto = Column(String(500), nullable=True)
    fecha_pago = Column(String(100), nullable=True)
    cedula = Column(String(50), nullable=True)
    monto = Column(String(100), nullable=True)
    numero_referencia = Column(String(200), nullable=True)
    drive_file_id = Column(String(100), nullable=True)
    drive_link = Column(String(500), nullable=True)
    drive_email_link = Column(String(500), nullable=True)
    sheet_name = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
'''

c = c.rstrip()
c = c + block + "\n"
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Added GmailTemporal")
