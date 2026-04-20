import os
import time
import random
import asyncio
import googleapiclient.errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from plugins.pm_filter import getCreds, get_access_id
from info import filters
from botii import Bot0
from plugins.database import db

# Global tracker for cancel logic
ACTIVE_TASKS = {}

def get_duration(start_time):
    seconds = int(time.time() - start_time)
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    return f"{hours}h {mins}m {secs}s" if hours > 0 else f"{mins}m {secs}s"

async def execute_with_retry(request_func, client, user_id):
    """Executes Google API calls with exponential backoff for rate limits."""
    max_retries = 5
    for n in range(max_retries):
        try:
            return await asyncio.get_event_loop().run_in_executor(None, request_func.execute)
        except googleapiclient.errors.HttpError as error:
            status = error.resp.status
            reason = error.error_details[0].get('reason') if error.error_details else ""

            if status in [403, 429] and reason in ["rateLimitExceeded", "userRateLimitExceeded"]:
                wait_time = (2 ** n) + random.random()
                try:
                    await client.send_message(user_id, f"⚠️ Limit hit. Retrying in {wait_time:.1f}s...")
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
            fields="nextPageToken, files(id, name, mimeType)",
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
    # Cancel Check
    if ACTIVE_TASKS.get(user_id) == "CANCELLED":
        return

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
            if new_folder and new_folder != "PERMISSION_DENIED":
                await recursive_copy(service, item['id'], new_folder['id'], client, user_id, stats, progress_msg, start_time)
        else:
            file_metadata = {'name': name, 'parents': [dest_id]}
            req = service.files().copy(fileId=item['id'], body=file_metadata, supportsAllDrives=True)
            res = await execute_with_retry(req, client, user_id)
            if res and res != "PERMISSION_DENIED":
                stats['copied'] += 1

        # Notification Logic (Every 10 items)
        total = stats['copied'] + stats['skipped']
        if total > 0 and total % 10 == 0 and total != stats.get('last_notified', 0):
            stats['last_notified'] = total
            duration = get_duration(start_time)
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Sitisha (Cancel)", callback_data=f"stop_gd_{user_id}")]])
            try:
                await progress_msg.edit(
                    f"⏳ **Inaendelea...**\n\n✅ Copied: `{stats['copied']}`\n⏭️ Skipped: `{stats['skipped']}`\n⏱️ Time: `{duration}`\n📊 Total: `{total}`",
                    reply_markup=btn
                )
            except: pass
        await asyncio.sleep(0.2)

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
    
    user_id = message.from_user.id
    ACTIVE_TASKS[user_id] = "RUNNING"
    start_time = time.time()
    
    progress_msg = await message.reply(
        "🔄 Scanning folders...",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Sitisha (Cancel)", callback_data=f"stop_gd_{user_id}")]])
    )
    
    stats = {'copied': 0, 'skipped': 0, 'last_notified': 0}

    try:
        await recursive_copy(service, source_id, dest_id, client, user_id, stats, progress_msg, start_time)
        
        if ACTIVE_TASKS.get(user_id) == "CANCELLED":
            await progress_msg.edit(f"🛑 **Kazi Imesitishwa!**\nItems Copied: `{stats['copied']}`")
        else:
            await progress_msg.edit(
                f"✅ **Kazi Imekamilika!**\n\n📁 Files Copied: `{stats['copied']}`\n⏭️ Skipped: `{stats['skipped']}`\n⏱️ Total Time: `{get_duration(start_time)}`"
            )
    except Exception as e:
        await message.reply(f"❌ Error: `{str(e)}`")
    finally:
        ACTIVE_TASKS.pop(user_id, None)

@Bot0.on_callback_query(filters.regex(r"^stop_gd_"))
async def stop_gdrive_callback(client, query):
    owner_id = int(query.data.split("_")[-1])
    if query.from_user.id != int(owner_id):
        return await query.answer("Huna ruhusa ya kusitisha hii!", show_alert=True)
    
    ACTIVE_TASKS[int(owner_id)] = "CANCELLED"
    await query.answer("Inasitisha kucopy...", show_alert=True)
