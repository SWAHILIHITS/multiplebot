import logging 
import asyncio
import logging.config
# Get logging configurations
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.ERROR)
from pyrogram import idle,Client, __version__,compose
from pyrogram.raw.all import layer
from utils import Media 
from plugins.database import db
from info import SESSION, API_ID, API_HASH, BOT_TOKEN


active_bots = {}

class MultiBot(Client):
    def __init__(self, name, token):
        super().__init__(
            name=name,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=token,
            plugins={"root": "plugins"},
            workers=50
        )

    async def start(self):
        await super().start()
        # Initialize DB indexes for each bot on start
        await Media.ensure_indexes()
        logging.info(f"Bot session {self.name} is now online.")
Bot0=[]
async def dynamic_loader():
    """Background task to fetch tokens and start bots."""
    while True:
        try:
            # Query admins with a token in the 'groups' table
            admins=await db.get_all_users()
            print(admins)
            async for admin in admins:
                print(admins)
                if admin["db_status"]['bot_token'] not in active_bots:
                    # Generate a unique session name
                    session_name = f"sessions/bot_{admin["id"]}"
                    
                    # Create and start the client without blocking the loop
                    new_bot = MultiBot(session_name, admin["db_status"]['bot_token'])
                    await new_bot.start()
                    Bot0.append(new_client)
                    # Keep a reference to prevent garbage collection
                    active_bots[admin["db_status"]['bot_token']] = new_bot
        except Exception as e:
            logging.error(f"Loader Error: {e}")
        
        await asyncio.sleep(60)

async def main():
    # Run the loader as a background task
    asyncio.create_task(dynamic_loader())
    
    # Keep the main thread alive for all background bots
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
