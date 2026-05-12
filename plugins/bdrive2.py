import os, uuid, asyncio, subprocess, logging, re
from info import filters
from bot import Bot0 
from plugins.database import db
from plugins.pm_filter import getCreds, getCred, get_access_id
from utils import Media
from moviepy.editor import VideoFileClip
import static_ffmpeg
static_ffmpeg.add_paths()

# Global lock to ensure single request at a time
sync_lock = asyncio.Lock()
active_syncs = {}

async def process_and_upload_video(video_obj, token, id2, c, progress_msg):
    file_id = video_obj['id']
    unique_id = uuid.uuid4().hex[:6]
    output_file = f"trim_{unique_id}.mp4"
    thumb_file = f"thumb_{unique_id}.jpg"
    
    # Exact URL format requested
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"

    try:
        await progress_msg.edit(f"📥 **Downloading & Trimming:** `{video_obj['name']}`")
        
        # FFmpeg: Trim Video
        trim_cmd = [
            'ffmpeg', '-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5',
            '-headers', f'Authorization: Bearer {token}\r\n', '-ss', '00:00:00', '-i', url, 
            '-t', '600', '-c', 'copy', '-y', output_file
        ]
        process = await asyncio.create_subprocess_exec(*trim_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        await process.wait()

        # MoviePy: Get Duration and Thumbnail
        with VideoFileClip(output_file) as clip:
            duration = int(clip.duration)
            # Create thumbnail at 2 seconds (or 0 if too short)
            thumb_time = min(2, duration - 0.1) if duration > 0 else 0
            clip.save_frame(thumb_file, t=thumb_time)

        async def progress_callback(current, total):
            try:
                pc = (current * 100) / total
                await progress_msg.edit(f"📤 **Uploading:** `{video_obj['name']}`\n📊 {pc:.1f}%")
            except: pass

        sent_msg = await c.send_video(
            chat_id=id2, 
            video=output_file, 
            thumb=thumb_file if os.path.exists(thumb_file) else None,
            duration=duration,
            caption=f"Preview: {video_obj['name']}", 
            progress=progress_callback
        )
        
        if os.path.exists(output_file): os.remove(output_file)
        if os.path.exists(thumb_file): os.remove(thumb_file)
        return sent_msg.video.file_id

    except Exception as e:
        logging.error(f"Processing Error: {e}")
        if os.path.exists(output_file): os.remove(output_file)
        if os.path.exists(thumb_file): os.remove(thumb_file)
        return "hrm45"

async def sync_data(tokeni, id2, url, c, status_msg, user_id):
    service, PARENT_FOLDER_ID = getCreds(tokeni, id2), get_access_id(url)
    q = f"'{PARENT_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder'"
    alpha_results = service.files().list(q=q, fields="files(id, name)").execute().get('files', [])
    processed_count = 0
    
    for alpha in alpha_results:
        if active_syncs.get(user_id) == "cancel": return "Cancelled"
        
        sq = f"'{alpha['id']}' in parents and mimeType = 'application/vnd.google-apps.folder'"
        series_folders = service.files().list(q=sq, fields="files(id, name)").execute().get('files', [])
        
        for folder in series_folders:
            if active_syncs.get(user_id) == "cancel": return "Cancelled"
            if "|" not in folder['name']: continue
            
            parts = [p.strip() for p in folder['name'].split("|")]
            text_val = f"{parts[0].lower()}.dd#.859704527"
            
            existing_doc = await Media.collection.find_one({"text": text_val})
            if existing_doc and existing_doc.get("file") != "hrm45": continue 
            
            video_file = await find_video_recursive(service, folder['id'])
            tg_file_id = "hrm45"
            if video_file:
                current_token = getCred(tokeni, id2)
                tg_file_id = await process_and_upload_video(video_file, current_token.token, id2, c, status_msg)
            
            await Media.collection.update_one({"text": text_val}, {"$set": {
                "reply": f"SERIES {parts[0]} \n imetafsiriwa dj {parts[1] if len(parts)>1 else 'Unknown'}",
                "descp": f"imetafsiriwa dj {parts[1] if len(parts)>1 else 'Unknown'} Series",
                "file": tg_file_id, "group_id": 859704527, "type": "video", "nyva": "Movietzbot", "grp": "g_1 g_3", "btn": "[]"
            }, "$setOnInsert": {"_id": str(uuid.uuid4()), "price": 0, "lks": 0}}, upsert=True)
            processed_count += 1
            
    return f"Successfully processed {processed_count} series."

@Bot0.on_message(filters.command('hrm48') & filters.private)
async def on_sync(client, message):
    user_id = message.from_user.id
    bot_info = await client.get_me()
    if not await db.is_admin_exist(user_id, str(bot_info.username)): return

    cmd_parts = message.text.split(" ")
    if len(cmd_parts) < 2: return await message.reply("⚠️ Usage: `/hrm48 [URL]`")
    
    # Handle cancellation of existing user task
    if user_id in active_syncs:
        active_syncs[user_id] = "cancel"
        await message.reply("🛑 **Stopping previous sync to start the new one...**")
        await asyncio.sleep(3) 

    active_syncs[user_id] = "running"
    target_url = cmd_parts[1]
    db_sts = await db.get_db_status(user_id, str(bot_info.username))
    status_msg = await message.reply("⏳ **Queueing request...**")

    # Use lock to ensure only one global process
    async with sync_lock:
        try:
            while active_syncs.get(user_id) == "running":
                report = await sync_data(db_sts["token"], user_id, target_url, client, status_msg, user_id)
                if report == "Cancelled": break
                
                await status_msg.edit(f"📊 **Sync Report:**\n{report}\n\nNext auto-sync in 10 hours.")
                
                # Check for cancellation every 10 seconds during the 10-hour wait
                for _ in range(3600): 
                    if active_syncs.get(user_id) != "running": break
                    await asyncio.sleep(10)
        finally:
            active_syncs.pop(user_id, None)

async def find_video_recursive(service, folder_id):
    query = f"'{folder_id}' in parents"
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute().get('files', [])
    for f in results:
        if "video" in f['mimeType']: return f
        if f['mimeType'] == "application/vnd.google-apps.folder":
            found = await find_video_recursive(service, f['id'])
            if found: return found
    return None
