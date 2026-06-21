import datetime
import json
import requests
import os
from dotenv import load_dotenv
load_dotenv(override=True) 
import datetime
import yt_dlp
import re
import pymongo

# 1. PLUG IN YOUR EXISTING TOKENS HERE
CLIENT_ID = os.environ['TWITCH_CLIENT_ID']
USER_ACCESS_TOKEN = os.environ['TWITCH_ACCESS_TOKEN']
####
headers = {
    "Client-Id": CLIENT_ID,
    "Authorization": f"Bearer {USER_ACCESS_TOKEN}",
}

db_client = pymongo.MongoClient(os.environ['REMOTE_MONGO_DB'])
db = db_client['db_vibe_streams']   

def extract_real_mp4_with_ytdlp(embed_url):
    """Uses yt-dlp to inspect the twitch page and extract the hidden direct .mp4 streaming link."""
    # Convert embed url back to the main clip url that yt-dlp expects
    # e.g., https://clips.twitch.tv/ObliviousAntediluvianBubbleteaSaltBae...
    clip_id = embed_url.split("?clip=")[1].split("&")[0]
    clean_clip_url = f"https://clips.twitch.tv/{clip_id}"

    ydl_opts = {
        "quiet": True,
        "skip_download": True,  # We only want the link metadata, don't download the file
        "force_generic_extractor": False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_clip_url, download=False)
            # Fetch the high-quality direct MP4 stream URL from the metadata manifest
            return info.get("url")
    except Exception as e:
        print(f"Extraction failed for {clip_id}: {e}")
        return None


def get_seconds_until_link_dies(twitch_mp4_url):
    """Parses the long Twitch CDN URL and returns how many seconds it has left to live."""
    # Find the "expires" number in the URL query string
    match = re.search(r"expires=(\d+)", twitch_mp4_url)
    
    if not match:
        # If there's no expires param, check inside the URL-encoded token block
        match = re.search(r"expires%22%3A(\d+)", twitch_mp4_url)
        
    if match:
        expire_timestamp = int(match.group(1))
        
        # Get current real-world UTC time
        now_timestamp = int(datetime.datetime.utcnow().timestamp())
        
        # Calculate time remaining
        seconds_left = expire_timestamp - now_timestamp
        return max(0, seconds_left) # Returns 0 if it already died
        
    return None

def get_yesterday_iso():
    now = datetime.datetime.utcnow()
    one_week_ago = now - datetime.timedelta(days=1)
    started_at = one_week_ago.isoformat() + "Z"
    return started_at

def get_today_iso():
    now = datetime.datetime.utcnow()
    started_at = now.isoformat() + "Z"
    return started_at

def get_native_tiktok_feed():
    # Fetch top 3 trending games
    games_resp = requests.get(
        "https://api.twitch.tv/helix/games/top?first=3", headers=headers
    )
    if games_resp.status_code != 200:
        print("Token Expired or Auth Failed!")
        return

    game_ids = [game["id"] for game in games_resp.json().get("data", [])]

    now = datetime.datetime.utcnow()
    one_week_ago = now - datetime.timedelta(days=7)
    started_at = one_week_ago.isoformat() + "Z"

    feed_clips = []
    print("Fetching raw clips and extracting hidden native MP4 URLs...")

    for game_id in game_ids:
        clips_url = f"https://api.twitch.tv/helix/clips?game_id={game_id}&started_at={started_at}&first=3"
        clips_resp = requests.get(clips_url, headers=headers)

        if clips_resp.status_code == 200:
            for clip in clips_resp.json().get("data", []):
                embed_url = clip.get("embed_url")

                # Run the extractor to get the hidden .mp4 streaming path
                print(f"Extracting streaming path for: {clip['title'][:30]}...")
                real_mp4_url = extract_real_mp4_with_ytdlp(embed_url)

                if real_mp4_url:
                    feed_clips.append(
                        {
                            "id": clip["id"],
                            "title": clip["title"],
                            "streamer": clip["broadcaster_name"],
                            "views": clip["view_count"],
                            "video_url": real_mp4_url,  # TRUE NATIVE MP4 LINK
                        }
                    )

    # Sort everything globally by view count
    feed_clips.sort(key=lambda x: x["views"], reverse=True)

    print(f"\n🚀 SUCCESS! Compiled {len(feed_clips)} native videos for Flutter:")
    for idx, clip in enumerate(feed_clips[:3], 1):
        print(f"\n[Video #{idx}]")
        print(f"Title: {clip['title']}")
        print(f"Streamer: @{clip['streamer']}")
        print(f"Direct MP4 Link: {clip['video_url']}")
        print(f"Seconds until link dies: {get_seconds_until_link_dies(clip['video_url']) // 3600} hours")

