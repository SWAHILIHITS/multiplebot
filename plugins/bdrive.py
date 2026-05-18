import os, time, random, asyncio, googleapiclient.errors
from googleapiclient.http import MediaFileUpload
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from plugins.pm_filter import getCreds, get_access_id
from bot import Bot0
from plugins.database import db

ACTIVE_TASKS = {}
get_duration = lambda s: (lambda m, s: f"{m//60}h {m%60}m {s}s" if m >= 60 else f"{m}m {s}s")(*divmod(int(time.time() - s), 60))
get_gb = lambda b: round(b / (1024**3), 2)

async def validate_id(service, file_id, name_type):
    try:
        meta = await asyncio.get_event_loop().run_in_executor(None, lambda: service.files().get(fileId=file_id, fields="id, name, mimeType, trashed, size, shortcutDetails", supportsAllDrives=True).execute())
        if meta.get('trashed'): return False, f"❌ **{name_type} Error:** Ipo kwenye Trash."
        if name_type == "Destination" and meta['mimeType'] != 'application/vnd.google-apps.folder': return False, "❌ **Error:** Destination lazima iwe Folder!"
        return True, meta
    except googleapiclient.errors.HttpError as e: return False, f"❌ **{name_type} Not Found/No Access:** {e.resp.status}"
    except Exception as e: return False, f"❌ **Error:** {str(e)}"

async def execute_with_retry(request_func, user_id):
    reason = "UNKNOWN_ERROR"
    for n in range(5):
        try: return await asyncio.get_event_loop().run_in_executor(None, request_func.execute)
        except googleapiclient.errors.HttpError as error:
            reasons = [r.get('reason','') for r in (error.error_details or [])]
            if error.resp.status == 403 and any(r in ["quotaExceeded", "dailyLimitExceeded", "activeItemCreationLimitExceeded", "storageQuotaExceeded"] for r in reasons):
                ACTIVE_TASKS[user_id] = "CANCELLED_LIMIT_REACHED"
                return "LIMIT_REACHED"
            if error.resp.status in and any(r in ["rateLimitExceeded", "userRateLimitExceeded"] for r in reasons):
                reason = "USER_RATE_LIMIT_EXCEEDED" if "userRateLimitExceeded" in reasons else "RATE_LIMIT_EXCEEDED"
                await asyncio.sleep((2 ** n) + random.random())
                continue
            return "ERROR"
    ACTIVE_TASKS[user_id] = f"CANCELLED_{reason}"
    return "RETRY_FAILED"

def get_folder_contents(service, folder_id):
    res_dict, page_token = {}, None
    while True:
        try:
            resp = service.files().list(q=f"'{folder_id}' in parents and trashed = false", fields="nextPageToken, files(id, name, mimeType, size, shortcutDetails)", pageToken=page_token, supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
            for f in resp.get('files', []): res_dict[f['name']] = f
            page_token = resp.get('nextPageToken')
            if not page_token: break
        except: break
    return res_dict

async def recursive_copy(service, src_id, dest_id, client, uid, stats, msg, start):
    if str(ACTIVE_TASKS.get(uid)).startswith("CANCELLED"): return
    src_items, dest_items = get_folder_contents(service, src_id), get_folder_contents(service, dest_id)
    for name, item in src_items.items():
        if str(ACTIVE_TASKS.get(uid)).startswith("CANCELLED"): break
        r_id, r_mime = item['id'], item['mimeType']
        if r_mime == 'application/vnd.google-apps.shortcut' and item.get('shortcutDetails'):
            r_id, r_mime = item['shortcutDetails'].get('targetId', r_id), item['shortcutDetails'].get('targetMimeType', r_mime)
        if name in dest_items:
            if r_mime == 'application/vnd.google-apps.folder': await recursive_copy(service, r_id, dest_items[name]['id'], client, uid, stats, msg, start)
            else: stats['skipped'] += 1
        elif r_mime == 'application/vnd.google-apps.folder':
            new_f = await execute_with_retry(service.files().create(body={'name': name, 'parents': [dest_id], 'mimeType': r_mime}, fields='id', supportsAllDrives=True), uid)
            if new_f in ["LIMIT_REACHED", "RETRY_FAILED"]: break
            if new_f and new_f != "ERROR": await recursive_copy(service, r_id, new_f['id'], client, uid, stats, msg, start)
            else: stats['failed'] += 1
        else:
            res = await execute_with_retry(service.files().copy(fileId=r_id, body={'name': name, 'parents': [dest_id]}, supportsAllDrives=True), uid)
            if res in ["LIMIT_REACHED", "RETRY_FAILED"]: break
            if res not in [None, "ERROR", "FAILED"]:
                stats['copied'] += 1
                stats['total_bytes'] += int(item.get('size', 0) or 0)
            else: stats['failed'] += 1
        if (stats['copied'] + stats['skipped'] + stats['failed']) % 10 == 0:
            try: await msg.edit(f"⏳ **Inaendelea...**\n\n✅ Copied: `{stats['copied']}`\n❌ Failed: `{stats['failed']}`\n📦 Size: `{get_gb(stats['total_bytes'])} GB`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Sitisha", callback_data=f"stop_gd_{uid}")]]))
            except: pass
            await asyncio.sleep(1.2)

