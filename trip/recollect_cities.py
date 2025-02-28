# %%
import requests
import csv
from pathlib import Path
from dotenv import load_dotenv
import os
import pymongo
import uuid

# %%
load_dotenv() 
TRIP_URL = os.environ['TRIP_URL']

# %%
db_client = pymongo.MongoClient('mongodb://localhost:27017')
collections = db_client['db_ai_travel_planner']
tb_city_org = collections['tb_city_org']
tb_city = collections['tb_city']

# %%
def generate_random_uuid():
    """Generates a random UUID (Universally Unique Identifier).

    Returns:
        A string representing the UUID.
    """
    return str(uuid.uuid4())

# %%
def custom_query(get_url):
    #print(get_url)
    try:
        r = requests.get(get_url)
        return r.json()
    except Exception as e:
       print(e)
       return r

# %%
#find other info of city
def get_trip_details(trip_city_id):
    url =  TRIP_URL + '19913/getTripAttractionList'
    HEADER = {'Content-Type': 'application/json'}
    json_data = {
        "head": {
            "extension": [
                {
                    "name": "platform",
                    "value": "Online"
                },
                {
                    "name": "locale",
                    "value": "en-US"
                }
            ]
        },
        "districtId": trip_city_id,
        "index": 1,
        "count": 20,
        "returnModuleType": "all"
    }

    try:
        r = requests.post(url, headers=HEADER, json=json_data)
        return r.json()
    except Exception as e:
       print(e)
       return {'error': e}

# %%
import random
def get_4_random_items(arr):
    """
    Returns 4 random items from the given array.

    Args:
        arr: The input array.

    Returns:
        A list containing 4 random items from the array, or a list containing the entire array if the array has less than 4 items.
    """
    if len(arr) <= 4:
        return arr[:] # Return a copy of the list to avoid modifying the original
    else:
        return random.sample(arr, 4)

# Example usage:
my_array = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
random_items = get_4_random_items(my_array)
print(random_items)

# %%
def upsert_city(new_city_obj):
    #print(new_city_obj)
    saved_city = tb_city.find_one({'name': new_city_obj['name'], 'country': new_city_obj['country']})
    if saved_city is not None:
        #existed, we need to update
        tb_city.update_one({'uuid': new_city_obj['uuid']}, {'$set': new_city_obj})
        print('Updated ------------ city: ' + new_city_obj['name'])
    else:
        #not existed, insert one
        tb_city.insert_one(new_city_obj)
        print('Inserted +++++++++++ city: ' + new_city_obj['name'])

# %%
#find cities that already scraped
db_cities = tb_city_org.find({'is_scraped': None, 'city_id': {"$ne": None}})
idx = 0 #21813
for city in db_cities:
    if idx < 22000:
        #find other images again
        raw_details = get_trip_details(city['city_id'])
        imgUrls = []
        if 'attractionList' in raw_details:
            allImgUrls = []
            for item in raw_details['attractionList']:
                if 'card' in item:
                    allImgUrls.append(item['card']['coverImageUrl'])
            #get max 4 images in the list
            if (len(allImgUrls) > 4):
                imgUrls = get_4_random_items(allImgUrls)
        #lock the org table
        org_city = city
        org_city['is_scraped'] = 1
        tb_city_org.update_one({'uuid': org_city['uuid']}, {'$set': org_city})      
        #new table
        if len(imgUrls) == 0:
            #no other info -> error
            city['error'] = 'Not enough images'
        else:
            city['imgUrls'] = imgUrls
            city['img'] = imgUrls[0]    #first image
        #upsert to db
        upsert_city(city)

    else:
        break
    #
    idx += 1
    print(idx)

# %%
#find images again



