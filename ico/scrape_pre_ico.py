#http://lxml.de/lxmlhtml.html
#author: Martin SangDo
from lxml import html

import const
import json
import requests
import time
import MySQLdb

def getICODetail(ico_id, ico_url):
	page = requests.get(ico_url, headers=const.REQUEST_HEADER)
	tree = html.fromstring(page.content)
	ico_detail = {
		'ico_id': ico_id
	}
	#get main content
	main_content = tree.findall('.//main[@class="ico-left-column"]')
	for tag in main_content:
		ico_detail['main_content'] = ''.join([html.tostring(child) for child in tag.iterdescendants()])
	#get minor content (review)
	minor_content = tree.findall('.//aside[@class="ico-sidebar div-block-36"]')
	for tag in minor_content:
		ico_detail['minor_content'] = ''.join([html.tostring(child) for child in tag.iterdescendants()])
	return ico_detail
#main process
source_url = 'https://topicolist.com/pre-icos'
type = 'pre_ico'
page = requests.get(source_url, headers=const.REQUEST_HEADER)
# print page.content
tree = html.fromstring(page.content)
#get title
# containers = tree.xpath('//div[@typeof="ListItem"]')
containers = tree.findall('.//div[@typeof="ListItem"]')

myConnection = MySQLdb.connect(host=const.HOSTNAME, user=const.USERNAME, passwd=const.PASSWORD, db=const.DATABASE, use_unicode=True, charset="utf8")
cursor = myConnection.cursor()
index = 1;

for tag in containers:
	detail = {
		'type': type,
		'thumb_url': '',		#may empty
		#get title
		'title' : tag.find('.//h4').text_content(),
		#get sub title
		'minor_title' : tag.find('.//div[@class="end-date _20px-left w-hidden-small w-hidden-tiny"]').text_content() + ' ' + tag.find('.//div[@class="end-date w-hidden-small w-hidden-tiny"]').text_content(),
		#get description
		'excerpt' : tag.find('.//p[@class="paragraph-61"]').text_content().encode("utf-8"),
		#get link
		'original_url' : 'https://topicolist.com' + tag.find('.//a[@property="url"]').attrib['href'],
		'sort_idx': index
	}
	index = index + 1
	# print tag.find('.//h4').text_content()
	#get thumbnail if exist
	if ('src' in tag.find('.//img[@property="image"]').attrib):
		detail['thumb_url'] = tag.find('.//img[@property="image"]').attrib['src']
	#check if the event existed in db
	existed_sql = 'SELECT _id FROM ico WHERE title="'+str(detail['title'])+'" AND original_url="'+str(detail['original_url'])+'"'
	cursor.execute(existed_sql)
	if (cursor.rowcount == 0):
		#not existed, insert to DB
		insert_sql = ('INSERT INTO ico (title,thumb_url,type,excerpt,original_url,minor_title,sort_idx) '+
			'VALUES (%(title)s,%(thumb_url)s,%(type)s,%(excerpt)s,%(original_url)s,%(minor_title)s,%(sort_idx)s)')
		cursor.execute(insert_sql, detail)
		myConnection.commit()
		inserted_id = cursor.lastrowid
		#get detail of this ico
		ico_detail = getICODetail(inserted_id, detail['original_url'])
		#insert into DB
		insert_sql = ('INSERT INTO ico_detail (ico_id,main_content,minor_content) '+
			'VALUES (%(ico_id)s,%(main_content)s,%(minor_content)s)')
		cursor.execute(insert_sql, ico_detail)
		myConnection.commit()

myConnection.close()
