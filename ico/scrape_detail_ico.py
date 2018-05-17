#http://lxml.de/lxmlhtml.html
#author: Martin SangDo
from lxml import html

import const
import json
import requests
import time
import MySQLdb

source_url = 'https://topicolist.com/ico/vernam'
page = requests.get(source_url, headers=const.REQUEST_HEADER)
# print page.content
tree = html.fromstring(page.content)

myConnection = MySQLdb.connect(host=const.HOSTNAME, user=const.USERNAME, passwd=const.PASSWORD, db=const.DATABASE, use_unicode=True, charset="utf8")
cursor = myConnection.cursor()
ico_detail = {
	'ico_id': 1
}
#get main content
main_content = tree.findall('.//main[@class="ico-left-column"]')
for tag in main_content:
	ico_detail['main_content'] = ''.join([html.tostring(child) for child in tag.iterdescendants()])
#get minor content (review)
minor_content = tree.findall('.//aside[@class="ico-sidebar div-block-36"]')
for tag in minor_content:
	ico_detail['minor_content'] = ''.join([html.tostring(child) for child in tag.iterdescendants()])

#insert into DB
insert_sql = ('INSERT INTO ico_detail (ico_id,main_content,minor_content) '+
	'VALUES (%(ico_id)s,%(main_content)s,%(minor_content)s)')
cursor.execute(insert_sql, ico_detail)
myConnection.commit()

myConnection.close()
