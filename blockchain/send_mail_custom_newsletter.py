#author: Martin sangdo
#select articles to send based on custom newsletter
#!/usr/bin/env python

import smtplib
import const
import MySQLdb

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def getValidNewsletters(cursor):
	condition = 'payment_status="Completed" AND (title_keywords <> "" OR excerpt_keywords <> "" OR content_keywords <> "") AND '\
			'is_unsubscribed = 0 AND DATEDIFF(NOW(), last_payment_time) <= 365'
	sql = 'SELECT _id,email,title_keywords,excerpt_keywords,content_keywords,empty_data_send_num FROM newsletter_custom WHERE ' + condition
	# print sql
	cursor.execute(sql)
	return cursor.fetchall()
#begin
myConnection = MySQLdb.connect(host=const.HOSTNAME, user=const.USERNAME, passwd=const.PASSWORD, db=const.DATABASE, use_unicode=True, charset="utf8")
cursor = myConnection.cursor()
#get custom newsletters need to be sent
sent_newsletters = getValidNewsletters(cursor)
#traverse each newsletter to get condition
