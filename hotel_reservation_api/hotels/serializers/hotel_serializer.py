"""
Serializers para la gestión de hoteles.
Valida y serializa datos entre la API REST y MongoDB.
"""
from rest_framework import serializers
from hotels.schemas.hotel_schema import HotelSchema


def _coordinates_to_lat_lng(coordinates):
    """
    Normaliza coordenadas desde MongoDB a formato { lat, lng }.
    Acepta GeoJSON { type: "Point", coordinates: [lng, lat] } o { lat, lng }.
    """
    if not coordinates:
        return None
    if coordinates.get('type') == 'Point' and 'coordinates' in coordinates:
        coords = coordinates['coordinates']
        if len(coords) >= 2:
            return {'lat': coords[1], 'lng': coords[0]}
    if 'lat' in coordinates and 'lng' in coordinates:
        return {'lat': coordinates['lat'], 'lng': coordinates['lng']}
    return None


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

    def to_representation(self, instance):
        """Acepta GeoJSON (MongoDB 2dsphere) o { lat, lng }; siempre devuelve { lat, lng }."""
        normalized = _coordinates_to_lat_lng(instance)
        if normalized is None:
            return {}
        return super().to_representation(normalized)

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
    description = serializers.CharField(allow_blank=True, required=False)
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


class PoliciesSerializer(serializers.Serializer):
    """Serializer para políticas del hotel."""
    check_in = serializers.CharField(max_length=10, default="14:00")
    check_out = serializers.CharField(max_length=10, default="12:00")
    cancellation = serializers.CharField(
        default="Free cancellation up to 24 hours before check-in"
    )
    house_rules = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        default=list
    )


class ContactSerializer(serializers.Serializer):
    """Serializer para información de contacto."""
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)


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
        Acepta GeoJSON o { lat, lng }; retorna { lat, lng } o None.
        """
        address = obj.get('address', {})
        coordinates = address.get('coordinates', {})
        normalized = _coordinates_to_lat_lng(coordinates)
        if not normalized:
            return None
        lat, lng = normalized['lat'], normalized['lng']
        if lat == 0.0 and lng == 0.0:
            return None
        return {'lat': lat, 'lng': lng}

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
        Acepta GeoJSON o { lat, lng }; retorna { lat, lng } o None.
        """
        address = obj.get('address', {})
        coordinates = address.get('coordinates', {})
        normalized = _coordinates_to_lat_lng(coordinates)
        if not normalized:
            return None
        lat, lng = normalized['lat'], normalized['lng']
        if lat == 0.0 and lng == 0.0:
            return None
        return {'lat': lat, 'lng': lng}


class HotelCreateSerializer(serializers.Serializer):
    """
    Serializer para creación de hoteles.
    Campos requeridos para registrar un nuevo hotel.
    """
    name = serializers.CharField(max_length=255)
    description = serializers.CharField()
    property_type = serializers.ChoiceField(
        choices=HotelSchema.PROPERTY_TYPES,
        default="hotel"
    )
    address = AddressSerializer()
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
    policies = PoliciesSerializer(required=False)
    contact = ContactSerializer(required=False)

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
