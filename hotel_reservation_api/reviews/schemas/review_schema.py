"""
Schema de validación para Review en MongoDB.
Define la estructura y validación de documentos de reseñas.
"""
from datetime import datetime
from typing import Dict


class ReviewSchema:
    """
    Esquema de validación y estructura para documentos de reseñas en MongoDB.
    
    Implementa Clean Architecture separando la definición del modelo de datos
    de su persistencia, permitiendo validaciones consistentes y reutilizables.
    """
    
    # Calificaciones mínimas y máximas permitidas
    MIN_RATING = 1
    MAX_RATING = 5
    
    # Categorías de calificación para desglose detallado
    RATING_CATEGORIES = [
        "cleanliness",      # Limpieza
        "communication",    # Comunicación
        "check_in",        # Check-in
        "accuracy",        # Precisión de la descripción
        "location",        # Ubicación
        "value",           # Relación calidad-precio
    ]
    
    # Estados de la reseña
    STATUS_PENDING = "pending"      # Pendiente de moderación
    STATUS_APPROVED = "approved"    # Aprobada y visible
    STATUS_REJECTED = "rejected"    # Rechazada por moderación
    STATUS_REPORTED = "reported"    # Reportada por usuario
    
    STATUSES = [STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_REPORTED]
    
    @staticmethod
    def get_default_document() -> Dict:
        """
        Retorna la estructura base de un documento de reseña.
        
        Siguiendo DRY, esta función centraliza la estructura del documento
        evitando duplicación en diferentes partes del código.
        
        Returns:
            Dict: Estructura base del documento de reseña
        """
        return {
            "hotel_id": None,           # ObjectId del hotel
            "user_id": None,            # UUID del usuario que publica
            "reservation_id": None,     # ObjectId de la reserva (opcional)
            "rating": 0,                # Calificación general (1-5)
            "rating_breakdown": {       # Desglose de calificaciones
                "cleanliness": 0,
                "communication": 0,
                "check_in": 0,
                "accuracy": 0,
                "location": 0,
                "value": 0,
            },
            "title": "",                # Título de la reseña
            "comment": "",              # Comentario detallado
            "pros": [],                 # Lista de aspectos positivos
            "cons": [],                 # Lista de aspectos negativos
            "images": [],               # URLs de imágenes adjuntas
            "response": None,           # Respuesta del propietario
            "status": ReviewSchema.STATUS_PENDING,  # Estado de moderación
            "helpful_count": 0,         # Número de "útil"
            "unhelpful_count": 0,       # Número de "no útil"
            "helpful_users": [],        # UUIDs de usuarios que marcaron útil
            "reported_by": [],          # UUIDs de usuarios que reportaron
            "report_reason": None,      # Razón del reporte
            "verified_stay": False,     # Si se verificó que el usuario se hospedó
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    
    @staticmethod
    def get_response_structure() -> Dict:
        """
        Retorna la estructura para la respuesta del propietario.
        
        Returns:
            Dict: Estructura de respuesta del propietario
        """
        return {
            "owner_id": None,          # UUID del propietario
            "comment": "",             # Comentario de respuesta
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    
    @staticmethod
    def validate_rating(rating: float) -> bool:
        """
        Valida que una calificación esté en el rango permitido.
        
        Args:
            rating: Calificación a validar
            
        Returns:
            bool: True si es válida, False en caso contrario
        """
        return ReviewSchema.MIN_RATING <= rating <= ReviewSchema.MAX_RATING
    
    @staticmethod
    def validate_rating_breakdown(breakdown: Dict) -> bool:
        """
        Valida que todas las categorías de calificación sean válidas.
        
        Args:
            breakdown: Diccionario con calificaciones por categoría
            
        Returns:
            bool: True si todas son válidas, False en caso contrario
        """
        if not isinstance(breakdown, dict):
            return False
        
        for category in ReviewSchema.RATING_CATEGORIES:
            rating = breakdown.get(category, 0)
            if not ReviewSchema.validate_rating(rating):
                return False
        
        return True
    
    @staticmethod
    def calculate_average_rating(breakdown: Dict) -> float:
        """
        Calcula el promedio de todas las categorías de calificación.
        
        Implementa lógica de negocio centralizada (DRY) para cálculo de rating.
        
        Args:
            breakdown: Diccionario con calificaciones por categoría
            
        Returns:
            float: Promedio de calificaciones redondeado a 2 decimales
        """
        if not breakdown:
            return 0.0
        
        ratings = [
            breakdown.get(category, 0)
            for category in ReviewSchema.RATING_CATEGORIES
        ]
        
        valid_ratings = [r for r in ratings if r > 0]
        if not valid_ratings:
            return 0.0
        
        return round(sum(valid_ratings) / len(valid_ratings), 2)
    
    @staticmethod
    def create_indexes(collection):
        """
        Crea índices en la colección de MongoDB para optimizar búsquedas.
        
        Implementa optimización de queries siguiendo mejores prácticas.
        
        Args:
            collection: Colección de MongoDB
        """
        # Índice para búsquedas por hotel (más común)
        collection.create_index([("hotel_id", 1), ("created_at", -1)])
        
        # Índice para búsquedas por usuario
        collection.create_index([("user_id", 1), ("created_at", -1)])
        
        # Índice para reseñas aprobadas y ordenadas por rating
        collection.create_index([
            ("hotel_id", 1),
            ("status", 1),
            ("rating", -1)
        ])
        
        # Índice para búsquedas por reserva
        collection.create_index("reservation_id")
        
        # Índice compuesto para estadísticas del hotel
        collection.create_index([
            ("hotel_id", 1),
            ("status", 1),
            ("verified_stay", 1)
        ])
    
    @staticmethod
    def get_validation_schema() -> Dict:
        """
        Retorna el schema de validación de MongoDB.
        
        Define reglas de validación a nivel de base de datos para
        garantizar integridad de datos.
        
        Returns:
            Dict: Schema de validación para MongoDB
        """
        return {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["hotel_id", "user_id", "rating", "status", "created_at"],
                "properties": {
                    "hotel_id": {
                        "bsonType": "objectId",
                        "description": "ID del hotel debe ser un ObjectId válido"
                    },
                    "user_id": {
                        "bsonType": "string",
                        "description": "UUID del usuario"
                    },
                    "reservation_id": {
                        "bsonType": ["objectId", "null"],
                        "description": "ID de reserva opcional"
                    },
                    "rating": {
                        "bsonType": "double",
                        "minimum": ReviewSchema.MIN_RATING,
                        "maximum": ReviewSchema.MAX_RATING,
                        "description": "Calificación general entre 1 y 5"
                    },
                    "rating_breakdown": {
                        "bsonType": "object",
                        "description": "Desglose de calificaciones por categoría"
                    },
                    "title": {
                        "bsonType": "string",
                        "maxLength": 200,
                        "description": "Título de la reseña"
                    },
                    "comment": {
                        "bsonType": "string",
                        "maxLength": 2000,
                        "description": "Comentario detallado"
                    },
                    "status": {
                        "enum": ReviewSchema.STATUSES,
                        "description": "Estado de moderación"
                    },
                    "verified_stay": {
                        "bsonType": "bool",
                        "description": "Si se verificó la estadía"
                    },
                    "created_at": {
                        "bsonType": "date",
                        "description": "Fecha de creación"
                    },
                    "updated_at": {
                        "bsonType": "date",
                        "description": "Fecha de actualización"
                    }
                }
            }
        }
