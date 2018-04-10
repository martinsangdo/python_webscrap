#author: Martin SangDo 2018
#get latest videos from Youtube channels

import requests
import const
import MySQLdb
import sys
import datetime

def doQuery(conn, video_list, playlist_id, original_playlist_id) :
	cur = conn.cursor()
	insert_count = 0;
	for video in video_list:
		cond_sql = 'SELECT _id FROM video_link WHERE original_id="'+video['snippet']['resourceId']['videoId']+'" AND playlist_id='+str(playlist_id)
		cur.execute(cond_sql)
		#if found this video in DB, should update it ?
		if (cur.rowcount == 0):
			add_row = ('INSERT INTO video_link (original_id, title, thumb_url, playlist_id) VALUES (%(original_id)s, %(title)s, %(thumb_url)s, %(playlist_id)s)')
			data_row = {
				  'original_id': video['snippet']['resourceId']['videoId'],
				  'title': video['snippet']['title'],
				  'thumb_url': video['snippet']['thumbnails']['medium']['url'],
				  'playlist_id': playlist_id
			}
			cur.execute(add_row, data_row)
			# Make sure data is committed to the database
			conn.commit()
			insert_count += 1
	#update crawling time of playlist
	if (insert_count > 0):
		#some videos inserted into DB
		update_sql = 'UPDATE video_playlist SET crawl_time=%s,video_num=video_num+'+str(insert_count)+' WHERE _id='+str(playlist_id)
		cur.execute(update_sql, [str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
		conn.commit()
#end doQuery
def getPlaylistInfo(conn, playlist_id):
	cur = conn.cursor()
	sql = 'SELECT original_id,channel_id FROM video_playlist WHERE status=1 AND _id='+str(playlist_id)
	cur.execute(sql)
	row = cur.fetchone()
	return row
#end get playlist info

if (len(sys.argv) == 1):	#empty parameter
	sys.exit()
playlist_id = sys.argv[1]
#get playlist id
myConnection = MySQLdb.connect(host=const.HOSTNAME, user=const.USERNAME, passwd=const.PASSWORD, db=const.DATABASE, use_unicode=True, charset="utf8")
playlist_info = getPlaylistInfo(myConnection, playlist_id)
#make API link
url = 'https://www.googleapis.com/youtube/v3/playlistItems?part='+const.PART+'+&maxResults='+const.PER_PAGE+'&playlistId='+playlist_info[0]+'&key='+const.API_KEY
#send request with fake browser (Avoid 403 error)
data = requests.get(url, headers=const.REQUEST_HEADER)
#parse data
j = data.json()
video_list=j['items']
#insert new videos to DB
doQuery( myConnection, video_list, playlist_id, playlist_info[0] )
myConnection.close()
