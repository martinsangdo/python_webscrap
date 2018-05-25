#author: Martin SangDo 2018
#put posts into each categories
import const
import MySQLdb
import sys
import datetime
# https://github.com/Anorov/cloudflare-scrape
import cfscrape
import json
import re

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
myConnection = MySQLdb.connect(host=const.HOSTNAME, user=const.USERNAME, passwd=const.PASSWORD, db=const.DATABASE, use_unicode=True, charset="utf8")
cursor = myConnection.cursor()

coin_names_str = get_top_coins(cursor)
#select 100 latest posts
posts_sql = 'SELECT _id, title, excerpt, content FROM block_content ORDER BY update_time DESC LIMIT 0,100'
cursor.execute(posts_sql)
if (cursor.rowcount > 0):
    result = cursor.fetchall()
    for row in result:
        #check if this post have some info of top coin list
		#1. search in title
        in_title = re.search(coin_names_str, row[1].encode('utf-8').strip())
		#2. search in excerpt
        in_excerpt = re.search(coin_names_str, row[2].encode('utf-8').strip())
		#3. search in content
        in_content = re.search(coin_names_str, row[3].encode('utf-8').strip())
		#confirm it
        if ((in_title is not None) or (in_excerpt is not None) or (in_content is not None)):
			#found (this post relates with top coin news), insert it to correct category
            insert_sql = ('INSERT INTO category_post (cat_id, post_id) VALUES (%(cat_id)s,%(post_id)s)')
            rel_detail = {
                'cat_id': const.TOP_COIN_NEWS_CAT_ID,
                'post_id': row[0]
            }
            cursor.execute(insert_sql, rel_detail)
            myConnection.commit()

myConnection.close()
