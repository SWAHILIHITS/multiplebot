from datetime import datetime
import time 
from info import DB2  

class Database:
    def __init__(self, db1):
        self.db1 = db1
        self.col = self.db1.admins
        self.fls = self.db1.acc

    def new_user(self, id,bot,link):
        return dict(
            id=id,
            join_date=datetime.now().isoformat(),
            db_status=dict(
                db_name = "SWAHILI GROUP MEDIA",
                descp = "Tunahusika na uuzaji wa muvi na sizon kal zilizotafsiriwa kwa bei ",
                p0 = "hrm45",
                p1 = "hrm45",
                lpa=False,
                bot_link= bot,
                token = f"hrm45",
                group = "hrm45##hrm45",
                channels ="hrm45##hrm45",
                user_link = link,
                muda = "30 days",
                mwongozo = "ufuatao n mwongozo mfupi",
                g_1=  "hrm45",
                g_2 = "hrm45",
                g_3 = "hrm45",
                g_4 = "hrm45",
                g_5 = "hrm45",
                g_6 = "hrm45",
            ),
            ban_status=dict(
                is_banned=False,
                ban_duration=0,
                banned_on=datetime.now().isoformat(),
                
            )
        )
    def new_acc(self, id,user_id,file_id,db_name,bot,tme):
        return dict(
            id=id,
            user_id=user_id,
            file_id = file_id,
            db_name = db_name,
            bot_link = bot,
            ban_status=dict(
                ban_duration=tme,
                banned_on=datetime.now().isoformat(),
            )
        )
    async def is_bot_exist(self, bot):
        user = self.col.find({})
        id2 = False
        async for id in user:
            if id['db_status']['bot_link']==bot.strip():
                id2=id['id']
        return id2
    async def add_acc(self, id,user_id,file_id,db_name,bot,tme):
        user = self.new_acc(id,int(user_id),file_id,db_name,bot,tme)
        await self.fls.insert_one(user)

    async def add_admin(self, id,bot,link):
        user = self.new_user(id,bot,link)
        await self.col.insert_one(user)

    async def is_admin_exist(self, id,bot):
        filter={'id': int(id)}
        filter["db_status.bot_link"]= bot
        user = await self.col.find_one(filter)
        return True if user else False

    async def is_email_exist(self, id,id2):
        filter={'user_id': int(id)}
        filter['db_name']=id2
        user = await self.fls.find_one(filter)
        return True if user else False

    async def is_acc_exist(self, id,file_id,db_name):
        filter={'user_id': int(id)}
        filter["file_id"]= file_id
        filter["db_name"]= int(db_name)
        user = await self.fls.find_one(filter)
        return True if user else False

    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count

    async def get_all_users(self):
        all_users = self.col.find({})
        return all_users

    async def get_all_acc(self):
        all_users = self.fls.find({})
        return all_users

    async def delete_acc(self, id):
        await self.fls.delete_many({'id': id})

    async def get_user(self,id,bot):
        filter={'id': int(id)}
        filter["db_status.bot_link"]= bot
        all_users = self.col.find(filter)
        return all_users

    async def get_acc(self,id):
        all_users = self.fls.find({'user_id': int(id)})
        return all_users

    async def delete_admin(self, user_id,bot):
        filter={'id': int(id)}
        filter["db_status.bot_link"]= bot
        await self.col.delete_many(filter)

    async def remove_ban(self, id,bot):
        ban_status = dict(
            is_banned=False,
            ban_duration= 0,
            banned_on=datetime.now().isoformat(),
            
        )
        filter={'id': int(id)}
        filter["db_status.bot_link"]= bot
        await self.col.update_one(filter, {'$set': {'ban_status': ban_status}})

    async def ban_user(self, user_id, ban_duration,bot):
        ban_status = dict(
            is_banned=True,
            ban_duration=ban_duration,
            banned_on=datetime.now().isoformat(),
            
        )
        filter={'id': int(user_id)}
        filter["db_status.bot_link"]= bot
        await self.col.update_one(filter, {'$set': {'ban_status': ban_status}})
    async def get_db_status(self, id,bot):
        default =dict(
                db_name = "SWAHILI GROUP MEDIA",
                descp = "Tunahusika na uuzaji wa muvi na sizon kal zilizotafsiriwa kwa bei ",
                p0 = "hrm45",
                p1 = "hrm45",
                lpa = False,
                bot_link= "hrm45",
                token = f"hrm45",
                group ="hrm45##hrm45",
                channels ="hrm45##hrm45",
                user_link = "link2",
                muda = "30 days",
                mwongozo = "ufuatao n mwongozo mfupi",
                g_1=  "hrm45",
                g_2 = "hrm45",
                g_3 = "hrm45",
                g_4 = "hrm45",
                g_5 = "hrm45",
                g_6 = "hrm45",
            )
        filter={'id': int(id)}
        filter['db_status.bot_link']=bot
        user = await self.col.find_one(filter)
        return user.get('db_status', default)
    async def update_db(self, user_id,ghi,ab,bot):
        ab1,ab2=ghi.split(" ",1)
        ab[ab1] = ab2
        update_admin =dict(
                db_name = ab["db_name"],
                descp = ab["descp"],
                p0 = ab["p0"],
                p1 = ab["p1"],
                lpa = ab["lpa"],
                bot_link= ab["bot_link"],
                token = ab['token'],
                group =ab["group"],
                channels =ab["channels"],
                user_link = ab["user_link"],
                muda = ab["muda"],
                mwongozo = ab["mwongozo"],
                g_1 = ab["g_1"],
                g_2 = ab["g_2"],
                g_3 = ab["g_3"],
                g_4 = ab["g_4"],
                g_5 = ab["g_5"],
                g_6 = ab["g_6"],
            )
        filter={'id': int(user_id)}
        filter["db_status.bot_link"]= bot
        await self.col.update_one(filter, {'$set': {'db_status': update_admin}})
    
    async def get_ban_status(self, id,bot):
        default = dict(
            is_banned=False,
            ban_duration=0,
            banned_on=datetime.now().isoformat(),
            
        )
        filter={'id': int(id)}
        filter['db_status.bot_link']=bot
        user = await self.col.find_one(filter)
        return user.get('ban_status', default)

    async def get_all_banned_users(self):
        banned_users = self.col.find({'ban_status.is_banned': True})
        return banned_users


db = Database(DB2)
