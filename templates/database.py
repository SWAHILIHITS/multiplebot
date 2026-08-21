import os
import logging
from pymongo import MongoClient

logger = logging.getLogger("appLogger")

# Load database URI from environment variable with fallback (Update default or use env vars)
MONGO_URI = os.getenv(
    "MONGO_URI", 
    "mongodb+srv://swahilihit:swahilihit@cluster0.3nfk1.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)

# Initialize client and database variables
client = None
db = None
vouchers_col = None
sessions_col = None
tokens_col = None

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['swahilihit56']
    vouchers_col = db["vouchers"]
    sessions_col = db["sessions"]
    tokens_col = db["wifidog_tokens"]
    
    # Initialize indexes for performance and data expiration (TTL)
    vouchers_col.create_index("code", unique=True)
    tokens_col.create_index("created_at", expireAfterSeconds=600)
    sessions_col.create_index("expire_date")
    logger.info("Successfully connected to MongoDB and verified collection indexes.")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")
