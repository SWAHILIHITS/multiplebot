from info import filters,CHANNELS,OWNER_ID
import uuid    
import time      
import asyncio
from pyrogram.errors import ChatAdminRequired
from utils import get_file_details,get_filter_results,is_user_exist,Media,User,is_subscribed,is_group_exist,save_file,add_user
from botii  import Bot0
from plugins.database import db
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from plugins.strings import START_MESSAGE, HELP_MESSAGE, ABOUT_MESSAGE, MARKDOWN_HELP
start_keyboard = [
    [
        InlineKeyboardButton(text = '🤔 Help', callback_data = "help"),
        InlineKeyboardButton(text = '🤖 About', callback_data = "about")
    ],
    [
        InlineKeyboardButton(text = 'Close 🔒', callback_data = "close"),
        InlineKeyboardButton(text = 'Search Here', switch_inline_query_current_chat = '')
    ]
]

start_keyboard_c = [
    [
        InlineKeyboardButton(text = '🤖 About', callback_data = "about"),
        InlineKeyboardButton(text = 'Close 🔒', callback_data = "close")
    ],
    [
        InlineKeyboardButton(text = 'Search Here', switch_inline_query_current_chat = '')
    ]
]

help_keyboard = [
    [
        InlineKeyboardButton(text = '✏️ Markdown Helper ✏️', callback_data = 'markdownhelper')
    ],
    [
        InlineKeyboardButton(text = '🤖 About', callback_data = 'about'),
        InlineKeyboardButton(text = 'Close 🔒', callback_data = 'close')
    ]
]

about_keyboard = [
     [
        InlineKeyboardButton(text = '🤔 Help', callback_data = 'help'),
        InlineKeyboardButton(text = 'Close 🔒', callback_data = 'close')
    ]
]

about_keyboard_c = [
    [
        InlineKeyboardButton(text = 'Close 🔒', callback_data = 'close')
    ]
]

