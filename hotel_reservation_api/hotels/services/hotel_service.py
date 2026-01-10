"""
Servicio para la gestión de hoteles en MongoDB.
Contiene toda la lógica de negocio y operaciones de base de datos.
"""
from datetime import datetime
from typing import Dict, List, Optional
from bson import ObjectId
from bson.errors import InvalidId
from app.mongodb import mongo_db
from hotels.schemas.hotel_schema import HotelSchema
import uuid


class HotelService:
    """
    Servicio para operaciones CRUD de hoteles en MongoDB.
    """
    
    def __init__(self):
        self.collection = mongo_db.db['hotels']
        # Asegurar que los índices estén creados
        HotelSchema.create_indexes(self.collection)
    
    def create_hotel(self, hotel_data: Dict, owner_id: str) -> Dict:
        """
        Crea un nuevo hotel en MongoDB.
        
        Args:
            hotel_data: Datos del hotel
            owner_id: UUID del propietario
            
        Returns:
            Hotel creado con su ID
        """
        # Obtener documento base y actualizarlo con los datos
        hotel_document = HotelSchema.get_default_document()
        hotel_document.update(hotel_data)
        hotel_document['owner_id'] = str(owner_id)
        hotel_document['created_at'] = datetime.utcnow()
        hotel_document['updated_at'] = datetime.utcnow()
        
        # Insertar en MongoDB
        result = self.collection.insert_one(hotel_document)
        hotel_document['_id'] = str(result.inserted_id)
        
        return hotel_document
    
    def get_hotel_by_id(self, hotel_id: str) -> Optional[Dict]:
        """
        Obtiene un hotel por su ID.
        
        Args:
            hotel_id: ID del hotel
            
        Returns:
            Documento del hotel o None si no existe
        """
        try:
            object_id = ObjectId(hotel_id)
            hotel = self.collection.find_one({"_id": object_id})
            
            if hotel:
                hotel['_id'] = str(hotel['_id'])
                # Calcular precio mínimo si tiene habitaciones
                if hotel.get('rooms'):
                    prices = [room.get('price_per_night', 0) for room in hotel['rooms']]
                    hotel['min_price'] = min(prices) if prices else 0
            
            return hotel
        except InvalidId:
            return None
    
    def list_hotels(self, filters: Optional[Dict] = None, 
                   skip: int = 0, limit: int = 20) -> List[Dict]:
        """
        Lista hoteles con filtros opcionales y paginación.
        
        Args:
            filters: Filtros de búsqueda (city, country, property_type, etc.)
            skip: Número de documentos a saltar (paginación)
            limit: Límite de documentos a retornar
            
        Returns:
            Lista de hoteles
        """
        query = filters or {}
        
        # Por defecto, solo mostrar hoteles activos
        if 'is_active' not in query:
            query['is_active'] = True
        
        hotels = list(
            self.collection.find(query)
            .sort('created_at', -1)
            .skip(skip)
            .limit(limit)
        )
        
        # Convertir ObjectId a string y calcular precio mínimo
        for hotel in hotels:
            hotel['_id'] = str(hotel['_id'])
            if hotel.get('rooms'):
                prices = [room.get('price_per_night', 0) for room in hotel['rooms']]
                hotel['min_price'] = min(prices) if prices else 0
        
        return hotels
    
    def count_hotels(self, filters: Optional[Dict] = None) -> int:
        """
        Cuenta el número de hoteles que coinciden con los filtros.
        
        Args:
            filters: Filtros de búsqueda
            
        Returns:
            Número de hoteles
        """
        query = filters or {}
        if 'is_active' not in query:
            query['is_active'] = True
        
        return self.collection.count_documents(query)
    
    def update_hotel(self, hotel_id: str, update_data: Dict, owner_id: str) -> Optional[Dict]:
        """
        Actualiza un hotel existente.
        
        Args:
            hotel_id: ID del hotel
            update_data: Datos a actualizar
            owner_id: UUID del propietario (para validación)
            
        Returns:
            Hotel actualizado o None si no existe o no es el propietario
        """
        try:
            object_id = ObjectId(hotel_id)
            
            # Verificar que el hotel exista y pertenezca al propietario
            existing_hotel = self.collection.find_one({
                "_id": object_id,
                "owner_id": str(owner_id)
            })
            
            if not existing_hotel:
                return None
            
            # Actualizar fecha de modificación
            update_data['updated_at'] = datetime.utcnow()
            
            # Actualizar documento
            result = self.collection.update_one(
                {"_id": object_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                return self.get_hotel_by_id(hotel_id)
            
            return existing_hotel
            
        except InvalidId:
            return None
    
    def delete_hotel(self, hotel_id: str, owner_id: str, soft: bool = True) -> bool:
        """
        Elimina un hotel (soft delete por defecto).
        
        Args:
            hotel_id: ID del hotel
            owner_id: UUID del propietario (para validación)
            soft: Si True, solo marca como inactivo; si False, elimina permanentemente
            
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        try:
            object_id = ObjectId(hotel_id)
            
            # Verificar que el hotel exista y pertenezca al propietario
            existing_hotel = self.collection.find_one({
                "_id": object_id,
                "owner_id": str(owner_id)
            })
            
            if not existing_hotel:
                return False
            
            if soft:
                # Soft delete: marcar como inactivo
                result = self.collection.update_one(
                    {"_id": object_id},
                    {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
                )
                return result.modified_count > 0
            else:
                # Hard delete: eliminar permanentemente
                result = self.collection.delete_one({"_id": object_id})
                return result.deleted_count > 0
                
        except InvalidId:
            return False
    
    def get_hotels_by_owner(self, owner_id: str, skip: int = 0, limit: int = 20) -> List[Dict]:
        """
        Obtiene todos los hoteles de un propietario específico.
        
        Args:
            owner_id: UUID del propietario
            skip: Número de documentos a saltar
            limit: Límite de documentos
            
        Returns:
            Lista de hoteles del propietario
        """
        return self.list_hotels(
            filters={"owner_id": str(owner_id)},
            skip=skip,
            limit=limit
        )
    
    def add_room(self, hotel_id: str, room_data: Dict, owner_id: str) -> Optional[Dict]:
        """
        Agrega una habitación a un hotel.
        
        Args:
            hotel_id: ID del hotel
            room_data: Datos de la habitación
            owner_id: UUID del propietario
            
        Returns:
            Hotel actualizado o None si falla
        """
        try:
            object_id = ObjectId(hotel_id)
            
            # Verificar que el hotel exista y pertenezca al propietario
            existing_hotel = self.collection.find_one({
                "_id": object_id,
                "owner_id": str(owner_id)
            })
            
            if not existing_hotel:
                return None
            
            # Crear estructura de habitación con ID único
            room = HotelSchema.get_room_structure()
            room.update(room_data)
            room['room_id'] = str(uuid.uuid4())
            
            # Agregar habitación al array
            result = self.collection.update_one(
                {"_id": object_id},
                {
                    "$push": {"rooms": room},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            if result.modified_count > 0:
                return self.get_hotel_by_id(hotel_id)
            
            return None
            
        except InvalidId:
            return None
    
    def update_room(self, hotel_id: str, room_id: str, 
                   room_data: Dict, owner_id: str) -> Optional[Dict]:
        """
        Actualiza una habitación específica de un hotel.
        
        Args:
            hotel_id: ID del hotel
            room_id: ID de la habitación
            room_data: Datos actualizados de la habitación
            owner_id: UUID del propietario
            
        Returns:
            Hotel actualizado o None si falla
        """
        try:
            object_id = ObjectId(hotel_id)
            
            # Verificar que el hotel exista y pertenezca al propietario
            existing_hotel = self.collection.find_one({
                "_id": object_id,
                "owner_id": str(owner_id)
            })
            
            if not existing_hotel:
                return None
            
            # Preparar actualización de campos específicos de la habitación
            update_fields = {}
            for key, value in room_data.items():
                update_fields[f"rooms.$.{key}"] = value
            
            update_fields["updated_at"] = datetime.utcnow()
            
            # Actualizar habitación específica
            result = self.collection.update_one(
                {
                    "_id": object_id,
                    "rooms.room_id": room_id
                },
                {"$set": update_fields}
            )
            
            if result.modified_count > 0:
                return self.get_hotel_by_id(hotel_id)
            
            return None
            
        except InvalidId:
            return None
    
    def delete_room(self, hotel_id: str, room_id: str, owner_id: str) -> Optional[Dict]:
        """
        Elimina una habitación de un hotel.
        
        Args:
            hotel_id: ID del hotel
            room_id: ID de la habitación
            owner_id: UUID del propietario
            
        Returns:
            Hotel actualizado o None si falla
        """
        try:
            object_id = ObjectId(hotel_id)
            
            # Verificar que el hotel exista y pertenezca al propietario
            existing_hotel = self.collection.find_one({
                "_id": object_id,
                "owner_id": str(owner_id)
            })
            
            if not existing_hotel:
                return None
            
            # Eliminar habitación del array
            result = self.collection.update_one(
                {"_id": object_id},
                {
                    "$pull": {"rooms": {"room_id": room_id}},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            if result.modified_count > 0:
                return self.get_hotel_by_id(hotel_id)
            
            return None
            
        except InvalidId:
            return None
    
    def search_hotels(self, search_text: str, skip: int = 0, limit: int = 20) -> List[Dict]:
        """
        Búsqueda de texto completo en hoteles.
        
        Args:
            search_text: Texto a buscar
            skip: Número de documentos a saltar
            limit: Límite de documentos
            
        Returns:
            Lista de hoteles que coinciden con la búsqueda
        """
        hotels = list(
            self.collection.find(
                {
                    "$text": {"$search": search_text},
                    "is_active": True
                }
            )
            .sort('created_at', -1)
            .skip(skip)
            .limit(limit)
        )
        
        # Convertir ObjectId a string y calcular precio mínimo
        for hotel in hotels:
            hotel['_id'] = str(hotel['_id'])
            if hotel.get('rooms'):
                prices = [room.get('price_per_night', 0) for room in hotel['rooms']]
                hotel['min_price'] = min(prices) if prices else 0
        
        return hotels
