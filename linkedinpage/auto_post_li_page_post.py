# %%
import requests
import os
from dotenv import load_dotenv
import pymongo
import time
from urllib.parse import urlparse
import re


# %%
def get_current_timestamp_milliseconds():
  """
  Returns the current timestamp in milliseconds since the epoch.
  """
  return int(time.time() * 1000)

# %%
load_dotenv() 
LI_URI = os.environ['LI_URI']
LI_REST_URI = os.environ['LI_REST_URI']
LI_VERSION = os.environ['LI_VERSION']
LI_ACCESS_TOKEN = os.environ['LI_ACCESS_TOKEN']

# %%
li_headers = {
    'Authorization': LI_ACCESS_TOKEN,
    'LinkedIn-Version': LI_VERSION,
    'Content-Type': 'application/json'
}

# %%
owner_id = "urn:li:organization:" + os.environ['MY_PAGE_ID']    #my page

# %%
db_client = pymongo.MongoClient(os.environ['REMOTE_MONGO_DB'])
db = db_client['db_infographic']
tb_page_post = db['tb_page_posts']

# %%
def post_2_page(payload):
    #print(url)
    url = LI_REST_URI + 'posts'
    try:
        detail = requests.post(url, json=payload, headers=li_headers)
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
#get 1 random post to reshare if there were less than 5 posts in last 24 hours
def get_1_latest_post():
    timenow = get_current_timestamp_milliseconds()  #milliseconds
    last24hours = timenow - 24 * 60 * 60 * 1000
    todayPosts = tb_page_post.count_documents({'shared': 1, '$and': [ {'shared_time': {'$gt': last24hours }}, {'shared_time': {'$lt': timenow }} ] })
    # print(last24hours)
    print(todayPosts)
    if todayPosts < 10:
        #2. if today posted < 5 posts:
        #2.1 get 1 new post RANDOMLY, sorted by lastModifiedAt
        random_document = next(tb_page_post.aggregate([
            {"$match": {'shared': 0}},
            {"$sort": {"lastModifiedAt": -1}},
            #{"$sort": [("lastModifiedAt", -1)]},
            {"$sample": {"size": 1}}
        ]))
        return random_document
    #
    return None

# %%
#testing
#the_post = tb_page_post.find_one({'id':'urn:li:share:7317871023838699520'})
the_post = get_1_latest_post()

# %%
#log the time when the post is shared
def update_shared_info(post_id, post_desc):
    tb_page_post.update_one({'id': post_id}, {'$set': {'shared': 1, 'shared_time': get_current_timestamp_milliseconds()}})
    print('Finished reshare to the page with description: ' + post_desc + ' ...')

# %%
#repost exactly, do not download (maximum 5 repost per day)
def auto_repost(random_document):
    #2 post it to page
    if random_document != None:
        payload = {
            "author": owner_id,    #post to my page
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
            #2.3 Update to db: shared=1, shared_time=now
            update_shared_info(random_document['id'], random_document['description'][:30])
        else:
            print('error when sharing')
            print(result)
    else:
        print('No post to share today')

# %%
#download image into the folder
def download_img(image_url, img_name):
    folder_name = 'img' #in same place
    try:
        # Create the save folder if it doesn't exist
        os.makedirs(folder_name, exist_ok=True)
        # Get the filename from the URL
        file_path = os.path.join(folder_name, img_name + ".jpg")
        print(file_path)
        # Download the image
        response = requests.get(image_url, stream=True)
        response.raise_for_status()  # Raise an exception for bad status codes

        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        print(f"Image downloaded successfully and saved to: {file_path}")
        return file_path
    except requests.exceptions.RequestException as e:
        print(f"Error downloading image from {image_url}: {e}")
    except OSError as e:
        print(f"Error creating or writing to file: {e}")
    return None #no file downloaded

# %%
#get upload link from LI
def get_upload_link():
    url = LI_URI + 'v2/assets?action=registerUpload'
    payload = {
        "registerUploadRequest": {
            "recipes": [
                "urn:li:digitalmediaRecipe:feedshare-image"
            ],
            "owner": owner_id,
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }
            ]
        }
    }
    try:
        detail = requests.post(url, json=payload, headers=li_headers)
        return detail.json()
    except Exception as e:
        print(e)
        return {'error': e}