markdown_keyboard = [
    [
        InlineKeyboardButton(text = '🔙 Back', callback_data = 'help')
    ]
]
@Bot0.on_message(filters.command('start') & filters.private)
async def start_msg_admins(client, message):
    botusername=await client.get_me()
    nyva=botusername.username  
    nyva=str(nyva)
    if await db.is_admin_exist(message.from_user.id,nyva):
        reply_markup = InlineKeyboardMarkup(start_keyboard)
    else:
        reply_markup = InlineKeyboardMarkup(start_keyboard_c)
    
    user_details = await db.is_bot_exist(nyva)
    hjkl = f'{user_details}##{message.from_user.id}'
    if not await is_user_exist(hjkl,nyva):
        await add_user(hjkl,nyva)
    hjkl = f'{user_details}##{message.from_user.id}'
    user_details1 = await is_user_exist(hjkl,nyva)
    ban_status = await db.get_db_status(user_details)   
    try:
       if user_details1:
           text = ban_status['descp'].format(
                mention = message.from_user.mention,
                first_name = message.from_user.first_name,
                last_name = message.from_user.last_name,
                user_id = message.from_user.id,
                username = '' if message.from_user.username == None else '@'+message.from_user.username
            )
       else:
           text = f"Samahani Mpendwa **{message.from_user.mention}** \n\nRudi kwenye main group kwa kubonyeza hii link {ban_status['group'].split('##')[1]}\n\nkisha tuma neno movie \n ili kuweza kujua jinsi ya kupata huduma za robot huyu Au Soma maelekezo utakayo pewa ili kusoma muongozo utakapo kwama tuulize kwenye kikundi tukusaidie"       
    except Exception as e:
        text = f'robot yupo kwenye matengenezo subiri mtajulishwa atakapo kuwa sawa{e}'     
    usr_cmdall1 = message.text
    cmd=message
    try:
        aby = await  is_subscribed(client, message, int(ban_status['group'].split('##')[0]) )
        
    except :
        ts=await client.get_users(user_details)
        await client.send_message(
            chat_id=user_details,
            text=f"Tafadhali ili wateja wako waweze kumtumia robot huyu add update channel na main movie group.......\n\n**Group**\nkwenye kikundi(group) muadd robot huyu kama admin kisha tuma /niunge\n**CHANNEL**\nTuma /niunge kwenye channel kisha forward ujumbe huo kwa robot huyu kumbuka umuadd robot huyu kama admin kwenye channel hiyo.... ",
        )
        try:
            await client.send_message(
                chat_id=message.from_user.id,
                text=f"Samahani Mpendwa **{message.from_user.mention}**\n\nTafadhali ili kumtumia robot huyu mwambie admin wako add update channel na main movie group bonyeza **@{ts.username}** kumfuata inbox",
            )
        except:
            pass
        return
    
    if usr_cmdall1.startswith("/start mwongozo"):
        abx=await client.send_message(
                chat_id=cmd.from_user.id,
                text=f"Samahani mpendwa\n\nJe wewe n mgeni au mzoefu na telegram \nBASI KAMA WEWE NI:\n\nMGENI\nTunakukaribisha telegram kuwa huru kuuliza chochote ambacho utaona huelew mfano jinsi ya kuforward,kudownload,kureply ujumbe wa mtu na pia jinsi ya kutuma media.\n Yote haya utauliza baada ya kusoma muongozo mpaka mwisho kisha kurudi kwenye kikundi na kuanza kupata huduma zetu na kusema changamoto uliokumbana nayo kama ipo.\n\nMZOEFU\nSina maneno mengi bonyeza button Soma zaidi kuendelea \n**Note**\nJitahidi kusoma mpaka mwisho kiumakini..yaan ukutane na button ya kukurudisha kwenye kikundi ndio utaruhusiwa kutuma ujumbe kwenye kikundi ",
                reply_markup=InlineKeyboardMarkup( [[InlineKeyboardButton("SOMA ZAIDI", callback_data =f'3hmbele {cmd.text.split("hrm")[1]}')]]),                        
            )
        return
        
    elif usr_cmdall1.startswith("/start subinps"):
        try:
            ident, file_id = cmd.text.split("_-_-_-_")
            filedetails = await get_file_details(file_id)
            for files in filedetails:
                f_caption=files.reply
                id2 = files.id
                group_id = files.group_id
                msg_type =files.type
                prc=files.price
                grp = files.grp
            if not filedetails:
                await client.send_message(
                    chat_id=cmd.from_user.id,
                    text=f"Samahani **{cmd.from_user.first_name}** hii movie uliochagua imefutwa kwenye database yangu tafadhali rudi kwenye kikundi kisha iombe tena"
                )   
                return 
            grp1,grp2=grp.split(" ") 
            ban_status = await db.get_ban_status(group_id)
            lk = await client.get_users(group_id)
            if ban_status["is_banned"] == False and group_id != cmd.from_user.id :           
                await client.send_message(
                        chat_id=cmd.from_user.id,
                        text=f"Samahani **{cmd.from_user.first_name}** nmeshindwa kukuruhusu kendelea kwa sababu Kifurushi cha admin alicho lipia kumtumia robot huyu kimeisha mtaarifu alipie ***\n\n[BONYEZA HAPA KUMTAARIFU](tg://user?id={group_id})\n\n***Ili muweze kuendelea kumutumia robot huyu")
                return
            if (not (await db.is_acc_exist(cmd.from_user.id,grp1,group_id) or await db.is_acc_exist(cmd.from_user.id,id2,group_id) or await db.is_acc_exist(cmd.from_user.id,grp2,group_id)) or prc == '0')and group_id != cmd.from_user.id :
                if msg_type =="Photo":
                    await client.send_photo(
                        chat_id=cmd.from_user.id,
                        photo=files.file,
                        caption=f_caption,
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 DOWNLOAD",url= f'https://t.me/{nyva}?start=subinps_-_-_-_{file_id}')]])
                    )     
                else:
                    await client.send_cached_media(
                        chat_id=cmd.from_user.id,
                        file_id=files.file,
                        caption=f_caption,
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 DOWNLOAD",url= f'https://t.me/{nyva}?start=subinps_-_-_-_{file_id}')]])
                    )
                             
                await client.send_message(
                    chat_id=cmd.from_user.id,
                    text=f"Samahani **{cmd.from_user.first_name}**\n🚫nmeshindwa kukuruhusu kendelea kwa sababu muv au sizon uliochagua ni za kulipia\n🏘Tafadhal chagua nchi uliopo kuweza kulipia uweze kuitazama \n\n✅**Kisha baada ya kufanya malipo na kuthibitishiwa malipo yako na admin utabonyeza download hapo juu kuipata movie yako kama utalipia kifurushi utazipakua nyingine zaid kwenye kikundi....\n\n🙇🙇‍♂** [BONYEZA HAPA](https://t.me/{lk.username})** kwa msaada/maelekezo zaidi ",
                    disable_web_page_preview = True,
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton("🇹🇿 TANZANIA", callback_data =f"tzn##tsh {file_id}"),
                                InlineKeyboardButton("🇰🇪 KENYA",callback_data =f"tzn##ksh {file_id}" )
                            ]
                        ]
                    )
                )
                return
            strg=files.descp.split('.dd#.')[3]
            if filedetails:
                if strg.lower() == 'm':
                    filez=await get_filter_results( file_id ,group_id)
                    abx=[]
                    for file in (filez):
                        if abx==[]:
                            abx.append(file.grp)
                        elif file.grp not in abx:
                            abx.append(file.grp)
                    cpt=f_caption
                    if abx==[]:
                        reply_markup = None
                        caption=f"{f_caption }\n\n.Samahani kuna mteja alikuwa anaomba uweke movie hii..Kisha baada ya kuweka bonyeza done ili tumtaarifu kuwa ushaiweka"
                        rpymk1=InlineKeyboardMarkup([[InlineKeyboardButton(f"✅  DONE__", callback_data =f"3hdns {message.from_user.id}")]])
                        f_caption=f"{f_caption}\n\n**Samahani mteja Series hii uliokuwa unaiomba bado haijawekwa nmeshatoa taarifa kwa msimamizi wangu atakapoiweka tu ntakujuza.**"
                        if msg_type =="Photo":
                            await client.send_photo(
                                chat_id=group_id,
                                photo=files.file,
                                caption=caption,
                                reply_markup= rpymk1
                            )
                        
                        else:
                            await client.send_cached_media(
                                chat_id=group_id,
                                file_id=files.file,
                                caption=caption,
                                reply_markup=rpymk1
                            )
                    elif len(abx)==1:
                        f_caption = f"{f_caption}\n\n**Chagua formate ya kudownload**"
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(f"📡{abx[0]}p", callback_data =f"3hdmuv##{abx[0]} {file_id}")
                        ]])
                    elif len(abx)==2:
                        f_caption = f"{f_caption}\n\n**Chagua formate ya kudownload**"
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(f"📡{abx[0]}p", callback_data =f"3hdmuv##{abx[0]} {file_id}"),
                            InlineKeyboardButton(f"📡{abx[1]}p", callback_data =f"3hdmuv##{abx[1]} {file_id}")
                        ]])
                    elif len(abx)==3:
                        f_caption = f"{f_caption}\n\n**Chagua formate ya kudownload**"
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(f"📡{abx[0]}p", callback_data =f"3hdmuv##{abx[0]} {file_id}"),
                            InlineKeyboardButton(f"📡{abx[1]}p", callback_data =f"3hdmuv##{abx[1]} {file_id}"),
                            InlineKeyboardButton(f"📡{abx[2]}p", callback_data =f"3hdmuv##{abx[2]} {file_id}")
                        ]])
                    try
                        if msg_type =="Photo":
                            await client.send_photo(
                                chat_id=cmd.from_user.id,
                                photo=files.file,
                                caption= f_caption,
                                reply_markup = reply_markup
                            )
                        
                        else:
                            await client.send_cached_media(
                                chat_id=cmd.from_user.id,
                                file_id=files.file,
                                caption= f_caption ,
                                reply_markup=reply_markup
                            )
                        return
                    except:
                        if msg_type =="Photo":
                            await client.send_photo(
                                chat_id=cmd.from_user.id,
                                photo=files.file,
                                caption= cpt,
                                reply_markup = reply_markup
                            )
                        
                        else:
                            await client.send_cached_media(
                                chat_id=cmd.from_user.id,
                                file_id=files.file,
                                caption= cpt,
                                reply_markup=reply_markup
                            )
                        return
                elif strg.lower()=="ms":
                    abdata = ""
                    btn3 = None
                    filez=await get_filter_results( file_id ,group_id)
                    for file in reversed(filez):
                        btn3=[]
                        abtext=file.grp.split("##")[0]
                        if abdata == "":
                            abdata=abtext
                        elif abtext not in abdata:
                            abdata =f"{abdata}##{abtext}"       
                    for s in range(0,10):
                        s+=1
                        if f"s{s}" in abdata:
                            dtc=s
                    if btn3==None:
                        rpymk=None
                        caption=f"{f_caption }\n\n.Samahani kuna mteja alikuwa anaomba uweke series au movie hii..Kisha baada ya kuweka bonyeza done ili tumtaarifu kuwa ushaiweka"
                        rpymk1=InlineKeyboardMarkup([[InlineKeyboardButton(f"✅  DONE__", callback_data =f"3hdns {message.from_user.id}")]])
                        f_caption=f"{f_caption}\n\nSamahani mteja Series hii uliokuwa unaiomba bado haijawekwa nmeshatoa taarifa kwa msimamizi wangu atakapoiweka tu ntakujuza."
                        if msg_type =="Photo":
                            await client.send_photo(
                                chat_id=group_id,
                                photo=files.file,
                                caption=caption,
                                reply_markup= rpymk1
                            )
                        
                        else:
                            await client.send_cached_media(
                                chat_id=group_id,
                                file_id=files.file,
                                caption=caption,
                                reply_markup=rpymk1
                            )
                    else:
                        for st in range(0,dtc,2):
                            if st+2 <= dtc :
                                btn3.append([
                                    InlineKeyboardButton(f"🧳  season {st+1}", callback_data =f"3hszn s{st+1}##{file_id}"),
                                    InlineKeyboardButton(f"🧳  season {st+2}", callback_data =f"3hszn s{st+2}##{file_id}")
                                ])
                            else:
                                btn3.append([
                                    InlineKeyboardButton(f"🧳  season {st+1}", callback_data =f"3hszn s{st+1}##{file_id}"),
                                ])
                        rpymk=InlineKeyboardMarkup(btn3)
                    if msg_type =="Photo":
                        await client.send_photo(
                            chat_id=cmd.from_user.id,
                            photo=files.file,
                            caption=f_caption,
                            reply_markup= rpymk
                        )
                        
                    else:
                        await client.send_cached_media(
                                chat_id=cmd.from_user.id,
                                file_id=files.file,
                                caption=f_caption,
                                reply_markup=rpymk
                        )         
                    return
                elif strg.lower() == 's':
                    
                    link = files.descp.split('.dd#.')[2]
                    f_caption =f'{f_caption}\n💥Kama huwezi kufungua link zetu \ntuma **email yako** Mfano:\n**mohamed@gmail.com **\nkumbuka tuma kwa herufi ndogo \n\n** [BONYEZA HAPA](https://t.me/{lk.username})**\nNikupe maelekezo\n🌟@{nyva}'
                    if msg_type =="Photo":
                        await client.send_photo(
                            chat_id=cmd.from_user.id,
                            photo=files.file,
                            caption=f_caption,
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 DOWNLOAD",url= link)]])
                        )
                        
                    else:
                        await client.send_cached_media(
                                chat_id=cmd.from_user.id,
                                file_id=files.file,
                                caption=f_caption,
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 DOWNLOAD",url= link)]])
                        )         
                    return           
        except Exception as err:
            await cmd.reply_text(f"Something went wrong!\n\n**Error:** `{err}`")
    elif usr_cmdall1.startswith("/start xsubinps"):
        
        try:
            ident, file_id = cmd.text.split("_-_-_-_")
            filedetails = await get_file_details(file_id)
            for files in filedetails:
                f_caption=files.reply
                id2 = files.id
                group_id = files.group_id
                msg_type =files.type
                grp = files.grp
            if message.from_user.id !=group_id:
                await client.send_message(chat_id=message.from_user.id,text='Tafadhali bonyeza download kuipakua kweny posta ulikobonyeza button ya edit huna ruksa ya kuedit movie au series hii ')
                return 
            grp1,grp2=grp.split(" ")
            if filedetails:
                if filedetails:  
                    link = files.descp.split('.dd#.')[2]
                    if link == 'data':
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Rekebisha text', callback_data = f"xtext {file_id}")],[InlineKeyboardButton('Rekebisha caption', callback_data = f"xcaption {id2}")],[InlineKeyboardButton('Rekebisha video/file',callback_data = f"xfile {id2}")],[InlineKeyboardButton('Rekebisha kundi', callback_data = "xba")],[InlineKeyboardButton('Rekebisha bei', callback_data = f"xprice {id2}")],[InlineKeyboardButton('Rekebisha Maelezo ya media', callback_data = f"xdescp {id2}")]])
            
                    else:
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Rekebisha text', callback_data = f"xtext {file_id}")],[InlineKeyboardButton('Rekebisha caption', callback_data = f"xcaption {id2}")],[InlineKeyboardButton('Rekebisha link', callback_data = f"xfile {id2}")],[InlineKeyboardButton('Rekebisha kundi', callback_data = "xba")],[InlineKeyboardButton('Rekebisha Maelezo ya media', callback_data = f"xdescp {id2}")]])
            
                    f_caption =f'{f_caption}\n\n**...chagua kitu cha kuedit kwa kubonyeza button husika'
                    if msg_type =="Photo":
                        await client.send_photo(
                            chat_id=cmd.from_user.id,
                            photo=files.file,
                            caption=f_caption,
                            reply_markup=reply_markup
                        )
                    else:
                        await client.send_cached_media(
                                chat_id=cmd.from_user.id,
                                file_id=files.file,
                                caption=f_caption,
                                reply_markup=reply_markup
                        ) 
        except:
            pass
    elif usr_cmdall1.startswith("/start psubinps"):
        await client.send_message(text="Samahani kwa usumbufu tumia /delete <ujumbe wa kufuta> kisha utume sms upya tena Au Utume sms husika tena kwa kutumia jina lilelile  utajifuta wnyewe automatically kisha kupachika sms mpya uliotuma kuna changamoto mcheki @hrm45 akusaidie",chat_id=query.from_user.id)
    else:
        await message.reply(
            text = text,
            quote = True,
            reply_markup = reply_markup,
            disable_web_page_preview = True
        )
        
