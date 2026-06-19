import datetime
import requests
import os
from dotenv import load_dotenv
load_dotenv(override=True) 
import datetime
import yt_dlp
import re

# 1. PLUG IN YOUR EXISTING TOKENS HERE
CLIENT_ID = os.environ['TWITCH_CLIENT_ID']
USER_ACCESS_TOKEN = os.environ['TWITCH_ACCESS_TOKEN']
####
headers = {
    "Client-Id": CLIENT_ID,
    "Authorization": f"Bearer {USER_ACCESS_TOKEN}",
}

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

if __name__ == "__main__":
    get_native_tiktok_feed()