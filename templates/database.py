import os
import logging
from pymongo import MongoClient
logger = logging.getLogger("appLogger")

# Database URI from environment variable
MONGO_URI = os.getenv(
    "MONGO_URI", 
    "mongodb+srv://swahiligroup97_db_user:YqpWxsG3cHDRKL13@cluster0.opf1rju.mongodb.net?appName=Cluster0"
)

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['swahilihit56']
    
    # Exported Collections
    vouchers_col = db["vouchers"]
    sessions_col = db["sessions"]
    tokens_col = db["wifidog_tokens"]
    packages_col = db["packages"]
    connection_logs_col = db["connection_logs"]  # Added for centralized connection tracking
    
    # Initialize indexes for high performance and security
    vouchers_col.create_index("code", unique=True)
    vouchers_col.create_index("used_by_mac")  # Crucial for fast auto-reconnect checks per user device
    
    tokens_col.create_index("created_at", expireAfterSeconds=600)
    
    sessions_col.create_index("expire_date")
    sessions_col.create_index("code")
    
    packages_col.create_index("created_at")
    
    # Indexes for fast telemetry, session tracking, and dashboard rendering
    connection_logs_col.create_index("mac")
    connection_logs_col.create_index("code")
    connection_logs_col.create_index("start_time")
    
    logger.info("Successfully connected to MongoDB and initialized collections & indexes.")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")
    raise e
