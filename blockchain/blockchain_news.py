#author: Martin SangDo 2018
#get latest posts from wordpress sites
import const
import MySQLdb
import sys
import datetime
# https://github.com/Anorov/cloudflare-scrape
import cfscrape
import json
import re

def getSiteInfo(cur, site_id):
	sql = 'SELECT _id,home_url,post_uri,item_num,thumb_url_param FROM site WHERE status=1 AND _id='+site_id
	cur.execute(sql)
	row = cur.fetchone()
	return row
#end getSiteInfo
#get thumbnail url of post
def get_thumbnail_url(site_info, post_raw_detail, scraper):
	if (post_raw_detail['_links']['wp:featuredmedia'][0] is not None and post_raw_detail['_links']['wp:featuredmedia'][0]['href'] != ''):
		#there is one attached media
		media_info = scraper.get(post_raw_detail['_links']['wp:featuredmedia'][0]['href']).content
		media_json = json.loads(media_info.decode("utf-8"))
		if ('media_details' in media_json):
			if (len(media_json['media_details']['sizes']) > 0):
				if ('medium_large' in media_json['media_details']['sizes']):
					return media_json['media_details']['sizes']['medium_large']['source_url']
				elif ('large' in media_json['media_details']['sizes']):
					return media_json['media_details']['sizes']['large']['source_url']
				elif ('medium' in media_json['media_details']['sizes']):
					return media_json['media_details']['sizes']['medium']['source_url']
				elif ('full' in media_json['media_details']['sizes']):
					return media_json['media_details']['sizes']['full']['source_url']
				elif (media_json['source_url'] != ''):
					return media_json['source_url'] + site_info[4]
			elif (media_json['source_url'] != ''):
				return media_json['source_url'] + site_info[4]
		return '/public/blockbod/img/sample_cover/c1.jpg'	#default
	else :
		return '/public/blockbod/img/sample_cover/c1.jpg'	#default
#end get_thumbnail_url
#get more information of post
def get_meaningful_detail(site_info, post_raw_detail, scraper):
	data_row = {
		'site_id': site_info[0],
		'title': post_raw_detail['title']['rendered'],
		'thumb_url': '',
		'slug': post_raw_detail['slug'],
		'time': post_raw_detail['date'],
		'author_name': '',
		'excerpt': post_raw_detail['excerpt']['rendered'],
		'content': post_raw_detail['content']['rendered'],
		'original_post_id': post_raw_detail['id'],
		'original_url': post_raw_detail['link'],
		'categories': post_raw_detail['categories'],		#this one not exist in DB
		'is_top_coin_news': 0
	}
	#get thumbnail url
	data_row['thumb_url'] = get_thumbnail_url(site_info, post_raw_detail, scraper)
	#get author name
	if (post_raw_detail['author'] > 0):
		user_info = scraper.get(site_info[1]+'/wp-json/wp/v2/users/'+str(post_raw_detail['author'])).content
		user_json = json.loads(user_info.decode("utf-8"))
		if (user_json is not None and 'name' in user_json):
			data_row['author_name'] = user_json['name']
	return data_row
#get list of top coins
def get_top_coins (cursor):
	top_coin_names_sql = 'SELECT name FROM coin_list ORDER BY rank LIMIT 0,50'
	cursor.execute(top_coin_names_sql)
	names = []
	if (cursor.rowcount > 0):
		result = cursor.fetchall()
		for row in result:
	  		names.append(str(row[0]))
	  		#join names into 1 string
		return '|'.join(map(str, names))
	else:
		return ''

# print ('------start-----------')
if (len(sys.argv) == 1):	#empty parameter (site id)
	sys.exit()
#get site id
site_id = sys.argv[1]
# print site_id
myConnection = MySQLdb.connect(host=const.HOSTNAME, user=const.USERNAME, passwd=const.PASSWORD, db=const.DATABASE, use_unicode=True, charset="utf8")
cursor = myConnection.cursor()

site_info = getSiteInfo( cursor, site_id )
# print (site_info)
api_url = site_info[1]+'/wp-json/wp/v2/'+site_info[2]+'&per_page='+str(site_info[3])
# print (api_url)
scraper = cfscrape.create_scraper()  # returns a CloudflareScraper instance
json_data = scraper.get(api_url).content
json_data = json.loads(json_data.decode("utf-8"))
# print data
#parse data
# json_data = data.json()
final_data = []
for post_raw_detail in json_data:
	final_data.append(get_meaningful_detail(site_info, post_raw_detail, scraper))
