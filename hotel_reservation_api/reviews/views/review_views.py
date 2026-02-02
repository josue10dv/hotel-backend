"""
Vistas para la gestión de reseñas.

Implementa endpoints REST usando ViewSets de Django REST Framework.
Aplica Clean Architecture manteniendo la lógica de negocio en el service layer.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from reviews.serializers import (
    ReviewSerializer,
    ReviewCreateSerializer,
    ReviewUpdateSerializer,
    ReviewListSerializer,
    ReviewStatsSerializer,
    OwnerResponseSerializer,
    MarkHelpfulSerializer,
    ReportReviewSerializer,
)
from reviews.services.review_service import ReviewService
from app.utilities import (
    created_response,
    success_response,
    validation_error_response,
    not_found_response,
)


class ReviewViewSet(viewsets.ViewSet):
    """
    ViewSet para operaciones CRUD de reseñas.
    
    Endpoints disponibles:
    - POST /api/reviews/                         → Crear reseña (autenticado)
    - GET /api/reviews/{id}/                     → Obtener detalle de reseña (público)
    - PUT /api/reviews/{id}/                     → Actualizar reseña completa (autor)
    - PATCH /api/reviews/{id}/                   → Actualizar reseña parcial (autor)
    - DELETE /api/reviews/{id}/                  → Eliminar reseña (autor/staff)
    - GET /api/reviews/hotel/{hotel_id}/         → Listar reseñas de un hotel (público)
    - GET /api/reviews/my-reviews/               → Mis reseñas (autenticado)
    - GET /api/reviews/stats/{hotel_id}/         → Estadísticas de reseñas de hotel (público)
    - POST /api/reviews/{id}/respond/            → Responder como propietario (owner)
    - POST /api/reviews/{id}/helpful/            → Marcar útil/no útil (autenticado)
    - POST /api/reviews/{id}/report/             → Reportar reseña (autenticado)
    
    Implementa principios SOLID:
    - Single Responsibility: Solo maneja la capa de presentación
    - Dependency Inversion: Depende del servicio (abstracción)
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.review_service = ReviewService()
    
    def get_permissions(self):
        """
        Configura permisos según la acción.
        
        - Público: Listar, detalle, estadísticas
        - Autenticado: Crear, actualizar, eliminar, responder, marcar útil, reportar
        """
        if self.action in ['list', 'retrieve', 'hotel_reviews', 'stats']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def create(self, request):
        """
        Crea una nueva reseña.
        
        POST /api/reviews/
        Body: {
            "hotel_id": "string",
            "rating_breakdown": {...},
            "comment": "string",
            "title": "string" (opcional),
            ...
        }
        """
        serializer = ReviewCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        try:
            review = self.review_service.create_review(
                review_data=serializer.validated_data,
                user_id=str(request.user.id)
            )
            
            # Serializar respuesta
            response_serializer = ReviewSerializer(review)
            
            return created_response(
                data=response_serializer.data,
                message="Reseña creada exitosamente. Está pendiente de aprobación."
            )
        
        except ValueError as e:
            return validation_error_response({'error': str(e)})
        except Exception as e:
            return Response(
                {'error': f'Error al crear la reseña: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, pk=None):
        """
        Obtiene el detalle de una reseña por ID.
        
        GET /api/reviews/{id}/
        """
        try:
            user_id = str(request.user.id) if request.user.is_authenticated else None
            review = self.review_service.get_review_by_id(pk, user_id=user_id)
            
            if not review:
                return not_found_response("Reseña no encontrada")
            
            serializer = ReviewSerializer(review)
            return success_response(data=serializer.data)
        
        except Exception as e:
            return Response(
                {'error': f'Error al obtener la reseña: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, pk=None):
        """
        Actualiza una reseña completa.
        
        PUT /api/reviews/{id}/
        """
        serializer = ReviewUpdateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        try:
            updated_review = self.review_service.update_review(
                review_id=pk,
                update_data=serializer.validated_data,
                user_id=str(request.user.id)
            )
            
            if not updated_review:
                return not_found_response("Reseña no encontrada o no se pudo actualizar")
            
            response_serializer = ReviewSerializer(updated_review)
            return success_response(
                data=response_serializer.data,
                message="Reseña actualizada exitosamente"
            )
        
        except ValueError as e:
            return validation_error_response({'error': str(e)})
        except Exception as e:
            return Response(
                {'error': f'Error al actualizar la reseña: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def partial_update(self, request, pk=None):
        """
        Actualiza parcialmente una reseña.
        
        PATCH /api/reviews/{id}/
        """
        serializer = ReviewUpdateSerializer(data=request.data, partial=True)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        try:
            updated_review = self.review_service.update_review(
                review_id=pk,
                update_data=serializer.validated_data,
                user_id=str(request.user.id)
            )
            
            if not updated_review:
                return not_found_response("Reseña no encontrada o no se pudo actualizar")
            
            response_serializer = ReviewSerializer(updated_review)
            return success_response(
                data=response_serializer.data,
                message="Reseña actualizada exitosamente"
            )
        
        except ValueError as e:
            return validation_error_response({'error': str(e)})
        except Exception as e:
            return Response(
                {'error': f'Error al actualizar la reseña: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, pk=None):
        """
        Elimina una reseña.
        
        DELETE /api/reviews/{id}/
        """
        try:
            deleted = self.review_service.delete_review(
                review_id=pk,
                user_id=str(request.user.id),
                is_staff=request.user.is_staff
            )
            
            if not deleted:
                return not_found_response("Reseña no encontrada")
            
            return success_response(
                message="Reseña eliminada exitosamente"
            )
        
        except ValueError as e:
            return validation_error_response({'error': str(e)})
        except Exception as e:
            return Response(
                {'error': f'Error al eliminar la reseña: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='hotel/(?P<hotel_id>[^/.]+)')
    def hotel_reviews(self, request, hotel_id=None):
        """
        Lista las reseñas de un hotel con paginación.
        
        GET /api/reviews/hotel/{hotel_id}/?page=1&limit=10&sort=recent
        
        Query params:
        - page: Número de página (default: 1)
        - limit: Resultados por página (default: 10, max: 50)
        - sort: recent | rating_high | rating_low | helpful (default: recent)
        - status: approved | pending | rejected (default: approved, solo staff ve otros)
        """
        # Extraer parámetros de paginación y ordenamiento
        page = int(request.query_params.get('page', 1))
        limit = min(int(request.query_params.get('limit', 10)), 50)
        sort_by = request.query_params.get('sort', 'recent')
        status_filter = request.query_params.get('status', 'approved')
        
        # Solo staff puede ver reseñas no aprobadas
        if status_filter != 'approved' and not request.user.is_staff:
            status_filter = 'approved'
        
        try:
            reviews, total = self.review_service.get_reviews_by_hotel(
                hotel_id=hotel_id,
                page=page,
                limit=limit,
                status=status_filter,
                sort_by=sort_by
            )
            
            # Serializar respuesta
            serializer = ReviewListSerializer(reviews, many=True)
            
            return success_response(
                data={
                    'reviews': serializer.data,
                    'pagination': {
                        'page': page,
                        'limit': limit,
                        'total': total,
                        'pages': (total + limit - 1) // limit
                    }
                }
            )
        
        except Exception as e:
            return Response(
                {'error': f'Error al obtener reseñas: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='my-reviews')
    def my_reviews(self, request):
        """
        Lista las reseñas del usuario autenticado.
        
        GET /api/reviews/my-reviews/?page=1&limit=10
        """
        page = int(request.query_params.get('page', 1))
        limit = min(int(request.query_params.get('limit', 10)), 50)
        
        try:
            reviews, total = self.review_service.get_reviews_by_user(
                user_id=str(request.user.id),
                page=page,
                limit=limit
            )
            
            serializer = ReviewSerializer(reviews, many=True)
            
            return success_response(
                data={
                    'reviews': serializer.data,
                    'pagination': {
                        'page': page,
                        'limit': limit,
                        'total': total,
                        'pages': (total + limit - 1) // limit
                    }
                }
            )
        
        except Exception as e:
            return Response(
                {'error': f'Error al obtener tus reseñas: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='stats/(?P<hotel_id>[^/.]+)')
    def stats(self, request, hotel_id=None):
        """
        Obtiene estadísticas de reseñas de un hotel.
        
        GET /api/reviews/stats/{hotel_id}/
        """
        try:
            stats = self.review_service.get_review_stats(hotel_id)
            serializer = ReviewStatsSerializer(stats)
            
            return success_response(data=serializer.data)
        
        except Exception as e:
            return Response(
                {'error': f'Error al obtener estadísticas: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='respond')
    def respond(self, request, pk=None):
        """
        Permite al propietario del hotel responder a una reseña.
        
        POST /api/reviews/{id}/respond/
        Body: {
            "comment": "string"
        }
        """
        serializer = OwnerResponseSerializer(data=request.data)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        try:
            updated_review = self.review_service.add_owner_response(
                review_id=pk,
                owner_id=str(request.user.id),
                response_text=serializer.validated_data['comment']
            )
            
            if not updated_review:
                return not_found_response("Reseña no encontrada")
            
            response_serializer = ReviewSerializer(updated_review)
            return success_response(
                data=response_serializer.data,
                message="Respuesta publicada exitosamente"
            )
        
        except ValueError as e:
            return validation_error_response({'error': str(e)})
        except Exception as e:
            return Response(
                {'error': f'Error al responder a la reseña: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='helpful')
    def helpful(self, request, pk=None):
        """
        Marca una reseña como útil o no útil.
        
        POST /api/reviews/{id}/helpful/
        Body: {
            "helpful": true  // true para útil, false para no útil
        }
        """
        serializer = MarkHelpfulSerializer(data=request.data)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        try:
            updated_review = self.review_service.mark_helpful(
                review_id=pk,
                user_id=str(request.user.id),
                helpful=serializer.validated_data['helpful']
            )
            
            if not updated_review:
                return not_found_response("Reseña no encontrada")
            
            response_serializer = ReviewSerializer(updated_review)
            return success_response(
                data=response_serializer.data,
                message="Marcado actualizado exitosamente"
            )
        
        except ValueError as e:
            return validation_error_response({'error': str(e)})
        except Exception as e:
            return Response(
                {'error': f'Error al marcar la reseña: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='report')
    def report(self, request, pk=None):
        """
        Reporta una reseña como inapropiada.
        
        POST /api/reviews/{id}/report/
        Body: {
            "reason": "spam|offensive|fake|irrelevant|other",
            "details": "string" (opcional)
        }
        """
        serializer = ReportReviewSerializer(data=request.data)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        try:
            reported = self.review_service.report_review(
                review_id=pk,
                user_id=str(request.user.id),
                reason=serializer.validated_data['reason'],
                details=serializer.validated_data.get('details', '')
            )
            
            if not reported:
                return not_found_response("Reseña no encontrada")
            
            return success_response(
                message="Reseña reportada exitosamente. Será revisada por moderadores."
            )
        
        except ValueError as e:
            return validation_error_response({'error': str(e)})
        except Exception as e:
            return Response(
                {'error': f'Error al reportar la reseña: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
