"""
Schema de validación para Reservaciones en MongoDB.
Define la estructura y validación de documentos de reservaciones.
"""
from datetime import datetime
from typing import Dict, List, Optional
from bson import ObjectId
import uuid


class ReservationSchema:
    """
    Esquema de validación y estructura para documentos de reservaciones en MongoDB.
    """
    
    # Estados de reservación permitidos
    STATUS_CHOICES = ["pending", "confirmed", "cancelled", "completed", "rejected"]
    
    # Estados de pago permitidos
    PAYMENT_STATUS_CHOICES = ["pending", "paid", "refunded", "failed"]
    
    @staticmethod
    def get_default_document() -> Dict:
        """
        Retorna la estructura base de un documento de reservación.
        """
        return {
            "reservation_id": str(uuid.uuid4()),  # ID único de la reservación
            "hotel_id": None,  # ObjectId del hotel
            "room_id": None,  # ID de la habitación dentro del hotel
            "guest_id": None,  # UUID del huésped
            "owner_id": None,  # UUID del propietario del hotel
            
            # Información de fechas
            "check_in": None,  # datetime
            "check_out": None,  # datetime
            "nights": 0,  # Número de noches calculado
            
            # Información de huéspedes
            "number_of_guests": 1,
            "guest_details": {
                "name": "",
                "email": "",
                "phone": "",
                "special_requests": ""
            },
            
            # Información de precios
            "price_per_night": 0.0,
            "total_price": 0.0,
            "currency": "USD",
            
            # Estado de la reservación
            "status": "pending",
            "payment_status": "pending",
            
            # Información adicional
            "cancellation_reason": None,
            "special_requests": "",
            
            # Metadatos
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "cancelled_at": None,
            "confirmed_at": None,
        }
    
    @staticmethod
    def get_validation_schema() -> Dict:
        """
        Retorna el schema de validación de MongoDB para reservaciones.
        """
        return {
            "$jsonSchema": {
                "bsonType": "object",
                "required": [
                    "reservation_id",
                    "hotel_id",
                    "room_id",
                    "guest_id",
                    "owner_id",
                    "check_in",
                    "check_out",
                    "number_of_guests",
                    "status",
                    "created_at"
                ],
                "properties": {
                    "reservation_id": {
                        "bsonType": "string",
                        "description": "ID único de la reservación (UUID)"
                    },
                    "hotel_id": {
                        "bsonType": "objectId",
                        "description": "ID del hotel en MongoDB"
                    },
                    "room_id": {
                        "bsonType": "string",
                        "description": "ID de la habitación dentro del hotel"
                    },
                    "guest_id": {
                        "bsonType": "string",
                        "description": "UUID del usuario huésped"
                    },
                    "owner_id": {
                        "bsonType": "string",
                        "description": "UUID del propietario del hotel"
                    },
                    "check_in": {
                        "bsonType": "date",
                        "description": "Fecha de entrada"
                    },
                    "check_out": {
                        "bsonType": "date",
                        "description": "Fecha de salida"
                    },
                    "nights": {
                        "bsonType": "int",
                        "minimum": 1,
                        "description": "Número de noches"
                    },
                    "number_of_guests": {
                        "bsonType": "int",
                        "minimum": 1,
                        "description": "Número de huéspedes"
                    },
                    "guest_details": {
                        "bsonType": "object",
                        "properties": {
                            "name": {"bsonType": "string"},
                            "email": {"bsonType": "string"},
                            "phone": {"bsonType": "string"},
                            "special_requests": {"bsonType": "string"}
                        }
                    },
                    "price_per_night": {
                        "bsonType": "double",
                        "minimum": 0,
                        "description": "Precio por noche"
                    },
                    "total_price": {
                        "bsonType": "double",
                        "minimum": 0,
                        "description": "Precio total de la reservación"
                    },
                    "currency": {
                        "bsonType": "string",
                        "description": "Moneda del precio"
                    },
                    "status": {
                        "enum": ["pending", "confirmed", "cancelled", "completed", "rejected"],
                        "description": "Estado de la reservación"
                    },
                    "payment_status": {
                        "enum": ["pending", "paid", "refunded", "failed"],
                        "description": "Estado del pago"
                    },
                    "created_at": {
                        "bsonType": "date",
                        "description": "Fecha de creación"
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
        Crea índices para optimizar consultas de reservaciones.
        """
        # Índice para buscar por reservation_id
        collection.create_index("reservation_id", unique=True)
        
        # Índice para buscar reservaciones por hotel
        collection.create_index("hotel_id")
        
        # Índice para buscar reservaciones por huésped
        collection.create_index("guest_id")
        
        # Índice para buscar reservaciones por propietario
        collection.create_index("owner_id")
        
        # Índice compuesto para buscar por hotel y fechas
        collection.create_index([
            ("hotel_id", 1),
            ("room_id", 1),
            ("check_in", 1),
            ("check_out", 1)
        ])
        
        # Índice para buscar por estado
        collection.create_index("status")
        
        # Índice para ordenar por fecha de creación
        collection.create_index([("created_at", -1)])
