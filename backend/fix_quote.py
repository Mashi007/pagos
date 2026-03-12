path = r"app\api\v1\endpoints\notificaciones_tabs.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
# Fix extra quote: """"" -> """
c = c.replace('    """""', '    """')
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Fixed")
