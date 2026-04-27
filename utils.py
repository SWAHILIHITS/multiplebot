import re  
import base64   
import logging
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from marshmallow.exceptions import ValidationError
import os
import requests
import json
from info import DB2, COLLECTION_NAME

COLLECTION_NAME_2="groups""
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

instance = Instance.from_db(DB2)
imdb=Instance.from_db(DB2)
likes =Instance.from_db(DB2)

@instance.register
class Media(Document):
    id = fields.StrField(attribute='_id')
    text = fields.StrField(required=True)
    reply = fields.StrField(required=True)
    btn = fields.StrField(required=True)
    file = fields.StrField(required=True)
    type = fields.StrField(required=True)
    group_id = fields.IntField(required=True)
    grp = fields.StrField(required=True)
    class Meta:
        collection_name = COLLECTION_NAME
@imdb.register
class User(Document):
    id = fields.StrField(attribute='_id')
    grp =fields.StrField(required=True)
    email = fields.StrField(required=True)
    tme = fields.IntField(required=True)
    class Meta:
        collection_name = COLLECTION_NAME_2

async def add_user(id,sts):
    try:
        data = User(
            id = id,
            grp = sts,
            email = 'hrm45',
            tme=0
        )
    except ValidationError:
        logger.exception('Error occurred while saving group in database')
    else:
        try:
            await data.commit()
        except DuplicateKeyError:
            logger.warning("already saved in database")
        else:
            logger.info("group is saved in database")

async def save_file(text,reply,btn,file,type,id,user_id,grp):
    """Save file in database"""
    "
    try:
        file = Media(
            id=id,
            text=text,
            reply=str(reply),
            btn=f'{button}',
            file= str(file),
            type=str(type),
            group_id =user_id,
            grp=grp
            
       )
    except ValidationError:
        logger.exception('Error occurred while saving file in database')
    else:
        try:
            await file.commit()
        except DuplicateKeyError:
            logger.warning(text + " is already saved in database")
        else:
            logger.info(text + " is saved in database")

async def get_search_results(query, group_id, nyva, max_results=10, offset=0):
    """For given query return (results, next_offset)"""
    
    query = query.strip()
    query = query.lower()
    ab='empty'
    if query.startswith('movie'):
        ab='x movie'
        query=query.replace('movie','')
        query = query.strip()
        raw_pattern1 = ab.replace(' ', r'.*[\s\.\+\-_]')
    elif query.startswith('series'):
        query=query.replace('series','')
        ab='x series'
        query = query.strip()
        raw_pattern1 = ab.replace(' ', r'.*[\s\.\+\-_]')
    elif query.startswith('dj'):
        try:
            ab,query=query.split('#',1)
            query=query.strip()
        except:
            ab=query.strip()
            query =''
        ab=f"x {ab}"
        raw_pattern1 = ab.replace(' ', r'.*[\s\.\+\-_]')
    else:
        ab="x dd#"
        raw_pattern1 = ab.replace(' ', r'.*[\s\.\+\-_]')
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'\b' + query + r'.*'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        return []
    else:
        filter = {'text': regex}
    if ab!='empty':
        try:
            regex1 = re.compile(raw_pattern1, flags=re.IGNORECASE)
        except Exception as e:
            print(e)
        else:
            filter['descp']= regex1
    filter['group_id'] = group_id
    if nyva != 'Movietzbot':
        filter['nyva']=nyva
    total_results = await Media.count_documents(filter)
    next_offset = offset + max_results

    if next_offset > total_results:
        next_offset = ''

    cursor = Media.find(filter)
    # Sort by recent
    cursor.sort('text', 1)
    # Slice files according to offset and max results
    cursor.skip(offset).limit(max_results)
    # Get list of files
    files = await cursor.to_list(length=max_results)

    return files, next_offset
async def get_filter_result(group_id,nyva):
    filter = {"group_id": group_id}
    if nyva != 'Movietzbot':
        filter['nyva']=nyva
    total_results = await Media.count_documents(filter)
    cursor = Media.find(filter)
    cursor.sort('text', 1)
    files = await cursor.to_list(length=int(total_results))
    return files
async def get_filter_results(query,group_id,nyva):
    query = query.strip()
    query = query.lower()
    ab='empty'
    if query.startswith('movie'):
        ab='movie'
        query=query.replace('movie','')
        query = query.strip()
        raw_pattern1 = r'\b' + ab + r'.*'
    elif query.startswith('series'):
        query=query.replace('series','')
        ab='series'
        query = query.strip()
        raw_pattern1 = r'\b' + ab + r'.*'
    elif query.startswith('dj'):
        try:
            ab,query=query.split('#',1)
            query=query.strip()
        except:
            ab=query.strip()
            query =''
        if ' ' not in ab:
            raw_pattern1 = r'\b' + ab + r'.*'
        else:
            raw_pattern1 = ab.replace(' ', r'.*[\s\.\+\-_]')
    
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'\b' + query + r'.*'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        return []
    filter = {"text": regex}
    if ab!='empty':
        try:
            regex1 = re.compile(raw_pattern1, flags=re.IGNORECASE)
        except Exception as e:
            print(e)
        else:
            filter['descp']= regex1
    filter['group_id'] = group_id
    if nyva != 'Movietzbot':
        filter['nyva']=nyva
    total_results = await Media.count_documents(filter)
    cursor = Media.find(filter)
    cursor.sort('text', 1)
    files = await cursor.to_list(length=int(total_results))
    return files

async def is_user_exist(query,rbt):
    filter = {'id': query}
    filter['rbt'] = rbt
    cursor = User.find(filter)
    userdetails = await cursor.to_list(length=1)
    return userdetails

async def is_group_exist(query1,query):
    filter = {'email':query1}
    filter['rbt']= query
    cursor = User.find(filter)
    cursor.sort('$natural', -1)
    count = await User.count_documents(filter)
    userdetails = await cursor.to_list(length = int(count))
    return userdetails
async  def get_random_details(query,group_id,nyva):
    filter = {'grp':query}
    filter['group_id'] = int(group_id)
    if nyva != 'Movietzbot':
        filter['nyva']=nyva
    cursor = Media.find(filter)
    cursor.sort('$natural', -1)
    count = await Media.count_documents(filter)
    userdetails = await cursor.to_list(length = int(count))
    return userdetails

async def get_file_details(query):
    filter = {'id': query}
    cursor = Media.find(filter)
    filedetails = await cursor.to_list(length=1)
    return filedetails
