from pyrogram import filters
import os 
import re
from os import environ
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
id_pattern = re.compile(r'^.\d+$')

# Bot information
SESSION = environ.get('SESSION', 'Media_search')
API_ID = 10786281
API_HASH = '5f42bc5562f6a1eb8bae8b77617186a0'
BOT_TOKEN ='6289396925:AAGBWFC0s_VuE27HFNFHPRwg2HVTmQGsJL0'

# Bot settings
CACHE_TIME = int(environ.get('CACHE_TIME', 300))
USE_CAPTION_FILTER = bool(environ.get('USE_CAPTION_FILTER', False))
CHANNELS = -1001609087881
AUTH_CHANNEL = -1001726632341
# MongoDB information
COLLECTION_NAME = environ.get('COLLECTION_NAME', 'Telegram_file')
client = AsyncIOMotorClient('mongodb+srv://swahilihit:swahilihit@cluster0.3nfk1.mongodb.net/myFirstDatabase?retryWrites=true&w=majority')
client.get_io_loop = asyncio.get_running_loop

# The current database ("test")
DB2 = client['swahilihit56']

TG_BOT_WORKERS = int(os.environ.get("BOT_WORKERS", '4'))
thumb = os.environ.get('THUMBNAIL_URL', 'https://telegra.ph/file/516ca261de9ebe7f4ffe1.jpg')
OWNER_ID = 859704527
CUSTOM_START_MESSAGE = os.environ.get('START_MESSAGE','')
FILTER_COMMAND = os.environ.get('FILTER_COMMAND', 'add')
DELETE_COMMAND = os.environ.get('DELETE_COMMAND', 'del')
IS_PUBLIC = True if os.environ.get('IS_PUBLIC', 'True').lower() != 'false' else False
ADMINS = [859704527]

def is_owner(_, __, update):
    try:
        user_id = update.from_user.id
    except:
        return False

    if user_id == OWNER_ID:
        return True
    else:
        return False


def check_inline(_, __, update):
    try:
        user_id = update.from_user.id
    except:
        return False

    if IS_PUBLIC:
        return True
    elif user_id in ADMINS:
        return True
    else:
        return False

filters.owner = filters.create(is_owner)
filters.inline = filters.create(check_inline)
