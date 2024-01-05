from info import filters,CHANNELS,OWNER_ID
import uuid
import time,re,os,asyncio
from plugins.base_command import btn22
from pyrogram.errors import ChatAdminRequired
from utils import get_file_details,get_filter_results,is_user_exist,Media,is_subscribed,is_group_exist,save_file,add_user
from botii  import Bot0
import requests
from plugins.database import db
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery,ForceReply,ChatPermissions

@Bot0.on_message( filters.command('edit_admin') & filters.private)
async def group2(client, message):
    botusername=await client.get_me()
    nyva=botusername.username  
    nyva=str(nyva)
    status= await db.is_admin_exist(message.from_user.id,nyva)
    if not status:
        return
    await client.send_message(chat_id= message.from_user.id,text="chagua huduma unayotaka kufanya marekebisho",
            reply_markup =InlineKeyboardMarkup([[InlineKeyboardButton('Rekebisha Makundi', callback_data = "kundii")],[InlineKeyboardButton('Rekebisha Jina la Kikundi', callback_data = "dbname")],[InlineKeyboardButton('Rekebisha Startup sms', callback_data = "startup")],[InlineKeyboardButton('Rekebisha Mawasiliano', callback_data = "xba")]])
        ) 
@Bot0.on_message( filters.command('renamee') & filters.private)
async def grouop22(client, message):
    filter = {'group_id': regex}
    total_results = await Media.count_documents(filter)
    cursor = Media.find(filter)
    await message.reply_text(
            f"total found {total_results}")
    cursor.sort('text', 1)
    for file in await cursor.to_list(length=int(total_results)):
        if len(file.reply)>=900:
            await message.reply_text(
                f"len{file.reply}")
        #await Media.collection.update_one({'_id':file.id},{'$set':{'text':file.text.replace( message.command[1] , message.command[2])}})
            
"""@Bot0.on_message( filters.command('rename') & filters.private)
async def grouop2(client, message):
    if len(message.command) != 5:
        await message.reply_text(
            f"tuma /rename 1234kb 1234kw usrkbadlisha usrkuweka")
        return 
    raw_pattern = r'\b' + message.command[1] + r'.*'
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except Exception as e :
        print(e)
        return
    else:
        filter = {'text': regex}
    filter["type"]="Photo"
    filter['group_id'] = int(message.command[1])
    total_results = await Media.count_documents(filter)
    cursor = Media.find(filter)
    await message.reply_text(
            f"total found {total_results}")
    cursor.sort('text', 1)
    for file in await cursor.to_list(length=int(total_results)):
        if "data" in file.descp :
            print("hi")
            continue 
        elif len(file.descp.split(".dd#."))>=3:
            abb = await save_file( file.text.split(".dd#")[0] + ".dd#." + message.command[2], 'reply_text', [], 'fileid', 'msg_type', 'strid',int(message.command[2]),'descp',"chec",'normal')
            if abb != "hrm46":
                print("hi")
                strid = str(uuid.uuid4())
                file.reply=file.reply.replace( message.command[3] ,message.command[4])
                file.reply=file.reply.replace("hrm45",message.command[4])
                await save_file(file.text.split(".dd#")[0] + ".dd#." + message.command[2], file.reply, file.btn, file.file, file.type, strid, int(message.command[2]) ,file.descp,file.price,file.grp)
  """      