async def progress_for_pyrogram(current, total, ud_type, message, start):
    diff = time.time() - start
    if round(diff % 5.0) == 0 or current == total:
        blks = int((current * 100 / total) // 10)
        try: await message.edit(f"**{ud_type}**\n`[{'█'*blks + '░'*(10-blks)}] {round(current*100/total, 2)}%`\n📦 Size: `{get_gb(current)} GB / {get_gb(total)} GB`")
        except: pass

@Bot0.on_message(filters.command("gdrive") | filters.regex('^https://google.com.*'))
async def addfilesondrive(client, message):
    b_info = await client.get_me()
    uid = message.from_user.id
    if not await db.is_admin_exist(uid, b_info.username): return
    text0, args = message.text.strip(), message.text.strip().split()
    gd = await db.get_db_status(uid, b_info.username)
    service = getCreds(gd["token"], uid)
    if service in ['auth_error', 'token_error']: return await message.reply('❌ **Fail:** Token expired. Please login again.')

    if message.reply_to_message and any([message.reply_to_message.document, message.reply_to_message.video, message.reply_to_message.audio]):
        if text0 != "/gdrive" and len(args) != 2: return await message.reply('Tuma: `/gdrive dest_url` (Reply on file) au /gdrive bx tu')
        dest_id = get_access_id(args) if len(args) == 2 else 'root'
        media = message.reply_to_message.document or message.reply_to_message.video or message.reply_to_message.audio
        f_name = media.file_name or "telegram_file"
        if f_name in get_folder_contents(service, dest_id): return await message.reply(f"⏭ **Skipped:** `{f_name}` tayari ipo kwenye Drive.")
        msg_check = await message.reply(f"📥 **Inaanza kupakua...**\n📂 File: `{f_name}`")
        start = time.time()
        try: local_path = await client.download_media(message.reply_to_message, progress=progress_for_pyrogram, progress_args=("📥 Inapakua...", msg_check, start))
        except Exception as e: return await msg_check.edit(f"❌ **Download Failed:** {str(e)}")
        if not local_path or not os.path.exists(local_path): return await msg_check.edit("❌ **Error:** Faili halikupatikana.")
        await msg_check.edit("📤 **Inatuma kwenda Google Drive...**")
        try:
            uploaded = await asyncio.get_event_loop().run_in_executor(None, lambda: service.files().create(body={'name': f_name, 'parents': [dest_id]} if dest_id != 'root' else {'name': f_name}, media_body=MediaFileUpload(local_path, resumable=True), supportsAllDrives=True).execute())
            await msg_check.edit(f"✅ **Imekamilika!**\n📂 Jina: `{f_name}`\n🆔 ID: `{uploaded.get('id')}`")
        except googleapiclient.errors.HttpError as error:
            reasons = [r.get('reason','') for r in (error.error_details or [])]
            if error.resp.status == 403 and any(r in ["quotaExceeded", "dailyLimitExceeded", "storageQuotaExceeded"] for r in reasons): await msg_check.edit("🛑 **Imesitishwa!** Google Upload Limit imefikiwa.")
            elif any(r in ["rateLimitExceeded", "userRateLimitExceeded"] for r in reasons): await msg_check.edit("🛑 **Imesitishwa!** Rate Limit imefikiwa baada ya kujaribu mara 5.")
            else: await msg_check.edit(f"❌ **Upload Failed:** {str(error)}")
        except Exception as e: await msg_check.edit(f"❌ **Upload Failed:** {str(e)}")
        finally: 
            if os.path.exists(local_path): os.remove(local_path)
    else:
        if len(args) == 3: src_id, dest_id = get_access_id(args), get_access_id(args)
        elif len(args) == 2: src_id, dest_id = get_access_id(args), 'root'
        elif text0.startswith('http'): src_id, dest_id = get_access_id(text0), 'root'
        else: return await message.reply('Tuma: `/gdrive source_url dest_url` au reply kwenye file.au tuma url ya kudownload')
        msg_check = await message.reply("🔍 **Validating...**")
        v_src, src_meta = await validate_id(service, src_id, "Source")
        v_dest, dest_meta = await validate_id(service, dest_id, "Destination")
        if not v_src or not v_dest: return await msg_check.edit("❌ **Validation Failed:** Tafadhali kagua ID za Drive zako.")
        ACTIVE_TASKS[uid], start, stats = "RUNNING", time.time(), {'copied': 0, 'skipped': 0, 'total_bytes': 0, 'failed': 0}
        r_id, r_mime = src_meta['id'], src_meta['mimeType']
        if r_mime == 'application/vnd.google-apps.shortcut': r_id, r_mime = src_meta.get('shortcutDetails', {}).get('targetId', r_id), src_meta.get('shortcutDetails', {}).get('targetMimeType', r_mime)
        await msg_check.edit(f"🚀 **Kazi Inaanza...**\n📂 Jina: `{src_meta['name']}`\n📂 Aina: `{'Folder' if r_mime == 'application/vnd.google-apps.folder' else 'File'}`")
        if r_mime == 'application/vnd.google-apps.folder': await recursive_copy(service, r_id, dest_id, client, uid, stats, msg_check, start)
        else:
            if src_meta['name'] in get_folder_contents(service, dest_id): return await msg_check.edit(f"⏭ **Skipped:** `{src_meta['name']}` tayari ipo kwenye Drive.")
            res = await execute_with_retry(service.files().copy(fileId=r_id, body={'name': src_meta['name']} if text0.startswith("http") or len(args)==2 else {'name': src_meta['name'], 'parents': [dest_id]}, supportsAllDrives=True), uid)
            if res not in ["LIMIT_REACHED", "RETRY_FAILED", "ERROR", "FAILED", None]: stats['copied'], stats['total_bytes'] = stats['copied'] + 1, stats['total_bytes'] + int(src_meta.get('size', 0) or 0)
            elif res not in ["LIMIT_REACHED", "RETRY_FAILED"]: stats['failed'] += 1
        
        lbl = {"CANCELLED_USER_RATE_LIMIT_EXCEEDED": "🛑 **Imesitishwa!** User Rate Limit imezidi baada ya kujaribu mara 5.", "CANCELLED_RATE_LIMIT_EXCEEDED": "🛑 **Imesitishwa!** Rate Limit imezidi baada ya kujaribu mara 5.", "CANCELLED_LIMIT_REACHED": "🛑 **Imesitishwa!** Google Drive Upload/Quota limit imefikiwa.", "CANCELLED": "🛑 **Imesitishwa na Mtumiaji!**"}.get(ACTIVE_TASKS.get(uid), "✅ **Imekamilika!**")
        await msg_check.edit(f"{lbl}\n\n✅ Copied: `{stats['copied']}`\n❌ Failed: `{stats['failed']}`\n📦 Size: `{get_gb(stats['total_bytes'])} GB`\n⏱ Time: `{get_duration(start)}`")
        ACTIVE_TASKS.pop(uid, None)

@Bot0.on_callback_query(filters.regex(r"^stop_gd_(\d+)$"))
async def stop_gdrive_task(client, query):
    u_id = int(query.data.split("_")[-1])
    if query.from_user.id != u_id: return await query.answer("❌ Huna ruhusa ya kusitisha kazi hii!", show_alert=True)
    if ACTIVE_TASKS.get(u_id) == "RUNNING":
        ACTIVE_TASKS[u_id] = "CANCELLED"
        await query.answer("🛑 Inasitishwa... Tafadhali subiri.", show_alert=True)
    else: await query.answer("⚠️ Kazi tayari imeshaisha au imesitishwa.", show_alert=True)
