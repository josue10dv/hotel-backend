"""
Serializers para la funcionalidad de wishlist.
"""
from rest_framework import serializers
from bson import ObjectId


class WishlistHotelSerializer(serializers.Serializer):
    """
    Serializer para información básica de un hotel en la wishlist.
    """
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    property_type = serializers.CharField(read_only=True)
    rating = serializers.FloatField(read_only=True)
    total_reviews = serializers.IntegerField(read_only=True)
    min_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
        allow_null=True
    )
    images = serializers.ListField(
        child=serializers.URLField(),
        read_only=True
    )
    address = serializers.DictField(read_only=True)
    location = serializers.SerializerMethodField()
    added_at = serializers.DateTimeField(read_only=True)
    
    def get_location(self, obj):
        """Extrae las coordenadas en formato {lat, lng} para Google Maps."""
        try:
            coords = obj.get("address", {}).get("coordinates", {})
            lat = coords.get("lat", 0.0)
            lng = coords.get("lng", 0.0)
            
            # Retornar None si las coordenadas son inválidas
            if lat == 0.0 and lng == 0.0:
                return None
                
            return {"lat": lat, "lng": lng}
        except (AttributeError, TypeError):
            return None


class WishlistSerializer(serializers.Serializer):
    """
    Serializer para la wishlist completa del usuario.
    """
    user_id = serializers.CharField(read_only=True)
    total_hotels = serializers.IntegerField(read_only=True)
    hotels = WishlistHotelSerializer(many=True, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class AddToWishlistSerializer(serializers.Serializer):
    """
    Serializer para agregar un hotel a la wishlist.
    """
    hotel_id = serializers.CharField(required=True)
    
    def validate_hotel_id(self, value):
        """
        Valida que el hotel_id sea un ObjectId válido.
        """
        try:
            ObjectId(value)
            return value
        except Exception:
            raise serializers.ValidationError("ID de hotel inválido")
