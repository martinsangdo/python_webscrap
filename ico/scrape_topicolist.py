#author: Martin SangDo
#scraping data from topicolist.com
from lxml import html

import const
import requests
import time
import MySQLdb
import sys
import cfscrape
import datetime
import AdvancedHTMLParser		#https://pypi.org/project/AdvancedHTMLParser/6.2.4/

def getLinkInfo(cursor, link_id):
	sql = 'SELECT url,type FROM ico_link WHERE status=1 AND _id='+link_id
	cursor.execute(sql)
	return cursor.fetchone()

def getICODetail(parser, ico_url):
	page = requests.get(ico_url, headers=const.REQUEST_HEADER)
	parser.parseStr(page.content)

	ico_detail = {
		'main_content': '',
		'minor_content': ''
	}
	#get main content
	main_content = parser.getElementsByClassName('ico-left-column')
	for tag in main_content:
		ico_detail['main_content'] = tag.innerHTML
	#get minor content (review)
	minor_content = parser.getElementsByClassName('ico-sidebar')
	for tag in minor_content:
		ico_detail['minor_content'] = tag.innerHTML
	return ico_detail

if (len(sys.argv) == 1):	#empty parameter (ico list/link id)
	sys.exit()
#get ico link id
link_id = sys.argv[1]
root_url = 'https://topicolist.com'
parser = AdvancedHTMLParser.AdvancedHTMLParser()
myConnection = MySQLdb.connect(host=const.HOSTNAME, user=const.USERNAME, passwd=const.PASSWORD, db=const.DATABASE, use_unicode=True, charset="utf8")
cursor = myConnection.cursor()

#get link info
link_info = getLinkInfo(cursor, link_id)
#get data from link
scraper = cfscrape.create_scraper()  # returns a CloudflareScraper instance
json_data = scraper.get(link_info[0]).content
tree = html.fromstring(json_data.decode("utf-8"))
#get list of ICO
ico_containers = tree.findall('.//div[@typeof="ListItem"]')
index = 1;		#ico index (order in the list)
new_post_num = 0

for container in ico_containers:
	detail = {	#ICO detail
		#get title
		'title' : container.find('.//h4').text_content(),
		#get sub title
		'minor_title' : container.find('.//div[@class="end-date _20px-left w-hidden-small w-hidden-tiny"]').text_content() + ' ' + container.find('.//div[@class="end-date w-hidden-small w-hidden-tiny"]').text_content(),
		#get description
		'excerpt' : container.find('.//p[@class="paragraph-61"]').text_content().encode("utf-8"),
		#get link
		'original_url' : root_url + container.find('.//a[@property="url"]').attrib['href'],
		'sort_idx': index
	}
	index += 1
	# print tag.find('.//h4').text_content()
	#get thumbnail if exist
	if ('src' in container.find('.//img[@property="image"]').attrib):
		detail['thumb_url'] = container.find('.//img[@property="image"]').attrib['src']
	#get detail of ICO
	ico_detail = getICODetail(parser, root_url + container.find('.//a[@property="url"]').attrib['href'])
	detail['main_content'] = ico_detail['main_content']
	detail['minor_content'] = ico_detail['minor_content']
	#check if the event existed in db
	existed_sql = 'SELECT _id FROM ico WHERE title="'+str(detail['title'])+'" AND original_url="'+str(detail['original_url'])+'" AND ico_id='+link_id
	cursor.execute(existed_sql)
	saved_ico_detail = cursor.fetchone()
	detail['ico_id'] = link_id
	if (cursor.rowcount == 0):
		#not existed, insert to DB
		insert_sql = ('INSERT INTO ico (title,ico_id,thumb_url,excerpt,original_url,minor_title,main_content,minor_content,sort_idx) '+
			'VALUES (%(title)s,%(ico_id)s,%(thumb_url)s,%(excerpt)s,%(original_url)s,%(minor_title)s,%(main_content)s,%(minor_content)s,%(sort_idx)s)')
		cursor.execute(insert_sql, detail)
		myConnection.commit()
		new_post_num += 1
	else:
		#update info
		update_sql = ('UPDATE ico SET title=%s,thumb_url=%s,excerpt=%s,original_url=%s,minor_title=%s,main_content=%s,minor_content=%s,sort_idx=%s '+
			'WHERE _id='+str(saved_ico_detail[0]))
		cursor.execute(update_sql, (detail['title'], detail['thumb_url'], detail['excerpt'], detail['original_url'],
				detail['minor_title'], detail['main_content'], detail['minor_content'], detail['sort_idx']))
		myConnection.commit()
#update crawling time of ICO link
update_sql = ('UPDATE ico_link SET scrape_time=%s,num=num+'+str(new_post_num)+' WHERE _id='+str(link_id))
cursor.execute(update_sql, [str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])
myConnection.commit()
