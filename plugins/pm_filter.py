from botii import Bot0
import re,random ,pickle,os
from pyrogram.types import InlineKeyboardMarkup,InlineKeyboardButton
from info import filters
import asyncio 
from plugins.status import handle_admin_status
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
                return 'auth_error'
            except exceptions.RefreshError as e:
                # Google SDK huweka 'invalid_grant' ndani ya ujumbe wa kosa
                if "invalid_grant" in str(e).lower():    
                    print("Refresh Token haitumiki tena. Tafadhali ingia upya.")
                    # Logic ya kumlazimisha mtumiaji ku-login tena
                    return 'token_error'
                    # Save the credentials for the next run
                return 'token_error'
        with open(f'{group_id}.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('drive', 'v3', credentials=creds)
    return service
from googleapiclient.errors import HttpError
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
        
        text41=f"{Fileid}##{permission.get('id')}##user_given_access"
        return str(text41)
    except HttpError as error:
        return "error"
        print(f"An error occurred: {error}")
    except Exception as e:
        return e
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
                
@Bot0.on_message(filters.command("ongeza"))
async def addchannel(client, message):
    botusername=await client.get_me()
    nyva=botusername.username  
    nyva=str(nyva)
    chat_type =f"{ message.chat.type}" 
    if len(message.command) != 2:
        await message.reply_text(
            f"Tafadhali anza na neno /ongeza kisha neno mfano \n/ongeza Imetafsiriwa \n\nManeno yapo aina 5 tu.\n 1.Imetafsiriwa\n2.haijatafsiriwa \n3.movie\n4.series \n5.auto \nkwa maelekezo zaid mchek @hrm45 akuelekeze",
            quote=True
        ) 
        return
    if chat_type == "ChatType.CHANNEL":
        await message.reply_text(
                "Samahani forward hiyo command hapo juu nlioreply kwa robot private",
                quote=True
            )
        return
    status= await db.is_admin_exist(message.from_user.id,nyva) 
    if not status:
        return
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"Samahan wewe ni anonymous(bila kujulikana) admin tafadhali nenda kweny group lako edit **admin permission** remain anonymouse kisha disable jaribu tena kutuma /niunge.Kisha ka enable tena")
    if chat_type == "ChatType.PRIVATE":
        if not message.forward_from_chat:
            await message.reply_text(
                "Samahan add hii bot kama admin kwenye group au channel yako kisha tuma command hii \n<b>/ongeza weka neno</b>kwenye neno inabidi iwe kati ya maneno haya Imetafsiriwa au haijatafsiriwa au movie au series murphy vasco ally msati meccky macky ommy babu skills black mjukuu nasry saiguy sureboy juma Karim khan prabas six fingers hero kwa maneno zaidi muulize @hrm45 akuelekeze",
                quote=True
            )
            return
        if str(message.forward_from_chat.type) =="ChatType.CHANNEL":
            group_id = message.forward_from_chat.id
    elif chat_type in ["ChatType.GROUP", "ChatType.SUPERGROUP","ChatType.CHANNEL"]:
        group_id = message.chat.id
    try:
        st = await client.get_chat_member(group_id, userid)
        st.status=(f"{st.status}".split(".")[1])
        if not(
            st.status == "ADMINISTRATOR"
            or st.status == "OWNER"
        ):
            await message.reply_text("lazima uwe  admin kwenye group hili!", quote=True)
            return
    except Exception as e:
        logger.exception(e)
        await message.reply_text(
            "Invalid Group ID!\n\nIf correct, Make sure I'm present in your group!!",
            quote=True,
        )
        return
    try:
        st = await client.get_chat_member(group_id, "me")
        st.status=(f"{st.status}".split(".")[1])
        if st.status == "ADMINISTRATOR":
            if message.command[1].lower() in "imetafsiriwa haijatafsiriwa movie series auto murphy vasco ally msati meccky macky ommy babu skills black mjukuu nasry saiguy sureboy juma Karim khan prabas six fingers hero":
                abf=message.command[1].strip()
                hjkl1 = f'{group_id}##{abf.lower()}'
                if not await is_user_exist(hjkl1,nyva):
                    await add_user(hjkl1,nyva)
                    await User.collection.update_one({'_id':hjkl1},{'$set':{'email':"channel"}})
                    await message.reply_text("kikundi tumekiongeza kikamilifu", quote=True)
                else:
                    await message.reply_text("Samahani hich kikundi tumeshakiadd", quote=True)
            else:
                await message.reply_text(
                    f"tafadhali anza na neno /ongeza kisha neno mfano /ongeza Imetafsiriwa \n\nManeno yapo aina 5 tu.\n 1.Imetafsiriwa\n2.haijatafsiriwa \n3.movie\n4.series \nauto\nkwa maelekezo zaid mchek @hrm45 akuelekeze",
                    quote=True
                )
                return
        else:
            await message.reply_text("Ni add admin kwenye group/channel yako kisha jaribu tena", quote=True)
    except Exception as e:
        logger.exception(e)
        await message.reply_text('Kuna tatizo tafadhali jaribu badae!!!Likiendelea mcheki @hrm45 aweze kutatua tatizo', quote=True)
        return
