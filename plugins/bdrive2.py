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

# Tracks active task IDs per user to allow concurrency and instant cancellation
active_syncs = {}

# Quality Settings Mapping
QUALITY_MAP = {
    "low": {"crf": "30", "scale": "480:-1", "preset": "ultrafast"},
    "medium": {"crf": "24", "scale": "720:-1", "preset": "veryfast"},
    "high": {"crf": "18", "scale": "1080:-1", "preset": "medium"}
}

async def get_remote_duration(url, token):
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', 
           '-headers', f'Authorization: Bearer {token}\r\n', url]
    try:
        process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, _ = await process.communicate()
        return float(stdout.decode().strip())
    except:
        return 600

async def process_and_upload_video(video_obj, token, id2, c, progress_msg, user_id, quality_key, task_id):
    file_id = video_obj['id']
    unique_id = uuid.uuid4().hex[:6]
    output_file, thumb_file = f"trim_{unique_id}.mp4", f"thumb_{unique_id}.jpg"
    
    # Exact Stream URL
    url = f"https://googleapis.com{file_id}?alt=media"
    
    q = QUALITY_MAP.get(quality_key, QUALITY_MAP["medium"])

    try:
        if active_syncs.get(user_id) != task_id: return "Cancelled"
        remote_dur = await get_remote_duration(url, token)
        trim_time = min(remote_dur, 600)
        
        await progress_msg.edit(f"📥 **Processing:** `{video_obj['name']}`\nLength: {int(trim_time)}s")
        
        cmd = ['ffmpeg', '-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5',
               '-headers', f'Authorization: Bearer {token}\r\n', '-ss', '00:00:00', '-i', url, 
               '-t', str(trim_time), '-vf', f"scale={q['scale']}", '-c:v', 'libx264', '-crf', q['crf'], 
               '-preset', q['preset'], '-c:a', 'aac', '-y', output_file]

        process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        while process.returncode is None:
            if active_syncs.get(user_id) != task_id:
                process.kill()
                return "Cancelled"
            try:
                await asyncio.wait_for(process.wait(), timeout=1.0)
            except asyncio.TimeoutError: continue

        with VideoFileClip(output_file) as clip:
            final_duration = int(clip.duration)
            thumb_ts = 20 if final_duration > 20 else max(0, final_duration - 0.1)
            clip.save_frame(thumb_file, t=thumb_ts)

        async def progress_callback(current, total):
            if active_syncs.get(user_id) != task_id: raise Exception("CANCEL_SIGNAL") 
            try:
                pc = (current * 100) / total
                await progress_msg.edit(f"📤 **Uploading:** `{video_obj['name']}`\n📊 {pc:.1f}%")
            except: pass

        sent_msg = await c.send_video(
            chat_id=id2, video=output_file, thumb=thumb_file, duration=final_duration,
            caption=f"Preview: {video_obj['name']}\nQuality: {quality_key.upper()}", 
            progress=progress_callback
        )
        return sent_msg.video.file_id
    except Exception as e:
        if "CANCEL_SIGNAL" in str(e): return "Cancelled"
        logging.error(f"Media Error: {e}")
        return "hrm45"
    finally:
        for f in [output_file, thumb_file]:
            if os.path.exists(f): os.remove(f)

