from info import CHANNELS ,OWNER_ID 
from datetime import datetime 
import time
import asyncio
from plugins.database import db
from plugins.pm_filter import getCreds,get_access_id,remove_access_email,remove_access
from utils import is_user_exist,get_file_details,add_user,User
from pyrogram.types import InlineKeyboardMarkup,InlineKeyboardButton
async def handle_admin_status(bot, cmd):
        a='start'
        botusername=await bot.get_me()
        nyva=botusername.username  
        nyva=str(nyva)
        while a=='start':
            await asyncio.sleep(60)
            all_users=await db.get_all_banned_users()
            async for user in all_users:
                if  user['db_status']['bot_link']!= nyva:
                    continue  
                ban_status = await db.get_ban_status(user['id'],nyva)
                if ban_status["is_banned"]:
                    if ban_status["ban_duration"] < (datetime.now() - datetime.fromisoformat(ban_status["banned_on"])).days:
                        await bot.send_message(chat_id=int(user['id']),text=f"Samahan admin kifurushi ulicho lipia kumtumia BOXFLIX MEDIA GROUP kimeisha tafadhali lipia ili wateja wako waendelee kupata huduma zetu")
                        await db.remove_ban(user['id'],nyva)
            all_users =await db.get_all_acc()
            async for user in all_users:
                if  user['bot_link']!= nyva:
                    continue  
                if user["ban_status"]["ban_duration"] <= (datetime.now() - datetime.fromisoformat(user["ban_status"]["banned_on"])).days:
                    try:
                        abc2=await db.get_db_status( int(user['db_name']),nyva)
                    except:
                        await db.delete_acc(user['id'])
                        continue
                    if user['file_id'].startswith('g_'):
                        abc=f"{abc2[user['file_id']].split('#@')[0]} kimeisha"
                        descp=abc2[user['file_id']].split('#@')[3]
                    else:
                        abn=await get_file_details(user['file_id'])
                        for file in abn:
                            abc=f"{file.text.split('.dd#.')[0]} mda wake wa kuipakua umeisha" 
                            descp=file.descp.split(".dd#.")[2]
                    if nyva ==abc2["bot_link"]:
                        hjkl=f'{user["db_name"]}##{user["user_id"]}'
                        if not await is_user_exist(hjkl,nyva):
                            await add_user(hjkl,nyva)
                        gdh = await is_user_exist(hjkl,nyva)
                        for gvb in gdh:
                            gdhz=gvb.email
                        try:
                            hjgh = f'{user['file_id']}##{user['user_id']}'
                            found = await User.collection.find_one({"_id":hjgh})
                            service = getCreds(abc2['token'],int(user["db_name"]))
                            if service=='auth_error' or service=='token_error':
                                await client.send_message(chat_id= int(user["db_name"]),text=f'tafadhali token imeexpire tengeneza mpya')
                            if found and (service!='auth_error' or service!='token_error'):
                                await bot.send_message(chat_id=int(user['user_id']),text=f"{abc} tafadhali jiunge kuendelea kupata huduma zetu kwa bei nafuu")
                                if found['tme'] == 1000:
                                    fvx=found['email']
                                    fjc=remove_access(service,fvx.split("##")[0],fvx.split("##")[1])
                                elif found['tme']==2000:
                                    fvx=found['email']
                                    fghk=get_access_id(f'{descp}')
                                    if fghk!="url_invalid":
                                        fjc=remove_access_email(service,fghk,fvx)
                            elif "google" in descp.lower():
                                await bot.send_message(chat_id=int(user['user_id']),text=f"{abc} tafadhali jiunge kuendelea kupata huduma zetu kwa bei nafuu")
                                await bot.send_message(chat_id=int( user['db_name'] ),text=f"Tafadhali naomba uondoe uwezo wakuacces mda wake umeisha kutumia \n{abc}\nkwa email\n**{gdhz}**\n kama uliadd kwa email kama sivyo bonyeza close",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="Close",callback_data="close")]]))
                            else:
                                await bot.send_message(chat_id=int(user['user_id']),text=f"{abc} tafadhali jiunge kuendelea kupata huduma zetu kwa bei nafuu")
                            await db.delete_acc(user['id'])
                        except Exception as e:
                            await bot.send_message(chat_id=int( user['db_name'] ),text=f"Tafadhali tuma huu kwa msimamizi aweze rekebisha hili tatizo {e}")
                    
                    await asyncio.sleep(5) 
                
                    
