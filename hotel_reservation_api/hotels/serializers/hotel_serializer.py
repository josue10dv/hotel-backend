"""
Serializers para la gestión de hoteles.
Valida y serializa datos entre la API REST y MongoDB.
"""
from rest_framework import serializers
from hotels.schemas.hotel_schema import HotelSchema


class CoordinatesSerializer(serializers.Serializer):
    """Serializer para coordenadas geográficas compatible con Google Maps."""
    lat = serializers.FloatField(
        min_value=-90, 
        max_value=90,
        help_text="Latitud (-90 a 90). Ejemplo: -34.9011 para Montevideo"
    )
    lng = serializers.FloatField(
        min_value=-180, 
        max_value=180,
        help_text="Longitud (-180 a 180). Ejemplo: -56.1645 para Montevideo"
    )
    
    def validate(self, data):
        """Validación adicional de coordenadas."""
        lat = data.get('lat')
        lng = data.get('lng')
        
        # Validar que no sean exactamente 0, 0 (indica coordenadas no establecidas)
        if lat == 0.0 and lng == 0.0:
            raise serializers.ValidationError(
                "Las coordenadas (0.0, 0.0) no son válidas. Por favor proporciona la ubicación real."
            )
        
        return data


class AddressSerializer(serializers.Serializer):
    """Serializer para dirección del hotel."""
    street = serializers.CharField(max_length=255)
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=100)
    country = serializers.CharField(max_length=100)
    postal_code = serializers.CharField(max_length=20)
    coordinates = CoordinatesSerializer(required=False)


class RoomSerializer(serializers.Serializer):
    """Serializer para habitaciones del hotel."""
    room_id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(allow_blank=True, required=False, default='')
    type = serializers.ChoiceField(
        choices=HotelSchema.ROOM_TYPES,
        default="double"
    )
    capacity = serializers.IntegerField(min_value=1, max_value=20)
    price_per_night = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2,
        min_value=0
    )
    available = serializers.BooleanField(default=True)
    amenities = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list
    )
    images = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        default=list
    )
    
    def to_representation(self, instance):
        """Asegura arrays vacíos en lugar de None."""
        data = super().to_representation(instance)
        if data.get('amenities') is None:
            data['amenities'] = []
        if data.get('images') is None:
            data['images'] = []
        if data.get('description') is None:
            data['description'] = ''
        return data


class PoliciesSerializer(serializers.Serializer):
    """Serializer para políticas del hotel."""
    check_in_time = serializers.CharField(
        max_length=10, 
        default="15:00",
        help_text="Hora de check-in en formato HH:MM"
    )
    check_out_time = serializers.CharField(
        max_length=10, 
        default="12:00",
        help_text="Hora de check-out en formato HH:MM"
    )
    cancellation_policy = serializers.CharField(
        default="Cancelación gratuita hasta 24 horas antes",
        help_text="Política de cancelación del hotel"
    )
    pet_policy = serializers.CharField(
        default="No se aceptan mascotas",
        help_text="Política de mascotas del hotel"
    )


class ContactSerializer(serializers.Serializer):
    """Serializer para información de contacto."""
    phone = serializers.CharField(
        max_length=20, 
        required=False, 
        allow_blank=True,
        default=''
    )
    email = serializers.EmailField(
        required=False, 
        allow_blank=True,
        default=''
    )
    website = serializers.URLField(
        required=False, 
        allow_blank=True,
        default=''
    )


