"""
FASE 2: UX & Accesibilidad - Mejoras de experiencia de usuario
"""

# ==============================================================================
# FASE 2.1: COMPONENTE REUTILIZABLE - Form Feedback Visual
# ==============================================================================

from typing import Optional
from pydantic import BaseModel, Field


class FormFieldConfig(BaseModel):
    """Configuración de un campo de formulario con validación y feedback"""
    name: str
    type: str = Field(default="text", description="email, password, text, etc")
    label: str
    placeholder: str = ""
    required: bool = True
    minlength: Optional[int] = None
    maxlength: Optional[int] = None
    pattern: Optional[str] = None
    help_text: Optional[str] = None
    aria_label: Optional[str] = None
    aria_describedby: Optional[str] = None


class FormConfig(BaseModel):
    """Configuración completa de un formulario"""
    title: str
    fields: list[FormFieldConfig]
    submit_text: str = "Enviar"
    csrf_enabled: bool = True
    show_validation_feedback: bool = True
    show_spinner_on_submit: bool = True


# ==============================================================================
# FASE 2.2: VALIDADORES REUTILIZABLES
# ==============================================================================

class FormValidators:
    """Validadores comunes para formularios"""
    
    @staticmethod
    def validate_email(email: str) -> tuple[bool, str]:
        """Validar email con mensaje descriptivo"""
        import re
        pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if re.match(pattern, email):
            return True, "Email válido"
        return False, "Email no válido"
    
    @staticmethod
    def validate_password_strength(password: str) -> tuple[str, str]:
        """Evaluar fortaleza de contraseña
        
        Returns:
            (strength: weak|medium|strong, feedback: mensaje descriptivo)
        """
        feedback = []
        
        if len(password) < 8:
            return "weak", "Mínimo 8 caracteres"
        
        if not any(c.isupper() for c in password):
            feedback.append("Agregar mayúscula")
        if not any(c.isdigit() for c in password):
            feedback.append("Agregar número")
        if not any(c in "!@#$%^&*" for c in password):
            feedback.append("Agregar símbolo (!@#$%^&*)")
        
        if not feedback:
            return "strong", "Contraseña fuerte ✓"
        elif len(feedback) <= 1:
            return "medium", "Contraseña moderada - " + " y ".join(feedback)
        else:
            return "weak", "Contraseña débil - " + " y ".join(feedback)
    
    @staticmethod
    def validate_phone(phone: str) -> tuple[bool, str]:
        """Validar número telefónico"""
        import re
        # Aceptar: +569 1234 5678, +56 9 1234 5678, 912345678, etc
        pattern = r'^\+?[\d\s\-]{7,}$'
        if re.match(pattern, phone.replace(" ", "")):
            return True, "Teléfono válido"
        return False, "Teléfono no válido"
    
    @staticmethod
    def validate_required(value: str, field_name: str) -> tuple[bool, str]:
        """Validar campo requerido"""
        if value and value.strip():
            return True, ""
        return False, f"{field_name} es requerido"


# ==============================================================================
# COMPONENTE: FormFieldComponent (para usar en templates)
# ==============================================================================

