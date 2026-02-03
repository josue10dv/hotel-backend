"""
MongoDB connection manager for the application.
Conexión a MongoDB como servicio en el servidor (Ubuntu). Usa variables de entorno.
"""

from pymongo import MongoClient
from django.conf import settings
from urllib.parse import quote_plus


class MongoDBConnection:
    """
    Singleton class to manage MongoDB connection.
    """

    _instance = None
    _client = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBConnection, cls).__new__(cls)
            cls._instance._initialize_connection()
        return cls._instance

    def _initialize_connection(self):
        """Inicializa la conexión a MongoDB usando variables de entorno (servicio en Ubuntu)."""
        mongo_settings = settings.MONGODB_SETTINGS

        host = mongo_settings["host"]
        port = mongo_settings["port"]
        db_name = mongo_settings["db"]
        username = mongo_settings.get("username", "").strip()
        password = mongo_settings.get("password", "").strip()
        auth_source = mongo_settings.get("auth_source", "admin")

        if username and password:
            username_encoded = quote_plus(username)
            password_encoded = quote_plus(password)
            connection_string = (
                f"mongodb://{username_encoded}:{password_encoded}@{host}:{port}/"
                f"{db_name}?authSource={auth_source}"
            )
        else:
            connection_string = f"mongodb://{host}:{port}/{db_name}"

        self._client = MongoClient(connection_string)
        self._db = self._client[db_name]

    @property
    def db(self):
        """Get the MongoDB database instance."""
        return self._db
    
    def get_db(self):
        """Get the MongoDB database instance (method version)."""
        return self._db

    def close(self):
        """Close MongoDB connection."""
        if self._client:
            self._client.close()


# Create a global instance
mongo_db = MongoDBConnection()


def get_mongo_db():
    """
    Helper function to get MongoDB database instance.
    
    Usage:
        from app.mongodb import get_mongo_db
        
        db = get_mongo_db()
        collection = db['my_collection']
        collection.insert_one({'name': 'example'})
    """
    return mongo_db.db


# Collection helpers
def get_hotels_collection():
    """Get hotels collection."""
    return get_mongo_db()['hotels']


def get_reservations_collection():
    """Get reservations collection."""
    return get_mongo_db()['reservations']


def get_reviews_collection():
    """Get reviews collection."""
    return get_mongo_db()['reviews']


def get_wishlist_collection():
    """Get wishlist collection."""
    return get_mongo_db()['wishlist']


def get_notifications_collection():
    """Get notifications collection."""
    return get_mongo_db()['notifications']
