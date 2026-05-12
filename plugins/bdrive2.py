import os, uuid, asyncio, subprocess, logging, re
from moviepy.editor import VideoFileClip
from pyrogram import filters
from bot import Bot0
from plugins.database import db
from plugins.pm_filter import getCreds, getCred, get_access_id
from utils import Media
import static_ffmpeg

static_ffmpeg.add_paths()
active_syncs = {}
QUALITY_MAP = {
    "low": {"crf": "30", "scale": "480:-1", "preset": "ultrafast"},
    "medium": {"crf": "24", "scale": "720:-1", "preset": "veryfast"},
    "high": {"crf": "18", "scale": "1080:-1", "preset": "medium"}
}

async def get_remote_dur(url, token):
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', '-headers', f'Authorization: Bearer {token}\r\n', url]
    try:
        p = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out, _ = await p.communicate()
        return float(out.decode().strip())
    except: return 600

async def proc_vid(v_obj, token, id2, c, msg, u_id, q_key, t_id):
    f_id, u_hex = v_obj['id'], uuid.uuid4().hex[:6]
    out, thumb = f"tr_{u_hex}.mp4", f"th_{u_hex}.jpg"
    url = f"https://www.googleapis.com/drive/v3/files/{f_id}?alt=media"
    q = QUALITY_MAP.get(q_key, QUALITY_MAP["medium"])
    try:
        if active_syncs.get(u_id) != t_id: return "Cancelled"
        dur = min(await get_remote_dur(url, token), 600)
        await msg.edit(f"📥 **Processing:** `{v_obj['name']}`\nForce: YES")
        cmd = ['ffmpeg', '-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5', '-headers', f'Authorization: Bearer {token}\r\n', '-ss', '00:00:00', '-i', url, '-t', str(dur), '-vf', f"scale={q['scale']}", '-c:v', 'libx264', '-crf', q['crf'], '-preset', q['preset'], '-c:a', 'aac', '-y', out]
        p = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        await p.wait()
        with VideoFileClip(out) as clip:
            f_dur = int(clip.duration)
            clip.save_frame(thumb, t=20 if f_dur > 20 else max(0, f_dur-0.1))
        async def prog(c, t):
            if active_syncs.get(u_id) != t_id: raise Exception("CANCEL")
            try: await msg.edit(f"📤 **Uploading:** `{v_obj['name']}`\n📊 {(c*100)/t:.1f}%")
            except: pass
        res = await c.send_video(id2, video=out, thumb=thumb, duration=f_dur, caption=f"Preview: {v_obj['name']}\nQuality: {q_key.upper()}", progress=prog)
        return res.video.file_id
    except Exception as e:
        logging.error(f"Error: {e}"); return "Cancelled" if "CANCEL" in str(e) else "hrm45"
    finally:
        for f in [out, thumb]: (os.remove(f) if os.path.exists(f) else None)

async def sync_data(tok, id2, url, c, msg, u_id, qual, t_id, b_name):
    try:
        svc, P_ID = getCreds(tok, id2), get_access_id(url)
        alpha = svc.files().list(q=f"'{P_ID}' in parents and mimeType='application/vnd.google-apps.folder'", fields="files(id, name)").execute().get('files', [])
        cnt = 0
        for a in alpha:
            if active_syncs.get(u_id) != t_id: return "Cancelled"
            folders = svc.files().list(q=f"'{a['id']}' in parents and mimeType='application/vnd.google-apps.folder'", fields="files(id, name)").execute().get('files', [])
            for f in folders:
                if active_syncs.get(u_id) != t_id: return "Cancelled"
                if "|" not in f['name']: continue
                parts = [p.strip() for p in f['name'].split("|")]
                bn, dj = parts[0], parts[1] if len(parts) > 1 else 'Unknown'
                nv, tv = bn.upper(), f"{bn.lower()}.dd#.{id2}"
                ext = await Media.collection.find_one({"text": tv})
                if ext and dj.lower() not in ext.get("reply", "").lower():
                    for l in "abcdefg":
                        sn, st = f"{bn.lower()} {l}", f"{bn.lower()} {l}.dd#.{id2}"
                        chk = await Media.collection.find_one({"text": st})
                        if not chk or dj.lower() in chk.get("reply", "").lower(): nv, tv = sn.upper(), st; break
                vids = svc.files().list(q=f"'{f['id']}' in parents and mimeType contains 'video/'", fields="files(id, name)").execute().get('files', [])
                tid = None
                for i, v in enumerate(vids[:5]):
                    if active_syncs.get(u_id) != t_id: return "Cancelled"
                    await msg.edit(f"🎬 **Converting:** `{nv}`")
                    tid = await proc_vid(v, getCred(tok, id2).token, id2, c, msg, u_id, qual, t_id)
                    if tid not in ["hrm45", "Cancelled"]: break
                if tid and tid != "Cancelled":
                    f_url = f"https://drive.google.com/drive/folders/{f['id']}"
                    await Media.collection.update_one({"text": tv}, {"$set": {"reply": f"SERIES {nv}\nimetafsiriwa dj {dj}", "file": tid, "group_id": id2, "type": "video", "nyva": b_name}, "$setOnInsert": {"_id": str(uuid.uuid4()), "descp": f"x.dd#.imetafsiriwa na {dj}\nSeries.dd#.{f_url}.dd#.s", "price": 3000, "lks": 0, "grp": "g_1 g_3", "btn": "[]"}}, upsert=True)
                    cnt += 1
        return f"Processed {cnt} series."
    except Exception as e: return f"Error: {e}"

@Bot0.on_message(filters.command('hrm48') & filters.private)
async def on_sync(c, m):
    u_id, bot = m.from_user.id, await c.get_me()
    if not await db.is_admin_exist(u_id, bot.username): return
    p = m.text.split(" ")
    if len(p) < 2: return await m.reply("⚠️ Usage: `/hrm48 [URL] [quality]`")
    url, q = p[1], p[2].lower() if len(p) > 2 and p[2].lower() in QUALITY_MAP else "medium"
    tid = str(uuid.uuid4()); active_syncs[u_id] = tid
    sts = await m.reply(f"🚀 **Sync Started...**\nBot: @{bot.username}")
    try:
        while active_syncs.get(u_id) == tid:
            sts_db = await db.get_db_status(u_id, bot.username)
            rep = await sync_data(sts_db["token"], u_id, url, c, sts, u_id, q, tid, bot.username)
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
