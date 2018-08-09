#author: Martin sangdo
#select articles to send based on custom newsletter
#!/usr/bin/env python

import smtplib
import const
import mail_const
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
#select articles based on conditions (and valid & limit in 1 week)
def getArticlesBasedOnQuery(cursor, condition, limit):
	sql = 'SELECT _id,thumb_url,slug,title,excerpt FROM block_content WHERE status = 1 AND DATEDIFF(NOW(), update_time) < 7 AND ' + condition + ' ORDER BY update_time DESC LIMIT 0,'+str(limit)
	cursor.execute(sql)
	return cursor.fetchall()
#search articles based on keywords in excerpt & content
def getArticlesBasedOnContent(cursor, excerpt_keywords, content_keywords, reject_id_list, limit):
	minor_key_cond = []
	excerpt_cond = composeQueryString('excerpt', excerpt_keywords)	#condition to search in excerpt
	if (excerpt_cond != ''):
		minor_key_cond.append('('+excerpt_cond+')')
	content_cond = composeQueryString('content', content_keywords)	#condition to search in content
	if (content_cond != ''):
		minor_key_cond.append('('+content_cond+')')
	minor_cond = ' AND '.join(minor_key_cond)
	if (len(reject_id_list) > 0):
		minor_cond += ' AND _id NOT IN ('+','.join(reject_id_list)+')'		#reject those ids
	extra_articles = None
	if (minor_cond != ''):
		extra_articles = getArticlesBasedOnQuery(cursor, minor_cond, limit)
	return extra_articles
#get articles involving to keywords
#RULES:
#1) If keyword appears in title, get it immediatedly
#2) If keyword is not in title, excerpt or content must have (appear 3 times at least in content)
def getRelatedArticles(title_keywords,excerpt_keywords,content_keywords,article_num):
	articles_2_send = []
	#compose query condition of each fields
	title_cond = composeQueryString('title', title_keywords)
	if (title_cond != ''):
		articles_titles = getArticlesBasedOnQuery(cursor, '('+title_cond+')', mail_const.PER_PAGE)
		if (len(articles_titles) < mail_const.PER_PAGE):	#not enough articles, let search more in excerpt & content
			#get list of _in in articles searched by title keywords
			id_list = []
			for one_article in articles_titles:
				id_list.append(str(one_article[0]))
			#make query to search in excerpt and content
			extra_articles = getArticlesBasedOnContent(cursor, excerpt_keywords, content_keywords, id_list, mail_const.PER_PAGE - len(articles_titles))
			#send mail to user
			for one_article in articles_titles:
				articles_2_send.append(one_article)
			if (extra_articles is not None):
				for one_article in extra_articles:
					articles_2_send.append(one_article)
		else:	#enough articles
			for one_article in articles_titles:
				articles_2_send.append(one_article)
	else:	#there is no condition of title keywords, let search in excerpt & content
		extra_articles = getArticlesBasedOnContent(cursor, excerpt_keywords, content_keywords, [], const.PER_PAGE)
		for one_article in extra_articles:
			articles_2_send.append(one_article)
	return articles_2_send
#send bunch of mails
def sendMailBatch(mail_contents):
	#configure email
	msg = MIMEMultipart('alternative')
	msg['Subject'] = mail_const.CUSTOM_NEWS_SUBJECT
	msg['From'] = mail_const.NEWS_MAIL_FROM_NAME
	#login credential
	s = smtplib.SMTP(mail_const.SMTP_HOSTNAME, mail_const.SMTP_POST)
	s.login(mail_const.NEWS_MAIL_FROM, mail_const.NEWS_MAIL_FROM_PASSWORD)
	#put mail content here
	for email in mail_contents:
		part2 = MIMEText(mail_contents[email].encode("utf-8"), 'html', 'UTF-8')
		msg.attach(part2)
		s.sendmail(mail_const.NEWS_MAIL_FROM, email, msg.as_string())
	s.quit()
########## BEGIN
myConnection = MySQLdb.connect(host=const.HOSTNAME, user=const.USERNAME, passwd=const.PASSWORD, db=const.DATABASE, use_unicode=True, charset="utf8")
cursor = myConnection.cursor()
#get custom newsletters need to be sent
sent_newsletters = getValidNewsletters(cursor)
#traverse each newsletter to get condition
if (len(sent_newsletters) > 0):
	mails_html = {}		#all mails need to send
	#found newsletter to send
	for newsletter in sent_newsletters:
		articles_2_send = getRelatedArticles(newsletter[2],newsletter[3],newsletter[4],newsletter[5])
		if (len(articles_2_send) > 0):
			#has articles to send
			html_items = []
			for one_article in articles_2_send:
				item_html = mail_const.CUSTOM_NEWS_HTML_SMALL_ITEM_TMPL.replace('%slug_url%', mail_const.NEWS_LINK_PREFIX+one_article[2])
				item_html = item_html.replace('%thumb_url%', one_article[1])
				item_html = item_html.replace('%title%', one_article[3])
				item_html = item_html.replace('%excerpt%', one_article[4])
				html_items.append(item_html);
			mails_html[newsletter[1]] = mail_const.CUSTOM_NEWS_HTML_PREFIX + ''.join(html_items) + mail_const.CUSTOM_NEWS_HTML_POSTFIX
	# print mails_html
	sendMailBatch(mails_html)
