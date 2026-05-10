from info import filters,CHANNELS,OWNER_ID
import uuid
import time,re,os,asyncio
from plugins.base_command import btn22
from plugins.pm_filter import getCreds,get_access_id
from pyrogram.errors import ChatAdminRequired,FloodWait
from utils import get_file_details,get_filter_results,is_user_exist,Media,is_subscribed,is_group_exist,save_file,add_user,add_likes,Like,User
from bot  import Bot0
from plugins.database import db
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery,ForceReply

async def sync_data(tokeni,id2,url):
    service = getCreds(tokeni,id2)
    PARENT_FOLDER_ID = get_access_id(url)
    # List Alphabet Folders (A-Z)
    # Query for alphabet folders (A-Z)
    query = f"'{PARENT_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder'"
    alpha_results = service.files().list(q=query, fields="files(id, name)").execute()
    
    for alpha in alpha_results.get('files', []):
        s_query = f"'{alpha['id']}' in parents and mimeType = 'application/vnd.google-apps.folder'"
        series_results = service.files().list(q=s_query, fields="files(id, name)").execute()
        
        for folder in series_results.get('files', []):
            name_raw = folder['name']
            if "|" not in name_raw: continue
            
            parts = [p.strip() for p in name_raw.split("|")]
            text_val = parts[0]
            dj_val = parts[1] if len(parts) > 1 else "Unknown"

            # The 'filter' defines how we check if data already exists
            filter_query = {"text": text_val}
            
            # The 'update' defines what to save/add
            update_data = {
                "$set": {
                    "reply": f"{text_val} imetafsiriwa dj {dj_val}",
                    "descp": f"imetafsiriwa dj {dj_val} Series",
                    "file": "hrm45",
                    "type": "photo",
                    "nyva": "Movietzbot",
                    "grp": ["g_1", "g_3"]
                },
                # $setOnInsert only runs if the document is brand new
                "$setOnInsert": {
                    "id": str(uuid.uuid4()),
                    "price": 0,
                    "lks": 0,
                    "btn": []
                }
            }

            # 'upsert=True' performs the "add if not present" logic
            await collection.updat   e_one(filter_query, update_data, upsert=True)
            
    return print("✅ Synchronization and deduplication complete.")

@bot.on_message(filters.command('hrm48') & filters.private)
async def on_sync(client, message):
    a=true
    botusername=await client.get_me()
    nyva=botusername.username
    nyva=str(nyva)
    status= await db.is_admin_exist(message.from_user.id,nyva) 
    if not status:
        return
    db_sts =await db.get_db_status(message.from_user.id,nyva)
    while a:
        url=message.text.split(" ")[1]
        ab = await sync_data(db_sts["token"],message.from_user.id,url) 
        await asyncio.sleep(36,000)       
@bot.on_message(filters.text & (filters.group | filters.private))
async def on_search(client, message):
    query = message.text
    user_id = message.from_user.id # Capture the original sender's ID
    results = await get_results(query)
    if not results:
        return await message.reply("❌ Hakuna matokeo yaliyopatikana.")
    await send_paged_menu(message, results, 0, query, user_id)

async def send_paged_menu(message, results, page, query, user_id):
    start, end = page * 5, (page + 1) * 5
    items = results[start:end]
    
    # Series link buttons
    buttons = [[InlineKeyboardButton(i['text'], url=f"https://t.me{i['id']}")] for i in items]
    
    # Navigation buttons (Includes user_id to lock the button)
    nav = []
    if page > 0: 
        nav.append(InlineKeyboardButton("⬅️ Back", callback_data=f"p_{page-1}_{user_id}_{query}"))
    if end < len(results): 
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"p_{page+1}_{user_id}_{query}"))
    
    if nav: buttons.append(nav)

    text = f"🔍 Matokeo ya: **{query}**\n📄 Ukurasa: {page + 1}"
    
    try:
        if hasattr(message, "edit_text"):
            await message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await message.reply(text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        print(f"Error: {e}")

@bot.on_callback_query(filters.regex(r"^p_"))
async def handle_pages(client, cb):
    # Data format: p_page_ownerID_query
    data_parts = cb.data.split("_")
    page = int(data_parts[1])
    owner_id = int(data_parts[2])
    query = data_parts[3]

    # SECURITY CHECK: Is the person clicking the button the owner?
    if cb.from_user.id != owner_id:
        return await cb.answer("🚫 Hii siyo search yako! Tafadhali tuma jina la series unayotaka mwenyewe.", show_alert=True)

    results = await get_results(query)
    await send_paged_menu(cb.message, results, page, query, owner_id)

bot.run()