class HotelSerializer(serializers.Serializer):
    """
    Serializer completo para Hotel.
    Usado para lectura y respuesta detallada.
    Optimizado para Google Maps con campo 'location' de acceso directo.
    """
    id = serializers.CharField(read_only=True, source='_id')
    owner_id = serializers.UUIDField()
    name = serializers.CharField(max_length=255)
    description = serializers.CharField()
    property_type = serializers.ChoiceField(
        choices=HotelSchema.PROPERTY_TYPES,
        default="hotel"
    )
    address = AddressSerializer()
    # Campo de acceso directo a coordenadas para Google Maps
    location = serializers.SerializerMethodField(
        help_text="Coordenadas directas {lat, lng} para Google Maps"
    )
    rooms = RoomSerializer(many=True, required=False, default=list)
    amenities = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list
    )
    services = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list
    )
    images = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        default=list
    )
    rating = serializers.FloatField(read_only=True, default=0.0)
    total_reviews = serializers.IntegerField(read_only=True, default=0)
    policies = PoliciesSerializer(required=False)
    contact = ContactSerializer(required=False)
    is_active = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_location(self, obj):
        """
        Extrae las coordenadas del hotel para fácil uso con Google Maps.
        Retorna las coordenadas en formato {lat, lng} o None si no están disponibles.
        """
        address = obj.get('address', {})
        coordinates = address.get('coordinates', {})
        
        lat = coordinates.get('lat')
        lng = coordinates.get('lng')
        
        # Solo retornar si las coordenadas son válidas
        if lat is not None and lng is not None and not (lat == 0.0 and lng == 0.0):
            return {
                'lat': lat,
                'lng': lng
            }
        return None
    
    def to_representation(self, instance):
        """
        Asegura que la respuesta tenga la estructura correcta esperada por el frontend.
        Convierte None en arrays vacíos para campos de lista y proporciona valores por defecto.
        """
        data = super().to_representation(instance)
        
        # Asegurar que los arrays vacíos se devuelvan como [] en lugar de None
        list_fields = ['rooms', 'amenities', 'services', 'images']
        for field in list_fields:
            if data.get(field) is None:
                data[field] = []
        
        # Asegurar que policies tenga la estructura correcta
        if not data.get('policies'):
            data['policies'] = {
                'check_in_time': '15:00',
                'check_out_time': '12:00',
                'cancellation_policy': 'Cancelación gratuita hasta 24 horas antes',
                'pet_policy': 'No se aceptan mascotas'
            }
        
        # Asegurar que contact tenga la estructura correcta
        if not data.get('contact'):
            data['contact'] = {
                'phone': '',
                'email': '',
                'website': ''
            }
        
        # Asegurar que total_reviews tenga un valor
        if data.get('total_reviews') is None:
            data['total_reviews'] = 0
        
        # Asegurar que is_active esté presente
        if data.get('is_active') is None:
            data['is_active'] = True
        
        return data

    def validate_property_type(self, value):
        """Valida el tipo de propiedad."""
        if not HotelSchema.validate_property_type(value):
            raise serializers.ValidationError(
                f"Tipo de propiedad inválido. Opciones: {', '.join(HotelSchema.PROPERTY_TYPES)}"
            )
        return value


class HotelListSerializer(serializers.Serializer):
    """
    Serializer resumido para listado de hoteles.
    Solo incluye información básica para mejorar rendimiento.
    Optimizado para mostrar múltiples hoteles en Google Maps.
    """
    id = serializers.CharField(read_only=True, source='_id')
    owner_id = serializers.UUIDField()
    name = serializers.CharField()
    description = serializers.CharField()
    property_type = serializers.CharField()
    address = AddressSerializer()
    # Campo de acceso directo a coordenadas para Google Maps
    location = serializers.SerializerMethodField(
        help_text="Coordenadas directas {lat, lng} para marcadores en el mapa"
    )
    amenities = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list
    )
    services = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list
    )
    images = serializers.ListField(child=serializers.URLField())
    rating = serializers.FloatField()
    total_reviews = serializers.IntegerField()
    is_active = serializers.BooleanField()
    
    # Agregar precio mínimo calculado
    min_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2,
        required=False,
        read_only=True
    )
    
    def get_location(self, obj):
        """
        Extrae las coordenadas del hotel para Google Maps.
        Formato optimizado para renderizado de múltiples marcadores.
        """
        address = obj.get('address', {})
        coordinates = address.get('coordinates', {})
        
        lat = coordinates.get('lat')
        lng = coordinates.get('lng')
        
        # Solo retornar si las coordenadas son válidas
        if lat is not None and lng is not None and not (lat == 0.0 and lng == 0.0):
            return {
                'lat': lat,
                'lng': lng
            }
        return None
    
    def to_representation(self, instance):
        """
        Asegura que los arrays vacíos se devuelvan como [] en lugar de None.
        Coincide con la interfaz Hotel de TypeScript.
        """
        data = super().to_representation(instance)
        
        # Asegurar que los arrays vacíos se devuelvan como [] en lugar de None
        list_fields = ['amenities', 'services', 'images']
        for field in list_fields:
            if data.get(field) is None:
                data[field] = []
        
        # Asegurar que total_reviews tenga un valor
        if data.get('total_reviews') is None:
            data['total_reviews'] = 0
        
        return data