@Bot0.on_callback_query()
async def cb_handler(client, query):
    clicked = query.from_user.id
    try:
        typed = query.message.reply_to_message.from_user.id
    except:
        typed = query.from_user.id
        pass
    if (clicked == typed):
        if query.data == "kundii":
            ab = await db.get_db_status(query.from_user.id)
            grp="grp"
            if ab['g_1']=="hrm45":
                reply_markup=replymkup3(ab,grp,1)
            elif ab['g_2']=="hrm45":
                reply_markup=replymkup3(ab,grp,2)
           
            elif ab['g_3']=="hrm45":
                reply_markup=replymkup3(ab,grp,3)
            elif ab['g_4']=="hrm45":
                reply_markup=replymkup3(ab,grp,4)
            elif ab['g_5']=="hrm45":
                reply_markup=replymkup3(ab,grp,5)
            elif ab['g_6']=="hrm45":
                reply_markup=replymkup3(ab,grp,6)
            else:
                reply_markup=replymkup3(ab,grp,7)
            await query.edit_message_text(text = "🌺🌺🌺🌺🌺🌺🌺🌺🌺\nTafadhali chagua kifurushi cha kusahihisha au bonyeza 🦋 ADD KIFURUSHI kuongeza kifurushi kingine\n\n🌸kisha subiri utapewa maelekezo jinsi ya kusahihisha kifurushi chako\n\n💥Kumbuka vifurushi mwisho ni sita tu , pangilia vizuri vifurushi vyako", 
                reply_markup=reply_markup)
            await query.answer('Tafadhali subiri')
 
        elif query.data.startswith("kad2grp"):
            await query.answer('Subiri kidogo')
            await query.message.delete()
            ghi1=query.data.split(" ")[1]
            ab = await db.get_db_status(query.from_user.id)
            try:
                mkv11 = await client.send_message(chat_id = query.from_user.id,text=f'Naomba untumie jina LA kifurushi Mfano kifurushi cha vyote Mfano2 Kifurushi cha singo')
                a,b = funask()
                id1 = mkv11.id + 1
                while a==False:
                    try:
                        mkv1 = await client.get_messages("me",id1)
                        if mkv1.text!=None:
                            a=True
                        if (time.time()-b)>(3*60):
                            await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali anza upya jitahidi kutuma ujumbe ndani ya dakika 3 iliniweze kuhudumia na wengine",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
                            return
                        if mkv1.from_user.id != query.from_user.id :
                            a=False
                            id1=id1+1
                    except:
                        a=False
                a=False
                if mkv1.text==None: 
                    await client.send_message(chat_id = query.from_user.id,text=f"umetuma ujumbe ambao s sahihi,Kama hujaelewa jinsi tafadhal mcheki msimamiz @hrm45 akusaidie bonyeza rudi nyuma uanze upya kutengeneza kifurushi",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'kundii')]]))
                    return
                mkv7 = await client.send_message(chat_id = query.from_user.id,text=f'Naomba bei ya mteja atakayopata huduma hii kwa muda wa siku moja mfano 500 \nNote Tuma namba tu:::Kama huduma hii haipo tuma 0')
                a,b = funask()
                id1=mkv7.id+1
                while a==False:
                    try:
                        mkv777 = await client.get_messages("me",id1)
                        if mkv777.text!=None:
                            a=True
                        if (time.time()-b)>(60):
                            await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali anza upya jitahidi kutuma ujumbe ndani ya dakika 1 iliniweze kuhudumia na wengine",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
                            return
                        if mkv777.from_user.id != query.from_user.id :
                            a=False
                            id1=id1+1
                    except:
                        a=False
                mkv77 = int(mkv777.text)
                mkv2 = await client.send_message(chat_id = query.from_user.id,text=f'Naomba bei ya mteja atakayopata huduma hii kwa muda wa wiki 1 mfano 500 \nNote Tuma namba tu:::Kama huduma hii haipo tuma 0')
                a,b = funask()
                id1 = mkv2.id + 1
                while a==False:
                    try:
                        mkv222 = await client.get_messages("me",id1)
                        if mkv222.text!=None:
                            a=True
                        if (time.time()-b)>(60):
                            await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali anza upya jitahidi kutuma ujumbe ndani ya dakika 1 iliniweze kuhudumia na wengine",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
                            return
                        if mkv222.from_user.id != query.from_user.id :
                            a=False
                            id1=id1+1
                            
                    except:
                        a=False
                mkv22=int(mkv222.text)
                mkv3 = await client.send_message(chat_id = query.from_user.id,text=f'Naomba bei ya mteja atakayopata huduma hii kwa muda wa wiki 2 mfano 500 \nNote Tuma namba tu:::Kama huduma hii haipo tuma 0')
                a,b = funask()
                id1=mkv3.id+1
                while a==False:
                    try:
                        mkv333 = await client.get_messages("me",id1)
                        if mkv333.text!=None:
                            a=True
                        if (time.time()-b)>(60):
                            await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali anza upya jitahidi kutuma ujumbe ndani ya dakika 1 iliniweze kuhudumia na wengine",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
                            return
                        if mkv333.from_user.id != query.from_user.id :
                            a=False
                            id1=id1+1
                    except:
                        a=False
                mkv33=int(mkv333.text)
                mkv4 = await client.send_message(chat_id = query.from_user.id,text=f'Naomba bei ya mteja atakayopata huduma hii kwa muda wa wiki 3 mfano 500 \nNote Tuma namba tu:::Kama huduma hii haipo tuma 0')
                a,b = funask()
                id1 = mkv4.id+1
                while a==False:
                    try:
                        mkv444 = await client.get_messages("me",id1)
                        if mkv444.text!=None:
                            a=True
                        if (time.time()-b)>(60):
                            await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali anza upya jitahidi kutuma ujumbe ndani ya dakika 1 iliniweze kuhudumia na wengine",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
                            return
                        if mkv444.from_user.id != query.from_user.id :
                            a=False
                            id1=id1+1
                    except:
                        a=False
                mkv44 = int(mkv444.text)
                mkv5 = await client.send_message(chat_id = query.from_user.id,text=f'Naomba bei ya mteja atakayopata huduma hii kwa muda wa mwezi mfano 500 \nNote Tuma namba tu:::Kama huduma hii haipo tuma 0')
                a,b = funask()
                id1=mkv5.id+1
                while a==False:
                    try:
                        mkv555 = await client.get_messages("me",id1)
                        if mkv555.text!=None:
                            a=True
                        if (time.time()-b)>(60):
                            await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali anza upya jitahidi kutuma ujumbe ndani ya dakika 1 iliniweze kuhudumia na wengine",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
                            return
                        if mkv555.from_user.id != query.from_user.id :
                            a=False
                            id1=id1+1
                    except:
                        a=False
                mkv55 = int(mkv555.text)
                mkv66 = await client.send_message(chat_id = query.from_user.id,text=f'Naomba maelezo kidogo ya kifurushi hikii')   
                a,b = funask()
                id1=mkv66.id+1
                while a==False:
                    try:
                        mkv6 = await client.get_messages("me",id1)
                        if mkv6.text!=None:
                            a=True
                        if (time.time()-b)>(3*60):
                            await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali anza upya jitahidi kutuma ujumbe ndani ya dakika 3 iliniweze kuhudumia na wengine",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
                            return
                        if mkv6.from_user.id != query.from_user.id :
                            a=False
                            id1=id1+1
                    except:
                        a=False
                if mkv6.text ==None: 
                    await client.send_message(chat_id = query.from_user.id,text=f"umetuma ujumbe ambao s sahihi,Kama hujaelewa jinsi tafadhal mcheki msimamiz @hrm45 akusaidie bonyeza rudi nyuma uanze upya kutengeneza kifurushi",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'kundii')]]))
                    return
                await mkv1.delete()
                await mkv2.delete()
                await mkv3.delete()
                await mkv4.delete()
                await mkv5.delete()
                await mkv7.delete()
                await mkv6.delete()
                await mkv11.delete()
                await mkv222.delete()
                await mkv333.delete() 
                await mkv444.delete()
                await mkv555.delete()
                await mkv777.delete()
                await mkv66.delete()
            except:
                await client.send_message(chat_id = query.from_user.id,text=f"umetuma ujumbe ambao s sahihi,Kama hujaelewa jinsi tafadhal mcheki msimamiz @hrm45 akusaidie bonyeza rudi nyuma uanze upya kutengeneza kifurushi",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'kundii')]]))
                return
            ghi=f"{ghi1} {mkv1.text}#@{mkv77},{mkv22},{mkv33},{mkv44},{mkv55}#@{mkv6.text}"
            await db.update_db(query.from_user.id,ghi,ab)
            await mkv1.reply_text(text=f"data updated successful ",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'kundii')]]))
        elif query.data.startswith("xprice"):
            await query.answer('wait please')
            a=False
            b=time.time()
            mkv1 = await client.send_message(chat_id = query.from_user.id,text='⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️ \n Tafadhali ntumie Bei mpya ya movie/series  hii')
            id1=mkv1.id+1
            while a==False:
                try:
                    mkv = await client.get_messages("me",id1)
                    if mkv.text!=None:
                        a=True
                    
                    if (time.time()-b)>100:
                        mkv2 = await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali anza upya jitahidi kutuma ujumbe ndani ya dakika 1 iliniweze kuhudumia na wengine")
                        return
                    if mkv.from_user.id != query.from_user.id :
                        a=False
                        id1=id1+1
                except:
                    a=False
            if mkv.text==None:
                await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali tuna maneno sio picha wala kingine")
                return
            try:
                int(mkv.text)
                if mkv.text==0:
                    await mkv.reply(text='Movie hii umeset iwe bure kwa wateja wako endelea kujaza maelezo mengine')
            except:
                await mkv.reply(text='tuma ujumbe sahihi kama ulivyo elekezwa ,tafadhali anza upya kwa usahihi')
                return
            ghi=f'{mkv.text}'
            await Media.collection.update_one({'_id':query.data.split(" ",1)[1]},{'$set':{'price':ghi}})
            await mkv.reply_text(text=f"data updated successful ",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
        
        elif query.data.startswith("xtext"):
            await query.answer('wait please')
            a=False
            b=time.time()
            mkv1 = await client.send_message(chat_id = query.from_user.id,text='⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️ \n Tafadhali ntumie jina jipya la movie/series  hii')
            id1=mkv1.id+1
            while a==False:
                try:
                    mkv = await client.get_messages("me",id1)
                    if mkv.text!=None:
                        a=True
                    
                    if (time.time()-b)>100:
                        mkv2 = await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali anza upya jitahidi kutuma ujumbe ndani ya dakika 1 iliniweze kuhudumia na wengine")
                        return
                    if mkv.from_user.id != query.from_user.id :
                        a=False
                        id1=id1+1
                except:
                    a=False
            if mkv.text==None:
                await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali tuna maneno sio picha wala kingine")
                return
            ghi=f'{mkv.text.lower()}.dd#.{query.from_user.id}'
            await Media.collection.update_one({'_id':query.data.split(" ",1)[1]},{'$set':{'text':ghi}})
            await mkv.reply_text(text=f"data updated successful ",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
        elif query.data.startswith("xcaption"):
            await query.answer('wait please')
            a=False
            b=time.time()
            mkv1 = await client.send_message(chat_id = query.from_user.id,text='⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️\nTafadhali ntumie caption mpya ya movie au series  hii ')
            id1=mkv1.id+1
            while a==False:
                try:
                    mkv = await client.get_messages("me",id1)
                    if mkv.text!=None:
                        a=True
                    
                    if (time.time()-b)>100:
                        mkv2 = await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali anza upya jitahidi kutuma ujumbe ndani ya dakika 1 iliniweze kuhudumia na wengine")
                        return
                    if mkv.from_user.id != query.from_user.id :
                        a=False
                        id1=id1+1
                except:
                    a=False
            if mkv.text==None:
                await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali tuna maneno sio picha wala kingine")
                return
            
            await Media.collection.update_one({'_id':query.data.split(" ",1)[1]},{'$set':{'reply':mkv.text}})
            await mkv.reply_text(text=f"data updated successful ",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
        elif query.data.startswith("xfile"):
            botusername=await client.get_me()
            nyva=botusername.username  
            nyva=str(nyva)
            filedetails = await get_file_details(query.data.split(" ",1)[1])
            await query.answer(f'{query.data.split(" ",1)[1]}')
            for files in filedetails:
                descp=files.descp
            descp=descp.split(".dd#.")
            if descp[2]!="data":
                a=False
                b=time.time()
                mkv1 = await client.send_message(chat_id = query.from_user.id,text='⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️\nNtumie link mpya ya series/movie hii Au neno **video** ubadilshe kutoka kwenye mfumo wa link kwenda kwenye vipande')
                id1=mkv1.id+1
                while a==False:
                    try:
                        mkv = await client.get_messages("me",id1)
                        if mkv.text!=None:
                            a=True
                        if (time.time()-b)>100:
                            mkv2 = await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali anza upya jitahidi kutuma ujumbe ndani ya dakika 1 iliniweze kuhudumia na wengine")
                            return
                        if mkv.from_user.id != query.from_user.id :
                            a=False
                            id1=id1+1
                    except:
                        a=False
                if mkv.text==None:
                    await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali tuna maneno sio picha wala kingine")
                    return
                if mkv.text.lower()=="video":
                    mkv22 = await client.send_message(text=f'Samahani kidogo naomba utume neno m kama hii n singo movie au s kama n series ',chat_id = message.from_user.id)
                    a,b = funask()
                    id1 = mkv22.id+1
                    while a==False:
                        try:
                            mkvl1 = await client.get_messages("me",id1)
                            if mkvl1.text!=None:
                                a=True
                            if (time.time()-b)>(3*60):
                                await client.send_message(chat_id = message.from_user.id,text=f" Tafadhali anza upya jitahidi kutuma ujumbe ndani ya dakika 3 iliniweze kuhudumia na wengine")
                                return
                            if mkvl1.from_user.id != message.from_user.id :
                                a=False
                                id1=id1+1
                        except:
                            a=False
                    if mkvl1.text.lower()!='m' and mkvl1.text.lower()!='s' :
                        await mkv.reply(text='tuma ujumbe sahihi kama ulivyo elekezwa ,tafadhali anza upya kwa usahihi kama umeambia tuma s kwa series au m kwa movie ugumu hapo upo wap jamani')
                        return
                    if mkvl1.text.lower()=='m':
                        ab33='m'
                    elif mkvl1.text.lower()=='s':
                        ab33='ms'
                    descp=descp[0]+".dd#."+descp[1]+".dd#.data.dd#."+ab33
                    await Media.collection.update_one({'_id':query.data.split(" ",1)[1]},{'$set':{'descp':descp}})
                    await mkv.reply_text(text=f"data updated successful ",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
                else:
                    descp=descp[0]+".dd#."+descp[1]+".dd#."+mkv.text+".dd#."+descp[3]
                    await Media.collection.update_one({'_id':query.data.split(" ",1)[1]},{'$set':{'descp':descp}})
                    await mkv.reply_text(text=f"data updated successful ",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
            elif descp[3]=="m":
                fileid=query.data.split(" ")[1]
                reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(f"📡360p", callback_data =f"3hmuv##360 {fileid}"),
                        InlineKeyboardButton(f"📡480p", callback_data =f"3hmuv##480 {fileid}"),
                        InlineKeyboardButton(f"📡720p", callback_data =f"3hmuv##720 {fileid}")
                    ],
                    [
                        InlineKeyboardButton(f"💥  DONE", callback_data =f"close")
                    ]
                ])
                await query.edit_message_reply_markup(reply_markup=reply_markup)
            elif descp[3]=="ms":
                await query.edit_message_reply_markup(reply_markup=btn22(nyva,"series",f"3hsss##{ query.data.split(' ',1)[1] }"))
        elif query.data.startswith("xdescp"): 
            filedetails = await get_file_details(query.data.split(" ",1)[1])
            await query.answer(f'{query.data.split(" ",1)[1]}')
            for files in filedetails:
                descp=files.descp  
            descp=descp.split(".dd#.")
            a=False
            b=time.time()
            mkv1 = await client.send_message(chat_id = query.from_user.id,text='⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️\nNtumie maelezo mapya kuhusiana na movie hii Mfano Imetafsiriwa na dj Murphy Series ')
            id1=mkv1.id+1
            while a==False:
                try:
                    mkv = await client.get_messages("me",id1)
                    if mkv.text!=None:
                        a=True
                    
                    if (time.time()-b)>100:
                        mkv2 = await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali anza upya jitahidi kutuma ujumbe ndani ya dakika 1 iliniweze kuhudumia na wengine")
                        return
                    if mkv.from_user.id != query.from_user.id :
                        a=False
                        id1=id1+1
                except:
                    a=False
            if mkv.text==None:
                await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali tuna maneno sio picha wala kingine")
                return
            descp=descp[0]+".dd#."+mkv.text+".dd#."+descp[2]+".dd#."+descp[3]
            await Media.collection.update_one({'_id':query.data.split(" ",1)[1]},{'$set':{'descp':descp}})
            await mkv.reply_text(text=f"data updated successful ",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
        elif query.data == "startup":
            await query.answer('uzuri wa kitu ni muonekano')
            a=False
            b=time.time()
            mkv1 = await client.send_message(chat_id = query.from_user.id,text='⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️\nTafadhali Tuma maelezo kidogo kuhusu huduma/biashara unayo Fanya .Haya maelezo yataonekana endapo Mteja wako atakapo anza kumtumia robot huyu,\nKumbuka pia ukituma ujumbe wa zamani unafutwa kama ulishwahi tuma\n\nkwa maelezo zaidi mxheki @hrm45 akuelekeze zaidi\n\nukitaka kuadd jina andika {mention}.Mfano Mpendwa {mention}\n Karibu Swahili media tafadhali tuma ndani ya dakika 10 bila hvyo utaanza upya')
            id1=mkv1.id+1
            while a==False:
                try:
                    mkv = await client.get_messages("me",id1)
                    if mkv.text!=None:
                        a=True
                    
                    if (time.time()-b)>600:
                        mkv2 = await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali anza upya jitahidi kutuma ujumbe ndani ya dakika 10 iliniweze kuhudumia na wengine",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
                        return
                    if mkv.from_user.id != query.from_user.id :
                        a=False
                        id1=id1+1
                except:
                    a=False
            if mkv.text==None:
                await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali tuna maneno sio picha wala kingine")
                return
            ghi=f'descp {mkv.text}'
            ab = await db.get_db_status(query.from_user.id)
            await db.update_db(query.from_user.id,ghi,ab)
            await mkv.reply_text(text=f"data updated successful ",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
                
        elif query.data == "xba":
            await query.answer('Mtandao pendwa ndio bora')
            mkv1 = await client.send_message(chat_id = query.from_user.id,text='⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️\nTafadhali Tuma namba ya simu \n kumbuka tuma namba tu acha nafasi kampuni/aina ya huduma kisha acha nafasi jina litakalotoka baada ya kufanya malipo mfano 0679×××××× tigopesa hassan mohamed ',disable_web_page_preview = True)
            a=False  
            b=time.time()
            id1=mkv1.id+1
            while a==False:
                try:
                    mkv = await client.get_messages("me",id1)
                    if mkv.text!=None:
                        a=True
                    
                    if (time.time()-b)>200:
                        mkv2 = await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali anza upya jitahidi kutuma ujumbe ndani ya dakika 3 iliniweze kuhudumia na wengine",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
                        return
                    if mkv.from_user.id != query.from_user.id :
                        a=False
                        id1=id1+1
                except:
                    a=False 
            if mkv.text==None :
                await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali tuna maneno sio picha wala kingine anza upya kubonyez btn")
                return
            try:
                 int(mkv.text.split(" ")[0])
            except:
                await mkv.delete()
                await client.send_message(chat_id = query.from_user.id,text=f"umetuma ujumbe ambao s sahihi,Kama hujaelewa jinsi tafadhal mcheki msimamiz @hrm45 akusaidie bonyeza rudi nyuma uanze upya kutengeneza namba ya miamala yako",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
                return
            ghi=f'p0 {mkv.text}'
            ab = await db.get_db_status(query.from_user.id)
            await db.update_db(query.from_user.id,ghi,ab)
            await mkv.reply_text(text=f"data updated successful ",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
            
        elif query.data == "dbname":
            await query.answer('jina zuri huonesha uzuri')
            mkv1 = await client.send_message(chat_id = query.from_user.id,text='⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️⭐️\nTafadhali tuma jina la kikundi chako Mfano Swahili media group au Baoflix movies n.k ')
            a=False
            b=time.time()
            id1= mkv1.id+1
            while a==False:
                try:
                    mkv = await client.get_messages("me",id1)
                    if mkv.text!=None:
                        a=True
                    
                    if (time.time()-b)>100:
                        mkv2 = await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali anza upya jitahidi kutuma ujumbe ndani ya dakika 1 iliniweze kuhudumia na wengine",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
                        return
                    if mkv.from_user.id != query.from_user.id :
                        a=False
                        id1=id1+1
                except:
                    a=False 
            if mkv.text==None:
                await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali tuna maneno sio picha wala kingine")
                return
            ghi=f'db_name {mkv.text}'
            ab = await db.get_db_status(query.from_user.id)
            await db.update_db(query.from_user.id,ghi,ab)
            await mkv.reply_text(text=f"data updated successful ",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi nyuma' , callback_data = 'zkb')]]))
                
        elif query.data == "kenya":
            await query.answer('Tunaifanyia kaz huduma hii msijali')
            
        elif query.data.startswith("tzn"):
            fileid = query.data.split(" ",1)[1]
            filedetails = await get_file_details(fileid)
            for files in filedetails:
                f_caption=files.reply
                group_id = files.group_id
                id3 = files.file
                type1 = files.type
            if query.data.split(" ")[0].split("##")[1]=="tsh":
                kdflg="🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿"
            elif query.data.split(" ")[0].split("##")[1]=="ksh":
                await query.answer("Huduma hii badoo ipo kwny matengenezo ",show_alert=True)
                kdflg="🇰🇪🇰🇪🇰🇪🇰🇪🇰🇪🇰🇪🇰🇪🇰🇪🇰🇪🇰🇪🇰🇪🇰🇪🇰🇪"
                return
            await query.answer()
            await query.message.delete()
            db_details = await db.get_db_status(group_id)
            if type1=="Photo":
                await client.send_photo(
                            chat_id=query.from_user.id,
                            photo= id3,
                            caption =f'{kdflg}\n** VIFURUSHI VYA {db_details["db_name"].upper()} ** \nTafadhali chagua kifurush kupata maelezo zaidi na jinsi ya kufanya malipo kwa kubonyeza button zilizopo chini\n\nbonyeza **lipia hii tu** kuilipia movie/Series hii tu\n\n **__KARIBUN SANA {db_details["db_name"].upper()} __**',
                            reply_markup=InlineKeyboardMarkup([replymkup1(db_details["g_1"],fileid,'g_1'),replymkup1(db_details["g_2"],fileid,'g_2'),replymkup1(db_details["g_3"],fileid,'g_3'),replymkup1(db_details["g_4"],fileid,'g_4'),replymkup1(db_details["g_5"],fileid,'g_5'),replymkup1(db_details["g_6"],fileid,'g_6'),[InlineKeyboardButton("Lipia hii __ tu", callback_data=f"wiik2 {fileid}.g_1.500.m")]]) )
            else:
                await client.send_cached_media(
                                    chat_id=query.from_user.id,
                                    file_id=id3,
                                    caption =f'{kdflg}\n** VIFURUSHI VYA {db_details["db_name"].upper()} ** \nTafadhali chagua kifurush kupata maelezo zaidi na jinsi ya kufanya malipo kwa kubonyeza button zilizopo chini\n\nbonyeza **lipi hii tu** kulipia movie/series hii tu \n\n**__KARIBUN SANA {db_details["db_name"].upper()} __**',
                                    reply_markup=InlineKeyboardMarkup([replymkup1(db_details["g_1"],fileid,'g_1'),replymkup1(db_details["g_2"],fileid,'g_2'),replymkup1(db_details["g_3"],fileid,'g_3'),replymkup1(db_details["g_4"],fileid,'g_4'),replymkup1(db_details["g_5"],fileid,'g_5'),replymkup1(db_details["g_6"],fileid,'g_6'),[InlineKeyboardButton("Lipia hii __ tu", callback_data=f"wiik2 {fileid}.g_1.500.m")]]) )
           
        elif query.data.startswith("wik"):
            await query.answer()
            msgg1,fileid,msg2=query.data.split(" ") 
            filedetails = await get_file_details(fileid)
            await query.message.delete()
            for files in filedetails:
                group_id = files.group_id
            msg1 = group_id
            details = await db.get_db_status(msg1)
            data1= details[msg2]
            data2= data1.split("#@")[1]
            await client.send_message(chat_id = query.from_user.id,text=f"🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿\n{data1.split('#@')[0]}\n {data1.split('#@')[2]}\n Tafadhali bonyeza kitufe hapo chini kuweza kulipia muda utakao weza kupata huduma hii",
                    reply_markup=InlineKeyboardMarkup([replymkup2(f"Siku 1 tsh {data2.split(',')[0]}",f"{fileid}.{msg2}.{data2.split(',')[0]}.wk0"),replymkup2(f"week 1 tsh {data2.split(',')[1]}",f"{fileid}.{msg2}.{data2.split(',')[1]}.wk1"),replymkup2(f"week 2 tsh {data2.split(',')[2]}",f"{fileid}.{msg2}.{data2.split(',')[2]}.wk2"),replymkup2(f"week 3 tsh {data2.split(',')[3]}",f"{fileid}.{msg2}.{data2.split(',')[3]}.wk3"),replymkup2(f"mwezi 1 tsh {data2.split(',')[4]}",f"{fileid}.{msg2}.{data2.split(',')[4]}.mwz1"),[InlineKeyboardButton("rudi mwanzo", callback_data=f"tzn##tsh {fileid}")]])
                )
        elif query.data.startswith("wiik2"):
            await query.answer()
            fileid,msg2,prc1,tme = query.data.split(" ")[1].split(".")
            filedetails = await get_file_details(fileid)

            for files in filedetails:
                group_id = files.group_id
                prc2 = files.price
                name = files.text.split('.dd#.',1)[0]
                grp = files.grp
            details = await db.get_db_status(group_id)
            data1 = details[msg2]
            if tme=="wk0":
                tme1= "Siku 1"
            elif tme=="wk1":
                tme1= "wiki 1"
            elif tme=="wk2":
                tme1= "wiki 2"
            elif tme=="wk3":
                tme1= "wiki 3"
            elif tme== "mwz1":
                tme1= "mwezi mmoja"
            else:
                tme1=tme
            data2 = data1.split("#@")[0]
            p1,p2,p4=details["p0"].split(" ",2)
            mda = details["muda"]
            ts = await client.get_users(group_id)
            await query.message.delete()
            if tme == "m":
                await client.send_message(chat_id=query.from_user.id,
                        text = f'🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿\n{details["db_name"].upper} PAYMENT SECTION \n🦋Tafadhali lipia\n Tsh {prc2} kwenda **: {p1} {p2}** Jina litakuja :** {p4}**\n\n🦋Kumbuka unalipia tsh {prc2} kwa ajili ya kununua {name} kwa {mda}\nPia kama mtandao wako sio wa {p2} Tuma kwenda mitandao mingine kisha chagua mtandao husika wa kufanyia malipo..\n\n📲Ukishafanya  malipo bonyeza button **nmeshafanya malipo**..... kisha tuma screenshot ya malipo/muamala\n\n🙋🙋‍♀kwa msaada zaidi bonyeza **@{ts.username}** uje inbox tukuelekeze ulipokwama tukusaidie',disable_web_page_preview = True,
                        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("nmeshafanya malipo", callback_data=f"malipo {query.data.split(' ')[1]}"),InlineKeyboardButton("rudi mwanzo ", callback_data=f"tzn##tsh {fileid}")]]),
                    )
            else:
                await client.send_message(chat_id = query.from_user.id,
                        text = f'🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿\n{details["db_name"].upper} PAYMENT SECTION \n🦋Tafadhali lipia\n Tsh {prc1} kwenda **: {p1} {p2}** Jina litakuja :** {p4}**\n\n🦋Kumbuka unalipia tsh {prc1} kwa ajili ya kununua {data2} kwa {tme1} \nPia kama mtandao wako sio wa {p2} Tuma kwenda mitandao mingine kisha chagua mtandao husika wa kufanyia malipo..\n\n📲Ukishafanya  malipo bonyeza button **nmeshafanya malipo**.....kisha tuma screenshot ya malipo/muamala\n\n🙋🙋‍♀kwa msaada zaidi bonyeza **@{ts.username}** uje inbox tukuelekeze ulipokwama tukusaidie',disable_web_page_preview = True,
                        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("nmeshafanya malipo", callback_data=f"malipo {query.data.split(' ')[1]}"),InlineKeyboardButton("rudi mwanzo ", callback_data=f"tzn##tsh {fileid}")]]),
                    )
        elif query.data.startswith("malipo"):
            await query.answer()
            fileid,msg2,prc1,tme = query.data.split(" ")[1].split(".")
            filedetails = await get_file_details(fileid)
            for files in filedetails:
                group_id = files.group_id
                prc2 = files.price
                name = files.text.split('.dd#.',1)[0]
            if tme=="wk0":
                tme1= "Siku 1"
            elif tme=="wk1":
                tme1= "wiki 1"
            elif tme=="wk2":
                tme1= "wiki 2"
            elif tme=="wk3":
                tme1= "wiki 3"
            elif tme== "mwz1":
                tme1= "mwezi mmoja"
            else:
                tme1=tme
            details = await db.get_db_status(group_id)
            data1 = details[msg2]
            data2 = data1.split("#@")[0]
            p1,p2,p4=details['p0'].split(" ",2)
            mda = details['muda']
            ts = await client.get_users(group_id)
            dbname = details['db_name']
            mkv1 =await client.send_message(chat_id = query.from_user.id,text='🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿\nTuma picha ya screenshot ya malipo yako kisha subir kidogo wasimamiz wangu wahakiki muamala wako')
            a,b =funask()
            id1=(mkv1.id)+1
            while a==False:
                try:
                    mkv = await client.get_messages("me",id1)
                    if mkv.text!=None or mkv.media!=None:
                        a=True
                    
                    if (time.time()-b)>180:
                        mkv2 = await client.send_message(chat_id = query.from_user.id,text=f" Tafadhali anza upya jitahidi kutuma ujumbe ndani ya dakika 3 iliniweze kuhudumia na wengine",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text = f'rudi mwanzo' , callback_data = f'tanzania {fileid}')]]))
                        return

                    if mkv.from_user.id != query.from_user.id :
                        a=False
                        id1=id1+1
                except:
                    a=False
            channel=int(details['channels'].split('##')[0])
            if mkv.photo:
                await query.message.delete()
                await client.send_message(chat_id = query.from_user.id,text='🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿\ntumepokea screenshot ngoja tuihakiki tutakupa majibu tukimaliza')
                if tme=='m':
                    await client.send_photo(
                            chat_id=int(group_id),
                            photo= mkv.photo.file_id,
                            caption = f'Mteja **{query.from_user.mention}**Amechagua \n Jina :{name}\nBei yake : Tsh {prc2} \nTafadhal hakiki huu muamala wake,Kama amekosea tafadhal bonyeza maneno ya blue yaani jina lake kisha muelekeze aanze upya kuchagua kifurush sahihi au kutuma screenshot ya muamala sahihi.\n Bonyeza activate kumruhusu aweze kupata huduma ya {name} hii,Kama muamala wake upo sahihi \n\nNote:Kama utamshauri aanze upya tafadhali futa huu ujumbe ili usichanganye mada(ushauri tu)' ,
                            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Activate", callback_data=f"yq {query.from_user.id} {query.data.split(' ')[1]}")]]))
                    try:
                        await client.send_photo(
                            chat_id=int(channel),
                            photo= mkv.photo.file_id,
                            caption = f'Mteja **{query.from_user.mention}**Amechagua \n Jina :{name}\nBei yake : Tsh {prc2} \nTafadhali hii n kumbukumbu tafadhali kama sio sahihi bonyeza close' ,
                            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("CLOSE", callback_data=f"close")]]))
                    except Exception as e:
                        await client.send_message(chat_id = int(group_id),text=f'🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿\nkuna tatixo {e} forward kwa @hrm45 aondoe hii changamoto ')
                else:
                    await client.send_photo(
                            chat_id=int(group_id),
                            photo= mkv.photo.file_id,
                            caption = f'Mteja **{query.from_user.mention}**Amechagua kifurushi**\n {data1.split("#@")[0].upper()}**\n Muda wa : {tme1}\nBei yake : Tsh {prc1}\n Tafadhal hakiki huu muamala wake,Kama amekosea tafadhal bonyeza maneno ya blue yaani jina lake kisha muelekeze aanze upya kuchagua kifurush sahihi au kutuma screenshot ya muamala sahihi.\n Bonyeza activate kumruhusu aweze kupata huduma ya {name} hii,Kama muamala wake upo sahihi \n\nNote:Kama utamshauri aanze upya tafadhali futa huu ujumbe ili usichanganye mada(ushauri tu)' ,
                            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Activate", callback_data=f"yq {query.from_user.id} {query.data.split(' ')[1]}")]]))
                    try:
                        await client.send_photo(
                            chat_id=int(channel),
                            photo= mkv.photo.file_id,
                            caption = f'Mteja **{query.from_user.mention}**Amechagua \n Jina :{name}\nBei yake : Tsh {prc2} \nTafadhali hii n kumbukumbu tafadhali kama sio sahihi bonyeza close' ,
                            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("CLOSE", callback_data=f"close")]]))
                    except Exception as e:
                        await client.send_message(chat_id = int(group_id),text=f'🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿\nkuna tatixo {e} forward kwa @hrm45 aondoe hii changamoto')
               
            else:
                await query.message.delete()
                
                if tme == "m":
                     await client.send_message(chat_id = query.from_user.id,
                            text = f'NMELAZIMIKA KUKURUDISHA HAPA \n**(tafadhali Fanya kwa usahihi kama unavyo ambiwa kama huwez omba msaada usaidiwe)**\n🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿\n{details["db_name"].upper} PAYMENT SECTION\n🦋Tafadhali lipia\n Tsh {prc2} kwenda **: {p1} {p2}** Jina litakuja :** {p4}**\n\n🦋Kumbuka unalipia tsh {prc2} kwa ajili ya kununua {name} kwa {mda}\nPia kama mtandao wako sio wa {p2} Tuma kwenda mitandao mingine kisha chagua mtandao husika wa kufanyia malipo..\n\n📲Ukishafanya  malipo bonyeza button **nmeshafanya malipo**..... kisha tuma screenshot ya malipo/muamala\n\n🙋🙋‍♀kwa msaada zaidi bonyeza **@{ts.username}** uje inbox tukuelekeze ulipokwama tukusaidie',disable_web_page_preview = True,
                            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("nmeshafanya malipo", callback_data=f"malipo {query.data.split(' ')[1]}"),InlineKeyboardButton("rudi mwanzo ", callback_data=f"tzn##tsh {fileid}")]]),
                        )
                else:
                    await client.send_message(chat_id = query.from_user.id,
                            text = f'NMELAZIMIKA KUKURUDISHA HAPA \n**(tafadhali Fanya kwa usahihi kama unavyo ambiwa kama huwez omba msaada usaidiwe)**\n🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿\n{details["db_name"].upper} PAYMENT SECTION\n🦋Tafadhali lipia\n Tsh {prc1} kwenda **: {p1} {p2}** Jina litakuja :** {p4}**\n\n🦋Kumbuka unalipia tsh {prc1} kwa ajili ya kununua {data2} kwa {tme1}\nPia kama mtandao wako sio wa {p2} Tuma kwenda mitandao mingine kisha chagua mtandao husika wa kufanyia malipo..\n\n📲Ukishafanya  malipo bonyeza button **nmeshafanya malipo**..... kisha tuma screenshot ya malipo/muamala\n\n🙋🙋‍♀kwa msaada zaidi bonyeza **@{ts.username}** uje inbox tukuelekeze ulipokwama tukusaidie',disable_web_page_preview = True,
                            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("nmeshafanya malipo", callback_data="malipo {query.data.split(' ')[1]}"),InlineKeyboardButton("rudi mwanzo ", callback_data=f"tzn##tsh {fileid}")]]),
                       )
            
        elif query.data.startswith("yq"):
            msg1 = query.data.split(" ")[1]
            ttl = await client.get_users(int(msg1))
            await query.edit_message_caption(
                    caption = f'je unauhakika tumruhusu {ttl.mention} bonyeza ndiyo kukubali au bonyeza rudi kurudi kupata maelezo ya muamala',
                    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("ndiyo", callback_data=f"nq {msg1} {query.data.split(' ')[2]}"),InlineKeyboardButton("rudi ", callback_data=f"rq {msg1} {query.data.split(' ')[2]}")]])
                )
        elif query.data.startswith("rq"):
            msg,msg1,data3 = query.data.split(" ")         
            fileid,msg2,prc1,tme = data3.split("@#")[0].split(".")
            filedetails = await get_file_details(fileid)
            for files in filedetails:
                group_id = files.group_id
                prc2 = files.price
                name = files.text.split('.dd#.',1)[0]
            if tme=="wk0":
                tme1= "Siku 1"
            elif tme=="wk1":
                tme1= "wiki 1"
            elif tme=="wk2":
                tme1= "wiki 2"
            elif tme=="wk3":
                tme1= "wiki 3"
            elif tme== "mwz1":
                tme1= "mwezi mmoja"
            else:
                tme1=tme
            details = await db.get_db_status(group_id)
            data1 = details[msg2]
            ttl = await client.get_users(int(msg1))
            if tme1=="m":
                await query.edit_message_caption(
                        caption = f'Mteja {ttl.mention}Amechagua \n Jina :{name}\nBei yake : Tsh {prc2} \nTafadhal hakiki huu muamala wake,Kama amekosea tafadhal bonyeza maneno ya blue yaani jina lake kisha muelekeze aanze upya kuchagua kifurush sahihi au kutuma screenshot ya muamala sahihi.\n Bonyeza activate kumruhusu aweze kupata huduma ya {name} hii,Kama muamala wake upo sahihi \n\nNote:Kama utamshauri aanze upya tafadhali futa huu ujumbe ili usichanganye mada(ushauri tu)' ,
                        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Activate", callback_data=f"yq {msg1} {data3}")]])
                    )
            else:
                await query.edit_message_caption(
                        caption = f'Mteja {ttl.mention}Amechagua \n **{data1.split("#@")[0].upper()}**\n Kwa muda wa: {tme1}\nBei yake : Tsh {prc1} \nTafadhal hakiki huu muamala wake,Kama amekosea tafadhal bonyeza maneno ya blue yaani jina lake kisha muelekeze aanze upya kuchagua kifurush sahihi au kutuma screenshot ya muamala sahihi.\n Bonyeza activate kumruhusu aweze kupata huduma ya **{data1.split("#@")[0].upper()}** ,Kama muamala wake upo sahihi \n\nNote:Kama utamshauri aanze upya tafadhali futa huu ujumbe ili usichanganye mada(ushauri tu)' ,
                        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Activate", callback_data=f"yq {msg1} {data3}")]])
                    )
        elif query.data.startswith("nq"):
            botusername=await client.get_me()
            nyva=botusername.username  
            nyva=str(nyva)
            msg,msg1,data3 = query.data.split(" ")         
            fileid,msg2,prc1,tme = data3.split("@#")[0].split(".")
            filedetails = await get_file_details(fileid)
            for files in filedetails:
                group_id = files.group_id
                prc2 = files.price
                name = files.text.split('.dd#.',1)[0]
                grp = files.grp
            ban_status = await db.get_db_status(group_id)  
            group_id2 = int(ban_status['group'].split('##')[0])
            if tme=="wk0":
                tme1= 1
            elif tme=="wk1":
                tme1= 7
            elif tme=="wk2":
                tme1= 14
            elif tme=="wk3":
                tme1= 21
            elif tme== "mwz1":
                tme1= 30
            strid = str(uuid.uuid4())
            if tme == "m":
                await db.add_acc(strid,msg1,fileid,query.from_user.id,30)
                abx="**bonyeza download hapo juu ya movie uliochagua ili kuipakua**"
            else:
                abx="**bonyeza download hapo juu ya movie/Series  uliochagua ili kuipakua kisha nyingine utazipakua kama muingozo ulivyosoma kipind unajiunga**"
                await db.add_acc(strid,msg1,msg2,query.from_user.id,tme1)
            await query.message.delete()
            ttl = await client.get_users(int(msg1))
            await client.send_message(chat_id = query.from_user.id,text=f"🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿 mteja **{ttl.mention}** amesharuhusiwa kupata huduma ya kifurush alicho chagua Asante kwa mda wako"
                    )
            for grp in await is_group_exist("group",nyva):
                try:
                    grp_id = int(grp.id.split("##")[1])
                    await client.send_message(chat_id = int(grp_id),text=f"🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿 mteja **{ttl.first_name}** Tumepokea muamala wako,\nAsante kwa kutunga mkono\n\nEndelea kufurahia huduma zetu"
                        )
                except Exception as e:
                    print(e)
            try:
                hjkl = f'{group_id}##{msg1}'
                dtails = await is_user_exist(hjkl,nyva)
                for fls in dtails:
                    email = fls.email
                if email=='hrm45':
                    await client.send_message(chat_id = ( int(msg1) ),text=f"🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿 Tafadhali tunaomba ututumie email yako ili tukuwezeshe kutumia gdrive yetu:Tuma neno \n\weka email yako \nMfano\n\weka mohamed@gmail.com "
                        )
                elif '@gmail.com' in email:
                    if tme == 'm':
                        await client.send_message(chat_id = query.from_user.id,text=f"🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿 mteja {ttl.mention} muwezeshee email yake {email} kwenye movie \n**{files.text.split('.dd#.')[0]}\n"
                            )
                        await client.send_message(chat_id = (int(msg1)),text=f"🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿 Tumefanikiwa kuiwezesha email yako endelea kufurahia huduma zetu:"
                        )
                    else:
                        await client.send_message(chat_id = query.from_user.id,text=f"🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿 mteja {ttl.mention} muwezeshee email yake {email} kwenye {ban_status[msg2].split('#@')[0]}"

                            )
                        await client.send_message(chat_id = (int(msg1)),text=f"🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿 Tumefanikiwa kuiwezesha email yako endelea kufurahia huduma zetu:"
                        )
            except:
                await client.send_message(chat_id = (int(msg1)),text=f"🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿 Tafadhali tunaomba ututumie email yako ili tukuwezeshe kutumia gdrive yetu:"
                    )
            await client.send_message(chat_id = int(msg1),text=f"🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿🇹🇿Mpendwa {ttl.mention}\nSamahani kwa kukuchelewesha kukuruhusu mapema ila tutajitahidi kuboresha huduma zetu,Kwa sasa unaweza kupata huduma uliyoomba\n\n{abx}ITAKUJA DIRECT AU KAMA NI LINK BONYEZA BUTTON HUSIKA\n\n kujua salio na vifurushi vyako vyote tuma neno /salio ukiwa private yaani kwenye bot."
                    )
        
        elif query.data.startswith("zkb"):
            await query.edit_message_text(text="chagua huduma unayotaka kufanya marekebisho",
                reply_markup =InlineKeyboardMarkup([[InlineKeyboardButton('Rekebisha Makundi', callback_data = "kundii")],[InlineKeyboardButton('Rekebisha Jina la Kikundi', callback_data = "dbname")],[InlineKeyboardButton('Rekebisha Startup sms', callback_data = "startup")],[InlineKeyboardButton('Rekebisha Mawasiliano', callback_data = "xba")]])
            )
                                    
