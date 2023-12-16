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
            bot_token="6703433962:AAFGYkmXj3gFjkB6tii4hN3G9AyNr9ee4cQ",
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
            bot_token='2136703772:AAGvh59sqhRFY7SJXbNsBuiPFZcvXpVFIKA',
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
            name= 'SESSION2' ,
            api_id= 20670303,
            api_hash= "826ddb9f18248500206bb77675798229" ,
            bot_token="6584474313:AAFPHy1fTQn8e4LtWE-QRBPT3Uq6wR5mUj4",
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=6,
        )
    async def start(self):
        await super().start()
        await Media.ensure_indexes()    
    async def stop(self, *args):
        await super().stop()

class Bot3(Client):
    def __init__(self):
        super().__init__(
            name='SESSION3' ,
            api_id= 20670303,
            api_hash= "826ddb9f18248500206bb77675798229" ,
            bot_token="6584474313:AAFPHy1fTQn8e4LtWE-QRBPT3Uq6wR5mUj4",
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=4,
        )
    async def start(self):
        await super().start()
        await Media.ensure_indexes()    
    async def stop(self, *args):
        await super().stop()
class Bot4(Client):
    def __init__(self):
        super().__init__(
            name= 'SESSION4' ,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token="6658819313:AAFdl4m3NsB5oYHvGpneldXc1duA0N-q_zs",
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=4,
        )
    async def start(self):
        await super().start()
        await Media.ensure_indexes()    
    async def stop(self, *args):
        await super().stop()
class Bot5(Client):
    def __init__(self):
        super().__init__(
            name= 'SESSION5' ,
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
class Bot6(Client):
    def __init__(self):
        super().__init__(
            name= 'SESSION6' ,
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
class Bot7(Client):
    def __init__(self):
        super().__init__(
            name= 'SESSION7' ,
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
class Bot8(Client):
    def __init__(self):
        super().__init__(
            name= 'SESSION8' ,
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
class Bot9(Client):
    def __init__(self):
        super().__init__(
            name= 'SESSION9' ,
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
for i in [Bot,Bot1,Bot2]:
    Bot0=i
async def main():
    app=[Bot(),Bot1(),Bot2()]
    await compose(app)
