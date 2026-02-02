"""
Schema para notificaciones en MongoDB.
Define la estructura de documentos de notificaciones.
"""
from datetime import datetime
from typing import Dict, Any, List


class NotificationSchema:
    """
    Esquema de MongoDB para notificaciones.
    
    Estructura del documento:
    {
        "_id": ObjectId,
        "user_id": "UUID string del usuario receptor",
        "type": "reservation | payment | review | system",
        "title": "Título de la notificación",
        "message": "Mensaje de la notificación",
        "data": {
            // Datos adicionales específicos del tipo
            "reservation_id": "...",
            "hotel_id": "...",
            // etc
        },
        "read": false,
        "created_at": datetime,
        "read_at": datetime (opcional)
    }
    """
    
    NOTIFICATION_TYPES = ['reservation', 'payment', 'review', 'system']
    
    @staticmethod
    def validate_notification_type(notification_type: str) -> bool:
        """Valida que el tipo de notificación sea válido."""
        return notification_type in NotificationSchema.NOTIFICATION_TYPES
    
    @staticmethod
    def create_notification_document(
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Crea un documento de notificación válido.
        
        Args:
            user_id: UUID del usuario receptor
            notification_type: Tipo de notificación
            title: Título de la notificación
            message: Mensaje de la notificación
            data: Datos adicionales (opcional)
            
        Returns:
            Documento de notificación válido para MongoDB
        """
        if not NotificationSchema.validate_notification_type(notification_type):
            raise ValueError(
                f"Invalid notification type. Must be one of: {', '.join(NotificationSchema.NOTIFICATION_TYPES)}"
            )
        
        return {
            "user_id": str(user_id),
            "type": notification_type,
            "title": title,
            "message": message,
            "data": data or {},
            "read": False,
            "created_at": datetime.utcnow(),
            "read_at": None
        }
    
    @staticmethod
    def get_indexes() -> List[tuple]:
        """
        Define índices para la colección de notificaciones.
        
        Returns:
            Lista de tuplas (fields, options) para crear índices
        """
        return [
            ([("user_id", 1), ("read", 1), ("created_at", -1)], {"name": "user_notifications"}),
            ([("user_id", 1), ("type", 1)], {"name": "user_type_notifications"}),
            ([("created_at", -1)], {"name": "created_at_desc"}),
        ]
