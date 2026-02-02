"""
Servicio para manejar la lógica de negocio de wishlist.
"""
from datetime import datetime
from typing import Dict, List, Optional
from bson import ObjectId
from app.mongodb import MongoDBConnection
from wishlist.schemas import WishlistSchema


class WishlistService:
    """
    Servicio para gestionar operaciones de wishlist en MongoDB.
    """
    
    def __init__(self):
        self.db = MongoDBConnection().db
        self.wishlist_collection = self.db.wishlist
        self.hotels_collection = self.db.hotels
        
        # Crear índices si no existen
        WishlistSchema.create_indexes(self.wishlist_collection)
    
    def get_or_create_wishlist(self, user_id: str) -> Dict:
        """
        Obtiene la wishlist del usuario o la crea si no existe.
        
        Args:
            user_id: UUID del usuario
            
        Returns:
            Dict: Documento de wishlist
        """
        # Buscar wishlist existente
        wishlist = self.wishlist_collection.find_one({"user_id": user_id})
        
        if wishlist:
            return wishlist
        
        # Crear nueva wishlist
        new_wishlist = WishlistSchema.get_default_document()
        new_wishlist["user_id"] = user_id
        
        result = self.wishlist_collection.insert_one(new_wishlist)
        new_wishlist["_id"] = result.inserted_id
        
        return new_wishlist
    
    def add_hotel(self, user_id: str, hotel_id: str) -> Dict:
        """
        Agrega un hotel a la wishlist del usuario.
        
        Args:
            user_id: UUID del usuario
            hotel_id: ObjectId del hotel
            
        Returns:
            Dict: Resultado de la operación
            
        Raises:
            ValueError: Si el hotel no existe o ya está en la wishlist
        """
        # Validar que el hotel existe
        hotel_object_id = ObjectId(hotel_id)
        hotel = self.hotels_collection.find_one({"_id": hotel_object_id})
        
        if not hotel:
            raise ValueError("El hotel no existe")
        
        # Obtener o crear wishlist
        wishlist = self.get_or_create_wishlist(user_id)
        
        # Verificar si el hotel ya está en la wishlist
        if hotel_object_id in wishlist.get("hotels", []):
            raise ValueError("El hotel ya está en tu wishlist")
        
        # Agregar hotel a la wishlist
        result = self.wishlist_collection.update_one(
            {"user_id": user_id},
            {
                "$addToSet": {"hotels": hotel_object_id},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return {
            "success": True,
            "message": "Hotel agregado a la wishlist",
            "hotel_id": hotel_id
        }
    
    def remove_hotel(self, user_id: str, hotel_id: str) -> Dict:
        """
        Elimina un hotel de la wishlist del usuario.
        
        Args:
            user_id: UUID del usuario
            hotel_id: ObjectId del hotel
            
        Returns:
            Dict: Resultado de la operación
            
        Raises:
            ValueError: Si el hotel no está en la wishlist
        """
        hotel_object_id = ObjectId(hotel_id)
        
        # Verificar que el hotel esté en la wishlist
        wishlist = self.wishlist_collection.find_one({
            "user_id": user_id,
            "hotels": hotel_object_id
        })
        
        if not wishlist:
            raise ValueError("El hotel no está en tu wishlist")
        
        # Eliminar hotel de la wishlist
        result = self.wishlist_collection.update_one(
            {"user_id": user_id},
            {
                "$pull": {"hotels": hotel_object_id},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return {
            "success": True,
            "message": "Hotel eliminado de la wishlist",
            "hotel_id": hotel_id
        }
    
    def get_wishlist_with_hotels(self, user_id: str) -> Dict:
        """
        Obtiene la wishlist del usuario con la información completa de los hoteles.
        
        Args:
            user_id: UUID del usuario
            
        Returns:
            Dict: Wishlist con datos de hoteles
        """
        # Obtener wishlist
        wishlist = self.get_or_create_wishlist(user_id)
        
        # Si no hay hoteles, retornar wishlist vacía
        hotel_ids = wishlist.get("hotels", [])
        if not hotel_ids:
            return {
                "user_id": user_id,
                "total_hotels": 0,
                "hotels": [],
                "created_at": wishlist.get("created_at"),
                "updated_at": wishlist.get("updated_at")
            }
        
        # Obtener información de los hoteles
        hotels = list(self.hotels_collection.find({"_id": {"$in": hotel_ids}}))
        
        # Convertir ObjectId a string y agregar fecha de adición
        hotels_data = []
        for hotel in hotels:
            hotel["id"] = str(hotel.pop("_id"))
            hotel["owner_id"] = str(hotel.get("owner_id"))
            
            # Calcular precio mínimo de las habitaciones
            rooms = hotel.get("rooms", [])
            if rooms:
                prices = [room.get("price_per_night", 0) for room in rooms]
                hotel["min_price"] = min(prices) if prices else None
            else:
                hotel["min_price"] = None
            
            # Agregar fecha de adición (usar updated_at de wishlist como aproximación)
            hotel["added_at"] = wishlist.get("updated_at")
            
            hotels_data.append(hotel)
        
        return {
            "user_id": user_id,
            "total_hotels": len(hotels_data),
            "hotels": hotels_data,
            "created_at": wishlist.get("created_at"),
            "updated_at": wishlist.get("updated_at")
        }
    
    def is_hotel_in_wishlist(self, user_id: str, hotel_id: str) -> bool:
        """
        Verifica si un hotel está en la wishlist del usuario.
        
        Args:
            user_id: UUID del usuario
            hotel_id: ObjectId del hotel
            
        Returns:
            bool: True si el hotel está en la wishlist
        """
        hotel_object_id = ObjectId(hotel_id)
        
        wishlist = self.wishlist_collection.find_one({
            "user_id": user_id,
            "hotels": hotel_object_id
        })
        
        return wishlist is not None
    
    def get_wishlist_count(self, user_id: str) -> int:
        """
        Obtiene el número de hoteles en la wishlist del usuario.
        
        Args:
            user_id: UUID del usuario
            
        Returns:
            int: Número de hoteles
        """
        wishlist = self.wishlist_collection.find_one({"user_id": user_id})
        
        if not wishlist:
            return 0
        
        return len(wishlist.get("hotels", []))
    
    def clear_wishlist(self, user_id: str) -> Dict:
        """
        Elimina todos los hoteles de la wishlist del usuario.
        
        Args:
            user_id: UUID del usuario
            
        Returns:
            Dict: Resultado de la operación
        """
        result = self.wishlist_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "hotels": [],
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "success": True,
            "message": "Wishlist limpiada exitosamente"
        }
