"""
Schema de validación para Hotel en MongoDB.
Define la estructura y validación de documentos de hoteles.
"""
from datetime import datetime
from typing import Dict, List, Optional
from bson import ObjectId
import uuid


class HotelSchema:
    """
    Esquema de validación y estructura para documentos de hoteles en MongoDB.
    """
    
    # Tipos de propiedad permitidos
    PROPERTY_TYPES = ["hotel", "apartment", "house", "room", "resort", "hostel"]
    
    # Tipos de habitación permitidos
    ROOM_TYPES = ["single", "double", "twin", "suite", "deluxe", "family", "studio"]
    
    @staticmethod
    def get_default_document() -> Dict:
        """
        Retorna la estructura base de un documento de hotel.
        """
        return {
            "owner_id": None,  # UUID del propietario
            "name": "",
            "description": "",
            "property_type": "hotel",
            "address": {
                "street": "",
                "city": "",
                "state": "",
                "country": "",
                "postal_code": "",
                "coordinates": {
                    "lat": 0.0,
                    "lng": 0.0
                }
            },
            "rooms": [],
            "amenities": [],
            "services": [],
            "images": [],
            "rating": 0.0,
            "total_reviews": 0,
            "policies": {
                "check_in_time": "15:00",
                "check_out_time": "12:00",
                "cancellation_policy": "Cancelación gratuita hasta 24 horas antes",
                "pet_policy": "No se aceptan mascotas"
            },
            "contact": {
                "phone": "",
                "email": "",
                "website": ""
            },
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    
    @staticmethod
    def get_room_structure() -> Dict:
        """
        Retorna la estructura base de una habitación.
        """
        return {
            "room_id": str(uuid.uuid4()),
            "name": "",
            "description": "",
            "type": "double",
            "capacity": 2,
            "price_per_night": 0.0,
            "available": True,
            "amenities": [],
            "images": []
        }
    
    @staticmethod
    def validate_property_type(property_type: str) -> bool:
        """
        Valida que el tipo de propiedad sea válido.
        """
        return property_type in HotelSchema.PROPERTY_TYPES
    
    @staticmethod
    def validate_room_type(room_type: str) -> bool:
        """
        Valida que el tipo de habitación sea válido.
        """
        return room_type in HotelSchema.ROOM_TYPES
    
    @staticmethod
    def create_indexes(collection):
        """
        Crea índices en la colección de hoteles para optimizar búsquedas.
        """
        # Índice para búsqueda por propietario
        collection.create_index("owner_id")
        
        # Índice para búsqueda por ubicación
        collection.create_index([("address.city", 1), ("address.country", 1)])
        
        # Índice geoespacial para búsquedas por coordenadas
        collection.create_index([("address.coordinates", "2dsphere")])
        
        # Índice para búsqueda por tipo de propiedad
        collection.create_index("property_type")
        
        # Índice para búsqueda por estado activo
        collection.create_index("is_active")
        
        # Índice de texto para búsqueda por nombre y descripción
        collection.create_index([
            ("name", "text"),
            ("description", "text"),
            ("address.city", "text"),
            ("address.country", "text")
        ])
