"""
Servicio para la gestión de reservaciones en MongoDB.
Contiene toda la lógica de negocio y operaciones de base de datos.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.utils import timezone
from bson import ObjectId
from bson.errors import InvalidId
from app.mongodb import mongo_db
from reservations.schemas.reservation_schema import ReservationSchema
import uuid


class ReservationService:
    """
    Servicio para operaciones CRUD de reservaciones en MongoDB.
    """
    
    def __init__(self):
        self.collection = mongo_db.db['reservations']
        self.hotels_collection = mongo_db.db['hotels']
        # Asegurar que los índices estén creados
        ReservationSchema.create_indexes(self.collection)
    
    def create_reservation(self, reservation_data: Dict, guest_id: str) -> Dict:
        """
        Crea una nueva reservación en MongoDB.
        
        Args:
            reservation_data: Datos de la reservación
            guest_id: UUID del huésped
            
        Returns:
            Reservación creada con su ID
            
        Raises:
            ValueError: Si hay errores de validación
        """
        # Obtener información del hotel y habitación
        hotel = self._get_hotel(reservation_data['hotel_id'])
        if not hotel:
            raise ValueError("Hotel no encontrado")
        
        room = self._get_room(hotel, reservation_data['room_id'])
        if not room:
            raise ValueError("Habitación no encontrada")
        
        # Validar fechas
        check_in = reservation_data['check_in']
        check_out = reservation_data['check_out']
        self._validate_dates(check_in, check_out)
        
        # Validar disponibilidad
        if not self.check_availability(
            reservation_data['hotel_id'],
            reservation_data['room_id'],
            check_in,
            check_out
        ):
            raise ValueError("La habitación no está disponible en las fechas seleccionadas")
        
        # Validar capacidad
        if reservation_data.get('number_of_guests', 1) > room.get('capacity', 1):
            raise ValueError(f"La habitación tiene capacidad máxima de {room['capacity']} huéspedes")
        
        # Calcular noches y precio
        nights = (check_out - check_in).days
        price_per_night = room.get('price_per_night', 0.0)
        total_price = nights * price_per_night
        
        # Obtener documento base y actualizarlo
        reservation_document = ReservationSchema.get_default_document()
        reservation_document.update({
            'hotel_id': ObjectId(reservation_data['hotel_id']),
            'room_id': reservation_data['room_id'],
            'guest_id': str(guest_id),
            'owner_id': str(hotel['owner_id']),
            'check_in': check_in,
            'check_out': check_out,
            'nights': nights,
            'number_of_guests': reservation_data.get('number_of_guests', 1),
            'guest_details': reservation_data.get('guest_details', {}),
            'price_per_night': price_per_night,
            'total_price': total_price,
            'special_requests': reservation_data.get('special_requests', ''),
            'status': 'pending',
            'payment_status': 'pending',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        
        # Insertar en MongoDB
        result = self.collection.insert_one(reservation_document)
        reservation_document['_id'] = str(result.inserted_id)
        
        return self._format_reservation(reservation_document)

    def validate_and_compute_for_checkout(self, reservation_data: Dict) -> Dict:
        """
        Valida los datos de reservación y calcula total. No persiste nada.
        Usado por checkout: solo se guarda la reserva cuando el pago es exitoso.
        Returns:
            Dict con datos listos para crear la reserva (hotel_id, room_id, check_in, check_out,
            nights, total_price, price_per_night, number_of_guests, guest_details, etc.)
        Raises:
            ValueError: Si hotel/room no existen, fechas inválidas, no disponible o capacidad.
        """
        hotel = self._get_hotel(reservation_data['hotel_id'])
        if not hotel:
            raise ValueError("Hotel no encontrado")
        room = self._get_room(hotel, reservation_data['room_id'])
        if not room:
            raise ValueError("Habitación no encontrada")
        check_in = reservation_data['check_in']
        check_out = reservation_data['check_out']
        self._validate_dates(check_in, check_out)
        if not self.check_availability(
            reservation_data['hotel_id'],
            reservation_data['room_id'],
            check_in,
            check_out,
        ):
            raise ValueError("La habitación no está disponible en las fechas seleccionadas")
        if reservation_data.get('number_of_guests', 1) > room.get('capacity', 1):
            raise ValueError(f"La habitación tiene capacidad máxima de {room['capacity']} huéspedes")
        nights = (check_out - check_in).days
        price_per_night = room.get('price_per_night', 0.0)
        total_price = nights * price_per_night
        return {
            'hotel_id': reservation_data['hotel_id'],
            'room_id': reservation_data['room_id'],
            'check_in': check_in,
            'check_out': check_out,
            'nights': nights,
            'number_of_guests': reservation_data.get('number_of_guests', 1),
            'guest_details': reservation_data.get('guest_details', {}),
            'special_requests': reservation_data.get('special_requests', ''),
            'price_per_night': price_per_night,
            'total_price': total_price,
            'currency': reservation_data.get('currency', 'USD'),
            'owner_id': str(hotel['owner_id']),
        }

    def create_reservation_after_payment(
        self, computed_data: Dict, guest_id: str, reservation_id: str
    ) -> Dict:
        """
        Crea la reservación en MongoDB solo después de pago exitoso.
        payment_status se guarda como 'paid'.
        """
        from bson import ObjectId
        reservation_document = ReservationSchema.get_default_document()
        reservation_document.update({
            'reservation_id': reservation_id,
            'hotel_id': ObjectId(computed_data['hotel_id']),
            'room_id': computed_data['room_id'],
            'guest_id': str(guest_id),
            'owner_id': computed_data['owner_id'],
            'check_in': computed_data['check_in'],
            'check_out': computed_data['check_out'],
            'nights': computed_data['nights'],
            'number_of_guests': computed_data['number_of_guests'],
            'guest_details': computed_data.get('guest_details', {}),
            'price_per_night': computed_data['price_per_night'],
            'total_price': computed_data['total_price'],
            'currency': computed_data.get('currency', 'USD'),
            'special_requests': computed_data.get('special_requests', ''),
            'status': 'pending',
            'payment_status': 'paid',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        })
        result = self.collection.insert_one(reservation_document)
        reservation_document['_id'] = result.inserted_id
        return self._format_reservation(reservation_document)

    def get_reservation_by_id(self, reservation_id: str) -> Optional[Dict]:
        """
        Obtiene una reservación por su ID.
        
        Args:
            reservation_id: ID de la reservación (puede ser _id o reservation_id)
            
        Returns:
            Reservación encontrada o None
        """
        try:
            # Intentar buscar por ObjectId primero
            reservation = self.collection.find_one({'_id': ObjectId(reservation_id)})
            if not reservation:
                # Si no se encuentra, buscar por reservation_id (UUID)
                reservation = self.collection.find_one({'reservation_id': reservation_id})
            
            return self._format_reservation(reservation) if reservation else None
        except InvalidId:
            # Si no es un ObjectId válido, buscar por reservation_id
            reservation = self.collection.find_one({'reservation_id': reservation_id})
            return self._format_reservation(reservation) if reservation else None
    
    def get_reservations_by_guest(self, guest_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Obtiene todas las reservaciones de un huésped.
        
        Args:
            guest_id: UUID del huésped
            filters: Filtros adicionales (status, dates, etc.)
            
        Returns:
            Lista de reservaciones
        """
        query = {'guest_id': str(guest_id)}
        
        if filters:
            if 'status' in filters:
                query['status'] = filters['status']
            if 'from_date' in filters:
                query['check_in'] = {'$gte': filters['from_date']}
            if 'to_date' in filters:
                query['check_out'] = {'$lte': filters['to_date']}
        
        reservations = self.collection.find(query).sort('created_at', -1)
        return [self._format_reservation(r) for r in reservations]
    
    def get_reservations_by_owner(self, owner_id: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Obtiene todas las reservaciones de los hoteles de un propietario.
        
        Args:
            owner_id: UUID del propietario
            filters: Filtros adicionales (status, hotel_id, dates, etc.)
            
        Returns:
            Lista de reservaciones
        """
        query = {'owner_id': str(owner_id)}
        
        if filters:
            if 'status' in filters:
                query['status'] = filters['status']
            if 'hotel_id' in filters:
                query['hotel_id'] = ObjectId(filters['hotel_id'])
            if 'from_date' in filters:
                query['check_in'] = {'$gte': filters['from_date']}
            if 'to_date' in filters:
                query['check_out'] = {'$lte': filters['to_date']}
        
        reservations = self.collection.find(query).sort('created_at', -1)
        return [self._format_reservation(r) for r in reservations]
    
    def update_reservation_status(self, reservation_id: str, new_status: str, 
                                  user_id: str, user_type: str,
                                  cancellation_reason: Optional[str] = None) -> Dict:
        """
        Actualiza el estado de una reservación.
        
        Args:
            reservation_id: ID de la reservación
            new_status: Nuevo estado (confirmed, cancelled, completed, rejected)
            user_id: UUID del usuario que realiza la acción
            user_type: Tipo de usuario (guest o owner)
            cancellation_reason: Razón de cancelación (opcional)
            
        Returns:
            Reservación actualizada
            
        Raises:
            ValueError: Si hay errores de validación
        """
        reservation = self.collection.find_one({'_id': ObjectId(reservation_id)})
        if not reservation:
            reservation = self.collection.find_one({'reservation_id': reservation_id})
        
        if not reservation:
            raise ValueError("Reservación no encontrada")
        
        # Validar permisos según el tipo de usuario
        if user_type == 'guest':
            # Solo el huésped puede cancelar su propia reservación
            if str(reservation['guest_id']) != str(user_id):
                raise ValueError("No tienes permiso para modificar esta reservación")
            if new_status not in ['cancelled']:
                raise ValueError("Los huéspedes solo pueden cancelar reservaciones")
        elif user_type == 'owner':
            # Solo el propietario puede confirmar/rechazar
            if str(reservation['owner_id']) != str(user_id):
                raise ValueError("No tienes permiso para modificar esta reservación")
            if new_status not in ['confirmed', 'rejected', 'completed']:
                raise ValueError("Los propietarios solo pueden confirmar, rechazar o completar reservaciones")
        
        # Validar transiciones de estado
        current_status = reservation['status']
        self._validate_status_transition(current_status, new_status)
        
        # Actualizar el documento
        update_data = {
            'status': new_status,
            'updated_at': datetime.utcnow()
        }
        
        if new_status == 'cancelled':
            update_data['cancelled_at'] = datetime.utcnow()
            if cancellation_reason:
                update_data['cancellation_reason'] = cancellation_reason
        elif new_status == 'confirmed':
            update_data['confirmed_at'] = datetime.utcnow()
        
        self.collection.update_one(
            {'_id': reservation['_id']},
            {'$set': update_data}
        )
        
        # Obtener y retornar la reservación actualizada
        updated_reservation = self.collection.find_one({'_id': reservation['_id']})
        return self._format_reservation(updated_reservation)
    
    def check_availability(self, hotel_id: str, room_id: str, 
                          check_in: datetime, check_out: datetime,
                          exclude_reservation_id: Optional[str] = None) -> bool:
        """
        Verifica si una habitación está disponible en las fechas especificadas.
        
        Args:
            hotel_id: ID del hotel
            room_id: ID de la habitación
            check_in: Fecha de entrada
            check_out: Fecha de salida
            exclude_reservation_id: ID de reservación a excluir (para actualizaciones)
            
        Returns:
            True si está disponible, False si no
        """
        query = {
            'hotel_id': ObjectId(hotel_id),
            'room_id': room_id,
            'status': {'$in': ['pending', 'confirmed']},
            '$or': [
                # Nueva reservación comienza durante una existente
                {'check_in': {'$lte': check_in}, 'check_out': {'$gt': check_in}},
                # Nueva reservación termina durante una existente
                {'check_in': {'$lt': check_out}, 'check_out': {'$gte': check_out}},
                # Nueva reservación envuelve una existente
                {'check_in': {'$gte': check_in}, 'check_out': {'$lte': check_out}}
            ]
        }
        
        # Excluir una reservación específica (útil para actualizaciones)
        if exclude_reservation_id:
            query['reservation_id'] = {'$ne': exclude_reservation_id}
        
        conflicting_reservations = self.collection.count_documents(query)
        return conflicting_reservations == 0
    
    def get_calendar_reservations(self, hotel_id: str, year: int, month: int) -> List[Dict]:
        """
        Obtiene las reservaciones de un hotel para un mes específico.
        
        Args:
            hotel_id: ID del hotel
            year: Año
            month: Mes (1-12)
            
        Returns:
            Lista de reservaciones del mes
        """
        # Calcular inicio y fin del mes
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        query = {
            'hotel_id': ObjectId(hotel_id),
            'status': {'$in': ['pending', 'confirmed', 'completed']},
            '$or': [
                {'check_in': {'$gte': start_date, '$lt': end_date}},
                {'check_out': {'$gt': start_date, '$lte': end_date}},
                {'check_in': {'$lt': start_date}, 'check_out': {'$gt': end_date}}
            ]
        }
        
        reservations = self.collection.find(query).sort('check_in', 1)
        return [self._format_reservation(r) for r in reservations]
    
    def _get_hotel(self, hotel_id: str) -> Optional[Dict]:
        """Obtiene un hotel por su ID."""
        try:
            return self.hotels_collection.find_one({'_id': ObjectId(hotel_id)})
        except InvalidId:
            return None
    
    def _get_room(self, hotel: Dict, room_id: str) -> Optional[Dict]:
        """Obtiene una habitación de un hotel."""
        rooms = hotel.get('rooms', [])
        for room in rooms:
            if room.get('room_id') == room_id:
                return room
        return None
    
    def _validate_dates(self, check_in: datetime, check_out: datetime):
        """Valida que las fechas sean correctas. Usa timezone-aware (now) para comparar con check_in/check_out de la API."""
        now = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        check_in_midnight = check_in.replace(hour=0, minute=0, second=0, microsecond=0)
        if check_in_midnight < now:
            raise ValueError("La fecha de entrada no puede ser en el pasado")
        
        if check_out <= check_in:
            raise ValueError("La fecha de salida debe ser posterior a la fecha de entrada")
        
        max_date = now + timedelta(days=365)
        if check_in_midnight > max_date:
            raise ValueError("No se pueden hacer reservaciones con más de un año de anticipación")
    
    def _validate_status_transition(self, current_status: str, new_status: str):
        """Valida que la transición de estado sea válida."""
        valid_transitions = {
            'pending': ['confirmed', 'cancelled', 'rejected'],
            'confirmed': ['cancelled', 'completed'],
            'cancelled': [],  # No se puede cambiar desde cancelado
            'completed': [],  # No se puede cambiar desde completado
            'rejected': []  # No se puede cambiar desde rechazado
        }
        
        if new_status not in valid_transitions.get(current_status, []):
            raise ValueError(
                f"No se puede cambiar el estado de '{current_status}' a '{new_status}'"
            )
    
    def _format_reservation(self, reservation: Dict) -> Dict:
        """Formatea una reservación para la respuesta."""
        if not reservation:
            return None
        
        formatted = {
            'id': str(reservation['_id']),
            'reservation_id': reservation['reservation_id'],
            'hotel_id': str(reservation['hotel_id']),
            'room_id': reservation['room_id'],
            'guest_id': reservation['guest_id'],
            'owner_id': reservation['owner_id'],
            'check_in': reservation['check_in'].isoformat() if isinstance(reservation['check_in'], datetime) else reservation['check_in'],
            'check_out': reservation['check_out'].isoformat() if isinstance(reservation['check_out'], datetime) else reservation['check_out'],
            'nights': reservation['nights'],
            'number_of_guests': reservation['number_of_guests'],
            'guest_details': reservation['guest_details'],
            'price_per_night': reservation['price_per_night'],
            'total_price': reservation['total_price'],
            'currency': reservation.get('currency', 'USD'),
            'status': reservation['status'],
            'payment_status': reservation['payment_status'],
            'special_requests': reservation.get('special_requests', ''),
            'cancellation_reason': reservation.get('cancellation_reason'),
            'created_at': reservation['created_at'].isoformat() if isinstance(reservation['created_at'], datetime) else reservation['created_at'],
            'updated_at': reservation['updated_at'].isoformat() if isinstance(reservation['updated_at'], datetime) else reservation['updated_at'],
            'cancelled_at': reservation['cancelled_at'].isoformat() if reservation.get('cancelled_at') and isinstance(reservation['cancelled_at'], datetime) else reservation.get('cancelled_at'),
            'confirmed_at': reservation['confirmed_at'].isoformat() if reservation.get('confirmed_at') and isinstance(reservation['confirmed_at'], datetime) else reservation.get('confirmed_at'),
        }
        
        return formatted
