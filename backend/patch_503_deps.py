# -*- coding: utf-8 -*-
"""Add 503 on DB OperationalError in deps.get_current_user and get_current_user_optional."""
import os
path = os.path.join(os.path.dirname(__file__), "app", "core", "deps.py")
with open(path, "r", encoding="utf-8", errors="replace") as f:
    c = f.read()

# Add import
if "from sqlalchemy.exc import OperationalError" not in c:
    c = c.replace(
        "from sqlalchemy.orm import Session\n",
        "from sqlalchemy.exc import OperationalError\nfrom sqlalchemy.orm import Session\n",
    )

# get_current_user: wrap db.query in try/except
old1 = """    email = sub if "@" in sub else f"{sub}@admin.local"
    u = db.query(User).filter(User.email == email).first()
    if u and u.is_active:
        return user_to_response(u)
    return _fake_user_response(email)


def get_current_user_optional"""

new1 = """    email = sub if "@" in sub else f"{sub}@admin.local"
    try:
        u = db.query(User).filter(User.email == email).first()
    except OperationalError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio no disponible. Reintente en unos segundos.",
        )
    if u and u.is_active:
        return user_to_response(u)
    return _fake_user_response(email)


def get_current_user_optional"""

if old1 in c:
    c = c.replace(old1, new1)
    print("deps: get_current_user patched")
else:
    print("deps: get_current_user block not found")

# get_current_user_optional: same
old2 = """    email = sub if "@" in sub else f"{sub}@admin.local"
    u = db.query(User).filter(User.email == email).first()
    if u and u.is_active:
        return user_to_response(u)
    return _fake_user_response(email)
"""
new2 = """    email = sub if "@" in sub else f"{sub}@admin.local"
    try:
        u = db.query(User).filter(User.email == email).first()
    except OperationalError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio no disponible. Reintente en unos segundos.",
        )
    if u and u.is_active:
        return user_to_response(u)
    return _fake_user_response(email)
"""
if old2 in c:
    c = c.replace(old2, new2)
    print("deps: get_current_user_optional patched")
else:
    print("deps: get_current_user_optional block not found")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("deps.py OK")
