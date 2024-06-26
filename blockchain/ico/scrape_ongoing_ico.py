#http://lxml.de/lxmlhtml.html
#author: Martin SangDo
from lxml import html

import const
import json
import requests
import time
import MySQLdb

source_url = 'https://topicolist.com/ongoing-icos'
type = 'ongoing_ico'
page = requests.get(source_url, headers=const.REQUEST_HEADER)
# print page.content
tree = html.fromstring(page.content)
#get title
# containers = tree.xpath('//div[@typeof="ListItem"]')
containers = tree.findall('.//div[@typeof="ListItem"]')

myConnection = MySQLdb.connect(host=const.HOSTNAME, user=const.USERNAME, passwd=const.PASSWORD, db=const.DATABASE, use_unicode=True, charset="utf8")
cursor = myConnection.cursor()

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
		'original_url' : 'https://topicolist.com' + tag.find('.//a[@property="url"]').attrib['href']
	}
	#get thumbnail if exist
	if ('src' in tag.find('.//img[@property="image"]').attrib):
		detail['thumb_url'] = tag.find('.//img[@property="image"]').attrib['src']
	#check if the event existed in db
	existed_sql = 'SELECT _id FROM ico WHERE title="'+str(detail['title'])+'" AND original_url="'+str(detail['original_url'])+'"'
	cursor.execute(existed_sql)
	if (cursor.rowcount == 0):
		#not existed, insert to DB
		insert_sql = ('INSERT INTO ico (title,thumb_url,type,excerpt,original_url,minor_title) '+
			'VALUES (%(title)s,%(thumb_url)s,%(type)s,%(excerpt)s,%(original_url)s,%(minor_title)s)')
		cursor.execute(insert_sql, detail)
		myConnection.commit()

myConnection.close()
