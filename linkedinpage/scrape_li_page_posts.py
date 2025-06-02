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
load_dotenv(override=True) 
LI_REST_URI = os.environ['LI_REST_URI']
LI_VERSION = os.environ['LI_VERSION']
LI_ACCESS_TOKEN = os.environ['LI_ACCESS_TOKEN']

# %%
db_client = pymongo.MongoClient(os.environ['REMOTE_MONGO_DB'])
db = db_client['db_infographic']
tb_author = db['tb_author']
tb_page_post = db['tb_page_posts']

# %%
def get_request(url):
    #print(url)
    url = LI_REST_URI + url
    headers = {
        'Authorization': LI_ACCESS_TOKEN,
        'LinkedIn-Version': LI_VERSION
    }
    try:
        detail = requests.get(url, headers=headers)
        return detail.json()
    except Exception as e:
        print(e)
        return {'error': e}

# %%
#get list of authors from db
def get_all_authors():
    authors = tb_author.find({'status': 1})
    return authors
#test
author_db = get_all_authors()

# %%
author_ids = []
for author in author_db:
    author_ids.append(author['id'])

# %%
#author_ids = [103195312]


# %%
#insert or update page posts to db
def upsert_page_posts(new_post):
    postDB = tb_page_post.find_one({'id': new_post['id']})
    if postDB == None:
        #insert new post
        new_post['shared'] = 0  #never shared to my page before
        tb_page_post.insert_one(new_post)
        print('+++++++++ inserted: ' + new_post['id'])
    else:   #update it if there is new description and this post is not shared
        if postDB['description'] != new_post['description'] and postDB['shared'] != 1:
            tb_page_post.update_one({'id': new_post['id']}, {'$set': {'description': new_post['description'], 'lastModifiedAt': get_current_timestamp_milliseconds()}})
            print('updated: ' + new_post['id'])


# %%
#scrape latest posts from all authors
def scrape_posts():
    for author_id in author_ids:
        page_posts = get_request('posts?author=urn%3Ali%3Aorganization%3A'+str(author_id)+'&q=author&count=10&sortBy=LAST_MODIFIED')
        for page_post in page_posts['elements']:
            try:
                #only get posts have media
                if 'media' in page_post['content']:
                    new_post = {
                        "id" : page_post['id'],
                        "lastModifiedAt" : page_post['lastModifiedAt'],
                        "author" : page_post['author'].replace('urn:li:organization:', ''),
                        "description": page_post['commentary'],
                        "media": page_post['content']['media']['id']
                    }
                    upsert_page_posts(new_post)
            except Exception as e:
                #any error, skip this post
                print(e)
        print('Finished scraping the page Id: ' + author_id)
    print('Finished scraping all pages')
#test
scrape_posts()
db_client.close()
# %%



