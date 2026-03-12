# Replace mojibake " â€" " with " - " in Plantillas.tsx
path = "frontend/src/pages/Plantillas.tsx"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
# Bytes in file: 20 c3 a2 e2 82 ac e2 80 9d 20 = space â € " space
mojibake = chr(0x20) + chr(0xE2) + chr(0x20AC) + chr(0x201D) + chr(0x20)
c = c.replace(mojibake, " - ")
c = c.replace(chr(0x20) + chr(0xE2) + chr(0x20AC) + chr(0x201D), " - ")
with open(path, "w", encoding="utf-8", newline="") as f:
    f.write(c)
print("Mojibake fixed")
