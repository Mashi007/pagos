"""
Mapeo de tipos de notificación a templates de Meta WhatsApp
"""

from typing import Dict, List, Optional

logger = __import__("logging").getLogger(__name__)


class WhatsAppTemplateMapper:
    """
    Mapea tipos de notificación del sistema a templates de Meta WhatsApp
    y extrae variables para los parámetros del template
    """

    # Mapeo de tipos de notificación a templates de Meta
    # Formato: tipo_notificacion -> nombre_template_meta
    TEMPLATE_MAP: Dict[str, str] = {
        "PAGO_5_DIAS_ANTES": "notificacion_pago_5_dias",
        "PAGO_3_DIAS_ANTES": "notificacion_pago_3_dias",
        "PAGO_1_DIA_ANTES": "notificacion_pago_1_dia",
        "PAGO_DIA_0": "notificacion_pago_dia_0",
        "MORA_1_DIA": "notificacion_mora_1_dia",
        "MORA_3_DIAS": "notificacion_mora_3_dias",
        "MORA_5_DIAS": "notificacion_mora_5_dias",
        "MORA_10_DIAS": "notificacion_mora_10_dias",
        "PREJUDICIAL": "notificacion_prejudicial",
    }

    @classmethod
    def get_template_name(cls, tipo_notificacion: str) -> Optional[str]:
        """
        Obtener nombre del template de Meta para un tipo de notificación
        
        Args:
            tipo_notificacion: Tipo de notificación (ej: "PAGO_DIA_0")
            
        Returns:
            Nombre del template de Meta o None si no hay mapeo
        """
        return cls.TEMPLATE_MAP.get(tipo_notificacion)

    @classmethod
    def extract_template_parameters(
        cls, 
        message: str, 
        variables: Dict[str, str],
        template_name: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Extraer parámetros del template desde el mensaje y variables
        
        Esta función intenta extraer los valores de las variables más comunes
        que se usan en los templates de notificaciones de pagos.
        
        Args:
            message: Mensaje completo (puede contener variables {{variable}})
            variables: Diccionario de variables disponibles
            template_name: Nombre del template (opcional, para lógica específica)
            
        Returns:
            Lista de parámetros para el template de Meta
            Formato: [{"text": "valor1"}, {"text": "valor2"}, ...]
        """
        parameters = []
        
        # Variables comunes en templates de notificaciones de pagos
        # Orden: nombre, monto, fecha_vencimiento, numero_cuota, credito_id
        common_vars = [
            "nombre",
            "monto",
            "fecha_vencimiento",
            "numero_cuota",
            "credito_id",
            "dias_atraso",
        ]
        
        # Extraer valores de variables comunes
        for var_name in common_vars:
            if var_name in variables:
                value = str(variables[var_name]).strip()
                if value:  # Solo agregar si tiene valor
                    parameters.append({"text": value})
        
        # Si no se encontraron variables, usar el mensaje completo como único parámetro
        if not parameters:
            logger.warning(
                f"⚠️ [TEMPLATE] No se encontraron variables para template '{template_name}', "
                f"usando mensaje completo como parámetro único"
            )
            # Limpiar variables del mensaje si están presentes
            clean_message = message
            for var_name, var_value in variables.items():
                clean_message = clean_message.replace(f"{{{{{var_name}}}}}", var_value)
            parameters = [{"text": clean_message}]
        
        return parameters

    @classmethod
    def should_use_template(cls, tipo_notificacion: str) -> bool:
        """
        Determinar si se debe usar template para un tipo de notificación
        
        Args:
            tipo_notificacion: Tipo de notificación
            
        Returns:
            True si hay template configurado, False si no
        """
        return tipo_notificacion in cls.TEMPLATE_MAP

    @classmethod
    def get_all_mapped_templates(cls) -> Dict[str, str]:
        """
        Obtener todos los templates mapeados
        
        Returns:
            Diccionario tipo_notificacion -> template_name
        """
        return cls.TEMPLATE_MAP.copy()

