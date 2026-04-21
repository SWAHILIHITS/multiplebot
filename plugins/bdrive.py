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

# --- NEW VALIDATION FUNCTION ---
async def validate_id(service, file_id, name_type):
    """
    Inahakiki kama ID ipo, haijafutwa, na bot ina access nayo.
    Returns: (isValid: bool, result: str)
    """
    try:
        # Tunajaribu kupata jina na mimeType. Hii itafeli kama ID haipo.
        metadata = await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: service.files().get(
                fileId=file_id, 
                fields="name, mimeType, trashed", 
                supportsAllDrives=True
            ).execute()
        )
        
        # Check kama ipo kwenye trash
        if metadata.get('trashed'):
            return False, f"❌ **{name_type} Error:** Folder/File hii ipo kwenye Trash (Imefutwa)."

        # Kwa Destination, lazima iwe Folder
        if name_type == "Destination" and metadata['mimeType'] != 'application/vnd.google-apps.folder':
            return False, "❌ **Error:** Destination link lazima iwe Folder, sio file!"
            
        return True, metadata['name']

    except googleapiclient.errors.HttpError as e:
        if e.resp.status == 404:
            return False, f"❌ **{name_type} Not Found:** Link hii haipo au imefutwa."
        elif e.resp.status == 403:
             return False, f"❌ **{name_type} Access Denied:** Sina permission ya kuona link hii. Hakikisha bot imeongezwa."
        else:
            return False, f"❌ **{name_type} Error:** {str(e)}"
    except Exception as e:
        return False, f"❌ **Error:** {str(e)}"

async def execute_with_retry(request_func, client, user_id):
    """Executes Google API calls with exponential backoff."""
    max_retries = 5
    for n in range(max_retries):
        try:
            return await asyncio.get_event_loop().run_in_executor(None, request_func.execute)
        except googleapiclient.errors.HttpError as error:
            status = error.resp.status
            reason = error.error_details[0].get('reason') if error.error_details else ""

            if status in [403, 429] and reason in ["rateLimitExceeded", "userRateLimitExceeded"]:
                if n == max_retries - 1:
                    await client.send_message(user_id, "❌ **Kikomo (Limit) kimefikiwa!** Kazi imesitishwa.")
                    return "CANCEL_ALL"
                
                wait_time = (2 ** n) + random.random()
                try:
                    await client.send_message(user_id, f"⚠️ Limit hit. Retrying {n+1}/{max_retries} in {wait_time:.1f}s...")
                except: pass
                await asyncio.sleep(wait_time)
                continue
            
            if status == 403 and reason == "insufficientPermissions":
                return "PERMISSION_DENIED"

            raise error
    return None

def get_folder_contents(service, folder_id):
    results_dict = {}
    page_token = None
    while True:
        response = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType, size)",
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        for file in response.get('files', []):
            results_dict[file['name']] = file
        page_token = response.get('nextPageToken')
        if not page_token: break
    return results_dict

async def recursive_copy(service, source_id, dest_id, client, user_id, stats, progress_msg, start_time):
    if ACTIVE_TASKS.get(user_id) == "CANCELLED": return

    source_items = get_folder_contents(service, source_id)
    dest_items = get_folder_contents(service, dest_id)

    for name, item in source_items.items():
        if ACTIVE_TASKS.get(user_id) == "CANCELLED": break

        if name in dest_items:
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                await recursive_copy(service, item['id'], dest_items[name]['id'], client, user_id, stats, progress_msg, start_time)
            else:
                stats['skipped'] += 1
        elif item['mimeType'] == 'application/vnd.google-apps.folder':
            folder_metadata = {'name': name, 'parents': [dest_id], 'mimeType': 'application/vnd.google-apps.folder'}
            req = service.files().create(body=folder_metadata, fields='id', supportsAllDrives=True)
            new_folder = await execute_with_retry(req, client, user_id)
            
            if new_folder == "CANCEL_ALL":
                ACTIVE_TASKS[user_id] = "CANCELLED"
                return
            
            if new_folder and new_folder != "PERMISSION_DENIED":
                await recursive_copy(service, item['id'], new_folder['id'], client, user_id, stats, progress_msg, start_time)
        else:
            file_metadata = {'name': name, 'parents': [dest_id]}
            req = service.files().copy(fileId=item['id'], body=file_metadata, supportsAllDrives=True)
            res = await execute_with_retry(req, client, user_id)
            
            if res == "CANCEL_ALL":
                ACTIVE_TASKS[user_id] = "CANCELLED"
                return
            
            if res and res != "PERMISSION_DENIED":
                stats['copied'] += 1
                stats['total_bytes'] += int(item.get('size', 0))

        # Update UI Logic
        total = stats['copied'] + stats['skipped']
        if total > 0 and total % 10 == 0 and total != stats.get('last_notified', 0):
            stats['last_notified'] = total
            duration = get_duration(start_time)
            size_gb = get_gb(stats['total_bytes'])
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Sitisha (Cancel)", callback_data=f"stop_gd_{user_id}")]])
            try:
                await progress_msg.edit(
                    f"⏳ **Inaendelea...**\n\n✅ Copied: `{stats['copied']}`\n⏭️ Skipped: `{stats['skipped']}`\n📦 Size: `{size_gb} GB`\n⏱️ Time: `{duration}`",
                    reply_markup=btn
                )
            except: pass
        await asyncio.sleep(0.1)

