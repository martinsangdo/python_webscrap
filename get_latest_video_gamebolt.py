#author: Martin SangDo 2018
#get latest youtube videos from channel GameSpot
#https://www.a2hosting.com/kb/developer-corner/mysql/connecting-to-mysql-using-python

import requests
import const
import MySQLdb
import sys

PLAYLIST_ID='UUXa_bzvv7Oo1glaW9FldDhQ'
#ALTER TABLE `video_link` CHANGE `time` `time` DATETIME on update CURRENT_TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;

# Simple routine to run a query on a database and print the results:
def doQuery(conn, video_list) :
	cur = conn.cursor()
	for video in video_list:
		cond_sql = 'SELECT _id FROM video_link WHERE original_id="'+video['snippet']['resourceId']['videoId']+'" AND playlist_id=1'
		cur.execute(cond_sql)
		#if found this video in DB, should update it ?
		if (cur.rowcount == 0):
			add_row = ('INSERT INTO video_link (original_id, title, thumb_url, playlist_id) VALUES (%(original_id)s, %(title)s, %(thumb_url)s, 1)')
			data_row = {
				  'original_id': video['snippet']['resourceId']['videoId'],
				  'title': video['snippet']['title'],
				  'thumb_url': video['snippet']['thumbnails']['medium']['url']
			}
			cur.execute(add_row, data_row)
			# Make sure data is committed to the database
			conn.commit()
#end doQuery


# if (len(sys.argv) == 1):	#empty parameter
# 	sys.exit()
#make API link
url = 'https://www.googleapis.com/youtube/v3/playlistItems?part='+const.PART+'+&maxResults='+const.PER_PAGE+'&playlistId='+PLAYLIST_ID+'&key='+const.API_KEY
#send request with fake browser (Avoid 403 error)
data = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
#parse data
j = data.json()
video_list=j['items']

myConnection = MySQLdb.connect(host=const.HOSTNAME, user=const.USERNAME, passwd=const.PASSWORD, db=const.DATABASE, use_unicode=True, charset="utf8")
doQuery( myConnection, video_list )
myConnection.close()
# print 'Done'