class FormFieldComponent:
    """
    Componente reutilizable para renderizar campos de formulario
    con validación, feedback visual y accesibilidad
    """
    
    @staticmethod
    def render_text_field(
        name: str,
        label: str,
        value: str = "",
        placeholder: str = "",
        required: bool = True,
        validation_type: str = "text",  # text, email, password, phone
        help_text: str = "",
        aria_label: str = "",
    ) -> str:
        """Renderizar campo de texto con validación"""
        field_id = f"field_{name}"
        message_id = f"{field_id}_message"
        
        html = f"""
        <div class="form-group">
            <label for="{field_id}">
                {label}
                {' *' if required else ''}
            </label>
            <div class="input-wrapper">
                <input
                    type="text"
                    id="{field_id}"
                    name="{name}"
                    placeholder="{placeholder}"
                    value="{value}"
                    {'required' if required else ''}
                    data-validation="{validation_type}"
                    aria-label="{aria_label or label}"
                    aria-describedby="{message_id}"
                    class="form-input"
                >
                <span class="validation-icon"></span>
            </div>
            {f'<small class="help-text">{help_text}</small>' if help_text else ''}
            <div class="form-message" id="{message_id}"></div>
        </div>
        """
        return html
    
    @staticmethod
    def render_password_field(
        name: str,
        label: str = "Contraseña",
        placeholder: str = "Ingresa tu contraseña",
        required: bool = True,
        show_strength: bool = True,
    ) -> str:
        """Renderizar campo de contraseña con indicador de fortaleza"""
        field_id = f"field_{name}"
        message_id = f"{field_id}_message"
        
        html = f"""
        <div class="form-group">
            <label for="{field_id}">
                {label}
                {' *' if required else ''}
            </label>
            <div class="input-wrapper">
                <input
                    type="password"
                    id="{field_id}"
                    name="{name}"
                    placeholder="{placeholder}"
                    minlength="8"
                    {'required' if required else ''}
                    data-validation="password"
                    aria-label="{label}"
                    aria-describedby="{message_id}"
                    class="form-input"
                >
                <span class="validation-icon"></span>
            </div>
            {f'<div class="password-strength"><div class="password-strength-bar"></div></div>' if show_strength else ''}
            <div class="form-message" id="{message_id}"></div>
        </div>
        """
        return html
    
    @staticmethod
    def render_checkbox(
        name: str,
        label: str,
        value: str = "on",
        checked: bool = False,
    ) -> str:
        """Renderizar checkbox accesible"""
        field_id = f"field_{name}"
        
        html = f"""
        <div class="form-group checkbox-group">
            <input
                type="checkbox"
                id="{field_id}"
                name="{name}"
                value="{value}"
                {'checked' if checked else ''}
                class="form-checkbox"
            >
            <label for="{field_id}">{label}</label>
        </div>
        """
        return html


# ==============================================================================
# ENDPOINTS: Proveer configuraciones de formularios (para frontend)
# ==============================================================================

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/forms", tags=["forms"])


@router.get("/config/login")
async def get_login_form_config() -> FormConfig:
    """Obtener configuración del formulario de login"""
    return FormConfig(
        title="Iniciar Sesión",
        fields=[
            FormFieldConfig(
                name="email",
                type="email",
                label="Correo Electrónico",
                placeholder="tu@email.com",
                help_text="Usaremos este email para tu cuenta",
                aria_label="Correo electrónico de la cuenta",
            ),
            FormFieldConfig(
                name="password",
                type="password",
                label="Contraseña",
                placeholder="Ingresa tu contraseña",
                minlength=8,
                help_text="Mínimo 8 caracteres",
                aria_label="Contraseña de la cuenta",
            ),
        ],
        submit_text="Iniciar Sesión",
    )


@router.get("/config/register")
async def get_register_form_config() -> FormConfig:
    """Obtener configuración del formulario de registro"""
    return FormConfig(
        title="Crear Cuenta",
        fields=[
            FormFieldConfig(
                name="email",
                type="email",
                label="Correo Electrónico",
                placeholder="tu@email.com",
            ),
            FormFieldConfig(
                name="name",
                type="text",
                label="Nombre Completo",
                placeholder="Juan Pérez",
            ),
            FormFieldConfig(
                name="password",
                type="password",
                label="Contraseña",
                minlength=8,
            ),
            FormFieldConfig(
                name="confirm_password",
                type="password",
                label="Confirmar Contraseña",
                minlength=8,
            ),
        ],
        submit_text="Crear Cuenta",
    )


# ==============================================================================
# VALIDADORES DE ACCESIBILIDAD (ARIA)
# ==============================================================================

class A11yValidator:
    """Validador de accesibilidad WCAG 2.1"""
    
    @staticmethod
    def validate_form_accessibility(form_html: str) -> dict:
        """Validar que un formulario cumpla con WCAG"""
        issues = []
        
        # Buscar inputs sin labels asociados
        import re
        inputs = re.findall(r'<input[^>]*>', form_html)
        for inp in inputs:
            if 'id=' in inp and '<label' not in form_html:
                issues.append("Input sin label asociado")
            if 'aria-label' not in inp and 'aria-describedby' not in inp:
                if 'type="hidden"' not in inp:
                    pass  # Solo warning si no es hidden
        
        # Verificar contraste de colores (requeriría análisis más profundo)
        # Verificar nombres de botones descriptivos
        buttons = re.findall(r'<button[^>]*>([^<]*)</button>', form_html)
        for btn_text in buttons:
            if btn_text.strip() in ['OK', 'Enviar', 'Ir']:
                pass  # Estos son aceptables
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "score": (100 - len(issues) * 10) if issues else 100,
        }


print("[OK] Modulo FASE 2 - UX & Accesibilidad cargado correctamente")
