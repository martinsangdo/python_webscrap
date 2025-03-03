# %%
import requests
import csv
from pathlib import Path
from dotenv import load_dotenv
import os
import pymongo
import uuid

# %%
#find the path of python to install new package
#import sys
#sys.executable

# %%
load_dotenv() 
WONDER_URL = os.environ['WONDER_URL']
TRIP_URL = os.environ['TRIP_URL']

# %%
db_client = pymongo.MongoClient('mongodb://localhost:27017')
collections = db_client['db_ai_travel_planner']
tb_city_org = collections['tb_city_org']

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
def search_trip_locations(keyword):
    url =  TRIP_URL + '20400/getGsMainSuggestForTripOnline'
    HEADER = {'Content-Type': 'application/json'}
    json_data = {
        "keyword": keyword.lower(),
        "head": {
            "extension": [
                {
                    "name": "locale",
                    "value": "en-US"
                },
                {
                    "name": "platform",
                    "value": "Online"
                },
                {
                    "name": "userAgent",
                    "value": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
                }
            ]
        }
    }
    try:
        r = requests.post(url, headers=HEADER, json=json_data)
        return r.json()
    except Exception as e:
       #print(e)
       return {'error': e}

# %%
def load_csv(filepath):
    data = []
    with open(filepath, 'r', newline='', encoding='utf-8') as csvfile:  # Handle encoding!
        reader = csv.reader(csvfile)  # Or csv.DictReader for dictionaries
        header = next(reader)  # Read the header row (if it exists)
        for row in reader:
            data.append(row)  # Or data.append(dict(zip(header, row))) for DictReader
    return header, data  # Return header and data

# %%
def search_city_in_trip(city):
    result = custom_query(TRIP_URL + 'api/v1/destinations?page=0&q=' + city.lower())  #1.8s

    return result['destinationMetas']

# %%
def search_city_in_wonderplan(city):
    result = custom_query(WONDER_URL + 'api/v1/destinations?page=0&q=' + city.lower())  #1.8s

    return result['destinationMetas']

# %%
#find common details between 2 services

def find_match_cities(city, country):
    response_data = {
        'city': city,
        'country': country,
        #'wonder_id': '',    #ID in wonderland, sample: DE/BY/Munich
        #'trip_id': 0,       #ID in trip, sample 1234
    }
    #1. find in wonderplan
    wonder_cities = search_city_in_wonderplan(city)
    if (len(wonder_cities) > 0):
        #found it in Wonderplan
        for item in wonder_cities:
            if item['type'] == 'DESTINATION_TYPE_CITY':
                response_data['wonder_id'] = item['id']
                #2. find in trip
                trip_cities = search_trip_locations(city)
                if 'data' in trip_cities:
                    for trip_item in trip_cities['data']:
                        if trip_item['type'] == 'district':
                            if (city.lower() == trip_item['word'].lower().replace('<em>', '').replace('</em>', '')):
                                response_data['trip_id'] = trip_item['id']
                #else:
                    #print('Not found city in Trip: ' + city + ' country: ' + country)
    #else:
        #print('Not found city in Wonderplan: ' + city + ' country: ' + country)
    #2. find in trip

    #get common id

    return response_data

find_match_cities('Tokyo', 'Japan')

# %%
continent_map = {}  #key: country, value: continent
continents = {} #key: continent, value: 1
#read continent info
header, data = load_csv(Path("./countries.csv"))
for row in data:
    continent = row[12].replace('Americas', 'America').replace('Oceania', 'Australia').lower()
    if continent != '' and continent != 'Polar':
        continent_map[row[1]] = continent
    # if row[12] not in continents:
    #     continents[row[12]] = 1
#print(continent_map)

# %%
def generate_random_uuid():
    """Generates a random UUID (Universally Unique Identifier).

    Returns:
        A string representing the UUID.
    """
    return str(uuid.uuid4())

# %%
#replace country name in db to match with the continent
scraping_country_map = {}   #key: country, value: 1
db_cities = tb_city_org.find({'error':None, 'city_id':None})
for db_city in db_cities:
    if db_city['country'] == 'Korea, South':
        db_city['country'] = db_city['country'].replace('Korea, South', 'South Korea')
    if db_city['country'] == 'Congo (Kinshasa)':
        db_city['country'] = db_city['country'].replace('Congo (Kinshasa)', 'Democratic Republic of the Congo')
    if db_city['country'] == 'Congo (Brazzaville)':
        db_city['country'] = db_city['country'].replace('Congo (Brazzaville)', 'Republic of the Congo')
    if db_city['country'] == 'Korea, North':
        db_city['country'] = db_city['country'].replace('Korea, North', 'North Korea')
    if db_city['country'] == 'Czechia':
        db_city['country'] = db_city['country'].replace('Czechia', 'Czech Republic')
    if db_city['country'] == 'Burma':
        db_city['country'] = db_city['country'].replace('Burma', 'Myanmar')
    if db_city['country'] == 'Macau':
        db_city['country'] = db_city['country'].replace('Macau', 'Macau S.A.R.')
    if db_city['country'] == 'Bahamas, The':
        db_city['country'] = db_city['country'].replace('Bahamas, The', 'The Bahamas')
    # if db_city['country'] == 'Philippines':
    #     db_city['country'] = db_city['country'].replace('', '')
    # if db_city['country'] == 'Fiji':
    #     db_city['country'] = db_city['country'].replace('', '')
    if db_city['country'] == 'Gambia, The':
        db_city['country'] = db_city['country'].replace('Gambia, The', 'The Gambia')
    if db_city['country'] == 'Cabo Verde':
        db_city['country'] = db_city['country'].replace('Cabo Verde', 'Cape Verde')
    # if db_city['country'] == 'Ireland':
    #     db_city['country'] = db_city['country'].replace('', '')
    if db_city['country'] == 'U.S. Virgin Islands':
        db_city['country'] = db_city['country'].replace('U.S. Virgin Islands', 'Virgin Islands (US)')
    scraping_country_map[db_city['country']] = 1
    #print(db_city)
        #update db
    tb_city_org.update_one({'uuid': db_city['uuid']}, {'$set': db_city})
