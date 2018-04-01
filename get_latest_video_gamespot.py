#author: Martin SangDo 2018
#get latest youtube videos from channel GameSpot
#http://lxml.de/lxmlhtml.html
from lxml import html

import requests
import const

#make API link
url = 'https://www.googleapis.com/youtube/v3/playlistItems?part='+const.PART+'+&maxResults='+const.PER_PAGE+'&playlistId='+const.PLAYLIST_ID+'&key='+const.API_KEY
#send request with fake browser (Avoid 403 error)
data = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
#parse data
j = data.json()
video_list=j['items']

for video in video_list:
	print video['snippet']['title']