async def sync_data(tokeni, id2, url, c, status_msg, user_id, quality, task_id, bot_username):
    try:
        service, PARENT_FOLDER_ID = getCreds(tokeni, id2), get_access_id(url)
        q = f"'{PARENT_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder'"
        alpha_results = service.files().list(q=q, fields="files(id, name)").execute().get('files', [])
        processed_count = 0

        for alpha in alpha_results:
            if active_syncs.get(user_id) != task_id: return "Cancelled"
            sq = f"'{alpha['id']}' in parents and mimeType = 'application/vnd.google-apps.folder'"
            series_folders = service.files().list(q=sq, fields="files(id, name)").execute().get('files', [])
            
            for folder in series_folders:
                if active_syncs.get(user_id) != task_id: return "Cancelled"
                if "|" not in folder['name']: continue
                
                parts = [p.strip() for p in folder['name'].split("|")]
                base_name, dj_val = parts[0], parts[1] if len(parts) > 1 else 'Unknown'
                
                name_val = base_name.upper()
                text_val = f"{base_name.lower()}.dd#.{id2}"
                
                # Check for same name but different DJ to add suffix (a, b, c...)
                existing_doc = await Media.collection.find_one({"text": text_val})
                if existing_doc and dj_val.lower() not in existing_doc.get("reply", "").lower():
                    for letter in "abcdefghijklmnopqrstuvwxyz":
                        suffix_name = f"{base_name.lower()} {letter}"
                        temp_text = f"{suffix_name}.dd#.{id2}"
                        check = await Media.collection.find_one({"text": temp_text})
                        if not check or dj_val.lower() in check.get("reply", "").lower():
                            name_val, text_val = suffix_name.upper(), temp_text
                            break

                # Re-check record for resolved text_val to decide on processing
                existing_record = await Media.collection.find_one({"text": text_val})
                tg_file_id = existing_record.get("file") if existing_record else None

                if not tg_file_id or tg_file_id == "hrm45":
                    v_q = f"'{folder['id']}' in parents and mimeType contains 'video/'"
                    video_list = service.files().list(q=v_q, fields="files(id, name)").execute().get('files', [])
                    
                    # Try up to 5 videos if FFmpeg fails
                    for i, video_file in enumerate(video_list[:5]):
                        if active_syncs.get(user_id) != task_id: return "Cancelled"
                        await status_msg.edit(f"🎬 **Attempt {i+1}/5 for:** `{name_val}`")
                        tg_file_id = await process_and_upload_video(video_file, getCred(tokeni, id2).token, id2, c, status_msg, user_id, quality, task_id)
                        if tg_file_id not in ["hrm45", "Cancelled"]: break

                if tg_file_id and tg_file_id != "Cancelled":
                    # Exact Folder URL
                    folder_url = f"https://google.com{folder['id']}"
                    
                    await Media.collection.update_one({"text": text_val}, {
                        "$set": {
                            "reply": f"SERIES {name_val} \n imetafsiriwa dj {dj_val}",
                            "file": tg_file_id, 
                            "group_id": id2, 
                            "type": "video", 
                            "nyva": bot_username
                        },
                        "$setOnInsert": {
                            "_id": str(uuid.uuid4()), 
                            "descp": f"x.dd#.imetafsiriwa na {dj_val}\n Series.dd#.{folder_url}.dd#.s",
                            "price": 3000, 
                            "lks": 0, 
                            "grp": "g_1 g_3", 
                            "btn": "[]"
                        }
                    }, upsert=True)
                    processed_count += 1
        return f"Processed {processed_count} series."
    except Exception as e: return f"Sync Error: {str(e)}"

@Bot0.on_message(filters.command('hrm48') & filters.private)
async def on_sync(client, message):
    user_id = message.from_user.id
    bot_info = await client.get_me()
    if not await db.is_admin_exist(user_id, str(bot_info.username)): return

    cmd_parts = message.text.split(" ")
    if len(cmd_parts) < 2: return await message.reply("⚠️ Usage: `/hrm48 [URL] [quality]`")

    target_url = cmd_parts[1]
    quality = cmd_parts[2].lower() if len(cmd_parts) > 2 and cmd_parts[2].lower() in QUALITY_MAP else "medium"
    
    task_id = str(uuid.uuid4())
    active_syncs[user_id] = task_id

    status_msg = await message.reply(f"🚀 **Sync Started...**\nBot: @{bot_info.username}\nQuality: {quality.upper()}")

    try:
        while active_syncs.get(user_id) == task_id:
            db_sts = await db.get_db_status(user_id, str(bot_info.username))
            report = await sync_data(db_sts["token"], user_id, target_url, client, status_msg, user_id, quality, task_id, bot_info.username)
            
            if report == "Cancelled":
                await status_msg.edit("🛑 **Process stopped.**")
                break
                
            await status_msg.edit(f"📊 **Final Report:** {report}\nSleeping for check...")
            
            # Monitoring loop (keeps alive for new files or cancellation)
            for _ in range(3600):
                if active_syncs.get(user_id) != task_id: break
                await asyncio.sleep(10)
    finally:
        if active_syncs.get(user_id) == task_id: 
            active_syncs.pop(user_id, None)