@Bot0.on_message(filters.command("gdrive"))
async def addfilesondrive(client, message):
    bot_info = await client.get_me()
    status = await db.is_admin_exist(message.from_user.id, bot_info.username) 
    if not status: return

    args = message.text.split(" ")
    if len(args) < 3:
        return await message.reply('Tafadhali tume: `/gdrive source_url dest_url`')

    gd = await db.get_db_status(message.from_user.id, bot_info.username)
    service = getCreds(gd["token"], message.from_user.id)
    if service in ['auth_error', 'token_error']:
        return await message.reply('Token imeexpire, tengeneza mpya.')

    source_id = get_access_id(args[1])
    dest_id = get_access_id(args[2])
    
    # --- VALIDATION SECTION START ---
    msg_check = await message.reply("🔍 **Inahakiki links (Validating)...**")
    
    # 1. Check Source
    valid_src, src_res = await validate_id(service, source_id, "Source")
    if not valid_src:
        # src_res contains the specific error (Deleted, Not Found, Permission)
        return await msg_check.edit(src_res)
    
    # 2. Check Destination
    valid_dest, dest_res = await validate_id(service, dest_id, "Destination")
    if not valid_dest:
        return await msg_check.edit(dest_res)
    
    await msg_check.edit(f"✅ **Imethibitishwa!**\n📂 Src: `{src_res}`\n📂 Dest: `{dest_res}`\n🚀 Inaanza kucopy...")
    # --- VALIDATION SECTION END ---
    
    user_id = message.from_user.id
    ACTIVE_TASKS[user_id] = "RUNNING"
    start_time = time.time()
    
    stats = {'copied': 0, 'skipped': 0, 'last_notified': 0, 'total_bytes': 0}

    try:
        await recursive_copy(service, source_id, dest_id, client, user_id, stats, msg_check, start_time)
        
        final_gb = get_gb(stats['total_bytes'])
        if ACTIVE_TASKS.get(user_id) == "CANCELLED":
            await msg_check.edit(f"🛑 **Kazi Imesitishwa!**\nFiles: `{stats['copied']}`\nSize: `{final_gb} GB`")
        else:
            await msg_check.edit(
                f"✅ **Kazi Imekamilika!**\n\n📁 Copied: `{stats['copied']}`\n⏭️ Skipped: `{stats['skipped']}`\n📦 Size: `{final_gb} GB`\n⏱️ Time: `{get_duration(start_time)}`"
            )
    except Exception as e:
        await msg_check.edit(f"❌ Error wakati wa copy: `{str(e)}`")
    finally:
        ACTIVE_TASKS.pop(user_id, None)

@Bot0.on_callback_query(filters.regex(r"^stop_gd_"))
async def stop_gdrive_callback(client, query):
    owner_id = int(query.data.split("_")[-1])
    if query.from_user.id != int(owner_id):
        return await query.answer("Huna ruhusa ya kusitisha hii!", show_alert=True)
    
    ACTIVE_TASKS[int(owner_id)] = "CANCELLED"
    await query.answer("Inasitisha kucopy...", show_alert=True)