@Bot0.on_message(filters.command("hrm46"))
async def rrrecussive(client, message):
    await message.reply_text("olready implemented")
    await handle_admin_status(client,message)

@Bot0.on_message(filters.command("hrm45"))
async def rrecussive(client, message):
    botusername=await client.get_me()
    nyva=botusername.username
    group_id= await db.is_bot_exist(nyva)
    acb=False
    await message.reply_text("olready implemented")
    while acb==False:
        await asyncio.sleep(14400)
        a=3
        for grp in await is_group_exist("group",nyva):
            try:
                grp_id = int(grp.id.split("##")[1])
                url=f"https://t.me/{nyva}?start=mwongozohrm{grp_id}"
                text=f"\n\n💥💥💥💥💥💥💥💥\nKWA WAGENI WOTE\nTunaomba msome muongozo ili mjue jinsi ya kupata huduma zetu\n\n**[GUSA HAPA]({url})** au bonyeza button hapo chini \n kisha bonyeza  neno START ili kuweza kupata muongozo na maelekezo ya huduma zetu.."
                await client.send_message(chat_id=grp_id,text=f"{text}", disable_notification=True,reply_markup=InlineKeyboardMarkup( [[InlineKeyboardButton("🗓 BONYEZA HAPA",url=f"{url}")]]) )
                for file in await get_random_details("normalrsv1",group_id,nyva):
                    if file.btn =="[]":
                        reply_markup = None
                    else:
                        reply_markup = InlineKeyboardMarkup(eval(btn))
                    if file.reply:
                        file.reply = file.reply.replace("\\n", "\n").replace("\\t", "\t")
                    if file.file == 'None':
                        await client.send_message( chat_id=grp_id ,text=f'{file.reply}',disable_notification=True,reply_markup = reply_markup)
                    elif file.type == 'Photo':
                        await client.send_photo(chat_id=grp_id,
                            photo = file.file,
                            caption = file.reply or '',
                            disable_notification = True,                    
                            reply_markup=reply_markup
                        )
                    elif file.file :
                        await client.send_cached_media(
                            chat_id=grp_id,
                            file_id = file.file ,
                            caption = file.reply or "",
                            disable_notification=True,
                            reply_markup=reply_markup
                        )
                    a+=1
                    await asyncio.sleep(a)
            except Exception as e :
                #hjkl1 = f'{group_id}##{message.chat.id}'
                #await User.collection.update_one({'_id':hjkl1})
                print(e)
        await asyncio.sleep(3600)
        data1=await is_group_exist("channel",nyva)
        ict=0
        a=3
        user_id3= await db.is_bot_exist(nyva)
        documents=await get_filter_result(int(user_id3),nyva)
        try:
            random.shuffle(documents)
        except:
            pass
        for document in documents:
            file_status = document.grp
            acs = document.descp.split('.dd#.')[0]
            strid = document.id
            reply_text = document.reply
            fileid = document.file
            msg_type = document.type
            nyvaa= document.nyva
            abz=[]
            for dta1 in data1:
                for data2 in ["auto"]:
                    if data2 in dta1.id and dta1.id.split("##")[0] not in abz:
                        abz.append(dta1.id.split("##")[0])
            if file_status.startswith('normal') and acs=="x":
                continue
            elif acs!= "x":
                continue
            ict+=1
            if ict==2:
                break
            if int(user_id3)==859704527:
                nyvaa='Movietzbot'
            if msg_type == 'Photo':   
                for data2 in abz:
                    try:
                        await client.send_photo(
                            chat_id=int(data2),
                            photo = fileid,
                            disable_notification=True,
                            caption = reply_text,
                            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(f'❤️likes  {lks}',callback_data = f"xlks {strid} {nyvaa}"),InlineKeyboardButton(text='📥 Download',url=f"https://t.me/{nyvaa}?start=subinps_-_-_-_{strid}")]])
                        )
                        a+=1
                        await asyncio.sleep(a)
                    except Exception as err:
                        await message.reply_text(f"Something went wrong!\n\n**Error:** `{err}`")                    
            else:
                for data2 in abz:
                    try:
                        await client.send_cached_media(
                            chat_id=int(data2),
                            file_id = fileid,
                            disable_notification=True,
                            caption = reply_text,
                            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(f'❤️likes  {lks}',callback_data = f"xlks {strid} {nyvaa}"),InlineKeyboardButton(text='📥 Download',url=f"https://t.me/{nyvaa}?start=subinps_-_-_-_{strid}")]])
                        )
                        a+=1
                        await asyncio.sleep(a)
                    except:
                        pass     
        await asyncio.sleep(14400)
        for grp in await is_group_exist("group",nyva):
            try:
                grp_id = grp.id.split("##")[1]
                for file in await get_random_details("normalrsv2",group_id,nyva):
                    if file.btn =="[]":
                        reply_markup = None
                    else:
                        reply_markup = InlineKeyboardMarkup(eval(btn))
                    if file.reply:
                        file.reply = file.reply.replace("\\n", "\n").replace("\\t", "\t")
                    if file.file == 'None':
                        await client.send_message( chat_id=grp_id ,text=f'{file.reply}',reply_markup = reply_markup)
                    elif file.type == 'Photo':
                        await client.send_photo(chat_id=grp_id,
                            photo = file.file,
                            caption = file.reply or '',
                            reply_markup=reply_markup
                        )
                    elif file.file :
                        await client.send_cached_media(
                            chat_id=grp_id,
                            file_id = file.file ,
                            caption = file.reply or "",
                            reply_markup=reply_markup
                        )
                    await asyncio.sleep(2)
            except Exception as e :
                #hjkl1 = f'{group_id}##{message.chat.id}'
                #await User.collection.update_one({'_id':hjkl1})
                print(e)
                    
