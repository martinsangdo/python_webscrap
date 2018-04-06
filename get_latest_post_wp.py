#author: Martin SangDo 2018
#get latest posts from wordpress sites
import requests
import const
import MySQLdb
import sys
import datetime


def getSiteInfo(conn, site_id):
	cur = conn.cursor()
	sql = 'SELECT _id,api_uri,post_uri,item_num,thumb_url_param FROM site WHERE status=1 AND _id='+site_id
	cur.execute(sql)
	row = cur.fetchone()
	return row
#end getSiteInfo
#get thumbnail url of post
def get_thumbnail_url(site_info, post_raw_detail):
	if (post_raw_detail['_links']['wp:featuredmedia'][0] is not None and post_raw_detail['_links']['wp:featuredmedia'][0]['href'] != ''):
		#there is one attached media
		media_info = requests.get(post_raw_detail['_links']['wp:featuredmedia'][0]['href'], headers=const.REQUEST_HEADER)
		media_json = media_info.json()
		if (len(media_json['media_details']['sizes']) > 0):
			if (media_json['media_details']['sizes']['medium']['source_url'] != ''):
				return media_json['media_details']['sizes']['medium']['source_url']
			elif (media_json['media_details']['sizes']['medium_large']['source_url'] != ''):
				return media_json['media_details']['sizes']['medium_large']['source_url']
			elif (media_json['media_details']['sizes']['large']['source_url'] != ''):
				return media_json['media_details']['sizes']['large']['source_url']
			elif (media_json['media_details']['sizes']['full']['source_url'] != ''):
				return media_json['media_details']['sizes']['full']['source_url']
			elif (media_json['source_url'] != ''):
				return media_json['source_url'] + site_info[4]
		elif (media_json['source_url'] != ''):
			return media_json['source_url'] + site_info[4]
		return '';
#end get_thumbnail_url
#get more information of post
def get_meaningful_detail(site_info, post_raw_detail):
	data_row = {
		'site_id': site_info[0],
		'title': post_raw_detail['title']['rendered'],
		'thumb_url': '',
		'slug': post_raw_detail['slug'],
		'time': post_raw_detail['date'],
		'author_name': '',
		'excerpt': post_raw_detail['excerpt']['rendered'],
		'category_name': '',      #should be first category
		'category_slug': '',
		'original_post_id': post_raw_detail['id'],
		'original_url': post_raw_detail['link']
	}
	#get thumbnail url
	data_row['thumb_url'] = get_thumbnail_url(site_info, post_raw_detail)
	#get author name
	if (post_raw_detail['author'] > 0):
		user_info = requests.get(site_info[1]+'users/'+str(post_raw_detail['author']), headers=const.REQUEST_HEADER);
		user_json = user_info.json()
		if (user_json is not None and 'name' in user_json):
			data_row['author_name'] = user_json['name']
	#get category name (the first one)
	if (len(post_raw_detail['categories']) > 0):
		cat_info = requests.get(site_info[1]+'categories/'+str(post_raw_detail['categories'][0]), headers=const.REQUEST_HEADER);
		cat_json = cat_info.json()
		data_row['category_name'] = cat_json['name'];
		data_row['category_slug'] = cat_json['slug'];
	return data_row;

if (len(sys.argv) == 1):	#empty parameter
	sys.exit()
#get site id
site_id = sys.argv[1]
# print site_id
myConnection = MySQLdb.connect(host=const.HOSTNAME, user=const.USERNAME, passwd=const.PASSWORD, db=const.DATABASE, use_unicode=True, charset="utf8")
site_info = getSiteInfo( myConnection, site_id )
api_url = site_info[1]+site_info[2]+'&per_page='+str(site_info[3])
# print api_url
data = requests.get(api_url, headers=const.REQUEST_HEADER)
#parse data
json_data = data.json()
# print json_data
final_data = []
for post_raw_detail in json_data:
	final_data.append(get_meaningful_detail(site_info, post_raw_detail))

#upsert post data to DB
cursor = myConnection.cursor()
for post_detail in final_data:
	#check if the post existed in db
	existed_sql = 'SELECT _id FROM block_content WHERE site_id='+str(site_info[0])+' AND original_post_id='+str(post_detail['original_post_id'])
	cursor.execute(existed_sql)
	if (cursor.rowcount > 0):
		#existed, update to DB
		update_sql = ('UPDATE block_content SET title=%s,thumb_url=%s,slug=%s,time=%s,author_name=%s,excerpt=%s,category_name=%s,category_slug=%s,original_url=%s '+
			'WHERE site_id='+str(site_info[0])+' AND original_post_id='+str(post_detail['original_post_id']))
		cursor.execute(update_sql, (post_detail['title'], post_detail['thumb_url'], post_detail['slug'], post_detail['time'],
				post_detail['author_name'], post_detail['excerpt'], post_detail['category_name'], post_detail['category_slug'], post_detail['original_url']))
		# Make sure data is committed to the database
		myConnection.commit()
	else:
		#insert new one
		insert_sql = ('INSERT INTO block_content (site_id,title,thumb_url,slug,time,author_name,excerpt,category_name,category_slug,original_url,original_post_id) '+
			'VALUES (%(site_id)s,%(title)s,%(thumb_url)s,%(slug)s,%(time)s,%(author_name)s,%(excerpt)s,%(category_name)s,%(category_slug)s,%(original_url)s,%(original_post_id)s)')
		cursor.execute(insert_sql, post_detail)
		# Make sure data is committed to the database
		myConnection.commit()
	#update crawling time of site
	update_sql = ('UPDATE site SET crawl_time=%s WHERE _id='+str(site_info[0]))
	cursor.execute(update_sql, [str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
	myConnection.commit()
	# print(cursor._last_executed)

myConnection.close()
