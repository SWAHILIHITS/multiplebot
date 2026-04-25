import os
import time
import random
import asyncio
import googleapiclient.errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from plugins.pm_filter import getCreds, get_access_id
from info import filters
from bot import Bot0
from plugins.database import db

# Global tracker for cancel logic
ACTIVE_TASKS = {}

def get_duration(start_time):
    seconds = int(time.time() - start_time)
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    return f"{hours}h {mins}m {secs}s" if hours > 0 else f"{mins}m {secs}s"

def get_gb(bytes_size):
    return round(bytes_size / (1024**3), 2)

async def validate_id(service, file_id, name_type):
    """Checks if ID exists and returns metadata for both files and folders."""
    try:
        metadata = await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: service.files().get(
                fileId=file_id, 
                fields="id, name, mimeType, trashed, size, shortcutDetails", 
                supportsAllDrives=True
            ).execute()
        )
        if metadata.get('trashed'):
            return False, f"❌ **{name_type} Error:** Ipo kwenye Trash."
        
        # Destination MUST be a folder
        if name_type == "Destination" and metadata['mimeType'] != 'application/vnd.google-apps.folder':
            return False, "❌ **Error:** Destination lazima iwe Folder!"
            
        return True, metadata
    except googleapiclient.errors.HttpError as e:
        return False, f"❌ **{name_type} Not Found/No Access:** {e.resp.status}"
    except Exception as e:
        return False, f"❌ **Error:** {str(e)}"

async def execute_with_retry(request_func, client, user_id):
    max_retries = 5
    for n in range(max_retries):
        try:
            return await asyncio.get_event_loop().run_in_executor(None, request_func.execute)
        except googleapiclient.errors.HttpError as error:
            status = error.resp.status
            reason = error.error_details[0].get('reason') if error.error_details else ""
            if status in [403, 429] and reason in ["rateLimitExceeded", "userRateLimitExceeded"]:
                wait_time = (2 ** n) + random.random()
                await asyncio.sleep(wait_time)
                continue
            return "ERROR"
    return "FAILED"

def get_folder_contents(service, folder_id):
    results_dict = {}
    page_token = None
    while True:
        try:
            response = service.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType, size, shortcutDetails)",
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            for file in response.get('files', []):
                results_dict[file['name']] = file
            page_token = response.get('nextPageToken')
            if not page_token: break
        except: break
    return results_dict

async def recursive_copy(service, source_id, dest_id, client, user_id, stats, progress_msg, start_time):
    if ACTIVE_TASKS.get(user_id) == "CANCELLED": return

    source_items = get_folder_contents(service, source_id)
    dest_items = get_folder_contents(service, dest_id)

    for name, item in source_items.items():
        if ACTIVE_TASKS.get(user_id) == "CANCELLED": break

        # Resolve Shortcut to Original File
        real_id = item['id']
        real_mime = item['mimeType']
        if real_mime == 'application/vnd.google-apps.shortcut':
            details = item.get('shortcutDetails')
            if details:
                real_id = details.get('targetId')
                real_mime = details.get('targetMimeType')

        if name in dest_items:
            if real_mime == 'application/vnd.google-apps.folder':
                await recursive_copy(service, real_id, dest_items[name]['id'], client, user_id, stats, progress_msg, start_time)
            else:
                stats['skipped'] += 1
        elif real_mime == 'application/vnd.google-apps.folder':
            folder_metadata = {'name': name, 'parents': [dest_id], 'mimeType': 'application/vnd.google-apps.folder'}
            req = service.files().create(body=folder_metadata, fields='id', supportsAllDrives=True)
            new_folder = await execute_with_retry(req, client, user_id)
            if new_folder and new_folder != "ERROR":
                await recursive_copy(service, real_id, new_folder['id'], client, user_id, stats, progress_msg, start_time)
            else: stats['failed'] += 1
        else:
            file_metadata = {'name': name, 'parents': [dest_id]}
            req = service.files().copy(fileId=real_id, body=file_metadata, supportsAllDrives=True)
            res = await execute_with_retry(req, client, user_id)
            if res and res != "ERROR":
                stats['copied'] += 1
                stats['total_bytes'] += int(item.get('size', 0) or 0)
            else: stats['failed'] += 1

        total = stats['copied'] + stats['skipped'] + stats['failed']
        if total % 10 == 0:
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Sitisha", callback_data=f"stop_gd_{user_id}")]])
            try:
                await progress_msg.edit(
                    f"⏳ **Inaendelea...**\n\n✅ Copied: `{stats['copied']}`\n❌ Failed: `{stats['failed']}`\n📦 Size: `{get_gb(stats['total_bytes'])} GB`",
                    reply_markup=btn
                )
            except: pass
            await asyncio.sleep(1.2)

