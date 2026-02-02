"""
Servicio para la gestión de reseñas en MongoDB.
Contiene toda la lógica de negocio y operaciones de base de datos.

Implementa Clean Architecture separando la lógica de negocio
de la capa de presentación (views) y persistencia (MongoDB).
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from bson import ObjectId
from bson.errors import InvalidId
from app.mongodb import mongo_db
from reviews.schemas.review_schema import ReviewSchema


class ReviewService:
    """
    Servicio para operaciones CRUD de reseñas en MongoDB.
    
    Aplica principios SOLID:
    - Single Responsibility: Solo maneja operaciones de reseñas
    - Open/Closed: Extensible sin modificar código existente
    - Dependency Inversion: Depende de abstracciones (schemas)
    """
    
    def __init__(self):
        """Inicializa el servicio y asegura índices de MongoDB."""
        self.collection = mongo_db.db['reviews']
        self.hotels_collection = mongo_db.db['hotels']
        
        # Crear índices para optimización de queries (DRY)
        ReviewSchema.create_indexes(self.collection)
    
    def create_review(self, review_data: Dict, user_id: str) -> Dict:
        """
        Crea una nueva reseña en MongoDB.
        
        Args:
            review_data: Datos de la reseña validados
            user_id: UUID del usuario que crea la reseña
            
        Returns:
            Dict: Reseña creada con su ID
            
        Raises:
            ValueError: Si el hotel no existe o datos inválidos
        """
        # Validar que el hotel exista
        hotel_id = review_data.get('hotel_id')
        if not self._validate_object_id(hotel_id):
            raise ValueError("ID de hotel inválido")
        
        hotel = self.hotels_collection.find_one({'_id': ObjectId(hotel_id)})
        if not hotel:
            raise ValueError("Hotel no encontrado")
        
        # Verificar que el usuario no haya reseñado ya este hotel
        existing_review = self.collection.find_one({
            'hotel_id': ObjectId(hotel_id),
            'user_id': user_id
        })
        
        if existing_review:
            raise ValueError(
                "Ya has publicado una reseña para este hotel. "
                "Puedes editarla en lugar de crear una nueva."
            )
        
        # Obtener documento base y actualizarlo (DRY)
        review_document = ReviewSchema.get_default_document()
        
        # Convertir hotel_id a ObjectId
        review_document['hotel_id'] = ObjectId(hotel_id)
        review_document['user_id'] = str(user_id)
        
        # Actualizar con datos proporcionados
        review_document.update({
            'rating': review_data.get('rating', 0),
            'rating_breakdown': review_data.get('rating_breakdown', {}),
            'title': review_data.get('title', ''),
            'comment': review_data.get('comment', ''),
            'pros': review_data.get('pros', []),
            'cons': review_data.get('cons', []),
            'images': review_data.get('images', []),
        })
        
        # Convertir reservation_id si existe
        reservation_id = review_data.get('reservation_id')
        if reservation_id and self._validate_object_id(reservation_id):
            review_document['reservation_id'] = ObjectId(reservation_id)
            # Si tiene reserva verificada, marcar como estadía verificada
            review_document['verified_stay'] = True
        
        # Insertar en MongoDB
        result = self.collection.insert_one(review_document)
        review_document['_id'] = str(result.inserted_id)
        
        # Actualizar estadísticas del hotel de forma asíncrona
        self._update_hotel_rating(hotel_id)
        
        # Convertir ObjectIds a strings para respuesta
        return self._prepare_review_for_response(review_document)
    
    def get_review_by_id(self, review_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """
        Obtiene una reseña por su ID.
        
        Args:
            review_id: ID de la reseña
            user_id: Usuario actual (para marcar si encontró útil)
            
        Returns:
            Dict: Reseña encontrada o None
        """
        if not self._validate_object_id(review_id):
            return None
        
        review = self.collection.find_one({'_id': ObjectId(review_id)})
        if not review:
            return None
        
        prepared_review = self._prepare_review_for_response(review)
        
        # Agregar flag si el usuario encontró útil esta reseña
        if user_id and 'helpful_users' in review:
            prepared_review['user_found_helpful'] = str(user_id) in review.get('helpful_users', [])
        
        return prepared_review
    
    def get_reviews_by_hotel(
        self,
        hotel_id: str,
        page: int = 1,
        limit: int = 10,
        status: str = ReviewSchema.STATUS_APPROVED,
        sort_by: str = 'recent'
    ) -> Tuple[List[Dict], int]:
        """
        Obtiene reseñas de un hotel con paginación.
        
        Args:
            hotel_id: ID del hotel
            page: Número de página (inicia en 1)
            limit: Cantidad de resultados por página
            status: Estado de las reseñas a filtrar
            sort_by: Criterio de ordenamiento ('recent', 'rating_high', 'rating_low', 'helpful')
            
        Returns:
            Tuple[List[Dict], int]: Lista de reseñas y total de resultados
        """
        if not self._validate_object_id(hotel_id):
            return [], 0
        
        # Construir query
        query = {
            'hotel_id': ObjectId(hotel_id),
            'status': status
        }
        
        # Determinar ordenamiento
        sort_criteria = self._get_sort_criteria(sort_by)
        
        # Calcular skip para paginación
        skip = (page - 1) * limit
        
        # Ejecutar queries en paralelo (optimización)
        cursor = self.collection.find(query).sort(sort_criteria).skip(skip).limit(limit)
        total = self.collection.count_documents(query)
        
        # Preparar respuestas
        reviews = [self._prepare_review_for_response(review) for review in cursor]
        
        return reviews, total
    
    def get_reviews_by_user(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 10
    ) -> Tuple[List[Dict], int]:
        """
        Obtiene todas las reseñas de un usuario.
        
        Args:
            user_id: UUID del usuario
            page: Número de página
            limit: Resultados por página
            
        Returns:
            Tuple[List[Dict], int]: Lista de reseñas y total
        """
        query = {'user_id': str(user_id)}
        skip = (page - 1) * limit
        
        cursor = self.collection.find(query).sort('created_at', -1).skip(skip).limit(limit)
        total = self.collection.count_documents(query)
        
        reviews = [self._prepare_review_for_response(review) for review in cursor]
        return reviews, total
    
    def update_review(self, review_id: str, update_data: Dict, user_id: str) -> Optional[Dict]:
        """
        Actualiza una reseña existente.
        
        Args:
            review_id: ID de la reseña
            update_data: Datos a actualizar
            user_id: ID del usuario (para verificar propiedad)
            
        Returns:
            Dict: Reseña actualizada o None
            
        Raises:
            ValueError: Si no tiene permiso o datos inválidos
        """
        if not self._validate_object_id(review_id):
            raise ValueError("ID de reseña inválido")
        
        # Verificar que la reseña exista y pertenezca al usuario
        review = self.collection.find_one({'_id': ObjectId(review_id)})
        if not review:
            raise ValueError("Reseña no encontrada")
        
        if review.get('user_id') != str(user_id):
            raise ValueError("No tienes permiso para editar esta reseña")
        
        # Preparar actualización
        update_doc = {'updated_at': datetime.utcnow()}
        
        # Campos actualizables
        updateable_fields = ['rating', 'rating_breakdown', 'title', 'comment', 'pros', 'cons', 'images']
        for field in updateable_fields:
            if field in update_data:
                update_doc[field] = update_data[field]
        
        # Actualizar en MongoDB
        result = self.collection.update_one(
            {'_id': ObjectId(review_id)},
            {'$set': update_doc}
        )
        
        if result.modified_count == 0:
            return None
        
        # Si se actualizó el rating, recalcular estadísticas del hotel
        if 'rating' in update_data or 'rating_breakdown' in update_data:
            hotel_id = str(review['hotel_id'])
            self._update_hotel_rating(hotel_id)
        
        # Obtener y retornar reseña actualizada
        updated_review = self.collection.find_one({'_id': ObjectId(review_id)})
        return self._prepare_review_for_response(updated_review)
    
    def delete_review(self, review_id: str, user_id: str, is_staff: bool = False) -> bool:
        """
        Elimina una reseña.
        
        Args:
            review_id: ID de la reseña
            user_id: ID del usuario
            is_staff: Si el usuario es staff (puede eliminar cualquier reseña)
            
        Returns:
            bool: True si se eliminó, False si no
            
        Raises:
            ValueError: Si no tiene permiso
        """
        if not self._validate_object_id(review_id):
            raise ValueError("ID de reseña inválido")
        
        review = self.collection.find_one({'_id': ObjectId(review_id)})
        if not review:
            raise ValueError("Reseña no encontrada")
        
        # Verificar permisos
        if not is_staff and review.get('user_id') != str(user_id):
            raise ValueError("No tienes permiso para eliminar esta reseña")
        
        # Guardar hotel_id antes de eliminar
        hotel_id = str(review['hotel_id'])
        
        # Eliminar
        result = self.collection.delete_one({'_id': ObjectId(review_id)})
        
        if result.deleted_count > 0:
            # Actualizar estadísticas del hotel
            self._update_hotel_rating(hotel_id)
            return True
        
        return False
    
    def add_owner_response(self, review_id: str, owner_id: str, response_text: str) -> Optional[Dict]:
        """
        Agrega la respuesta del propietario a una reseña.
        
        Args:
            review_id: ID de la reseña
            owner_id: UUID del propietario
            response_text: Texto de respuesta
            
        Returns:
            Dict: Reseña actualizada
            
        Raises:
            ValueError: Si no es el propietario del hotel
        """
        if not self._validate_object_id(review_id):
            raise ValueError("ID de reseña inválido")
        
        review = self.collection.find_one({'_id': ObjectId(review_id)})
        if not review:
            raise ValueError("Reseña no encontrada")
        
        # Verificar que el usuario sea el propietario del hotel
        hotel = self.hotels_collection.find_one({'_id': review['hotel_id']})
        if not hotel or hotel.get('owner_id') != str(owner_id):
            raise ValueError("Solo el propietario del hotel puede responder")
        
        # Crear estructura de respuesta
        response = ReviewSchema.get_response_structure()
        response.update({
            'owner_id': str(owner_id),
            'comment': response_text,
        })
        
        # Actualizar reseña
        self.collection.update_one(
            {'_id': ObjectId(review_id)},
            {
                '$set': {
                    'response': response,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        updated_review = self.collection.find_one({'_id': ObjectId(review_id)})
        return self._prepare_review_for_response(updated_review)
    
    def mark_helpful(self, review_id: str, user_id: str, helpful: bool) -> Optional[Dict]:
        """
        Marca una reseña como útil o no útil.
        
        Args:
            review_id: ID de la reseña
            user_id: UUID del usuario
            helpful: True para útil, False para no útil
            
        Returns:
            Dict: Reseña actualizada
        """
        if not self._validate_object_id(review_id):
            raise ValueError("ID de reseña inválido")
        
        review = self.collection.find_one({'_id': ObjectId(review_id)})
        if not review:
            raise ValueError("Reseña no encontrada")
        
        # No puede marcar su propia reseña
        if review.get('user_id') == str(user_id):
            raise ValueError("No puedes marcar tu propia reseña")
        
        helpful_users = review.get('helpful_users', [])
        user_str = str(user_id)
        
        # Determinar acción
        if helpful:
            # Agregar a útil si no está
            if user_str not in helpful_users:
                self.collection.update_one(
                    {'_id': ObjectId(review_id)},
                    {
                        '$addToSet': {'helpful_users': user_str},
                        '$inc': {'helpful_count': 1}
                    }
                )
        else:
            # Remover de útil si está
            if user_str in helpful_users:
                self.collection.update_one(
                    {'_id': ObjectId(review_id)},
                    {
                        '$pull': {'helpful_users': user_str},
                        '$inc': {'helpful_count': -1}
                    }
                )
        
        updated_review = self.collection.find_one({'_id': ObjectId(review_id)})
        return self._prepare_review_for_response(updated_review)
    
    def report_review(self, review_id: str, user_id: str, reason: str, details: str = "") -> bool:
        """
        Reporta una reseña como inapropiada.
        
        Args:
            review_id: ID de la reseña
            user_id: UUID del usuario que reporta
            reason: Motivo del reporte
            details: Detalles adicionales
            
        Returns:
            bool: True si se reportó exitosamente
        """
        if not self._validate_object_id(review_id):
            raise ValueError("ID de reseña inválido")
        
        review = self.collection.find_one({'_id': ObjectId(review_id)})
        if not review:
            raise ValueError("Reseña no encontrada")
        
        reported_by = review.get('reported_by', [])
        user_str = str(user_id)
        
        # Evitar reportes duplicados
        if user_str in reported_by:
            raise ValueError("Ya has reportado esta reseña")
        
        # Actualizar reseña
        result = self.collection.update_one(
            {'_id': ObjectId(review_id)},
            {
                '$addToSet': {'reported_by': user_str},
                '$set': {
                    'status': ReviewSchema.STATUS_REPORTED,
                    'report_reason': f"{reason}: {details}",
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        return result.modified_count > 0
    
    def get_review_stats(self, hotel_id: str) -> Dict:
        """
        Obtiene estadísticas agregadas de reseñas de un hotel.
        
        Args:
            hotel_id: ID del hotel
            
        Returns:
            Dict: Estadísticas de reseñas
        """
        if not self._validate_object_id(hotel_id):
            return self._get_empty_stats(hotel_id)
        
        # Pipeline de agregación para estadísticas eficientes
        pipeline = [
            {'$match': {
                'hotel_id': ObjectId(hotel_id),
                'status': ReviewSchema.STATUS_APPROVED
            }},
            {'$facet': {
                'general': [
                    {'$group': {
                        '_id': None,
                        'total': {'$sum': 1},
                        'avg_rating': {'$avg': '$rating'},
                        'verified_count': {
                            '$sum': {'$cond': ['$verified_stay', 1, 0]}
                        }
                    }}
                ],
                'distribution': [
                    {'$group': {
                        '_id': {'$round': '$rating'},
                        'count': {'$sum': 1}
                    }},
                    {'$sort': {'_id': -1}}
                ],
                'breakdown': [
                    {'$group': {
                        '_id': None,
                        'avg_cleanliness': {'$avg': '$rating_breakdown.cleanliness'},
                        'avg_communication': {'$avg': '$rating_breakdown.communication'},
                        'avg_check_in': {'$avg': '$rating_breakdown.check_in'},
                        'avg_accuracy': {'$avg': '$rating_breakdown.accuracy'},
                        'avg_location': {'$avg': '$rating_breakdown.location'},
                        'avg_value': {'$avg': '$rating_breakdown.value'},
                    }}
                ],
                'recent': [
                    {'$match': {
                        'created_at': {'$gte': datetime.utcnow() - timedelta(days=30)}
                    }},
                    {'$count': 'count'}
                ]
            }}
        ]
        
        result = list(self.collection.aggregate(pipeline))
        
        if not result or not result[0]['general']:
            return self._get_empty_stats(hotel_id)
        
        general = result[0]['general'][0]
        distribution = result[0]['distribution']
        breakdown = result[0]['breakdown'][0] if result[0]['breakdown'] else {}
        recent = result[0]['recent'][0]['count'] if result[0]['recent'] else 0
        
        # Construir distribución de ratings
        rating_dist = {str(i): 0 for i in range(1, 6)}
        for item in distribution:
            rating_dist[str(int(item['_id']))] = item['count']
        
        # Construir breakdown promedio
        avg_breakdown = {
            'cleanliness': round(breakdown.get('avg_cleanliness', 0), 2),
            'communication': round(breakdown.get('avg_communication', 0), 2),
            'check_in': round(breakdown.get('avg_check_in', 0), 2),
            'accuracy': round(breakdown.get('avg_accuracy', 0), 2),
            'location': round(breakdown.get('avg_location', 0), 2),
            'value': round(breakdown.get('avg_value', 0), 2),
        }
        
        return {
            'hotel_id': hotel_id,
            'total_reviews': general['total'],
            'average_rating': round(general['avg_rating'], 2),
            'rating_distribution': rating_dist,
            'average_breakdown': avg_breakdown,
            'verified_stays_count': general['verified_count'],
            'recent_reviews_count': recent,
        }
    
    # ========== Métodos Privados (Helper Methods) ==========
    
    def _validate_object_id(self, id_str: str) -> bool:
        """Valida si una cadena es un ObjectId válido."""
        if not id_str:
            return False
        try:
            ObjectId(id_str)
            return True
        except (InvalidId, TypeError):
            return False
    
    def _prepare_review_for_response(self, review: Dict) -> Dict:
        """
        Convierte ObjectIds a strings para respuestas API.
        Aplica DRY centralizando la transformación.
        """
        if not review:
            return {}
        
        review_copy = review.copy()
        
        # Convertir ObjectIds
        if '_id' in review_copy:
            review_copy['_id'] = str(review_copy['_id'])
        if 'hotel_id' in review_copy:
            review_copy['hotel_id'] = str(review_copy['hotel_id'])
        if 'reservation_id' in review_copy and review_copy['reservation_id']:
            review_copy['reservation_id'] = str(review_copy['reservation_id'])
        
        # Agregar flag si tiene respuesta
        review_copy['has_response'] = review_copy.get('response') is not None
        
        return review_copy
    
    def _get_sort_criteria(self, sort_by: str) -> List[Tuple[str, int]]:
        """
        Retorna criterios de ordenamiento según opción.
        
        Args:
            sort_by: Criterio de ordenamiento
            
        Returns:
            List: Lista de tuplas (campo, dirección)
        """
        sort_options = {
            'recent': [('created_at', -1)],
            'rating_high': [('rating', -1), ('created_at', -1)],
            'rating_low': [('rating', 1), ('created_at', -1)],
            'helpful': [('helpful_count', -1), ('created_at', -1)],
        }
        
        return sort_options.get(sort_by, [('created_at', -1)])
    
    def _update_hotel_rating(self, hotel_id: str) -> None:
        """
        Recalcula y actualiza el rating del hotel basado en sus reseñas.
        
        Args:
            hotel_id: ID del hotel
        """
        if not self._validate_object_id(hotel_id):
            return
        
        # Calcular estadísticas usando agregación
        pipeline = [
            {'$match': {
                'hotel_id': ObjectId(hotel_id),
                'status': ReviewSchema.STATUS_APPROVED
            }},
            {'$group': {
                '_id': None,
                'avg_rating': {'$avg': '$rating'},
                'total': {'$sum': 1}
            }}
        ]
        
        result = list(self.collection.aggregate(pipeline))
        
        if result:
            stats = result[0]
            avg_rating = round(stats['avg_rating'], 2)
            total_reviews = stats['total']
        else:
            avg_rating = 0.0
            total_reviews = 0
        
        # Actualizar hotel
        self.hotels_collection.update_one(
            {'_id': ObjectId(hotel_id)},
            {
                '$set': {
                    'rating': avg_rating,
                    'total_reviews': total_reviews,
                    'updated_at': datetime.utcnow()
                }
            }
        )
    
    def _get_empty_stats(self, hotel_id: str) -> Dict:
        """Retorna estructura de estadísticas vacía."""
        return {
            'hotel_id': hotel_id,
            'total_reviews': 0,
            'average_rating': 0.0,
            'rating_distribution': {str(i): 0 for i in range(1, 6)},
            'average_breakdown': {cat: 0.0 for cat in ReviewSchema.RATING_CATEGORIES},
            'verified_stays_count': 0,
            'recent_reviews_count': 0,
        }