#get clips of channels
CATEGORY_IDS = {    #6 categories
    'music': 26936,
    #more
}
TOTAL_VIDS_PER_CAT = 4000   #total videos per each category
ITEMS_PER_PAGE = 100
#1 week - 20000 clips -> 1 day scrapes 3000 clips within 4 hours -> 30 mins 500 clips per each category
#each category has 4000 clips
def get_all_clips(category_id):
    started_at = get_yesterday_iso()
    clips = []
    for i in range (0, 5):  #get 500 clips
        clips_url = f"https://api.twitch.tv/helix/clips?game_id={category_id}&started_at={started_at}&first={ITEMS_PER_PAGE}"
        response = requests.get(clips_url, headers=headers)
        if response.status_code != 200:
            print("Token Expired or Auth Failed!")
            break
        clips.extend(response.json().get("data", []))
    print(f"Total raw clips: {len(clips)}")
    if len(clips) == 0:
        return
    index = 0
    final_clips = []
    for clip in clips:
        mp4_url = extract_real_mp4_with_ytdlp(clip['embed_url'])
        if mp4_url is not None:
            index = index + 1
            print(f"Finish getting mp4 at {index}")
            # print(mp4_url)
            new_clip = {    #save minium to optimize database
                "id": clip['id'],
                "title": clip['title'],
                "t": clip['thumbnail_url'],
                "cr": clip['creator_name'],
                "v": clip['view_count'],
                "d": clip['duration'],
                "c": category_id,
                "m": mp4_url,
                "ca": get_today_iso()
            }
            # upsert_clip(new_clip)
            final_clips.append(new_clip)
            #todo: save streamer id and info (for user to follow)
        # if index == 3:
        #     break
    # print(final_clips)
    return final_clips
#upsert questions to collection
def upsert_clip(collection, a_clip):
    existed_doc = collection.find_one({'id': a_clip['id']})
    if existed_doc == None:
        #insert new document
        collection.insert_one(a_clip)
    else:
        #update
        collection.update_one({'id': a_clip['id']}, {'$set': a_clip})
    # print(f"Finish upsert {a_clip['title']}")

def upsert_clips_2_db(final_clips):
    collection = db['tb_clips']
    #find all ids in db
    old_ids = []
    old_clips = collection.find()
    for old_clip in old_clips:
        old_ids.append(old_clip['id'])
    #
    new_ids = []    #ids of all clips in db
    for clip in final_clips:
        upsert_clip(collection, clip)
        new_ids.append(clip['id'])
    #find ids that should be deleted
    deleted_ids = []
    for id in old_ids:
        if id not in new_ids:
            deleted_ids.append(id)
    #delete old clips (flush the db)
    print('Length of deleted ids: ' + str(len(deleted_ids)))
    if len(deleted_ids) > 0:
        collection.delete_many({'id': {'$in': deleted_ids}})
    #
###
if __name__ == "__main__":
    # get_native_tiktok_feed()
    print('=== START scraping: ' + get_today_iso())
    final_clips = get_all_clips(CATEGORY_IDS['music'])
    print('Total clips with mp4 link: ' + str(len(final_clips)))
    if len(final_clips) > 0:
        #save to file (Backup)
        with open('final_clips.json', 'w') as f:
            json.dump(final_clips, f)
        upsert_clips_2_db(final_clips)
    print('=== END scraping: ' + get_today_iso())   #500 clips ~ 6 mins