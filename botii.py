import logging
import logging.config
# Get logging configurations
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.ERROR)

from pyrogram import Client, __version__,compose
from pyrogram.raw.all import layer
from utils import Media
from info import SESSION, API_ID, API_HASH, BOT_TOKEN

class Bot(Client):
    def __init__(self):
        super().__init__(
            name=SESSION ,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token="2136703772:AAH7YT8ngkmRmsSgU8BUX1zjQT8hw8JVdyE",
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=4,
        )
    async def start(self):
        await super().start()
        await Media.ensure_indexes()    
    async def stop(self, *args):
        await super().stop()
        
class Bot1(Client): 
    def __init__(self):
        super().__init__(
            name='Mediasiearch',
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token='6332194321:AAE2pkCDZzeYkNfM_jd5gFt3wc-QyD6QfDY',
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=5,
        )
    async def start(self):
        await super().start()
        await Media.ensure_indexes() 
    async def stop(self, *args):
        await super().stop() 
class Bot2(Client):
    def __init__(self):
        super().__init__(
            name=SESSION ,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token="2136703772:AAH7YT8ngkmRmsSgU8BUX1zjQT8hw8JVdyE",
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=4,
        )
    async def start(self):
        await super().start()
        await Media.ensure_indexes()    
    async def stop(self, *args):
        await super().stop()

class Bot3(Client):
    def __init__(self):
        super().__init__(
            name=SESSION ,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token="2136703772:AAH7YT8ngkmRmsSgU8BUX1zjQT8hw8JVdyE",
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=4,
        )
    async def start(self):
        await super().start()
        await Media.ensure_indexes()    
    async def stop(self, *args):
        await super().stop()

BOT0=None
for i in [Bot,Bot1]:
    Bot0=i
async def main():
    app=[Bot(),Bot1()]
    await compose(app)
