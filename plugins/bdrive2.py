import os, uuid, asyncio, subprocess, logging, re
from tqdm import tqdm
from info import filters
from bot import Bot0
from plugins.database import db
from plugins.pm_filter import getCreds, getCred, get_access_id
from utils import Media
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import static_ffmpeg
static_ffmpeg.add_paths()

async def find_video_recursive(service, folder_id):
    query = f"'{folder_id}' in parents"
    try:
        results = service.files().list(q=query, fields="files(id, name, mimeType)").execute().get('files', [])
    except Exception as e:
        logging.error(f"List Error: {e}"); return None
    for f in results:
        if "video" in f['mimeType']: return f
        if f['mimeType'] == "application/vnd.google-apps.folder":
            found = await find_video_recursive(service, f['id'])
            if found: return found
    return None

async def process_and_upload_video(video_obj, token, id2, c, progress_msg):
    file_id, output_file = video_obj['id'], f"trim_{uuid.uuid4().hex[:6]}.mp4"
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    cmd = ['ffmpeg', '-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5',
           '-headers', f'Authorization: Bearer {token}\r\n', '-ss', '00:00:00', '-i', url, 
           '-t', '600', '-progress', 'pipe:1', '-c', 'copy', '-y', output_file]
    try:
        await progress_msg.edit(f"📥 **Downloading:** `{video_obj['name']}`")
        process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        await process.wait()
        async def progress_callback(current, total):
            try:
                pc = (current * 100) / total
                await progress_msg.edit(f"📤 **Uploading:** `{video_obj['name']}`\n📊 {pc:.1f}%")
            except: pass
        sent_msg = await c.send_video(chat_id=id2, video=output_file, caption=f"Preview: {video_obj['name']}", progress=progress_callback)
        if os.path.exists(output_file): os.remove(output_file)
        return sent_msg.video.file_id
    except Exception as e:
        logging.error(f"Error: {e}")
        if os.path.exists(output_file): os.remove(output_file)
        return "hrm45"

async def sync_data(tokeni, id2, url, c, status_msg):
    service, PARENT_FOLDER_ID = getCreds(tokeni, id2), get_access_id(url)
    q = f"'{PARENT_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder'"
    alpha_results = service.files().list(q=q, fields="files(id, name)").execute().get('files', [])
    processed_count = 0
    for alpha in alpha_results:
        sq = f"'{alpha['id']}' in parents and mimeType = 'application/vnd.google-apps.folder'"
        series_folders = service.files().list(q=sq, fields="files(id, name)").execute().get('files', [])
        for folder in series_folders:
            if "|" not in folder['name']: continue
            parts = [p.strip() for p in folder['name'].split("|")]
            text_val = f"{parts[0].lower()}.dd#.859704527"
            existing_doc = await Media.collection.find_one({"text": text_val})
            if existing_doc and existing_doc.get("file") != "hrm45": continue 
            video_file = await find_video_recursive(service, folder['id'])
            tg_file_id = "hrm45"
            if video_file:
                try:
                    current_token = getCred(tokeni, id2)
                    tg_file_id = await process_and_upload_video(video_file, current_token.token, id2, c, status_msg)
                except Exception as e: logging.error(f"Token Error: {e}")
            await Media.collection.update_one({"text": text_val}, {"$set": {
                "reply": f"SERIES {parts[0]} \n imetafsiriwa dj {parts[1] if len(parts)>1 else 'Unknown'}",
                "descp": f"imetafsiriwa dj {parts[1] if len(parts)>1 else 'Unknown'} Series",
                "file": tg_file_id, "group_id": 859704527, "type": "video", "nyva": "Movietzbot", "grp": "g_1 g_3", "btn": "[]"
            }, "$setOnInsert": {"_id": str(uuid.uuid4()), "price": 0, "lks": 0}}, upsert=True)
            processed_count += 1
    return f"Successfully processed {processed_count} series."

@Bot0.on_message(filters.command('hrm48') & filters.private)
async def on_sync(client, message):
    bot_info = await client.get_me()
    if not await db.is_admin_exist(message.from_user.id, str(bot_info.username)): return
    cmd_parts = message.text.split(" ")
    if len(cmd_parts) < 2: return await message.reply("⚠️ Usage: `/hrm48 [URL]`")
    url, db_sts = cmd_parts[1], await db.get_db_status(message.from_user.id, str(bot_info.username))
    status_msg = await message.reply("🚀 **Sync Initialized...**")
    while True:
        try:
            report = await sync_data(db_sts["token"], message.from_user.id, url, client, status_msg) 
            await status_msg.edit(f"📊 **Sync Report:**\n{report}\n\nNext sync in 10 hours.")
        except Exception as e: await status_msg.edit(f"❌ **Sync Error:**\n`{e}`")
        await asyncio.sleep(36000)
