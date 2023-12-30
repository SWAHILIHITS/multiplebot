from info import CHANNELS ,OWNER_ID
from datetime import datetime 
import time
import asyncio
from plugins.database import db
from utils import is_user_exist,get_file_details,add_user
from pyrogram.types import InlineKeyboardMarkup,InlineKeyboardButton
async def handle_admin_status(bot, cmd):
        a='start'
        botusername=await bot.get_me()
        nyva=botusername.username  
        nyva=str(nyva)
        while a=='start':
            asyncio.sleep(60)
            all_user =await db.get_all_users()
            async for user in all_user:
                ban_status = await db.get_ban_status(user['id'])
                if ban_status["is_banned"]:
                    if ban_status["ban_duration"] < (
                            datetime.now() - datetime.fromisoformat(ban_status["banned_on"])
                    ).days:
                        await bot.send_message(chat_id=int(user['id']),text=f"Samahan admin kifurushi ulicho lipia kumtumia swahili robot kimeisha tafadhali lipia ili wateja wako waendelee kupata huduma zetu")
                        await db.remove_ban(user['id'])
            all_users =await db.get_all_acc()
            async for user in all_users:  
                if user["ban_status"]["ban_duration"] <= (datetime.now() - datetime.fromisoformat(user["ban_status"]["banned_on"])).days:
                    abc2=await db.get_db_status( int(user['db_name']) )
                    if user['file_id'].startswith('g_'):
                        abc=f"{abc2[user['file_id']].split('#@')[0]} kimeisha"
                    else:
                        abn=await get_file_details(user['file_id'])
                        for file in abn:
                            abc=f"{file.text.split('.dd#.')[0]} mda wake wa kuipakua umeisha" 
                    if nyva ==abc2["bot_link"]:
                        hjkl=f'{user["db_name"]}##{user["user_id"]}'
                        if not await is_user_exist(hjkl,nyva):
                            await add_user(hjkl,nyva)
                        gdh = await is_user_exist(hjkl,nyva)
                        for gvb in gdh:
                            gdhz=gvb.email
                        try:
                            await db.delete_acc(user['id'])
                            await bot.send_message(chat_id=int(user['user_id']),text=f"{abc} tafadhali jiunge kuendelea kupata huduma zetu kwa bei nafuu")
                            await bot.send_message(chat_id=int( user['db_name'] ),text=f"Tafadhali naomba uondoe uwezo wakuacces mda wake umeisha kutumia \n{abc}\nkwa email\n**{gdhz}**\n kama uliadd kwa email kama sivyo bonyeza close",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="Close",callback_data="close")]]))
                        except Exception as e:
                            await bot.send_message(chat_id=int( user['db_name'] ),text=f"Tafadhali tuma huu kwa msimamizi wangu aweze rekebisha hili tatizo {e}")
                    asyncio.sleep(1) 
                
                    