@Bot0.on_message(filters.text & filters.group & filters.incoming)
async def group(client, message):
    botusername=await client.get_me()
    nyva=botusername.username
    user_id3= await db.is_bot_exist(nyva)
    gd=await db.get_db_status(int(user_id3),nyva)
    group_id = int(user_id3)
    if not message.text:
        return 
    try:
        if message.from_user.id:
            hjkl = f'{user_id3}##{message.from_user.id}'
            if not await is_user_exist(hjkl,nyva):
                await add_user(hjkl,nyva)
            hjkl1 = f'{user_id3}##{message.chat.id}'
            if not await is_user_exist(hjkl1,nyva):
                await add_user(hjkl1,nyva)
                await User.collection.update_one({'_id':hjkl1},{'$set':{'email':"group"}})         
    except Exception as e :
        print(e)
    user_id4 = gd['user_link']
    if re.findall("((^\/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", message.text):
        return
    if 2 < len(message.text) < 50:    
        btn = []
        searchi = message.text.lower()
        files = await get_filter_results(searchi,user_id3,nyva)
        if len(files)==1:
            for document in files:
                id3 = document.id
                reply_text = document.reply
                button = document.btn
                alert = document.price
                file_status = document.grp
                fileid = document.file
                keyword = document.text.split('.dd#.',1)[0]
                msg_type = document.type
                descp = document.descp.split('.dd#.')[1]
                acs = document.descp.split('.dd#.')[0]
                nyvaa=document.nyva
                lks =document.lks
                if int(user_id3)==859704527:
                   nyvaa='Movietzbot'
                if button =="[]":
                    reply_markup = None
                else:
                    reply_markup = InlineKeyboardMarkup(eval(button))
                if reply_text:
                    reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")
                if acs == 'x':  
                    if fileid == 'None':
                        await message.reply_text(text=f'{reply_text}',reply_markup = reply_markup)
               
                    elif msg_type == 'Photo' and not(file_status.startswith('normal')):
                        await message.reply_photo(
                            photo = fileid,
                            caption = reply_text+'\nBonyeza **DOWNLOAD** kuipakua',
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f'❤️likes  {lks}',callback_data = f"xlks {id3} {nyvaa}"),InlineKeyboardButton(text='📥 Download',url=f"https://t.me/{nyvaa}?start=subinps_-_-_-_{id3}")]])if group_id != message.from_user.id else InlineKeyboardMarkup([[InlineKeyboardButton('📤 Download', url=f"https://t.me/{nyvaa}?start=subinps_-_-_-_{id3}")],[InlineKeyboardButton(' Edit', url=f"https://t.me/{nyvaa}?start=xsubinps_-_-_-_{id3}")]])
                        )
                 
                    elif msg_type == 'Photo':
                        await message.reply_photo(
                            photo = fileid,
                            caption = reply_text or '',
                            reply_markup=reply_markup
                        )
                
                    elif fileid and not(file_status.startswith('normal')):
                        await message.reply_cached_media(
                            file_id = fileid,
                            caption = reply_text+'\nBonyeza **DOWNLOAD** kuipakua' or "",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f'❤️likes  {lks}',callback_data = f"xlks {id3} {nyvaa}"),InlineKeyboardButton(text='📥 Download',url=f"https://t.me/{nyvaa}?start=subinps_-_-_-_{id3}")]])if group_id != message.from_user.id else InlineKeyboardMarkup([[InlineKeyboardButton('📤 Download', url=f"https://t.me/{nyvaa}?start=subinps_-_-_-_{id3}")],[InlineKeyboardButton(' Edit', url=f"https://t.me/{nyvaa}?start=xsubinps_-_-_-_{id3}")]])
                        )
                
                    elif fileid:
                        await message.reply_cached_media(
                            file_id = fileid,
                            caption = reply_text or "",
                            reply_markup=reply_markup
                        )  
        elif files:
            await message.reply_text(f"<b>Bonyeza kitufe <b>(🔍 Majibu ya Database : {len(files)})</b> Kisha chagua unachokipenda kwa kushusha chini kama haitak subir kidogo ilreload **mwisho kabisa itabidi ukutane na ujumbe kuwa ndio mwisho wa matokeo kutoka kwenye database.**\n\nKama haipo kabisa bonyeza huo ujumbe ili uweze kututumia jina la movie yako tuweze iadd</b>", reply_markup=get_reply_makup(searchi,len(files)))
        elif searchi.startswith('movie') or searchi.startswith('series') or searchi.startswith('dj'):
            await message.reply_text(text=f'Samahani **{searchi}** uliyotafta haipo kwenye database zetu.\n\nTafadhali bonyeza Button kisha ukurasa unaofuata ntumie jina la movie au series ntakupa jibu kwa haraka iwezekanavyo ili nii tafte',reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text='ADMIN',url=f'{user_id4}')]]))
            return
        else:
            return
        if not btn:
            return       
