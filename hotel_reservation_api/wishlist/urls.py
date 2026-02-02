"""
URLs para la app de wishlist.
"""
from django.urls import path
from wishlist.views import (
    WishlistView,
    AddToWishlistView,
    RemoveFromWishlistView,
    CheckWishlistView,
    ClearWishlistView
)

app_name = 'wishlist'

urlpatterns = [
    # Obtener wishlist completa
    path('', WishlistView.as_view(), name='wishlist'),
    
    # Agregar hotel a wishlist
    path('add/', AddToWishlistView.as_view(), name='add-to-wishlist'),
    
    # Eliminar hotel de wishlist
    path('remove/<str:hotel_id>/', RemoveFromWishlistView.as_view(), name='remove-from-wishlist'),
    
    # Verificar si un hotel está en wishlist
    path('check/<str:hotel_id>/', CheckWishlistView.as_view(), name='check-wishlist'),
    
    # Limpiar wishlist completa
    path('clear/', ClearWishlistView.as_view(), name='clear-wishlist'),
]
