import os, uuid, asyncio, subprocess, logging, re
from info import filters
from bot import Bot0
from plugins.database import db
from plugins.pm_filter import getCreds, getCred, get_access_id
from utils import Media
from moviepy.editor import VideoFileClip
from pyrogram.errors import RPCError
import static_ffmpeg
static_ffmpeg.add_paths()

sync_lock = asyncio.Lock()
active_syncs = {}

async def process_and_upload_video(video_obj, token, id2, c, progress_msg, user_id):
    file_id, unique_id = video_obj['id'], uuid.uuid4().hex[:6]
    output_file, thumb_file = f"trim_{unique_id}.mp4", f"thumb_{unique_id}.jpg"
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"

    try:
        if active_syncs.get(user_id) == "cancel": return "Cancelled"
        await progress_msg.edit(f"📥 **Downloading:** `{video_obj['name']}`")
        
        trim_cmd = [
            'ffmpeg', '-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5',
            '-headers', f'Authorization: Bearer {token}\r\n', '-ss', '00:00:00', '-i', url, 
            '-t', '600', '-c', 'copy', '-y', output_file
        ]
        
        process = await asyncio.create_subprocess_exec(*trim_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        # Monitor FFmpeg for cancellation
        while process.returncode is None:
            if active_syncs.get(user_id) == "cancel":
                process.kill()
                return "Cancelled"
            try:
                await asyncio.wait_for(process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                continue

        with VideoFileClip(output_file) as clip:
            duration = int(clip.duration)
            clip.save_frame(thumb_file, t=min(2, duration - 0.1) if duration > 0 else 0)

        async def progress_callback(current, total):
            if active_syncs.get(user_id) == "cancel":
                raise Exception("User Cancelled") # Break the upload
            try:
                pc = (current * 100) / total
                await progress_msg.edit(f"📤 **Uploading:** `{video_obj['name']}`\n📊 {pc:.1f}%")
            except: pass

        sent_msg = await c.send_video(
            chat_id=id2, video=output_file, thumb=thumb_file, duration=duration,
            caption=f"Preview: {video_obj['name']}", progress=progress_callback
        )
        return sent_msg.video.file_id

    except Exception as e:
        if "User Cancelled" in str(e): return "Cancelled"
        logging.error(f"Media Error: {e}")
        return "hrm45"
    finally:
        for f in [output_file, thumb_file]:
            if os.path.exists(f): os.remove(f)

async def sync_data(tokeni, id2, url, c, status_msg, user_id):
    try:
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
                
                if await Media.collection.find_one({"text": text_val, "file": {"$ne": "hrm45"}}): continue 
                
                video_file = await find_video_recursive(service, folder['id'])
                tg_file_id = "hrm45"
                if video_file:
                    tg_file_id = await process_and_upload_video(video_file, getCred(tokeni, id2).token, id2, c, status_msg, user_id)
                
                if tg_file_id == "Cancelled": return "Cancelled"

                await Media.collection.update_one({"text": text_val}, {"$set": {
                    "reply": f"SERIES {parts[0]} \n imetafsiriwa dj {parts[1] if len(parts)>1 else 'Unknown'}",
                    "descp": f"imetafsiriwa dj {parts[1] if len(parts)>1 else 'Unknown'} Series",
                    "file": tg_file_id, "group_id": 859704527, "type": "video", "nyva": "Movietzbot", "grp": "g_1 g_3", "btn": "[]"
                }, "$setOnInsert": {"_id": str(uuid.uuid4()), "price": 0, "lks": 0}}, upsert=True)
                processed_count += 1
        return f"Successfully processed {processed_count} series."
    except Exception as e:
        return f"Google API Error: {str(e)}"

@Bot0.on_message(filters.command('hrm48') & filters.private)
async def on_sync(client, message):
    user_id = message.from_user.id
    bot_info = await client.get_me()
    if not await db.is_admin_exist(user_id, str(bot_info.username)): return
    
    cmd_parts = message.text.split(" ")
    if len(cmd_parts) < 2: return await message.reply("⚠️ Usage: `/hrm48 [URL]`")

    if user_id in active_syncs:
        active_syncs[user_id] = "cancel"
        await message.reply("🛑 **Cancellation signal sent. Starting new sync shortly...**")
        await asyncio.sleep(5) 

    active_syncs[user_id] = "running"
    status_msg = await message.reply("⏳ **Queueing...**")

    async with sync_lock:
        try:
            while active_syncs.get(user_id) == "running":
                db_sts = await db.get_db_status(user_id, str(bot_info.username))
                report = await sync_data(db_sts["token"], user_id, cmd_parts[1], client, status_msg, user_id)
                
                if report == "Cancelled":
                    await status_msg.edit("✅ **Process Cancelled Successfully.**")
                    break
                
                await status_msg.edit(f"📊 **Sync Report:**\n{report}\n\nSleeping 10 hours...")
                for _ in range(3600):
                    if active_syncs.get(user_id) != "running": break
                    await asyncio.sleep(10)
        except RPCError as e:
            await message.reply(f"❌ **Telegram Error:** `{e.MESSAGE}`")
        except Exception as e:
            await message.reply(f"❌ **Unexpected Error:** `{e}`")
        finally:
            active_syncs.pop(user_id, None)

async def find_video_recursive(service, folder_id):
    try:
        results = service.files().list(q=f"'{folder_id}' in parents", fields="files(id, name, mimeType)").execute().get('files', [])
        for f in results:
            if "video" in f['mimeType']: return f
            if f['mimeType'] == "application/vnd.google-apps.folder":
                found = await find_video_recursive(service, f['id'])
                if found: return found
    except: pass
    return None