@Bot0.on_message(filters.command("gdrive"))
async def addfilesondrive(client, message):
    bot_info = await client.get_me()
    if not await db.is_admin_exist(message.from_user.id, bot_info.username): return

    args = message.text.split(" ")
    if len(args) < 3:
        return await message.reply('Tuma: `/gdrive source_url dest_url`')

    gd = await db.get_db_status(message.from_user.id, bot_info.username)
    service = getCreds(gd["token"], message.from_user.id)
    if service in ['auth_error', 'token_error']:
        return await message.reply('Token expired. Please login again.')

    source_id = get_access_id(args[1])
    dest_id = get_access_id(args[2])
    
    msg_check = await message.reply("🔍 **Validating...**")
    
    v_src, src_meta = await validate_id(service, source_id, "Source")
    v_dest, dest_meta = await validate_id(service, dest_id, "Destination")
    
    if not v_src or not v_dest:
        return await msg_check.edit(src_meta if not v_src else dest_meta)
    
    user_id = message.from_user.id
    ACTIVE_TASKS[user_id] = "RUNNING"
    stats = {'copied': 0, 'skipped': 0, 'total_bytes': 0, 'failed': 0}
    start_time = time.time()

    # Determine if Source is File or Folder (Handle Shortcuts)
    src_real_id = src_meta['id']
    src_real_mime = src_meta['mimeType']
    if src_real_mime == 'application/vnd.google-apps.shortcut':
        details = src_meta.get('shortcutDetails', {})
        src_real_id = details.get('targetId', src_real_id)
        src_real_mime = details.get('targetMimeType', src_real_mime)

    await msg_check.edit(f"🚀 **Kazi Inaanza...**\n📂 Jina: `{src_meta['name']}`\n📂 Aina: `{'Folder' if src_real_mime == 'application/vnd.google-apps.folder' else 'File'}`")

    if src_real_mime == 'application/vnd.google-apps.folder':
        # Start recursive folder copy
        await recursive_copy(service, src_real_id, dest_id, client, user_id, stats, msg_check, start_time)
    else:
        # Direct File Copy
        file_metadata = {'name': src_meta['name'], 'parents': [dest_id]}
        req = service.files().copy(fileId=src_real_id, body=file_metadata, supportsAllDrives=True)
        res = await execute_with_retry(req, client, user_id)
        if res and res != "ERROR":
            stats['copied'] += 1
            stats['total_bytes'] += int(src_meta.get('size', 0) or 0)
        else: stats['failed'] += 1
    
    final_status = "✅ Imekamilika!" if ACTIVE_TASKS.get(user_id) != "CANCELLED" else "🛑 Imesitishwa!"
    await msg_check.edit(f"{final_status}\n\n✅ Copied: `{stats['copied']}`\n📦 Size: `{get_gb(stats['total_bytes'])} GB`\n⏱️ Time: `{get_duration(start_time)}`")
    ACTIVE_TASKS.pop(user_id, None)

@Bot0.on_callback_query(filters.regex(r"^stop_gd_(\d+)$"))
async def stop_gdrive_copy(client, query):
    user_id = int(query.data.split("_")[-1])
    if query.from_user.id != user_id:
        return await query.answer("⚠️ Not your task!", show_alert=True)
    if user_id in ACTIVE_TASKS:
        ACTIVE_TASKS[user_id] = "CANCELLED"
        await query.answer("🛑 Stopping task...")
        await query.edit_message_text("🛑 **Hali:** Inasitisha kazi... Tafadhali subiri.")
    else:
        await query.answer("ℹ️ Kazi tayari imeshaisha.", show_alert=True)