scraping_country_map


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
#test


# %%
#find all data in our db
# db_cities_total = tb_city_org.count_documents({})
# print(db_cities_total)
#find all missing cities
db_cities = tb_city_org.find({'city_id':None})
scrape_cities = []
city_country_map = {}   #key: city@country, value: 1
for city in db_cities:
    city_country_map[city['name']+'@'+city['country']] = 1
#
filepath = Path("./worldcities.csv")  # Relative path (better)
header, data = load_csv(filepath)
#print(str(len(data)))
scrape_cities = []
for row in data:
    if row[0]+'@'+row[4].strip() in city_country_map:
        #need to scrape this city
        scrape_cities.append({'name': row[0].strip(), 'country': row[4].strip()})
    
print(str(len(scrape_cities)))
#print(scrape_cities)


# %%
scrape_cities[0]

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

# %%

index = 0
error_cities = {}
for row in scrape_cities:
    city = row['name']
    country = row['country']
    #find if the city existed in db
    db_city = tb_city_org.find_one({'name': city, 'country': country})
    #never scrape info of this city
    if index < 22000:
        results = find_match_cities(city, country)
        if 'wonder_id' not in results or 'trip_id' not in results:
            error_cities[city] = 'Not found city'
            print('Not found city: ' + city + ' country: ' + country)
        else:
            #find other relevant info of city
            if country not in continent_map:
                error_cities[city] = 'Not found continent'
                print('Continent not found: ' + country)
            else:
                raw_details = get_trip_details(results['trip_id'])
                totalReview = 0
                imgUrls = []
                if 'attractionList' in raw_details:
                    allImgUrls = []
                    for item in raw_details['attractionList']:
                        if 'card' in item:
                            allImgUrls.append(item['card']['coverImageUrl'])
                            #get max 4 images in the list
                            if (len(allImgUrls) > 4):
                                imgUrls = get_4_random_items(allImgUrls)
                            if 'commentInfo' in item['card']:
                                totalReview += item['card']['commentInfo']['commentCount']
                            
                    if len(imgUrls) == 0:
                        #no other info
                        error_cities[city] = 'Not found other info'
                        print('Not found other info: ' + city + ' country: ' + country)
                    else:
                        #city has enough essential info
                        #upsert city detail into db
                        if db_city is None:
                            #not found, insert one
                            new_city_info = {
                                'uuid': generate_random_uuid(),
                                'name': city,
                                'country': country,
                                'city_id': results['trip_id'],
                                'continent': continent_map[country],
                                'review': totalReview,
                                'img': imgUrls[0],
                                'imgUrls': imgUrls,
                                'wonder_id': results['wonder_id']
                            }
                            tb_city_org.insert_one(new_city_info)
                            print("Inserted +++++++++++ city: " + city)
                        else:
                            #update info
                            update_city_info = {
                                'name': city,
                                'country': country,
                                'city_id': results['trip_id'],
                                'continent': continent_map[country],
                                'review': totalReview,
                                'img': imgUrls[0],
                                'imgUrls': imgUrls,
                                'wonder_id': results['wonder_id']
                            }
                            tb_city_org.update_one({'uuid': db_city['uuid']}, {'$set': update_city_info})
                            print("Updated --- city: " + city)
                else:
                    error_cities[city] = 'No attractions'
                    print('No attractions: ' + city + ' country: ' + country)
        if city in error_cities:
            #this city has issue which cannot get full details -> save error so that we don't scrape again
            if db_city is None:
                new_city_info = {
                    'uuid': generate_random_uuid(),
                    'name': city,
                    'country': country,
                    'error': error_cities[city]
                }
                tb_city_org.insert_one(new_city_info)
                print("Inserted +++++++++++ city with error: " + city)
            else:
                update_city_info = {
                    'error': error_cities[city]
                }
                print(update_city_info)
                tb_city_org.update_one({'uuid': db_city['uuid']}, {'$set': update_city_info})
                print("Updated --- city with error: " + city)
    index += 1
    print('Finish city# ' + str(index))

# %%
#print(error_cities)

# %%