@Bot0.on_message(filters.command('help') & filters.private)
async def help_msg(client, message):
    await message.reply(
        text = HELP_MESSAGE,
        quote = True,
        reply_markup = InlineKeyboardMarkup(help_keyboard)
    )

@Bot0.on_message(filters.command('about') & filters.private)
async def about_msg(client, message):
    user_id = message.from_user.id
    botusername=await client.get_me()
    nyva=botusername.username  
    nyva=str(nyva)
    if await db.is_admin_exist(user_id,nyva):
        reply_markup = InlineKeyboardMarkup(about_keyboard)
    else:
        reply_markup = InlineKeyboardMarkup(about_keyboard_c)
    await message.reply(
        text = ABOUT_MESSAGE,
        quote = True,
        reply_markup = reply_markup,
        disable_web_page_preview = True
    )

@Bot0.on_callback_query(filters.regex(r'^close$'))
async def close_cbb(client, query):
    try:
        await query.message.reply_to_message.delete()
    except:
        pass
    try:
        await query.message.delete()
    except:
        pass

@Bot0.on_callback_query(filters.regex(r'^help$'))
async def help_cbq(client, query):
    await query.edit_message_text(
        text = HELP_MESSAGE,
        reply_markup = InlineKeyboardMarkup(help_keyboard)
    )
   
@Bot0.on_callback_query(filters.regex('^about$'))
async def about_cbq(client, query):
    user_id = query.from_user.id
    botusername=await client.get_me()
    nyva=botusername.username  
    nyva=str(nyva)
    if await db.is_admin_exist(user_id,nyva):
        reply_markup = InlineKeyboardMarkup(about_keyboard)
    else:
        reply_markup = InlineKeyboardMarkup(about_keyboard_c)
    await query.edit_message_text(
        text = ABOUT_MESSAGE,
        reply_markup = reply_markup,
        disable_web_page_preview = True
    )

@Bot0.on_callback_query( filters.regex('^markdownhelper$') )
async def md_helper(client, query):
    await query.edit_message_text(
        text = MARKDOWN_HELP,
        reply_markup = InlineKeyboardMarkup(markdown_keyboard),
        disable_web_page_preview = True,
        
    )   