#search name of top coins so that we can arrange post to that group
coin_names_str = get_top_coins(cursor)
#begin upsert post data to DB
new_post_num = 0
for post_detail in final_data:
	#check if the post existed in db
	existed_sql = 'SELECT _id FROM block_content WHERE slug="'+str(post_detail['slug'])+'" AND original_post_id='+str(post_detail['original_post_id'])
	cursor.execute(existed_sql)
	if (cursor.rowcount > 0):
		#existed, update to DB
		update_sql = ('UPDATE block_content SET title=%s,thumb_url=%s,slug=%s,time=%s,author_name=%s,excerpt=%s,content=%s,original_url=%s '+
			'WHERE site_id='+str(site_info[0])+' AND original_post_id='+str(post_detail['original_post_id']))
		cursor.execute(update_sql, (post_detail['title'], post_detail['thumb_url'], post_detail['slug'], post_detail['time'],
				post_detail['author_name'], post_detail['excerpt'], post_detail['content'], post_detail['original_url']))
		myConnection.commit()
		# print ('updated: '+post_detail['title'])
	else:
		#check if this post have some info of top coin list
		#1. search in title
		in_title = re.search(coin_names_str, post_detail['title'])
		#2. search in excerpt
		in_excerpt = re.search(coin_names_str, post_detail['excerpt'])
		#3. search in content
		in_content = re.search(coin_names_str, post_detail['content'])
		#confirm it
		if ((in_title is not None) or (in_excerpt is not None) or (in_content is not None)):
			post_detail['is_top_coin_news'] = 1
		#insert new one
		insert_sql = ('INSERT INTO block_content (site_id,title,thumb_url,slug,time,author_name,excerpt,content,original_url,original_post_id,is_top_coin_news) '+
			'VALUES (%(site_id)s,%(title)s,%(thumb_url)s,%(slug)s,%(time)s,%(author_name)s,%(excerpt)s,%(content)s,%(original_url)s,%(original_post_id)s,%(is_top_coin_news)s)')
		cursor.execute(insert_sql, post_detail)
		myConnection.commit()
		# print ('inserted: '+post_detail['title'])
		new_post_num += 1
		#get categories of each post, save to DB
		saved_cat_id = 0
		inserted_post_id = cursor.lastrowid		#created post id
		if (len(post_detail['categories']) > 0):
			for cat_id in post_detail['categories']:
				#check if category existed in DB
				existed_sql = 'SELECT _id FROM category WHERE site_id='+str(site_info[0])+' AND site_cat_id='+str(cat_id)
				cursor.execute(existed_sql)
				if (cursor.rowcount == 0):
					#not existed, insert new category
					cat_info = scraper.get(site_info[1]+'/wp-json/wp/v2/categories/'+str(cat_id)).content
					cat_json = json.loads(cat_info.decode("utf-8"))
					insert_sql = ('INSERT INTO category (name, slug, site_id, site_cat_id, post_num) '+
						'VALUES (%(name)s,%(slug)s,%(site_id)s,%(site_cat_id)s,1)')
					cat_detail = {
						'name': cat_json['name'],
						'slug': cat_json['slug'],
						'site_id': site_info[0],
						'site_cat_id': cat_id
					}
					cursor.execute(insert_sql, cat_detail)
					myConnection.commit()
					saved_cat_id = cursor.lastrowid,	#latest category id in DB
				else :
					#category existed, increase post_num to 1
					row = cursor.fetchone()
					saved_cat_id = row[0]
					update_sql = 'UPDATE category SET post_num = post_num + 1 WHERE _id ='+str(saved_cat_id)
					cursor.execute(update_sql, {})
					myConnection.commit()
				#create relationship between category & new post
				insert_sql = ('INSERT INTO category_post (cat_id, post_id) VALUES (%(cat_id)s,%(post_id)s)')
				rel_detail = {
					'cat_id': saved_cat_id,
					'post_id': inserted_post_id
				}
				cursor.execute(insert_sql, rel_detail)
				myConnection.commit()
#update crawling time of site
update_sql = ('UPDATE site SET crawl_time=%s,post_num=post_num+'+str(new_post_num)+' WHERE _id='+str(site_info[0]))
cursor.execute(update_sql, [str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
myConnection.commit()
# print(cursor._last_executed)

myConnection.close()
