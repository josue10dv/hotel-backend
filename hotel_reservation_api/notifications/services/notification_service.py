"""
Servicio de notificaciones.
Maneja la lógica de negocio para crear, leer y gestionar notificaciones.
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
from bson import ObjectId
from app.mongodb import get_notifications_collection
from notifications.schemas import NotificationSchema


class NotificationService:
    """Servicio para gestión de notificaciones."""
    
    def __init__(self):
        self.collection = get_notifications_collection()
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Crea índices en la colección si no existen."""
        try:
            existing_indexes = [idx['name'] for idx in self.collection.list_indexes()]
            
            for fields, options in NotificationSchema.get_indexes():
                index_name = options.get('name')
                if index_name not in existing_indexes:
                    self.collection.create_index(fields, **options)
        except Exception:
            pass  # Silently fail if indexes can't be created
    
    def create_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Crea una nueva notificación.
        
        Args:
            user_id: UUID del usuario receptor
            notification_type: Tipo de notificación
            title: Título de la notificación
            message: Mensaje de la notificación
            data: Datos adicionales (opcional)
            
        Returns:
            Documento de notificación creado
        """
        notification_doc = NotificationSchema.create_notification_document(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data
        )
        
        result = self.collection.insert_one(notification_doc)
        notification_doc['_id'] = result.inserted_id
        
        return notification_doc
    
    def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Obtiene las notificaciones de un usuario.
        
        Args:
            user_id: UUID del usuario
            unread_only: Si True, solo retorna notificaciones no leídas
            skip: Número de notificaciones a saltar (paginación)
            limit: Número máximo de notificaciones a retornar
            
        Returns:
            Lista de notificaciones
        """
        query = {"user_id": str(user_id)}
        
        if unread_only:
            query["read"] = False
        
        notifications = list(
            self.collection.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        
        return notifications
    
    def count_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False
    ) -> int:
        """
        Cuenta las notificaciones de un usuario.
        
        Args:
            user_id: UUID del usuario
            unread_only: Si True, solo cuenta notificaciones no leídas
            
        Returns:
            Número de notificaciones
        """
        query = {"user_id": str(user_id)}
        
        if unread_only:
            query["read"] = False
        
        return self.collection.count_documents(query)
    
    def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """
        Marca una notificación como leída.
        
        Args:
            notification_id: ID de la notificación
            user_id: UUID del usuario (para verificar propiedad)
            
        Returns:
            True si se marcó como leída, False si no se encontró
        """
        try:
            object_id = ObjectId(notification_id)
        except Exception:
            return False
        
        result = self.collection.update_one(
            {
                "_id": object_id,
                "user_id": str(user_id),
                "read": False
            },
            {
                "$set": {
                    "read": True,
                    "read_at": datetime.utcnow()
                }
            }
        )
        
        return result.modified_count > 0
    
    def mark_all_as_read(self, user_id: str) -> int:
        """
        Marca todas las notificaciones de un usuario como leídas.
        
        Args:
            user_id: UUID del usuario
            
        Returns:
            Número de notificaciones marcadas como leídas
        """
        result = self.collection.update_many(
            {
                "user_id": str(user_id),
                "read": False
            },
            {
                "$set": {
                    "read": True,
                    "read_at": datetime.utcnow()
                }
            }
        )
        
        return result.modified_count
    
    def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """
        Elimina una notificación.
        
        Args:
            notification_id: ID de la notificación
            user_id: UUID del usuario (para verificar propiedad)
            
        Returns:
            True si se eliminó, False si no se encontró
        """
        try:
            object_id = ObjectId(notification_id)
        except Exception:
            return False
        
        result = self.collection.delete_one({
            "_id": object_id,
            "user_id": str(user_id)
        })
        
        return result.deleted_count > 0
    
    # Helper methods para crear notificaciones específicas
    
    def notify_reservation_confirmed(self, user_id: str, reservation_data: Dict) -> Dict:
        """Notifica que una reservación fue confirmada."""
        return self.create_notification(
            user_id=user_id,
            notification_type='reservation',
            title='Reservación Confirmada',
            message=f'Tu reservación en {reservation_data.get("hotel_name", "el hotel")} ha sido confirmada.',
            data=reservation_data
        )
    
    def notify_reservation_rejected(self, user_id: str, reservation_data: Dict) -> Dict:
        """Notifica que una reservación fue rechazada."""
        return self.create_notification(
            user_id=user_id,
            notification_type='reservation',
            title='Reservación Rechazada',
            message=f'Tu reservación en {reservation_data.get("hotel_name", "el hotel")} ha sido rechazada.',
            data=reservation_data
        )
    
    def notify_payment_successful(self, user_id: str, payment_data: Dict) -> Dict:
        """Notifica que un pago fue exitoso."""
        return self.create_notification(
            user_id=user_id,
            notification_type='payment',
            title='Pago Exitoso',
            message=f'Tu pago de ${payment_data.get("amount", 0)} ha sido procesado exitosamente.',
            data=payment_data
        )
    
    def notify_new_review(self, user_id: str, review_data: Dict) -> Dict:
        """Notifica al propietario sobre una nueva reseña."""
        return self.create_notification(
            user_id=user_id,
            notification_type='review',
            title='Nueva Reseña',
            message=f'Has recibido una nueva reseña en {review_data.get("hotel_name", "tu hotel")}.',
            data=review_data
        )
    
    def notify_review_response(self, user_id: str, review_data: Dict) -> Dict:
        """Notifica al huésped que el propietario respondió su reseña."""
        return self.create_notification(
            user_id=user_id,
            notification_type='review',
            title='Respuesta a tu Reseña',
            message=f'El propietario ha respondido tu reseña en {review_data.get("hotel_name", "el hotel")}.',
            data=review_data
        )
