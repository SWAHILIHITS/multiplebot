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

async def get_video_duration(url, token):
    """Fetches video duration to handle files shorter than 10 minutes."""
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-headers', f'Authorization: Bearer {token}\r\n',
        '-of', 'default=noprint_wrappers=1:nokey=1', url
    ]
    try:
        process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, _ = await process.communicate()
        return int(float(stdout.decode().strip()))
    except Exception as e:
        logging.error(f"FFprobe Error: {e}")
        return 600

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
    file_id = video_obj['id']
    unique_id = uuid.uuid4().hex[:6]
    output_file = f"trim_{unique_id}.mp4"
    thumb_file = f"thumb_{unique_id}.jpg"
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    # 1. Wait progress for 5 seconds
    for i in range(5, 0, -1):
        await progress_msg.edit(f"⏳ **Starting in {i}s...**\n`{video_obj['name']}`")
        await asyncio.sleep(1)

    # Calculate actual duration
    actual_duration = await get_video_duration(url, token)
    trim_duration = min(actual_duration, 600)

    # FFmpeg: Trim Video
    trim_cmd = [
        'ffmpeg', '-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5',
        '-headers', f'Authorization: Bearer {token}\r\n', '-ss', '00:00:00', '-i', url, 
        '-t', str(trim_duration), '-c', 'copy', '-y', output_file
    ]
    
    try:
        await progress_msg.edit(f"📥 **Downloading:** `{video_obj['name']}`")
        process = await asyncio.create_subprocess_exec(*trim_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        await process.wait()

        # FFmpeg: Generate Thumbnail (at 2s or 0s if very short)
        thumb_ts = "00:00:02" if trim_duration > 2 else "00:00:00"
        thumb_cmd = ['ffmpeg', '-i', output_file, '-ss', thumb_ts, '-vframes', '1', '-y', thumb_file]
        thumb_proc = await asyncio.create_subprocess_exec(*thumb_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        await thumb_proc.wait()

        async def progress_callback(current, total):
            try:
                pc = (current * 100) / total
                await progress_msg.edit(f"📤 **Uploading:** `{video_obj['name']}`\n📊 {pc:.1f}%")
            except: pass

        # Upload with time range (duration) and thumbnail
        sent_msg = await c.send_video(
            chat_id=id2, 
            video=output_file, 
            thumb=thumb_file if os.path.exists(thumb_file) else None,
            duration=trim_duration,
            caption=f"Preview: {video_obj['name']}", 
            progress=progress_callback
        )
        
        # Cleanup
        for f in [output_file, thumb_file]:
            if os.path.exists(f): os.remove(f)
        return sent_msg.video.file_id

    except Exception as e:
        logging.error(f"Processing Error: {e}")
        for f in [output_file, thumb_file]:
            if os.path.exists(f): os.remove(f)
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
    
    url = cmd_parts[1]
    db_sts = await db.get_db_status(message.from_user.id, str(bot_info.username))
    status_msg = await message.reply("🚀 **Sync Initialized...**")
    
    while True:
        try:
            report = await sync_data(db_sts["token"], message.from_user.id, url, client, status_msg) 
            await status_msg.edit(f"📊 **Sync Report:**\n{report}\n\nNext sync in 10 hours.")
        except Exception as e: 
            await status_msg.edit(f"❌ **Sync Error:**\n`{e}`")
        await asyncio.sleep(36000)
