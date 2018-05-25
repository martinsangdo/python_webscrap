#author: Martin SangDo 2018
#get 50 top icons
import const
import MySQLdb
import sys
import datetime
# https://github.com/Anorov/cloudflare-scrape
import cfscrape
import json

# print ('------start-----------')
api_url = 'https://api.coinmarketcap.com/v2/ticker/?limit=50&sort=rank'
# print (api_url)
scraper = cfscrape.create_scraper()  # returns a CloudflareScraper instance
json_data = scraper.get(api_url).content
json_data = json.loads(json_data.decode("utf-8"))
# print json_data
data_obj = json_data['data']
#parse data
final_data = []
for raw_detail in data_obj:
	final_data.append({
		'name': data_obj[raw_detail]['name'],
		'symbol': data_obj[raw_detail]['symbol'],
		'rank': data_obj[raw_detail]['rank']
	})
myConnection = MySQLdb.connect(host=const.HOSTNAME, user=const.USERNAME, passwd=const.PASSWORD, db=const.DATABASE, use_unicode=True, charset="utf8")
cursor = myConnection.cursor()
#reset rank in DB
update_sql = 'UPDATE coin_list SET rank=0'
cursor.execute(update_sql)
myConnection.commit()
#
for detail in final_data:
	#check if the coin existed in db
	existed_sql = 'SELECT _id FROM coin_list WHERE symbol="'+str(detail['symbol'])+'"'
	cursor.execute(existed_sql)
	if (cursor.rowcount > 0):
		#existed, update rank to DB
		update_sql = 'UPDATE coin_list SET rank='+str(detail['rank'])+' WHERE symbol="'+str(detail['symbol'])+'"'
		cursor.execute(update_sql)
		myConnection.commit()
	else:
		#insert new one
		insert_sql = 'INSERT INTO coin_list (name,symbol,rank) VALUES (%(name)s,%(symbol)s,%(rank)s)'
		cursor.execute(insert_sql, detail)
		myConnection.commit()
#
myConnection.close()
