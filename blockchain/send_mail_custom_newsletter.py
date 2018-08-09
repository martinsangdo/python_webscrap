#author: Martin sangdo
#select articles to send based on custom newsletter
#!/usr/bin/env python

import smtplib
import const
import MySQLdb

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

#get valid newsletter (paid & not expired)
def getValidNewsletters(cursor):
	condition = 'payment_status="Completed" AND (title_keywords <> "" OR excerpt_keywords <> "" OR content_keywords <> "") AND '\
			'is_unsubscribed = 0 AND DATEDIFF(NOW(), last_payment_time) <= 365'
	sql = 'SELECT _id,email,title_keywords,excerpt_keywords,content_keywords,empty_data_send_num FROM newsletter_custom WHERE ' + condition
	# print sql
	cursor.execute(sql)
	return cursor.fetchall()
#compose query string based on keywords
def composeQueryString(field, keywords):
	condition_arr = []
	if (keywords is not None and keywords != ''):
		key_arr = keywords.split(',')
		for key in key_arr:
			condition_arr.append(field+' LIKE "% '+key.strip()+'"')
			condition_arr.append(field+' LIKE "'+key.strip()+' %"')
			condition_arr.append(field+' LIKE "% '+key.strip()+' %"')
	return ' OR '.join(condition_arr)
#select articles based on conditions
def getArticlesBasedOnQuery(cursor, condition, limit):
	sql = 'SELECT _id,thumb_url,slug,title,excerpt FROM block_content WHERE status = 1 AND DATEDIFF(NOW(), update_time) < 7 AND ' + condition + ' ORDER BY update_time DESC LIMIT 0,'+str(limit)
	cursor.execute(sql)
	return cursor.fetchall()
#get articles involving to keywords
#RULES:
#1) If keyword appears in title, get it immediatedly
#2) If keyword is not in title, excerpt or content must have (appear 3 times at least in content)
def getRelatedArticles(title_keywords,excerpt_keywords,content_keywords,article_num):
	#compose query condition of each fields
	title_cond = composeQueryString('title', title_keywords)
	if (title_cond != ''):
		articles_titles = getArticlesBasedOnQuery(cursor, '('+title_cond+')', const.PER_PAGE)
		if (len(articles_titles) < int(const.PER_PAGE)):
			#get list of _in in articles searched by title keywords
			id_list = []
			for one_article in articles_titles:
				id_list.append(str(one_article[0]))
			#not enough articles, let search more in excerpt & content
			minor_key_cond = []
			excerpt_cond = composeQueryString('excerpt', excerpt_keywords)	#condition to search in excerpt
			if (excerpt_cond != ''):
				minor_key_cond.append('('+excerpt_cond+')')
			content_cond = composeQueryString('content', content_keywords)	#condition to search in content
			if (content_cond != ''):
				minor_key_cond.append('('+content_cond+')')
			minor_cond = ' AND '.join(minor_key_cond)
			if (len(id_list) > 0):
				minor_cond += ' AND _id NOT IN ('+','.join(id_list)+')'		#reject those ids
			extra_articles = None
			if (minor_cond != ''):
				extra_articles = getArticlesBasedOnQuery(cursor, minor_cond, int(const.PER_PAGE) - len(articles_titles))
			#send mail to user
			for one_article in articles_titles:
				print one_article[3]
			if (extra_articles is not None):
				for one_article in extra_articles:
					print one_article[3]
		# else:
			#enough articles, send mail to user

	#

	# condition = ''

#begin
myConnection = MySQLdb.connect(host=const.HOSTNAME, user=const.USERNAME, passwd=const.PASSWORD, db=const.DATABASE, use_unicode=True, charset="utf8")
cursor = myConnection.cursor()
#get custom newsletters need to be sent
sent_newsletters = getValidNewsletters(cursor)
#traverse each newsletter to get condition
# print sent_newsletters
for newsletter in sent_newsletters:
	articles = getRelatedArticles(newsletter[2],newsletter[3],newsletter[4],newsletter[5])
