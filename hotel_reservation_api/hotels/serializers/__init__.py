"""
Serializers para la app de hoteles.
"""
from .hotel_serializer import (
    HotelSerializer,
    HotelListSerializer,
    HotelCreateSerializer,
    HotelUpdateSerializer,
    AddressSerializer,
    RoomSerializer,
    ContactSerializer,
    PoliciesSerializer,
    CoordinatesSerializer,
)

__all__ = [
    HotelSerializer,
    HotelListSerializer,
    HotelCreateSerializer,
    HotelUpdateSerializer,
    AddressSerializer,
    RoomSerializer,
    ContactSerializer,
    PoliciesSerializer,
    CoordinatesSerializer,
]
