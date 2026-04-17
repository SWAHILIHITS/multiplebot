import os
from plugins.pm_filter import getCreds,get_acces_id
from info import filters
from botii import Bot0
import asyncio 
from plugins.database import db
def get_folder_contents(service, folder_id):
    """
    Retrieves all files/folders in a specific folder.
    Returns a dictionary: { 'Item Name': { 'id': '...', 'mimeType': '...' } }
    """
    results_dict = {}
    page_token = None
    
    while True:
        # supportsAllDrives=True is CRITICAL for shared content
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
        if not page_token:
            break
            
    return results_dict
@Bot0.on_message(filters.command("gdrive"))
async def addfilesondrive(client, message):
    botusername=await client.get_me()
    nyva=botusername.username
    status = await db.is_admin_exist(message.from_user.id,nyva) 
    if not status:
        return
    text1=message.strip()
    try:
        ab1,ab2,ab3=text1.split(" ")
    except:
        await client.send_message(chat_id=message.from_user.id,text=f'tafadhali tume /gdrive source_link dest_link ')
        return
    gd=await db.get_db_status(int(user_id3),nyva)
    service=getCreds(gd["token"],message.from_user.id)
    if service=='auth_error' or service=='token_error':
        await client.send_message(chat_id=message.from_user.id,text=f'tafadhali token imeexpire tengeneza mpya')
        return
    source_id=get_access_id(ab2)
    dest_id =get_access_id(ab3)
    if source_id == "url_invalid" or dest_id == "url_invalid":
        await client.send_message(chat_id=message.from_user.id,text=f'tafadhali hakikisha n url za google file au folder')
        return
    """
    Scans source, checks dest for duplicates, and copies missing items.
    Recurses into subfolders.
    """
    # 1. Map contents of both folders for quick lookup
    print(f"Scanning folder ID: {source_id}...")
    source_items = get_folder_contents(service, source_id)
    dest_items = get_folder_contents(service, dest_id)

    for name, item in source_items.items():
        # 2. Check for Duplicates
        if name in dest_items:
            # Item exists in destination
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                # If it's a folder, we must recurse inside to check for missing files
                print(f"  [Exists] Folder '{name}' - Checking contents...")
                recursive_copy(service, item['id'], dest_items[name]['id'])
            else:
                # If it's a file, skip it
                print(f"  [Skipping] File '{name}' already exists.")
            continue

        # 3. Copy or Create Missing Items
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            # Create new folder in destination
            print(f"  [Creating] Folder '{name}'")
            folder_metadata = {
                'name': name,
                'parents': [dest_id],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            new_folder = service.files().create(
                body=folder_metadata,
                fields='id',
                supportsAllDrives=True
            ).execute()
            
            # Recurse into the newly created folder
            recursive_copy(service, item['id'], new_folder['id'])
            
        else:
            # Copy file
            print(f"  [Copying] File '{name}'")
            file_metadata = {
                'name': name,
                'parents': [dest_id]
            }
            try:
                service.files().copy(
                    fileId=item['id'],
                    body=file_metadata,
                    supportsAllDrives=True
                ).execute()
            except Exception as e:
                print(f"   Error copying {name}: {e}")
def recursive_copy(service, source_id, dest_id):
    source_items = get_folder_contents(service, source_id)
    dest_items = get_folder_contents(service, dest_id)
    for name, item in source_items.items():
        # 2. Check for Duplicates
        if name in dest_items:
            # Item exists in destination
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                # If it's a folder, we must recurse inside to check for missing files
                print(f"  [Exists] Folder '{name}' - Checking contents...")
                recursive_copy(service, item['id'], dest_items[name]['id'])
            else:
                # If it's a file, skip it
                print(f"  [Skipping] File '{name}' already exists.")
            continue

        # 3. Copy or Create Missing Items
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            # Create new folder in destination
            print(f"  [Creating] Folder '{name}'")
            folder_metadata = {
                'name': name,
                'parents': [dest_id],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            new_folder = service.files().create(
                body=folder_metadata,
                fields='id',
                supportsAllDrives=True
            ).execute()
            
            # Recurse into the newly created folder
            recursive_copy(service, item['id'], new_folder['id'])
            
        else:
            # Copy file
            print(f"  [Copying] File '{name}'")
            file_metadata = {
                'name': name,
                'parents': [dest_id]
            }
            try:
                service.files().copy(
                    fileId=item['id'],
                    body=file_metadata,
                    supportsAllDrives=True
                ).execute()
            except Exception as e:
                print(f"   Error copying {name}: {e}")