# %%
#reformat the description because it contains credit plus hashtag
def reformat_description():
    if 'description' not in the_post:
        return ''
    description = the_post['description'].replace('{hashtag|\\', '')
    description = description.replace('#|', '#')
    description = description.replace('}', '')
    description = description.replace('\\_', '_')
    #author
    description = description.replace(':person\\_', ':person_')
    description = description.replace(':person\_', ':person_')
    description = description.replace('urn:li:person:', '')
    description = description.replace('urn:li:organization:', '')

    return description

# %%
#desc = reformat_description()
#desc


# %%
#share new post with new uploaded image
def share_my_img(asset):
    #print('asset: ' + asset)
    payload = {
        "author": owner_id,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": reformat_description() + '\n\nCredits to https://www.linkedin.com/company/'+the_post['author']
                },
                "shareMediaCategory": "IMAGE",
                "media": [
                    {
                        "status": "READY",
                        "media": asset
                    }
                ]
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    try:
        response = requests.post(LI_URI + 'v2/ugcPosts', json=payload, headers=li_headers)

        if response.status_code >= 200 and response.status_code < 300:
            print("The image was shared successfully!")
            return 'ok'
        else:
            print("The image was shared failed.")
            return 'failed'
    except Exception as e:
        print(e)   
        return 'failed'

# %%
#upload image to LI
def upload_img(file_path, upload_detail):
    uploadUrl = upload_detail['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
    #upload the image https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin#upload-image-or-video-binary-file
    try:
        with open(file_path, 'rb') as file:
            files = {'file': (file.name, file, 'image/jpg')}
            headers = {
                'Authorization': LI_ACCESS_TOKEN,
                'LinkedIn-Version': LI_VERSION
            }

            response = requests.post(uploadUrl, files=files, headers=headers)
            # print("Status Code:", response.status_code)
            # print("Headers:", response.headers)
            # print("Response Body:", response.text)

            if response.status_code >= 200 and response.status_code < 300:
                print("File uploaded successfully!")
                time.sleep(5)   #delay 5 seconds for image going through LI system
                result = share_my_img(upload_detail['asset'])
                return result
            else:
                print("File upload failed.")
                return 'failed'

    except FileNotFoundError:
        print(f"Error: File not found at path: {file_path}")
        return 'failed' 
    except requests.exceptions.RequestException as e:
        print(f"Error during upload: {e}")
        return 'failed'
    

# %%
#find the image link and reshare in LI page
def reshare_img(li_img_id):
    #find img details
    url = LI_REST_URI + 'images/' + li_img_id
    headers = {
        'Authorization': LI_ACCESS_TOKEN,
        'LinkedIn-Version': LI_VERSION
    }
    try:
        detail = requests.get(url, headers=headers)
        #print(detail.json())
        if 'downloadUrl' in detail.json():
            file_path = download_img(detail.json()['downloadUrl'], li_img_id.replace('urn:li:image:', ''))
            if file_path is not None:
                #download successfully, now upload to LI and share
                upload_link = get_upload_link()
                if 'error' not in upload_link and 'value' in upload_link:
                    result = upload_img(file_path, upload_link['value'])
                    return result
                else:
                    return 'failed'
    except Exception as e:
        print(e)
        return 'failed'

# %%
#download image and re-share into the page
def download_n_reshare_post():
    if the_post is None:
        return  #reach limit for last 24 hours, do not share anything
    #check type of the post
    if 'urn:li:image:' in the_post['media']:
        #download the image
        result = reshare_img(the_post['media'])
        if result == 'ok':
            update_shared_info(the_post['id'], the_post['description'][:30])
        else:
            print('Error when download_n_reshare_post')
    else:
        #reshare the video, do not download
        auto_repost(the_post)

# %%
download_n_reshare_post()

# %%
db_client.close()


