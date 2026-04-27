from bot import Bot0 
import re,random ,pickle,os
from pyrogram.types import InlineKeyboardMarkup,InlineKeyboardButton
from info import filters
import asyncio 
#from plugins.status import handle_admin_status
from plugins.database import db
from utils import get_filter_result,get_filter_results, is_user_exist,User ,get_file_details,is_subscribed,add_user,is_group_exist,get_random_details
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth import exceptions
from google.oauth2.credentials import Credentials

def getCreds(tokeni,group_id):
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    creds = None
    SCOPES = 'https://www.googleapis.com/auth/drive'

    if os.path.exists(f'{group_id}.pickle'):
        with open(f'{group_id}.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            try:
                creds = Credentials(
                    token=None,  # Hatuna access token ya sasa, tunataka mpya
                    refresh_token=tokeni,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id='5119780087-m9l5ctlcaq80d7di1065aohbjuk2b3np.apps.googleusercontent.com',
                    client_secret="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",
                )
                creds.refresh(Request())
            except exceptions.GoogleAuthError as e:
                with open(f'{group_id}.pickle', 'wb') as token:
                    pickle.dump(creds, token)
                return 'auth_error'
            except exceptions.RefreshError as e:
                # Google SDK huweka 'invalid_grant' ndani ya ujumbe wa kosa
                if "invalid_grant" in str(e).lower():    
                    print("Refresh Token haitumiki tena. Tafadhali ingia upya.")
                    # Logic ya kumlazimisha mtumiaji ku-login tena
                    
                    return 'token_error'
                    # Save the credentials for the next run
                with open(f'{group_id}.pickle', 'wb') as token:
                    pickle.dump(creds, token)
                return 'token_error'
        with open(f'{group_id}.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('drive', 'v3', credentials=creds)
    return service
from googleapiclient.errors import HttpError
def get_access_id(url):
    patterns = [
        r'/d/([a-zA-Z0-9-_]+)', 
        r'folders/([a-zA-Z0-9-_]+)',
        r'id=([a-zA-Z0-9-_]+)'
    ]
    file_id=None
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            file_id=match.group(1)
    if file_id==None:
        return "url_invalid"
    else:
        return file_id
    
def remove_access_email(service, folder_id, user_email):   
    try:
        # 1. Find the permission ID for the specific email address
        permissions = service.permissions().list(fileId=folder_id, fields="permissions(id, emailAddress)").execute()  
        target_perm_id = None
        for perm in permissions.get('permissions', []):
            if perm.get('emailAddress').lower() == user_email:
                target_perm_id = perm.get('id')
                break

        if target_perm_id:
            # 2. Delete the permission
            service.permissions().delete(fileId=folder_id, permissionId=target_perm_id).execute()
            print(f"Successfully removed access")
        else:
            print(f"No permission found for on this folder.")

    except HttpError as error:
        print(f"An error occurred: {error}")
def remove_access(service, url, per_id):   
    try:
        # 1. Find the permission ID for the specific email address
        # 2. Delete the permission
        service.permissions().delete(fileId=url, permissionId=per_id).execute()
        print(f"Successfully removed access")
        return "success"
    except HttpError as error:
        print(f"An error occurred: {error}")
        return "failed"
def grant_access(service, url, user_email):
    """Gives a specific user writer access to a file."""
    new_permission = {
        'type': 'user',
        'role': 'reader',  # Roles include: owner, writer, commenter, reader
        'emailAddress': user_email
    }
    
    # Regex for standard file links (/d/ID) and folder links (/folders/ID)
    patterns = [
        r'/d/([a-zA-Z0-9-_]+)', 
        r'folders/([a-zA-Z0-9-_]+)',
        r'id=([a-zA-Z0-9-_]+)'
    ]
    file_id=None
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            file_id=match.group(1)
    if file_id==None:
        return "url_invalid"
    try:
        permission = service.permissions().create(
            fileId=file_id,
            body=new_permission,
            fields='id'
        ).execute()
        
        print(f"Permission ID: {permission.get('id')}")
        
        return f"{file_id}##{permission.get('id')}##user_given_access"
        
    except HttpError as error:
        return "error"
        print(f"An error occurred: {error}")
    except Exception as e:
        return str(e)
@Bot0.on_message(filters.command("token"))
async def addtoken(client, message):
    botusername=await client.get_me()
    nyva=botusername.username
    nyva=str(nyva)
    try1=message.text.strip()
    ghi=f'{try1.split(" ")[1]}'
    ghi=f'token {ghi}'
    ab = await db.get_db_status(message.from_user.id,nyva)
    await db.update_db(message.from_user.id,ghi,ab,nyva)
    await message.reply_text(text=f"data updated successful tafadhali jaribu kama inafanya kaz")
                
