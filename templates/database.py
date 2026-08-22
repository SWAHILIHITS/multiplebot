import os
import logging
from pymongo import MongoClient

logger = logging.getLogger("appLogger")

# Database URI from environment variable
MONGO_URI = os.getenv(
    "MONGO_URI", 
    "mongodb+srv://swahilihit:swahilihit@cluster0.3nfk1.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['swahilihit56']
    
    # Exported Collections
    vouchers_col = db["vouchers"]
    sessions_col = db["sessions"]
    tokens_col = db["wifidog_tokens"]
    settings_col = db["settings"]
    packages_col = db["packages"]  # Added Package Collection
    
    # Initialize indexes for performance and security
    vouchers_col.create_index("code", unique=True)
    tokens_col.create_index("created_at", expireAfterSeconds=600)
    sessions_col.create_index("expire_date")
    packages_col.create_index("created_at")
    
    logger.info("Successfully connected to MongoDB and initialized collections.")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")
    raise e
