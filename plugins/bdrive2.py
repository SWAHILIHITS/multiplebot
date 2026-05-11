import os
import uuid
import asyncio
import subprocess
import logging
from info import filters
from bot import Bot0
from plugins.database import db
from plugins.pm_filter import getCreds,get_access_id
from utils import Media
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# --- HELPER: RECURSIVE SEARCH ---
async def find_video_recursive(service, folder_id):
    """Digs into subfolders until it finds a video file."""
    query = f"'{folder_id}' in parents"
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute().get('files', [])
    
    for f in results:
        if "video" in f['mimeType']:
            return f
        if f['mimeType'] == "application/vnd.google-apps.folder":
            found = await find_video_recursive(service, f['id'])
            if found: return found
    return None

# --- HELPER: VIDEO PROCESSING & UPLOAD ---
async def process_and_upload_video(service, video_obj, token,id2,c):
    """Trims 10 mins using FFmpeg and uploads to Telegram."""
    file_id = video_obj['id']
    file_name = video_obj['name'].lower()
    url = f"https://googleapis.com{file_id}?alt=media"
    output_file = f"trim_{uuid.uuid4().hex[:6]}.mp4"
    
    # Check if we should copy (fast) or convert (slow)
    if file_name.endswith(('.mp4', '.mkv', '.mov')):
        codec_settings = ['-c', 'copy']
    else:
        # Convert non-standard files to MP4
        codec_settings = ['-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac']

    # FFmpeg Command: -t 600 (10 mins)
    cmd = [
        'ffmpeg', '-headers', f'Authorization: Bearer {token}',
        '-i', url, '-ss', '00:00:00', '-t', '600'
    ] + codec_settings + ['-y', output_file]
    
    try:
        process = subprocess.run(cmd, capture_output=True, text=True)
        if process.returncode != 0:
            logging.error(f"FFmpeg Error: {process.stderr}")
            return "hrm45"

        # Upload to the specific Telegram Channel
        sent_msg = await c.send_video(
            chat_id=id2, 
            video=output_file, 
            caption=f"Preview: {video_obj['name']}"
        )
        
        if os.path.exists(output_file):
            os.remove(output_file)
            
        return sent_msg.video.file_id
    except Exception as e:
        logging.error(f"Upload Error: {e}")
        if os.path.exists(output_file): os.remove(output_file)
        return "hrm45"

# --- CORE: SYNC DATA ---
async def sync_data(tokeni, id2, url,c):
    service = getCreds(tokeni, id2)
    PARENT_FOLDER_ID = get_access_id(url)
    
    # Get A-Z Folders
    q = f"'{PARENT_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder'"
    alpha_results = service.files().list(q=q, fields="files(id, name)").execute().get('files', [])
    
    processed_count = 0
    for alpha in alpha_results:
        sq = f"'{alpha['id']}' in parents and mimeType = 'application/vnd.google-apps.folder'"
        series_folders = service.files().list(q=sq, fields="files(id, name)").execute().get('files', [])
        
        for folder in series_folders:
            if "|" not in folder['name']: continue
            
            parts = [p.strip() for p in folder['name'].split("|")]
            text_val2 = parts[0]
            text_val = f"{parts[0].lower()}.dd#.859704527"
            dj_val = parts[1] if len(parts) > 1 else "Unknown"

            # --- SKIP LOGIC ---
            existing_doc = await Media.collection.find_one({"text": text_val})
            if existing_doc and existing_doc.get("file") != "hrm45":
                continue # Skip already processed series
            
            # --- PROCESS NEW OR 'hrm45' SERIES ---
            video_file = await find_video_recursive(service, folder['id'])
            tg_file_id = "hrm45"
            
            if video_file:
                tg_file_id = await process_and_upload_video(service, video_file, tokeni,id2,c)

            update_data = {
                "$set": {
                    "reply": f"SERIES {text_val2} \n imetafsiriwa dj {dj_val}",
                    "descp": f"imetafsiriwa dj {dj_val} Series",
                    "file": tg_file_id,
                    "group_id": 859704527,
                    "type": "video",
                    "nyva": "Movietzbot",
                    "grp": "g_1 g_3",
                    "btn": "[]"
                },
                "$setOnInsert": {
                    "_id": str(uuid.uuid4()),
                    "price": 0,
                    "lks": 0
                }
            }
            await Media.collection.update_one({"text": text_val}, update_data, upsert=True)
            processed_count += 1
            
    return f"Successfully processed {processed_count} series."

# --- BOT COMMAND: START SYNC ---
@Bot0.on_message(filters.command('hrm48') & filters.private)
async def on_sync(client, message):
    bot_info = await client.get_me()
    nyva = str(bot_info.username)
    
    if not await db.is_admin_exist(message.from_user.id, nyva):
        return

    cmd_parts = message.text.split(" ")
    if len(cmd_parts) < 2:
        return await message.reply("⚠️ Usage: `/hrm48 [GDRIVE_URL]`")
    
    url = cmd_parts[1]
    db_sts = await db.get_db_status(message.from_user.id, nyva)
    await message.reply("✅ Sync Started. Running every 10 hours.")

    while True:
        try:
            logging.info("Starting GDrive Sync Cycle...")
            report = await sync_data(db_sts["token"], message.from_user.id, url,client) 
            await client.send_message(chat_id=message.from_user.id, text=f"📊 **Sync Report:**\n{report}")
        except Exception as e:
            logging.error(f"Sync Loop Error: {e}")
            await client.send_message(message.from_user.id, f"❌ **Sync Error:**\n`{e}`")
        
        await asyncio.sleep(36000) # 10 Hours