@Bot0.on_callback_query(filters.regex('^3h.*'))
async def cb_handler(client, query):
    clicked = query.from_user.id
    try:
        typed = query.message.reply_to_message.from_user.id
    except:
        typed = query.from_user.id
        pass
    if (clicked == typed):
        if query.data.startswith("3hdmuv"):
            botusername=await client.get_me()
            nyva=botusername.username  
            nyva=str(nyva)
            group_id = await db.is_bot_exist(nyva)
            frmt=query.data.split(" ")[0].split("##")[1]
            fileid=query.data.split(" ")[1]
            cmd=query
            for file in await get_file_details(fileid):
                grp=file.grp
                id2=file.id
                prc = file.price
            grp1,grp2 =grp.split(" ")
            if (not (await db.is_acc_exist(cmd.from_user.id,grp1,group_id) or await db.is_acc_exist(cmd.from_user.id,id2,group_id) or await db.is_acc_exist(cmd.from_user.id,grp2,group_id)) or prc == '0')and group_id != cmd.from_user.id :
                await query.edit_message_caption(
                    caption=f"Samahani **{cmd.from_user.first_name}** nmeshindwa kukuruhusu kendelea kwa sababu muv au sizon uliochagua ni za kulipia\n Tafadhal chagua nchi uliopo kuweza kulipia uweze kuitazama \n\n**Kisha baada ya kufanya malipo na kuthibitishiwa malipo yako na admin utabonyeza download hapo juu kuipata movie yako kama utalipia kifurushi utazipakua nyingine zaid kwenye kikundi....** ",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton("🇹🇿 TANZANIA", callback_data =f"tzn##tsh {fileid}"),
                                InlineKeyboardButton("🇰🇪 KENYA",callback_data =f"tzn##ksh {fileid}" )
                            ]
                        ]
                    )
                )
                return     
            await query.answer("hi")
            await query.message.delete()
            details4 =await get_filter_results(fileid,group_id)
            for document in details4:
                if document.grp == frmt:
                    await client.send_cached_media(
                        chat_id = query.from_user.id,
                        file_id = document.file,
                        caption = document.reply.replace("@bongohits_group",f"") if "@bongohits_group" in document.reply else f"{document.reply}" ,
                    )
        elif query.data.startswith("3hmuv"):
            botusername=await client.get_me()
            nyva=botusername.username  
            nyva=str(nyva)
            group_id = await db.is_bot_exist(nyva)
            frmt=query.data.split(" ")[0].split("##")[1]
            fileid=query.data.split(" ")[1]
            strid = fileid
            dta='start'
            icount = 0
            details4 =await get_filter_results(fileid,group_id)
            for document in details4:
                if document.grp == frmt:
                    await client.send_cached_media(
                        chat_id = query.from_user.id,
                        file_id = document.file,
                        caption = document.reply,
                        reply_markup = InlineKeyboardMarkup([[ InlineKeyboardButton(text='delete',callback_data=f'3hydelte {document.id}'),InlineKeyboardButton(text='close',callback_data=f'close')]])
                    )
                    icount+=1
            text1=" Tuma video au document au audio au neno stop kama ushamaliza kutuma ili njumuishe kwenye tangazo la movie au series yako"
            mkv22=await client.send_message(text = text1, chat_id = query.from_user.id)
            id1=mkv22.id+1
            await query.message.delete()
            while dta!='stop':
                stridm = str(uuid.uuid4())
                a,b = funask()
                while a==False:
                    try:
                        mk= await client.get_messages("me",id1)
                        if (mk.media!=None or mk.text!=None) and not mk.photo:
                            a=True
                        if mk.media != None or mk.text!=None:
                            id1=id1+1
                        if (time.time()-b)>(10*60):
                            await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali anza upya jitahidi kutuma ujumbe ndani ya dakika 10 iliniweze kuhudumia na wengine")
                            return
                        if mk.from_user.id != query.from_user.id:
                            a=False 
                    except:
                        a=False
                
                if mk.media and not (mk.photo):
                    for file_type in ("document", "video", "audio"):
                        media = getattr(mk, file_type, None)
                        if media is not None:
                            media.file_type = file_type
                            media.caption = mk.caption
                            break
                    try:
                        await client.send_cached_media(
                            chat_id = CHANNELS,
                            file_id = media.file_id,
                            caption = media.caption,
                        )
                        media.caption = f'{media.caption}\n🌟 @{nyva} 'if media.caption else f'🌟 @{nyva}'
                        await save_file(f'+{icount}.{strid}.{stridm.split("-")[1]}', media.caption, [], media.file_id, media.file_type, stridm,query.from_user.id,'d.dd#.data',0,f'{frmt}')
                    except Exception as e :
                        await client .send_cached_media(
                            chat_id = query.from_user.id,
                            file_id = media.file_id,
                            caption =f'❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌ **Samahani hii media nmeshindwa kusave** huenda caption n kubwa tafadhal punguza kisha itume tena \n Au kama hujui tatizo ntumie msimizi maneno haya ili atatue changamoto yako {e} @hrm46',
                        )
                elif mk.text.lower()=='stop':
                    dta = 'stop'
                    await query.message.copy(chat_id=query.from_user.id)    
                    await mk.reply(f'all file sent to database with id  {strid}')
                    break
                    
                icount+=1
                mkv22.delete()
                mkv22=await client.send_message(text =text1, chat_id = query.from_user.id)  
                
        if query.data.startswith("3hdns"):
            p_caption = query.message.caption.split(".Samahani kuna mteja alikuwa anaomba uweke")[0]
            p_caption =f"{p_caption}\n**🩸🩸🩸tumemtaarifu kikamilifu🩸🩸🩸**"
            f_caption=query.message.caption.replace(".Samahani kuna mteja alikuwa anaomba uweke",'👍Shukrani kwa subra yako tayar tumeshaweka')
            f_caption = f_caption.replace("Kisha baada ya kuweka bonyeza done ili tumtaarifu kuwa ushaiweka"," ")
            await query.edit_message_caption(caption=p_caption,reply_markup=None)
            await query.message.copy(chat_id=int(query.data.split(" ")[1]),caption=f"{f_caption}\n\n**Rudi kwenye kikundi kisha idownload tena ili uweze kuvipakua**",reply_markup=None) 
                
        elif query.data.startswith("3hvdo"):
            botusername=await client.get_me()
            nyva=botusername.username  
            nyva=str(nyva)
            group_id = await db.is_bot_exist(nyva)
            if not group_id:
                return
            abdata = ""
            btn3=None
            file_id= query.data.split(" ")[1]
            filez=await get_filter_results( file_id ,group_id)
            for file in (filez):
                btn3=[]
                abtext=file.grp.split("##")[0]
                if abdata == "":
                    abdata=abtext
                elif abtext not in abdata:
                    abdata =f"{abdata}##{abtext}"       
            for s in range(0,10):
                s+=1
                if f"s{s}" in abdata:
                    dtc=s
            if btn3==None:
                rpymk=None
                await query.edit_message_caption(caption=f"{query.message.caption}\n\nSamahani mteja Series hii uliokuwa unaiomba bado haijawekwa nmeshatoa taarifa kwa msimamizi wangu atakapoiweka tu ntakujuza.")
                await query.message.copy(chat_id=user_details,caption=f"{query.message.caption}\n\n.Samahani kuna mteja alikuwa anaomba uweke series au movie hii..Kisha baada ya kuweka bonyeza done ili tumtaarifu kuwa ushaiweka", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"✅  DONE__", callback_data =f"3hdns {query.from_user.id}")]])) 
            else:
                for st in range(0,dtc,2):
                    if st+2 <= dtc :
                        btn3.append([
                            InlineKeyboardButton(f"🧳  season {st+1}", callback_data =f"3hszn s{st+1}##{file_id}"),
                            InlineKeyboardButton(f"🧳  season {st+2}", callback_data =f"3hszn s{st+2}##{file_id}")
                        ])
                    else:
                        btn3.append([
                            InlineKeyboardButton(f"🧳  season {st+1}", callback_data =f"3hszn s{st+1}##{file_id}"),
                        ])
                rpymk=InlineKeyboardMarkup(btn3)
            stz = await get_file_details(file_id)
            for file in stz:
                f_caption = file.reply
            await query.edit_message_caption(caption=f_caption,reply_markup=rpymk)    
        elif query.data.startswith("3hszn"):
            botusername=await client.get_me()
            nyva=botusername.username  
            nyva=str(nyva)
            user_details = await db.is_bot_exist(nyva)
            if not user_details:
                return
            ab8=query.data.split('##')[-1]
            group_id = user_details
            for file in await get_file_details(ab8):
                grp=file.grp
                id2=file.id
                prc = file.price
            cmd=query
            grp1,grp2 =grp.split(" ")
            if (not (await db.is_acc_exist(cmd.from_user.id,grp1,group_id) or await db.is_acc_exist(cmd.from_user.id,id2,group_id) or await db.is_acc_exist(cmd.from_user.id,grp2,group_id)) or prc == '0')and group_id != cmd.from_user.id :
                await query.edit_message_caption(
                    caption=f"Samahani **{cmd.from_user.first_name}** nmeshindwa kukuruhusu kendelea kwa sababu muv au sizon uliochagua ni za kulipia\n Tafadhal chagua nchi uliopo kuweza kulipia uweze kuitazama \n\n**Kisha baada ya kufanya malipo na kuthibitishiwa malipo yako na admin utabonyeza download hapo juu kuipata movie yako kama utalipia kifurushi utazipakua nyingine zaid kwenye kikundi....** ",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton("🇹🇿 TANZANIA", callback_data =f"tzn##tsh id2"),
                                InlineKeyboardButton("🇰🇪 KENYA",callback_data =f"tzn##ksh id2" )
                            ]
                        ]
                    )
                )
                return     
            try:
                ab1,ab2=query.data.split('##')
                abdata = ""
                ab1=ab1.split(" ")[1]
                btn3=None
                filez=await get_filter_results( ab2,user_details)
                for file in (filez):
                    if (ab1 in file.grp) and "s10" not in file.grp:
                        btn3=[]
                        abtext=file.grp.split("##")[1]
                        if abdata == "":
                            abdata=abtext
                        elif abtext not in abdata:
                            abdata =f"{abdata}##{abtext}"   
                    elif (ab1 in file.grp) and ab1=="s10":
                        btn3=[]
                        abtext=file.grp.split("##")[1]
                        if abdata == "":
                            abdata=abtext
                        elif abtext not in abdata:
                            abdata =f"{abdata}##{abtext}"
                for s in range(0,1000,100):
                    s+=100
                    if f"{s}" in abdata:
                        dtc=s
                if btn3==None:
                    rpymk=None
                    await query.edit_message_caption(caption=f"{query.message.caption}\n\nSamahani mteja season uliokuwa unaiomba bado haijawekwa nmeshatoa taarifa kwa msimamizi wangu atakapoiweka tu ntakujuza..bonyeza rudi nyuma kutizama season nyingine",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"🔙 RUDI NYUMA", callback_data =f"3hvdo {ab2}")]]))
                    await query.message.copy(chat_id=user_details,caption=f"{query.message.caption}\n\n.Samahani kuna mteja alikuwa anaomba uweke season **{ab1}** ya series au movie hii..Kisha baada ya kuweka bonyeza done ili tumtaarifu kuwa ushaiweka", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"✅  DONE__", callback_data =f"3hdns {query.from_user.id}")]])) 
                else:
                    for st in range(0,dtc,200):  
                        if st+200 <= dtc :
                            btn3.append([
                                InlineKeyboardButton(f"🧳  {st+1} hadi {st+100}", callback_data =f"3hszn {ab1}##{st+100}##{ab2}"),
                                InlineKeyboardButton(f"🧳  {st+101} hadi {st+200}", callback_data =f"3hszn {ab1}##{st+200}##{ab2}")
                            ])
                        else:
                            btn3.append([
                                InlineKeyboardButton(f"🧳  {st+1} hadi {st+100}", callback_data =f"3hszn {ab1}##{st+100}##{ab2}"),
                            ])
                    btn3.append([
                                InlineKeyboardButton(f"🔙 RUDI NYUMA", callback_data =f"3hvdo {ab2}"),
                            ])
                    rpymk=InlineKeyboardMarkup(btn3)
                
                await query.edit_message_reply_markup(reply_markup=rpymk)    
            except :
                try: 
                    ab1,ab2,ab3=query.data.split('##')
                    abdata = ""
                    ab1=ab1.split(" ")[1]
                    btn3=None
                    ab2=int(ab2)
                    filez=await get_filter_results( ab3,user_details)
                    for file in (filez): 
                        
                        if (f"{ab1}##{ab2}") in file.grp and "1000" not in file.grp:
                            btn3=[]
                            abtext=file.grp.split("##")[2]
                            if abdata == "":
                                abdata=abtext
                            elif abtext not in abdata:
                                abdata =f"{abdata}##{abtext}"  
                        elif (f"{ab1}##{ab2}") in file.grp and ab2==1000:
                            btn3=[]
                            abtext=file.grp.split("##")[2]
                            if abdata == "":
                                abdata=abtext
                            elif abtext not in abdata:
                                abdata =f"{abdata}##{abtext}"

                    for s in range(0,100,10):
                        s+=10
                        if f"{s}" in abdata:
                            dtc=s
                    if btn3==None:
                        rpymk=None 
                        await query.edit_message_caption(caption=f"{query.message.caption}\n\nSamahani Vipande hivi uliokuwa unaiomba bado havijawekwa nmeshatoa taarifa kwa msimamizi wangu atakapoiweka tu ntakujuza..bonyeza rudi nyuma kutizama season nyingine",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"🔙 RUDI NYUMA", callback_data =f"3hvdo {ab3}")]]))
                        await query.message.copy(chat_id=user_details,caption=f"{query.message.caption}\n\n.Samahani kuna mteja alikuwa anaomba uweke season hii kuanzia kipande cha \n--->**{ab1}.{ab2-99} hadi {ab2}** ya series au movie hii..Kisha baada ya kuweka bonyeza done ili tumtaarifu kuwa ushaiweka", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"✅  DONE__", callback_data =f"3hdns {query.from_user.id}")]])) 
                        return
                    else:
                        for st in range(0,dtc,20):
                            if st+20 <= dtc :
                                btn3.append([
                                    InlineKeyboardButton(f"🧳  {st+ab2-99} hadi {st+ab2-90}", callback_data =f"3hszn {ab1}##{ab2}##{st+10}##{ab3}"),
                                    InlineKeyboardButton(f"🧳  {st+ab2-89} hadi {st+ab2-80}", callback_data =f"3hszn {ab1}##{ab2}##{st+20}##{ab3}")
                                ])
                            else:
                                btn3.append([
                                    InlineKeyboardButton(f"🧳  {st+ab2-99} hadi {st+ab2-90}", callback_data =f"3hszn {ab1}##{ab2}##{st+10}##{ab3}"),
                                ])
                        btn3.append([
                                InlineKeyboardButton(f"🔙 RUDI NYUMA", callback_data =f"3hszn {ab1}##{ab3}"),
                            ])
                        rpymk=InlineKeyboardMarkup(btn3)
                    await query.edit_message_reply_markup(reply_markup=rpymk)    
                except:
                    user_dts=await is_user_exist(f"{user_details}##{query.from_user.id}",nyva)
                    for usr1 in user_dts:
                        tme1=usr1.tme
                        tme1=tme1
            
                    if tme1 > 0:
                        abk=await client.send_message(chat_id=query.from_user.id,text=f'tafadhal subiri kwa sekunde {tme1} kabla ya kutuma ombi jengine')
                        for i in range(0,tme1,10):
                            await asyncio.sleep(10)
                            if tme1 < 10:
                                tme1=10
                            user_dts=await is_user_exist(f"{user_details}##{query.from_user.id}",nyva)
                            for usr1 in user_dts:
                                tme2=usr1.tme
                                tme2=tme2
                            if tme2==tme1:
                                await User.collection.update_one({'_id':f"{user_details}##{query.from_user.id}"} ,{'$set':{'tme':0}}) 
                            if (tme1-i-10) > 0:
                                await abk.edit_text(text=f"tafadhali subir kwa sekunde {tme1-i-10} kabla ya kutuma ombi lingine")
                            elif (tme1-i-10) <=0:
                                await abk.edit_text(text=f"Sasa unaweza kutuma ombi lingine")
                                break
                        return 
                    else:
                        await User.collection.update_one({'_id':f"{user_details}##{query.from_user.id}"} ,{'$set':{'tme':0}})             
                    ab1,ab2,ab4,ab3=query.data.split('##')
                    abdata = ""
                    ab1=ab1.split(" ")[1]
                    btn3=None
                    ab2=int(ab2)
                    ab4=int(ab4)
                    tme3=80
                    filez=await get_filter_results( ab3,user_details)
                    await User.collection.update_one({'_id':f"{user_details}##{query.from_user.id}"},{'$set':{'tme':80}})
                    await query.message.delete()
                    sb7=0
                    for file in (filez): 
                        if (f"{ab1}##{ab2}##{ab4}") in file.grp and "0##100" not in file.grp:
                            sb7=1
                            await client.send_cached_media(
                                chat_id=query.from_user.id,
                                file_id=file.file,
                                caption=file.reply.replace("@bongohits_group",f"") if "@bongohits_group" in file.reply else f"{file.reply}",
                            )
                            await asyncio.sleep(2)
                            tme3-=2
                            await User.collection.update_one({'_id':f"{user_details}##{query.from_user.id}"},{'$set':{'tme':tme3}})   
                        elif (f"{ab1}##{ab2}##{ab4}" in file.grp) and ab4==100:
                            sb7=1
                            await client.send_cached_media(
                                chat_id=query.from_user.id,
                                file_id=file.file,
                                caption=file.reply.replace("@bongohits_group",f"") if "@bongohits_group" in file.reply else f"{file.reply}",
                            )
                            await asyncio.sleep(2)
                            tme3-=2
                            await User.collection.update_one({'_id':f"{user_details}##{query.from_user.id}"},{'$set':{'tme':tme3}})   
                    user_dts=await is_user_exist(f"{user_details}##{query.from_user.id}",nyva)
                    for usr1 in user_dts:
                        tme1=usr1.tme
                    if sb7==0:
                        await User.collection.update_one({'_id':f"{user_details}##{query.from_user.id}"},{'$set':{'tme':0}})
                        await query.message.copy(chat_id=query.from_user.id,caption=f"{query.message.caption}\n\nSamahani Vipande hivi uliokuwa unaiomba bado havijawekwa nmeshatoa taarifa kwa msimamizi wangu atakapoiweka tu ntakujuza..bonyeza rudi nyuma kutizama vipande vingine",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"🔙 RUDI NYUMA", callback_data =f"3hvdo {ab3}")]]))
                        await query.message.copy(chat_id=user_details,caption=f"{query.message.caption}\n\n.Samahani kuna mteja alikuwa anaomba uweke season hii kuanzia kipande cha \n--->**{ab1}.{ab2-109+ab4} hadi {ab2-100+ab4}** ya series au movie hii..Kisha baada ya kuweka bonyeza done ili tumtaarifu kuwa ushaiweka", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"✅  DONE__", callback_data =f"3hdns {query.from_user.id}")]])) 
                        return
                    await query.message.copy(chat_id=query.from_user.id)
                    if tme1 != 0 :
                        for i in range(0,tme1,1):
                            await asyncio.sleep(1)
                            await User.collection.update_one( {'_id':f"{user_details}##{query.from_user.id}"} , {'$set':{'tme':tme1-i-1}})
        elif query.data.startswith("3htest1"):
            await query.answer("🎙Soma tangulizi mfupi wa robot huyu kama upo na Viongozi wangu walionitengeneza",show_alert=True,cache_time=10)
            botusername=await client.get_me()
            nyva=botusername.username  
            nyva=str(nyva)
            user_details = await db.is_bot_exist(nyva)
            if not user_details:
                return
            ban_status = await db.get_db_status(user_details)
            mtext1="""<b>{db_name}</b>
{descp}

<b>ABOUT THE BOT</b>
⭐️Mmiliki na anayehusika na robot Huyu:
**{admin_name}**🥹

☘Developer and designer
**{owner_name}**🥹

🟡Mda wowote tuma  /msaada utapata maelekezo na kuweza kutatua changamoto yako iwe kwenye kikundi au private ➡️yaani kwenye robot"""
            st1 = await client.get_users(int(user_details))
            st2 = await client.get_users(int(OWNER_ID))
            mtext1=mtext1.format(db_name=ban_status["db_name"].upper(),descp=ban_status["mwongozo"],admin_name=st1.mention.upper(),owner_name=st2.mention.upper())
            await query.edit_message_text(text=f'{mtext1}',reply_markup=InlineKeyboardMarkup( [[InlineKeyboardButton("⬅️ BACK", callback_data =f'3hmbele {query.data.split(" ")[1]}'),InlineKeyboardButton("💥 HITIMISHA", callback_data =f'3htest1 {query.data.split(" ")[1]}') ]]))
            await asyncio.sleep(9)
            await query.edit_message_text(text=f'{mtext1}..',reply_markup=InlineKeyboardMarkup( [[InlineKeyboardButton("⬅️ BACK", callback_data =f'3hmbele {query.data.split(" ")[1]}'),InlineKeyboardButton("💥 HITIMISHA", callback_data =f'3hfnl {query.data.split(" ")[1]}') ]]))
        elif query.data.startswith('3hfnl') :
            botusername=await client.get_me()
            nyva=botusername.username  
            nyva=str(nyva)
            user_details = await db.is_bot_exist(nyva)
            ban_status = await db.get_db_status(user_details)   
            hjkl = f'{user_details}##{query.from_user.id}'
            existt=await is_user_exist(hjkl,nyva)
            if not existt: 
                await add_user(hjkl,nyva)
            inv_lnk = await client.get_chat( int(query.data.split(" ")[1]) )
            inv_link=inv_lnk.invite_link
            await query.edit_message_text(text=f'✔️ Shukrani zetu zikufikie wewe uliweza kusoma mpaka hapa nahisi umetuelewa tunahusika na nini pia jinsi ya kupata huduma zetu..\n\n**Tumeshakuruhusu kutuma ujumbe kwenye kikundi ulichojiunga nacho** \n\nBonyeza **KIKUNDI** kurudi kwenye kikundi ',reply_markup=InlineKeyboardMarkup( [[InlineKeyboardButton("⬅️ BACK", callback_data =f'3htest1 {query.data.split(" ")[1]}'),InlineKeyboardButton("💥 KIKUNDI", url =f'{inv_link}') ]]))
        elif query.data.startswith("3hmbele"):
            botusername=await client.get_me()
            nyva=botusername.username  
            nyva=str(nyva)
            user_details = await db.is_bot_exist(nyva)
            if not user_details:
                return
            ban_status = await db.get_db_status(user_details)   
            mtext="""💥💥💥💥💥💥💥💥💥💥💥💥💥💥💥💥  
        <b>MWONGOZO {db_name}</b>
        
👉Tunahusika na uuzaji wa movie na series kwa njia ya kidigital na kupata movie yako hapo hapo...baada ya  kufanya malipo ya series/movie husika na kuipakua mda wowote saa 24
📖:Soma kiumakin maana  hutofanya chochote kama muongozo huu huja soma.

☀️Telegram tunatumia roboti kutoa huduma zetu hivyo kila mtu anajihudumia na huduma ni saa 24 kwasababu roboti hachoki, halali wala haishiwi bando cha kufanya fuata maelekezo jinsi ya kupakua huduma zetu.

1⃣Ukitaka movie/singo yoyote ile iwe ya kibongo, ya nje, iliyotafsiriwa au ambayo haijatafsiriwa, anza kwa kuandika MOVIE kisha acha nafasi andika jina la hiyo movie unayotaka. 
Mfano: MOVIE FAST X.

2⃣Ukitaka series anza kwa kuandika SERIES kisha acha nafasi andika jina la hiyo series unayotaka. 
Mfano: SERIES GHUM HE.

🚴‍♀Ukifuata maelekezo hayo hapo juu kwa usahihi utaletewa kitu unachotaka na utakachotakiwa kufanya utabonyeza mahali palipoandikwa download kisha ukurasa unaofuata utabonyeza neno START utapata unachotaka au kupata mwongozo jinsi ya kukipakua..
💥Kumbuka kama series au movie haipo tafadhali bonyeza sehemu husika ili admin aipakie chapu

Bonyeza button hapo chini kusoma hitimisho la huduma zetu """
            mtext=mtext.format(db_name=ban_status["db_name"].upper())
            await query.answer("💥Usiharakie mbele Soma kiumakini ntakurudisha hapa utakapo shindwa kufuata muongozo wa huduma zetu",show_alert=True,cache_time=10)
            await query.edit_message_text(text=f'{mtext}',reply_markup=InlineKeyboardMarkup( [[InlineKeyboardButton("MBELE ZAIDI", callback_data =f'3hmbele {query.data.split(" ")[1] }')]]))
            await asyncio.sleep(9)
            await query.edit_message_text(text=f'{mtext} .',reply_markup=InlineKeyboardMarkup( [[InlineKeyboardButton("MBELE ZAIDI", callback_data =f'3htest1 {query. data.split(" ")[1] }')]]))
        elif query.data.startswith("3h4ddd"):
            botusername=await client.get_me()
            nyva=botusername.username  
            nyva=str(nyva)
            await query.edit_message_reply_markup(reply_markup=btn22(nyva,"series",f"3hsss##{query.data.split(' ',1)[1] }"))
        elif query.data.startswith("3hsss"):
            botusername=await client.get_me()
            nyva=botusername.username  
            nyva=str(nyva)
            group_id = await db.is_bot_exist(nyva)
            
            ab=''
            bb,ab=query.data.split(' ',1)
            ab=str(ab) 
            strid=bb.split('##')[1]
            try:
                ab1=ab.split('##')
                if len(ab1) != 1:
                    ab1,ab2,ab3,ab4 = ab.split('##')
                a2b='Chagua button husika kuadi vipande vya series hii kwa mpangilio.Note kama usha tuma vipande vya nyuma vitatumwa kama kuna ambacho ulikosea waeza futa kisha ukatuma tena..kama sivyo bonyeza close kwenye kila kipande'         
                if a2b in query.message.caption:
                    await query.edit_message_caption(caption=f'{query.message.caption}',reply_markup=btn2(10,ab,bb))
                if a2b not in query.message.caption:
                    await query.edit_message_caption(caption=f'{query.message.caption.split("...")[0]}\n\n Chagua button husika kuadi vipande vya series hii kwa mpangilio.Note kama usha tuma vipande vya nyuma vitatumwa kama kuna ambacho ulikosea waeza futa kisha ukatuma tena..kama sivyo bonyeza close kwenye kila kipande',reply_markup=btn2(10,ab,bb))    
            except:
                try:
                    ab1,ab2=ab.split('##')
                    await query.edit_message_caption(caption=f'{query.message.caption}',reply_markup=btn2(1,ab,bb))    
                except:
                    try: 
                        ab1,ab2,ab3=ab.split('##')
                        dta='start'
                        icount = int(ab3)
                        details4 =await get_filter_results(bb.split('##')[1],group_id )
                        for document in details4:
                            if ab==document.grp:
                                await client.send_cached_media(
                                        chat_id = query.from_user.id,
                                        file_id = document.file,
                                        caption = document.reply,
                                        reply_markup = InlineKeyboardMarkup([[ InlineKeyboardButton(text='delete',callback_data=f'3hydelte {document.id}'),InlineKeyboardButton(text='close',callback_data=f'close')]])
                                    )
                            icount+=1
                        text1=" Tuma video au document au audio au neno stop kama ushamaliza kutuma ili njumuishe kwenye tangazo la movie au series yako"
                        mkv22=await client.send_message(text = text1, chat_id = query.from_user.id)
                        id1=mkv22.id+1
                        await query.message.delete()
                        while dta!='stop':
                            stridm = str(uuid.uuid4())
                            a,b = funask()
                            while a==False:
                                try:
                                    mk= await client.get_messages("me",id1)
                                    if (mk.media!=None or mk.text!=None) and not mk.photo:
                                        a=True
                                    if mk.media != None or mk.text!=None:
                                        id1=id1+1
                                    if (time.time()-b)>(10*60):
                                        await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali anza upya jitahidi kutuma ujumbe ndani ya dakika 10 iliniweze kuhudumia na wengine")
                                        return
                                    if mk.from_user.id != query.from_user.id:
                                        a=False 
                                except:
                                    a=False
                
                            if mk.media and not (mk.photo):
                                for file_type in ("document", "video", "audio"):
                                    media = getattr(mk, file_type, None)
                                    if media is not None:
                                        media.file_type = file_type
                                        media.caption = mk.caption
                                        break
                                try:
                                    await asyncio.sleep(2)
                                    await client.send_cached_media(
                                        chat_id = CHANNELS,
                                        file_id = media.file_id,
                                        caption = media.caption,
                                    )
                                    media.caption = f'{media.caption}\n🌟 @{nyva} 'if media.caption else '🌟 @{nyva}'
                                    await save_file(f'+{icount}.{strid}.{stridm.split("-")[1]}', media.caption, [], media.file_id, media.file_type, stridm,query.from_user.id,'d.dd#.data',0,f'{ab}')
                                except Exception as e :
                                    await client .send_cached_media(
                                        chat_id = query.from_user.id,
                                        file_id = media.file_id,
                                        caption =f'❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌❌ **Samahani hii media nmeshindwa kusave** huenda caption n kubwa tafadhal punguza kisha itume tena \n Au kama hujui tatizo ntumie msimizi maneno haya ili atatue changamoto yako {e} @hrm46',
                                    )
                            elif mk.text.lower()=='stop':
                                dta = 'stop'
                                await query.message.copy(chat_id=query.from_user.id)    
                                await mk.reply(f'all file sent to database with id  {strid}')
                                break
                    
                            icount+=1
                            mkv22.delete()
                            mkv22=await client.send_message(text =text1, chat_id = query.from_user.id)  
            
                    except Exception as e :
                        await client.send_message(query.from_user.id,text=f'error{e}')         
        elif query.data.startswith("3hdone"):
            await query.edit_message_text("tumetaarifu kikamilifu asante kwa kuonyesha uaminifu kwa wateja wako")
            gd=await db.get_db_status(query.from_user.id)
            await client.send_message(chat_id=int(query.data.split(" ")[1]),text=f'Shukrani kwa subra yako sasa unaeza pata huduma zote ulizolipia kifurushi chamgamoto yoyote tuulize kwenye kikundi\n\n{gd["group"].split("##")[1]}')           
        elif query.data.startswith("3hydelte"):
            id1=query.data.split(" ")[1]                                                              
            await query.edit_message_caption(caption="je unauhakika unataka tufute",reply_markup= InlineKeyboardMarkup([[InlineKeyboardButton(text='yes',callback_data=f'3hdelte {id1}')] ,[InlineKeyboardButton(text='Close',callback_data=f'close')]]))                                                                        
        elif query.data.startswith("3hdelte"):
            try:
                id1=query.data.split(" ")[1]                                                                 
                await Media.collection.delete_one({"_id":id1})
                await query.edit_message_caption(
                    caption = f"imefutika kikamilifu bonyeza close kuifuta hapa",  
                    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text='Close',callback_data=f'close')]])
                )
            except:
                await client.send_message(
                      chat_id =query.from_user.id,
                      text = f"samahani huenda hii media imeshafutwa nmeikosa kwenye database yng  ",
                      
                )
                                                                             
