# Fix: formatdate import wrong place -> move to top, remove from try
path = "app/core/email.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
# Remove the misplaced import
c = c.replace("\nfrom email.utils import formatdate\n        from email import encoders", "\n        from email import encoders")
# Add at top after "from typing import ..."
c = c.replace("from typing import List, Optional, Tuple\n\n# Timeout", "from typing import List, Optional, Tuple\nfrom email.utils import formatdate\n\n# Timeout")
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Fixed")
