#author: Martin SangDo 2018
#get latest youtube videos from channel GameSpot
#https://www.a2hosting.com/kb/developer-corner/mysql/connecting-to-mysql-using-python

from lxml import html

import requests
import const
import MySQLdb
import sys

# Simple routine to run a query on a database and print the results:
def doQuery( conn ) :
    cur = conn.cursor()
    cur.execute( "SELECT * FROM video_link" )
    for row in cur:
    	print(row[2])
        
# if (len(sys.argv) == 1):	#empty parameter
# 	sys.exit()
#make API link
url = 'https://www.googleapis.com/youtube/v3/playlistItems?part='+const.PART+'+&maxResults='+const.PER_PAGE+'&playlistId='+const.PLAYLIST_ID+'&key='+const.API_KEY
#send request with fake browser (Avoid 403 error)
data = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
#parse data
j = data.json()
video_list=j['items']

for video in video_list:
	print video['snippet']['title']
	
myConnection = MySQLdb.connect(host=const.HOSTNAME, user=const.USERNAME, passwd=const.PASSWORD, db=const.DATABASE )
doQuery( myConnection )
myConnection.close()
