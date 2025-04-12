# %%
import requests
import os
from dotenv import load_dotenv
import pymongo
import time

# %%
def get_current_timestamp_milliseconds():
  """
  Returns the current timestamp in milliseconds since the epoch.
  """
  return int(time.time() * 1000)

# %%
load_dotenv() 
LI_URI = os.environ['LI_URI']
LI_VERSION = os.environ['LI_VERSION']
LI_ACCESS_TOKEN = os.environ['LI_ACCESS_TOKEN']

# %%
db_client = pymongo.MongoClient('mongodb://localhost:27017')
db = db_client['db_li_page_posts']
tb_page_post = db['tb_page_posts']

# %%
def post_2_page(payload):
    #print(url)
    url = LI_URI + 'posts'
    headers = {
        'Authorization': LI_ACCESS_TOKEN,
        'LinkedIn-Version': LI_VERSION,
        'Content-Type': 'application/json'
    }
    try:
        detail = requests.post(url, json=payload, headers=headers)
        return detail   #LI does not return response detail
    except Exception as e:
        print(e)
        return {'error': e}

# %%
#get 1 latest post and repost to LI
def get_1_latest_pots():
    latest_post = tb_page_post.find_one({'shared': 0}, sort=[('lastModifiedAt', -1)])
    return latest_post
#test
#end

# %%
#todo auto get RANDOMLY 1 new post from all pages, (maximum 5 repost per day)
def auto_repost():
    #1. check how many posts today (<24 hours)
    timenow = get_current_timestamp_milliseconds()  #milliseconds
    last24hours = timenow - 24 * 60 * 60 * 1000
    todayPosts = tb_page_post.count_documents({'shared': 1, 'shared_time': {'$gt': last24hours }, 'shared_time': {'$lt': timenow }})
    #print(last24hours)
    if todayPosts < 5:
        #2. if today posted < 5 posts:
        #2.1 get 1 new post RANDOMLY, sorted by lastModifiedAt
        random_document = next(tb_page_post.aggregate([
            {"$match": {'shared': 0}},
            {"$sort": {"lastModifiedAt": -1}},
            #{"$sort": [("lastModifiedAt", -1)]},
            {"$sample": {"size": 1}}
        ]))
        #2.2 post it to page
        if random_document != None:
            payload = {
                "author": "urn:li:organization:" + os.environ['MY_PAGE_ID'],    #post to my page
                "commentary": '',   #the_post['description'], #duplicated content
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED"
                },
                "lifecycleState": "PUBLISHED",
                "reshareContext": {
                    "parent": random_document['id']
                }
            }
            #print(payload)
            result = post_2_page(payload)
            # print(result)
            if 'error' not in result:
                #2.3 Update to db: shared=1, shared_time=
                tb_page_post.update_one({'id': random_document['id']}, {'$set': {'shared': 1, 'shared_time': get_current_timestamp_milliseconds()}})
                print('Finished post to the page with description: ' + random_document['description'][:30] + ' ...')
#test
auto_repost()

# %%
db_client.close()


