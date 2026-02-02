"""
Utilidades para manejo de imágenes de hoteles.
"""
import os
import uuid
from pathlib import Path
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile


class ImageHandler:
    """Maneja la carga y almacenamiento de imágenes de hoteles."""
    
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
    @staticmethod
    def save_hotel_image(image_file, hotel_name: str = None) -> str:
        """
        Guarda una imagen de hotel y retorna la URL.
        
        Args:
            image_file: Archivo de imagen de Django
            hotel_name: Nombre del hotel (opcional, para organización)
            
        Returns:
            URL de la imagen guardada
            
        Raises:
            ValueError: Si la imagen no es válida
        """
        # Validar extensión
        file_ext = os.path.splitext(image_file.name)[1].lower()
        if file_ext not in ImageHandler.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Formato de imagen no permitido. Usa: {', '.join(ImageHandler.ALLOWED_EXTENSIONS)}"
            )
        
        # Validar tamaño
        if image_file.size > ImageHandler.MAX_FILE_SIZE:
            raise ValueError(
                f"La imagen es demasiado grande. Tamaño máximo: {ImageHandler.MAX_FILE_SIZE / (1024*1024)}MB"
            )
        
        # Generar nombre único
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        
        # Organizar por carpetas si se proporciona hotel_name
        if hotel_name:
            # Limpiar el nombre del hotel para usarlo como carpeta
            safe_hotel_name = "".join(c for c in hotel_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_hotel_name = safe_hotel_name.replace(' ', '_')[:50]  # Limitar longitud
            file_path = os.path.join('hotels', safe_hotel_name, unique_filename)
        else:
            file_path = os.path.join('hotels', unique_filename)
        
        # Guardar el archivo
        saved_path = default_storage.save(file_path, ContentFile(image_file.read()))
        
        # Retornar la URL completa
        return f"{settings.MEDIA_URL}{saved_path}"
    
    @staticmethod
    def save_multiple_images(image_files, hotel_name: str = None) -> list:
        """
        Guarda múltiples imágenes y retorna lista de URLs.
        
        Args:
            image_files: Lista de archivos de imagen
            hotel_name: Nombre del hotel (opcional)
            
        Returns:
            Lista de URLs de las imágenes guardadas
        """
        urls = []
        errors = []
        
        for i, image_file in enumerate(image_files):
            try:
                url = ImageHandler.save_hotel_image(image_file, hotel_name)
                urls.append(url)
            except ValueError as e:
                errors.append(f"Imagen {i+1}: {str(e)}")
        
        if errors:
            raise ValueError("; ".join(errors))
        
        return urls
    
    @staticmethod
    def delete_hotel_image(image_url: str) -> bool:
        """
        Elimina una imagen del sistema de archivos.
        
        Args:
            image_url: URL de la imagen a eliminar
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            # Extraer el path del archivo de la URL
            if image_url.startswith(settings.MEDIA_URL):
                file_path = image_url.replace(settings.MEDIA_URL, '')
                if default_storage.exists(file_path):
                    default_storage.delete(file_path)
                    return True
        except Exception:
            pass
        return False
    
    @staticmethod
    def delete_multiple_images(image_urls: list) -> int:
        """
        Elimina múltiples imágenes.
        
        Args:
            image_urls: Lista de URLs de imágenes
            
        Returns:
            Número de imágenes eliminadas exitosamente
        """
        deleted_count = 0
        for url in image_urls:
            if ImageHandler.delete_hotel_image(url):
                deleted_count += 1
        return deleted_count
