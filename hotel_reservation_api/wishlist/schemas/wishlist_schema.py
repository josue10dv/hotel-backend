"""
Schema de validación para Wishlist en MongoDB.
Define la estructura y validación de documentos de wishlist.
"""
from datetime import datetime
from typing import Dict, List
from bson import ObjectId


class WishlistSchema:
    """
    Esquema de validación y estructura para documentos de wishlist en MongoDB.
    
    Cada usuario tiene una única wishlist que contiene múltiples hoteles.
    """
    
    @staticmethod
    def get_default_document() -> Dict:
        """
        Retorna la estructura base de un documento de wishlist.
        
        Returns:
            Dict: Estructura del documento
        """
        return {
            "user_id": None,  # UUID del usuario (string)
            "hotels": [],  # Lista de ObjectId de hoteles
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    
    @staticmethod
    def get_validation_schema() -> Dict:
        """
        Retorna el esquema de validación de MongoDB.
        
        Returns:
            Dict: Esquema de validación JSON Schema
        """
        return {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["user_id", "hotels", "created_at", "updated_at"],
                "properties": {
                    "user_id": {
                        "bsonType": "string",
                        "description": "UUID del usuario propietario de la wishlist"
                    },
                    "hotels": {
                        "bsonType": "array",
                        "description": "Lista de ObjectIds de hoteles en la wishlist",
                        "items": {
                            "bsonType": "objectId"
                        }
                    },
                    "created_at": {
                        "bsonType": "date",
                        "description": "Fecha de creación de la wishlist"
                    },
                    "updated_at": {
                        "bsonType": "date",
                        "description": "Fecha de última actualización"
                    }
                }
            }
        }
    
    @staticmethod
    def create_indexes(collection):
        """
        Crea los índices necesarios para la colección de wishlist.
        
        Args:
            collection: Colección de MongoDB
        """
        # Índice único por user_id (cada usuario tiene una sola wishlist)
        collection.create_index("user_id", unique=True, name="idx_user_id")
        
        # Índice para búsquedas en el array de hoteles
        collection.create_index("hotels", name="idx_hotels")
        
        # Índice compuesto para verificar si un hotel está en la wishlist de un usuario
        collection.create_index(
            [("user_id", 1), ("hotels", 1)],
            name="idx_user_hotels"
        )
        
        print("✅ Índices de wishlist creados exitosamente")
    
    @staticmethod
    def validate_document(document: Dict) -> bool:
        """
        Valida que un documento tenga la estructura correcta.
        
        Args:
            document: Documento a validar
            
        Returns:
            bool: True si es válido
            
        Raises:
            ValueError: Si el documento no es válido
        """
        required_fields = ["user_id", "hotels", "created_at", "updated_at"]
        
        for field in required_fields:
            if field not in document:
                raise ValueError(f"Campo requerido faltante: {field}")
        
        if not isinstance(document["hotels"], list):
            raise ValueError("El campo 'hotels' debe ser una lista")
        
        # Validar que todos los elementos de hotels sean ObjectId
        for hotel_id in document["hotels"]:
            if not isinstance(hotel_id, ObjectId):
                raise ValueError(f"ID de hotel inválido: {hotel_id}")
        
        return True