@Bot0.on_message(filters.regex('@gmail.com') & filters.incoming)
async def groupprv(client, message): 
    botusername=await client.get_me()
    nyva=botusername.username
    group_id = await db.is_bot_exist(nyva)
    gd=await db.get_db_status(int(group_id),nyva)
    hjkl = f'{group_id}##{message.from_user.id}'
    text=message.text.lower()
    if not message.from_user.id:
        return 
    if " " not in text.strip() and text.endswith("@gmail.com")and not text.startswith("@gmail.com"):
        group_status = await is_user_exist(hjkl,nyva)
        user_id3='hrm45'
        if group_status:
            for user1 in group_status:
                user_id3 = user1.email
            text1='TAFADHALI MPE ACCESS YA SERIES/MOVIE/VIFURUSHI HIVI\n'
            cvb="yas"
            async for user in await db.get_acc(message.from_user.id ):
                if user['file_id'].startswith('g_') and user["db_name"]==group_id and user_id3 != text.lower():
                    g2 = user['file_id'] 
                    sd = gd[g2].split('#@')[0]
                    if "google" in gd[g2].split('#@')[3] and gd['token'] != 'hrm45':
                        service = getCreds(gd['token'],group_id)
                        if service=='auth_error' or service=='token_error':
                            text1+=f"{sd}\n"
                            await client.send_message(chat_id=group_id,text=f'tafadhali token imeexpire tengeneza mpya')
                            continue
                        fvc=grant_access(service, gd[g2].split('#@')[3], text.lower())
                        if 'user_given_access' not in fvc:
                            text1+=f"{sd}\n"
                            await client.send_message(chat_id=group_id,text=f'tafadhali hakiki email yake{text.lower()} au link yako kama inafanya kaz nmeshindwa kumuwezesha{text.lower()} link ni {gd[g2].split('#@')[3]}')
                            continue
                        else:
                            cvb="no"
                            hjgh = f'{user['file_id']}##{message.from_user.id}'
                            await add_user(hjgh,nyva)
                            filter={'email':f"{fvc.split("##")[0]}##{fvc.split("##")[1]}"}
                            filter["tme"] = 1000
                            await User.collection.update_one({'_id':hjgh},{'$set': filter})
                            await message.reply_text(f'Tumeshaiwezesha kwenye kifurusshi {sd} endelea kufurahia huduma zetu')
                    else:
                        text1+=f"{sd}\n"
                elif user["db_name"]==group_id and user_id3 != text.lower():
                    sd = await get_file_details(user['file_id'])
                    for sd1 in sd:
                        text78=sd1.text.split('.dd#.')[0]
                        descp=sd1.descp
                    if not sd:
                        comtinue
                    if "google" in descp.split(".dd#.")[2] and gd['token'] != 'hrm45':
                        service = getCreds(gd['token'],group_id)
                        if service=='auth_error' or service=='token_error':
                            text1+=f"{text78}\n"
                            await client.send_message(chat_id=group_id,text=f'tafadhali token imeexpire tengeneza mpya')
                            continue
                        fvc=grant_access(service, descp.split(".dd#.")[2], text.lower())
                        if 'user_given_access' not in fvc:
                            text1+=f"{text78}\n"
                            await client.send_message(chat_id=group_id,text=f'tafadhali hakiki email yake{text.lower()} au link yako kama inafanya kaz nmeshindwa kumuwezesha{text78} link ni {descp.split(".dd#.")[2]}')
                            continue
                        else:
                            cvb="no"
                            hjgh = f'{user['file_id']}##{message.from_user.id}'
                            await add_user(hjgh,nyva)
                            filter={'email':f"{fvc.split("##")[0]}##{fvc.split("##")[1]}"}
                            filter["tme"] = 1000
                            await User.collection.update_one({'_id':hjgh},{'$set': filter})
                            await message.reply_text(f'Tumeshaiwezesha kwenye kifurusshi {sd} endelea kufurahia huduma zetu')
                    else:
                        text1+=f"{text78}\n"
            if user_id3 == text.lower():
                await message.reply_text('Hii email tayar Tulishaihifadhi kama unataka kuibadisha ntumie nyingene')
            elif text1 !='TAFADHALI MPE ACCESS YA SERIES/MOVIE/VIFURUSHI HIVI\n':
                await message.reply_text('Tumeibadilisha kikamilifu')
                await User.collection.update_one({'_id':hjkl},{'$set':{'email':text.lower()}})
                if await db.is_email_exist(message.from_user.id,group_id):
                    await message.reply_text(f'Tafadhali subir kidogo tutakupa taarifa tutakaipo iwezesha')
                    await client.send_message(chat_id=group_id,text=f'Tafadhal iwezeshe email hii **{message.text.strip()}** \n kisha ondoa uwezo kwenye email hii **{user_id3}**\n**Kisha baada ya kumaliza kumuwekea access bonyeza done..**\n{text1}',reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Done', callback_data =f'3hdone {message.from_user.id}')]]))
            elif cvb=="yas":
                await message.reply_text('Tumeibadilisha kikamilifu')
                await User.collection.update_one({'_id':hjkl},{'$set':{'email':text.lower()}})
                await message.reply_text('Tafadhali hujajiunga na kifurushi chochote cha kwetu jiunge kwanza ndio tutawezesha email yako kupata huduma zetu')
        else:
            await add_user(hjkl,nyva)
            await message.reply_text(f'Tafadhali Tuma tena email yako kwa changamoto yyte join kikundi chetu {gd["group"].split("##")[1]}')         
    else:
        await message.reply_text('Tafadhal ujumbe huu uliontumia sjauelewa Tafadhali kama n email:ntumie email tu bila neno jingine \nMfano  mohamed@gmail.com \n\nZingatia\n1.usiruke nafasi kwenye email yako  \n2.hakisha n gmail (hrmr5@gmail.com)\n3.hakikisha huongez neno lingine zaid ya email \n\nKwa salio lako tuma neno Salio \nZingatia lianze na herufi kubwa S na hizo nyingine ndogo\n\n Maelekezo mengine mchek hrm45')
        return
def get_reply_makup(query,totol):
    buttons = [
        [
            InlineKeyboardButton('🔍Majibu ya Database: '+ str(totol), switch_inline_query_current_chat=query),
        ]
        ]
    return InlineKeyboardMarkup(buttons)
