"""
MongoDB connection manager for the application.
Use this module to interact with MongoDB collections.
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
        """Initialize MongoDB connection using settings."""
        mongo_settings = settings.MONGODB_SETTINGS
        
        host = mongo_settings['host']
        port = mongo_settings['port']
        db_name = mongo_settings['db']
        username = mongo_settings.get('username', '')
        password = mongo_settings.get('password', '')
        
        # Build connection string based on whether authentication is needed
        if username and password:
            # With authentication - encode credentials for special characters
            username_encoded = quote_plus(username)
            password_encoded = quote_plus(password)
            connection_string = (
                f"mongodb://{username_encoded}:{password_encoded}@{host}:{port}/"
                f"{db_name}?authSource=admin"
            )
        else:
            # Without authentication (local development)
            connection_string = f"mongodb://{host}:{port}/"
        
        self._client = MongoClient(connection_string)
        self._db = self._client[db_name]

    @property
    def db(self):
        """Get the MongoDB database instance."""
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