def btn2(ab6,ab22,ab34):
    ab77=[]
    ab9=0
    for i in range(0,5):
        ab9=ab9+1
        if ab6==10:
            ab8 = f"{ab6*(ab9-1)}1 hadi {ab6*(ab9)}0" 
            ab10 = f"{ab6*(ab9)}1 hadi {ab6*(ab9+1)}0"
            ab77.append([
                InlineKeyboardButton(f"{ab8}", callback_data =f"{ab34} {ab22}##{ab6*(ab9)}0"),
                InlineKeyboardButton(f"{ab10}", callback_data =f"{ab34} {ab22}##{ab6*(ab9+1)}0")
            ])
        elif ab6==1:
            abd=(int(ab22.split("##")[1]))-100
            sd1=int(f"{ab6*(ab9-1)}1")+abd
            sd2=int(f"{ab6*(ab9)}0")+abd
            sd3=int(f"{ab6*(ab9)}1")+abd
            sd4= int(f"{ab6*(ab9+1)}0")+abd
            ab8 = f"{sd1} hadi {sd2}" 
            ab10 = f"{sd3} hadi {sd4}"
            ab77.append([
                InlineKeyboardButton(f"{ab8}", callback_data =f"{ab34} {ab22}##{ab6*(ab9)}0"),
                InlineKeyboardButton(f"{ab10}", callback_data =f"{ab34} {ab22}##{ab6*(ab9+1)}0")
            ])
        ab9=ab9+1
    if ab6==10:
        ab77.append([
                    InlineKeyboardButton(f"rudi nyuma", callback_data =f"3h4ddd {ab34.split('##')[1]}")
            ])
    elif ab6==1:
        ab77.append([
                    InlineKeyboardButton(f"rudi nyuma", callback_data =f"{ab34} {ab22.split('##')[0]}")
            ])
    return InlineKeyboardMarkup(ab77)

def funask():
    a=False
    b=time.time()
    return a,b

def btn22(nyva,ab22,ab43):
    ab=[]
    ab7="n"
    try:
        ab6=int(nyva)
        ab7="y"
    except:
        pass
    ab9=0
    for i in range(0,5):
        ab9=ab9+1
        if ab7=="n":
            ab8=f"season {ab9}"
            ab11=ab9+1
            ab10=f"season {ab11}"
            ab.append([
                InlineKeyboardButton(f"{ab8}", callback_data =f"{ab43} s{ab9}"),
                InlineKeyboardButton(f"{ab10}", callback_data =f"{ab43} s{ab11}")
            ])
        ab9=ab9+1
    ab.append([
                InlineKeyboardButton(f"rudi nyuma", url=f"https://t.me/{nyva}?start=xsubinps_-_-_-_{ab43.split('##')[1]}"),
        ])
    return InlineKeyboardMarkup(ab)
