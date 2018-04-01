#author: Martin SangDo 2018
#get latest youtube videos from channel GameSpot
#http://lxml.de/lxmlhtml.html
from lxml import html

import requests

part='contentDetails,snippet'
per_page='10'
playlist_id='UUbu2SsF-Or3Rsn3NxqODImw'
api_key = 'AIzaSyCbEOvBCOQrBl4xHaKoDaSguRxmC4RZUiE'

#make API link
url = 'https://www.googleapis.com/youtube/v3/playlistItems?part='+part+'+&maxResults='+per_page+'&playlistId='+playlist_id+'&key='+api_key
#send request with fake browser (Avoid 403 error)
data = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
#parse data
j = data.json()
video_list=j['items']

for video in video_list:
	print video['snippet']['title']