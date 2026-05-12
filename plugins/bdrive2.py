import os, uuid, asyncio, subprocess, logging, re
from moviepy.editor import VideoFileClip
from pyrogram.errors import RPCError
from info import filters
from bot import Bot0
from plugins.database import db
from plugins.pm_filter import getCreds, getCred, get_access_id
from utils import Media
import static_ffmpeg

static_ffmpeg.add_paths()

sync_lock = asyncio.Lock()
active_syncs = {}

# Quality Settings Mapping
QUALITY_MAP = {
    "low": {"crf": "30", "scale": "480:-1", "preset": "ultrafast"},
    "medium": {"crf": "24", "scale": "720:-1", "preset": "veryfast"},
    "high": {"crf": "18", "scale": "1080:-1", "preset": "medium"}
}

async def process_and_upload_video(video_obj, token, id2, c, progress_msg, user_id, quality_key):
    file_id = video_obj['id']
    unique_id = uuid.uuid4().hex[:6]
    output_file, thumb_file = f"trim_{unique_id}.mp4", f"thumb_{unique_id}.jpg"
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    q = QUALITY_MAP.get(quality_key, QUALITY_MAP["medium"])

    try:
        if active_syncs.get(user_id) == "cancel": return "Cancelled"
        await progress_msg.edit(f"📥 **Processing ({quality_key}):** `{video_obj['name']}`")
        
        # FFmpeg with Quality settings - Removed '-c copy' to allow resizing/crf
        cmd = ['ffmpeg', '-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5',
               '-headers', f'Authorization: Bearer {token}\r\n', '-ss', '00:00:00', '-i', url, 
               '-t', '600', '-vf', f"scale={q['scale']}", '-c:v', 'libx264', '-crf', q['crf'], 
               '-preset', q['preset'], '-c:a', 'aac', '-y', output_file]

        process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        while process.returncode is None:
            if active_syncs.get(user_id) == "cancel":
                process.kill(); return "Cancelled"
            try: await asyncio.wait_for(process.wait(), timeout=1.0)
            except asyncio.TimeoutError: continue

        # MoviePy for sharp duration & frame extraction
        with VideoFileClip(output_file) as clip:
            duration = int(clip.duration)
            # save_frame ensures a sharp raw frame (no blur)
            clip.save_frame(thumb_file, t=min(2, duration - 0.1) if duration > 0 else 0)

        async def progress_callback(current, total):
            if active_syncs.get(user_id) == "cancel": raise Exception("CANCEL_SIGNAL") 
            try:
                pc = (current * 100) / total
                await progress_msg.edit(f"📤 **Uploading:** `{video_obj['name']}`\n📊 {pc:.1f}%")
            except: pass

        sent_msg = await c.send_video(
            chat_id=id2, video=output_file, thumb=thumb_file, duration=duration,
            caption=f"Preview: {video_obj['name']}\nQuality: {quality_key.upper()}", 
            progress=progress_callback
        )
        return sent_msg.video.file_id

    except Exception as e:
        if "CANCEL_SIGNAL" in str(e): return "Cancelled"
        logging.error(f"Media Error: {e}"); return "hrm45"
    finally:
        for f in [output_file, thumb_file]:
            if os.path.exists(f): os.remove(f)

async def sync_data(tokeni, id2, url, c, status_msg, user_id, quality):
    service, PARENT_FOLDER_ID = getCreds(tokeni, id2), get_access_id(url)
    q_drive = f"'{PARENT_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder'"
    alpha_results = service.files().list(q=q_drive, fields="files(id, name)").execute().get('files', [])
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
            
            if await Media.collection.find_one({"text": text_val, "file": {"$ne": "hrm45"}}): continue 

            video_file = await find_video_recursive(service, folder['id'])
            tg_file_id = "hrm45"
            if video_file:
                tg_file_id = await process_and_upload_video(video_file, getCred(tokeni, id2).token, id2, c, status_msg, user_id, quality)
            
            if tg_file_id == "Cancelled": return "Cancelled"
            # ... (database update logic remains same)
            processed_count += 1
    return f"Processed {processed_count} series."

@Bot0.on_message(filters.command('hrm48') & filters.private)
async def on_sync(client, message):
    user_id = message.from_user.id
    if not await db.is_admin_exist(user_id, str((await client.get_me()).username)): return

    cmd_parts = message.text.split(" ")
    if len(cmd_parts) < 2: return await message.reply("⚠️ Usage: `/hrm48 [URL] [high/medium/low]`")

    target_url = cmd_parts[1]
    # Default to medium if quality not specified
    quality = cmd_parts[2].lower() if len(cmd_parts) > 2 and cmd_parts[2].lower() in QUALITY_MAP else "medium"

    if user_id in active_syncs:
        active_syncs[user_id] = "cancel"
        await message.reply("🛑 **Stopping previous process...**"); await asyncio.sleep(5) 

    active_syncs[user_id] = "running"
    status_msg = await message.reply(f"⏳ **Locking... Quality: {quality.upper()}**")

    async with sync_lock:
        try:
            while active_syncs.get(user_id) == "running":
                db_sts = await db.get_db_status(user_id, str((await client.get_me()).username))
                report = await sync_data(db_sts["token"], user_id, target_url, client, status_msg, user_id, quality)
                if report == "Cancelled": break
                await status_msg.edit(f"📊 **Report:** {report}\nSleeping 10 hours...")
                for _ in range(3600):
                    if active_syncs.get(user_id) != "running": break
                    await asyncio.sleep(10)
        finally:
            active_syncs.pop(user_id, None)

# find_video_recursive remains unchanged