def replymkup2(msg2,msg4):
    msg1 = msg2.split('tsh ')[1]
    msg1 =int(msg1)
    if msg1 == 0:
        return []
    else:
        return [InlineKeyboardButton(f"{msg2}", callback_data=f"wiik2 {msg4}")]

def replymkup1(msg3,msg1,msg2):
    if msg3=="hrm45":
        return []
    elif msg3.split("#@")[1]=="0,0,0,0,0":
        return []
    else:
        msg3=msg3.split("#@")[0]
        return [InlineKeyboardButton(f"{msg3}", callback_data=f"wik {msg1} {msg2}")]
def funask():
    a=False
    b=time.time()
    return a,b
def replymkup3(ab,typ,nmb):
    ab3=[]
    for i in range(0,nmb):
        if typ=="grp":
            if i == (nmb-1) and i !=6 :
                b=i+1
                ab2 = [InlineKeyboardButton(text = '🦋 ADD KIFURUSHI ', callback_data = f'kad2grp g_{b}')]
                ab3.append(ab2)    
            elif i != 6:
                a=i+1
                abh=f'g_{a}'
                ab1=ab[abh].split("#@")[0]
                ab2=[InlineKeyboardButton(text = f'🦋 {ab1}' , callback_data = f'kad2grp {abh}')]
                ab3.append(ab2)
    ab2=[InlineKeyboardButton(text = f'🦋 RUDI NYUMA' , callback_data = f'zkb')]
    ab3.append(ab2)
    return InlineKeyboardMarkup(ab3)
