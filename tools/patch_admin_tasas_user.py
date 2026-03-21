from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    uu = ROOT / "backend" / "app" / "core" / "user_utils.py"
    t = uu.read_text(encoding="utf-8", errors="replace")
    if "def user_is_administrator" not in t:
        add = """

def user_is_administrator(user: UserResponse) -> bool:
    \"\"\"True si el usuario tiene rol administrador (respuesta de get_current_user).\"\"\"
    return (user.rol or \"\").strip().lower() == \"administrador\"
"""
        uu.write_text(t.rstrip() + add + "\n", encoding="utf-8")
    print("user_utils ok")

    p = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "admin_tasas_cambio.py"
    t = p.read_text(encoding="utf-8", errors="replace")
    t = t.replace(
        "from app.core.deps import get_current_user",
        "from app.core.deps import get_current_user\n"
        "from app.core.user_utils import user_is_administrator\n"
        "from app.schemas.auth import UserResponse",
    )
    t = t.replace(
        "current_user: dict = Depends(get_current_user)",
        "current_user: UserResponse = Depends(get_current_user)",
    )
    t = t.replace(
        'if not current_user.get("is_admin"):',
        "if not user_is_administrator(current_user):",
    )
    old_g = """    usuario_email = current_user.get(\"email\") if isinstance(current_user, dict) else getattr(current_user, \"email\", None)
    usuario_id = current_user.get(\"id\") if isinstance(current_user, dict) else getattr(current_user, \"id\", None)"""
    new_g = """    usuario_email = current_user.email
    usuario_id = current_user.id"""
    if old_g in t:
        t = t.replace(old_g, new_g)
    p.write_text(t, encoding="utf-8")
    print("admin_tasas_cambio ok")

    v = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "tasa_cambio_validacion.py"
    t = v.read_text(encoding="utf-8", errors="replace")
    if "user_is_administrator" not in t:
        t = t.replace(
            "from app.core.deps import get_current_user",
            "from app.core.deps import get_current_user\n"
            "from app.core.user_utils import user_is_administrator\n"
            "from app.schemas.auth import UserResponse",
        )
    t = t.replace(
        "current_user: dict = Depends(get_current_user)",
        "current_user: UserResponse = Depends(get_current_user)",
    )
    t = t.replace(
        'if not current_user.get("is_admin"):',
        "if not user_is_administrator(current_user):",
    )
    v.write_text(t, encoding="utf-8")
    print("tasa_cambio_validacion ok")


if __name__ == "__main__":
    main()