class HotelCreateSerializer(serializers.Serializer):
    """
    Serializer para creación de hoteles.
    Campos requeridos para registrar un nuevo hotel.
    Acepta imágenes como archivos (image_files) o URLs (images).
    """
    name = serializers.CharField(max_length=255)
    description = serializers.CharField()
    property_type = serializers.ChoiceField(
        choices=HotelSchema.PROPERTY_TYPES,
        default="hotel"
    )
    address = serializers.JSONField()
    amenities = serializers.JSONField(required=False, default=list)
    services = serializers.JSONField(required=False, default=list)
    # Soportar tanto URLs como archivos
    images = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        default=list,
        write_only=True,
        help_text="Lista de URLs de imágenes (opcional si se envían archivos)"
    )
    image_files = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        write_only=True,
        help_text="Lista de archivos de imagen para subir"
    )
    policies = serializers.JSONField(required=False)
    contact = serializers.JSONField(required=False)
    
    def validate_address(self, value):
        """Valida el campo address usando AddressSerializer."""
        if isinstance(value, str):
            import json
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Invalid JSON format for address")
        
        address_serializer = AddressSerializer(data=value)
        if not address_serializer.is_valid():
            raise serializers.ValidationError(address_serializer.errors)
        return address_serializer.validated_data
    
    def validate_amenities(self, value):
        """Valida amenities."""
        if isinstance(value, str):
            import json
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Invalid JSON format for amenities")
        
        if not isinstance(value, list):
            raise serializers.ValidationError("Amenities must be a list")
        
        # Validar cada amenity
        for amenity in value:
            if not isinstance(amenity, str):
                raise serializers.ValidationError("Each amenity must be a string")
            if len(amenity) > 100:
                raise serializers.ValidationError(f"Amenity '{amenity}' exceeds 100 characters")
        
        return value
    
    def validate_services(self, value):
        """Valida services."""
        if isinstance(value, str):
            import json
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Invalid JSON format for services")
        
        if not isinstance(value, list):
            raise serializers.ValidationError("Services must be a list")
        
        # Validar cada service
        for service in value:
            if not isinstance(service, str):
                raise serializers.ValidationError("Each service must be a string")
            if len(service) > 100:
                raise serializers.ValidationError(f"Service '{service}' exceeds 100 characters")
        
        return value
    
    def validate_policies(self, value):
        """Valida policies."""
        if isinstance(value, str):
            import json
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Invalid JSON format for policies")
        
        if value:
            policies_serializer = PoliciesSerializer(data=value)
            if not policies_serializer.is_valid():
                raise serializers.ValidationError(policies_serializer.errors)
            return policies_serializer.validated_data
        return value
    
    def validate_contact(self, value):
        """Valida contact."""
        if isinstance(value, str):
            import json
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Invalid JSON format for contact")
        
        if value:
            contact_serializer = ContactSerializer(data=value)
            if not contact_serializer.is_valid():
                raise serializers.ValidationError(contact_serializer.errors)
            return contact_serializer.validated_data
        return value

    def validate_property_type(self, value):
        """Valida el tipo de propiedad."""
        if not HotelSchema.validate_property_type(value):
            raise serializers.ValidationError(
                f"Tipo de propiedad inválido. Opciones: {', '.join(HotelSchema.PROPERTY_TYPES)}"
            )
        return value


class HotelUpdateSerializer(serializers.Serializer):
    """
    Serializer para actualización de hoteles.
    Todos los campos son opcionales para permitir actualización parcial.
    """
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False)
    property_type = serializers.ChoiceField(
        choices=HotelSchema.PROPERTY_TYPES,
        required=False
    )
    address = AddressSerializer(required=False)
    amenities = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False
    )
    services = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False
    )
    images = serializers.ListField(
        child=serializers.URLField(),
        required=False
    )
    policies = PoliciesSerializer(required=False)
    contact = ContactSerializer(required=False)
    is_active = serializers.BooleanField(required=False)

    def validate_property_type(self, value):
        """Valida el tipo de propiedad."""
        if not HotelSchema.validate_property_type(value):
            raise serializers.ValidationError(
                f"Tipo de propiedad inválido. Opciones: {', '.join(HotelSchema.PROPERTY_TYPES)}"
            )
        return value
