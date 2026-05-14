import os, uuid, asyncio, subprocess, logging, re, shutil
import io
from moviepy.editor import VideoFileClip
from pyrogram import filters
from bot import Bot0
from plugins.database import db
from plugins.pm_filter import getCreds, getCred, get_access_id
from utils import Media
import static_ffmpeg
from googleapiclient.http import MediaIoBaseDownload

static_ffmpeg.add_paths()
active_syncs = {}

QUALITY_MAP = {
    "low": {"crf": "30", "scale": "480:-2", "preset": "ultrafast"},
    "medium": {"crf": "24", "scale": "720:-2", "preset": "veryfast"},
    "high": {"crf": "18", "scale": "1080:-2", "preset": "medium"}
}

async def proc_vid(v_obj, token, id2, c, msg, u_id, q_key, t_id, svc):
    f_id, u_hex = v_obj['id'], uuid.uuid4().hex[:6]
    out, thumb = f"tr_{u_hex}.mp4", f"th_{u_hex}.jpg"
    local_download = f"dl_{u_hex}.mp4"
    q = QUALITY_MAP.get(q_key, QUALITY_MAP["medium"])
    
    ffmpeg_exe = shutil.which("ffmpeg") or "ffmpeg"
    
    try:
        if active_syncs.get(u_id) != t_id: return "Cancelled"
        
        # Explicit Google API Media Request URL Logic
        url = f"https://www.googleapis.com/drive/v3/files/{f_id}?alt=media"
        request = svc.files().get_media(fileId=f_id)
        
        with io.FileIO(local_download, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request, chunksize=1024*1024*5)
            done = False
            last_step = -1
            
            while not done:
                if active_syncs.get(u_id) != t_id: return "Cancelled"
                status, done = downloader.next_chunk()
                
                percent = int(status.progress() * 100)
                current_step = (percent // 10) * 10
                
                if current_step > last_step or done:
                    try: 
                        await msg.edit(f"📥 **Downloading Media:** `{v_obj['name']}`\n📊 {percent}%")
                        last_step = current_step
                    except Exception as e:
                        logging.warning(f"Download edit skipped: {e}")

        await msg.edit(f"⚙️ **Converting Localized Media...**")
        
        cmd = [
            ffmpeg_exe, '-err_detect', 'ignore_err', '-loglevel', 'error',
            '-ss', '00:00:00', '-i', local_download, '-t', '600', 
            '-vf', f"scale={q['scale']}", '-c:v', 'libx264', '-crf', q['crf'], 
            '-preset', q['preset'], '-c:a', 'aac', '-sn', '-y', out
        ]
        
        p = await asyncio.create_subprocess_exec(
            *cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            env=os.environ.copy()
        )
        stdout, stderr = await p.communicate()
        
        if p.returncode != 0 or not os.path.exists(out) or os.path.getsize(out) == 0:
            err_msg = stderr.decode().strip() if stderr else "Unknown Binary Processing Fault"
            logging.error(f"FFmpeg Crash Context Logs: {err_msg}")
            raise Exception(f"FFmpeg failed with exit code {p.returncode}. Reason: {err_msg}")
            
        clip = VideoFileClip(out)
        f_dur = int(clip.duration)
        clip.save_frame(thumb, t=20 if f_dur > 20 else max(0, f_dur-0.1))
        clip.close()
        
        last_upload_step = [-1]

        async def prog(cur, tot):
            if active_syncs.get(u_id) != t_id: raise Exception("CANCEL")
            
            percent = int((cur * 100) / tot)
            current_step = (percent // 10) * 10
            
            if current_step > last_upload_step or cur == tot:
                try: 
                    await msg.edit(f"📤 **Uploading Preview:** `{v_obj['name']}`\n📊 {percent}%")
                    last_upload_step = current_step
                except Exception as e: 
                    logging.warning(f"Upload edit skipped: {e}")
            
        res = await c.send_video(id2, video=out, thumb=thumb, duration=f_dur, caption=f"Preview: {v_obj['name']}", progress=prog)
        return res.video.file_id
        
    except Exception as e:
        logging.error(f"Execution handling failure: {e}")
        return "Cancelled" if "CANCEL" in str(e) else "hrm45"
    finally:
        for f in [out, thumb, local_download]:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass

async def sync_data(tok, id2, url, c, msg, u_id, qual, t_id, b_name):
    df_img = "https://i.ibb.co/3yDbR1fR/image.jpg"
    try:
        svc, P_ID = getCreds(tok, id2), get_access_id(url)
        alpha = svc.files().list(q=f"'{P_ID}' in parents and mimeType='application/vnd.google-apps.folder'", fields="files(id, name)").execute().get('files', [])
        cnt = 0
        for a in alpha:
            folders = svc.files().list(q=f"'{a['id']}' in parents and mimeType='application/vnd.google-apps.folder'", fields="files(id, name)").execute().get('files', [])
            for f in folders:
                if active_syncs.get(u_id) != t_id: return "Cancelled"
                if "|" not in f['name']: continue
                
                parts = [p.strip() for p in f['name'].split("|")]
                bn = parts[0]
                dj = parts[1] if len(parts) > 1 else 'Unknown'
                
                nv, tv = bn.upper(), f"{bn.lower()}.dd#.{id2}"
                
                ext = await Media.collection.find_one({"text": tv})
                if ext and dj.lower() not in ext.get("reply", "").lower():
                    for l in "abcdefg":
                        sn, st = f"{bn.lower()} {l}", f"{bn.lower()} {l}.dd#.{id2}"
                        chk = await Media.collection.find_one({"text": st})
                        if not chk or dj.lower() in chk.get("reply", "").lower(): 
                            nv, tv, ext = sn.upper(), st, chk
                            break

                cur_f = ext.get("file", df_img) if ext else df_img
                cur_t = "Video" if cur_f != df_img else "Photo"

                if cur_f == df_img:
                    vids = svc.files().list(q=f"'{f['id']}' in parents and mimeType contains 'video/'", fields="files(id, name)").execute().get('files', [])
                    
                    # Deep-subfolder fall-back block if no video is directly found
                    if not vids:
                        vids = svc.files().list(q=f"'{f['id']}' in parents and mimeType contains 'video/' and trashed = false", fields="files(id, name)").execute().get('files', [])
                        if not vids:
                            # Runs transitive search across all subdirectories inside folder f
                            vids = svc.files().list(q=f"recursive=true and '{f['id']}' in parents and mimeType contains 'video/'", fields="files(id, name)").execute().get('files', [])
                    
                    for i, v in enumerate(vids[:5]):
                        if active_syncs.get(u_id) != t_id: return "Cancelled"
                        new_id = await proc_vid(v, getCred(tok, id2).token, id2, c, msg, u_id, qual, t_id, svc)
                        if new_id not in ["hrm45", "Cancelled"]: 
                            cur_f, cur_t = new_id, "Video"
                            break
                
                f_url = f"https://drive.google.com/drive/folders/{f['id']}"
                await Media.collection.update_one({"text": tv}, {"$set": {
                    "reply": f"SERIES {nv}\nimetafsiriwa dj {dj}",
                    "file": cur_f, "type": cur_t, "group_id": id2, "nyva": b_name,
                    "descp": f"x.dd#.imetafsiriwa na {dj}\nSeries.dd#.{f_url}.dd#.s"
                }, "$setOnInsert": {
                    "_id": str(uuid.uuid4()), "price": 3000, "lks": 0, "grp": "g_1 g_3", "btn": "[]"
                }}, upsert=True)
                cnt += 1
        return f"Processed {cnt} series."
    except Exception as e: return f"Error: {e}"

@Bot0.on_message(filters.command('hrm48') & filters.private)
async def on_sync(c, m):
    u_id, bot = m.from_user.id, await c.get_me()
    if not await db.is_admin_exist(u_id, bot.username): return
    p = m.text.split(" ")
    if len(p) < 2: return await m.reply("⚠️ Usage: `/hrm48 [URL] [quality]`")
    url = p[1]
    q = p[2].lower() if len(p) > 2 and p[2].lower() in QUALITY_MAP else "medium"
    tid = str(uuid.uuid4()); active_syncs[u_id] = tid
    sts = await m.reply(f"🚀 **Sync Started...**\nBot: @{bot.username}")
    try:
        while active_syncs.get(u_id) == tid:
            db_s = await db.get_db_status(u_id, bot.username)
            rep = await sync_data(db_s["token"], u_id, url, c, sts, u_id, q, tid, bot.username)
            if rep == "Cancelled": break
            await sts.edit(f"📊 **Report:** {rep}\n🕒 Next run in 1 hour.")
            for _ in range(360):
                if active_syncs.get(u_id) != tid: break
                await asyncio.sleep(10)
    finally: (active_syncs.pop(u_id) if active_syncs.get(u_id) == tid else None)

@Bot0.on_message(filters.command('stop') & filters.private)
async def on_stop(c, m):
    if active_syncs.pop(m.from_user.id, None): await m.reply("🛑 **Stopped.**")
    else: await m.reply("❌ No active sync.")
