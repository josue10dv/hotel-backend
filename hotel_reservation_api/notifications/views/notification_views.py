"""
Vistas para notificaciones.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from notifications.serializers import NotificationSerializer
from notifications.services import NotificationService
from app.utilities import (
    success_response,
    validation_error_response,
    parse_pagination_params,
)


class NotificationViewSet(viewsets.ViewSet):
    """
    ViewSet para gestión de notificaciones.
    
    Endpoints disponibles:
    - GET /api/notifications/               → Listar notificaciones del usuario
    - PATCH /api/notifications/{id}/read/   → Marcar notificación como leída
    - POST /api/notifications/read-all/     → Marcar todas como leídas
    - DELETE /api/notifications/{id}/       → Eliminar notificación
    """
    
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.notification_service = NotificationService()
    
    def list(self, request):
        """
        Lista las notificaciones del usuario autenticado.
        
        GET /api/notifications/
        
        Query Parameters:
            - unread_only: boolean (default: false)
            - page: integer
            - page_size: integer
        """
        # Parse parameters
        unread_only = request.query_params.get('unread_only', 'false').lower() == 'true'
        pagination = parse_pagination_params(request.query_params)
        
        # Get notifications
        notifications = self.notification_service.get_user_notifications(
            user_id=str(request.user.id),
            unread_only=unread_only,
            skip=pagination['skip'],
            limit=pagination['page_size']
        )
        
        # Count total and unread
        total_count = self.notification_service.count_user_notifications(
            user_id=str(request.user.id),
            unread_only=False
        )
        
        unread_count = self.notification_service.count_user_notifications(
            user_id=str(request.user.id),
            unread_only=True
        )
        
        # Serialize
        serializer = NotificationSerializer(notifications, many=True)
        
        return success_response(data={
            'count': total_count,
            'unread_count': unread_count,
            'page': pagination['page'],
            'page_size': pagination['page_size'],
            'total_pages': (total_count + pagination['page_size'] - 1) // pagination['page_size'],
            'results': serializer.data
        })
    
    @action(detail=True, methods=['patch'], url_path='read')
    def mark_as_read(self, request, pk=None):
        """
        Marca una notificación como leída.
        
        PATCH /api/notifications/{id}/read/
        """
        success = self.notification_service.mark_as_read(
            notification_id=pk,
            user_id=str(request.user.id)
        )
        
        if not success:
            return validation_error_response({
                'notification': ['Notification not found or already read']
            })
        
        return success_response(message='Notificación marcada como leída')
    
    @action(detail=False, methods=['post'], url_path='read-all')
    def mark_all_as_read(self, request):
        """
        Marca todas las notificaciones del usuario como leídas.
        
        POST /api/notifications/read-all/
        """
        count = self.notification_service.mark_all_as_read(
            user_id=str(request.user.id)
        )
        
        return success_response(
            message=f'{count} notificaciones marcadas como leídas',
            data={'count': count}
        )
    
    def destroy(self, request, pk=None):
        """
        Elimina una notificación.
        
        DELETE /api/notifications/{id}/
        """
        success = self.notification_service.delete_notification(
            notification_id=pk,
            user_id=str(request.user.id)
        )
        
        if not success:
            return validation_error_response({
                'notification': ['Notification not found']
            })
        
        return success_response(
            message='Notificación eliminada',
            status_code=status.HTTP_204_NO_CONTENT
        )
