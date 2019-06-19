import const_mojo
from selenium import webdriver
import mysql.connector
import datetime
import html2text

def get_unparsed_videos(conn):
	cur = conn.cursor()
	sql = 'SELECT original_id FROM tbl_video WHERE is_parsed_detail=0 ORDER BY updated_time ASC LIMIT '+str(const_mojo.VID_PARSE_NUM)
	cur.execute(sql)
	return cur.fetchmany(const_mojo.VID_PARSE_NUM)

print(datetime.datetime.now())
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox') # required when running as root user. otherwise you would get no sandbox errors.
driver = webdriver.Chrome(executable_path=const_mojo.CHROME_DRIVER, options=chrome_options)
#
#connect db
db_config = {
  'user': const_mojo.USERNAME,
  'password': const_mojo.PASSWORD,
  'host': const_mojo.HOSTNAME,
  'port': const_mojo.PORT,
  'database': const_mojo.DATABASE,
  'raise_on_warnings': True
}
#init connection to db
cnx = mysql.connector.connect(**db_config)
parsing_videos = get_unparsed_videos(cnx)
# print(len(parsing_videos))
#parse each page
for video in parsing_videos:
	page_url = const_mojo.DOMAIN + 'video/id/' + str(video[0])
	driver.get(page_url)
	# print(page_url)
	video_link = ''
	vid_type = ''
	try:
		vid_youtube = driver.find_element_by_id('player')
		video_link = vid_youtube.get_attribute('src')
		vid_type = 'youtube'
	except:
		vid_dailymotion = driver.find_element_by_xpath("//iframe[@class='resp-iframe']")
		video_link = vid_dailymotion.get_attribute('src')
		vid_type = 'dailymotion'
	finally:
		#parsed detail of this page
		print('parsing : ' + page_url)
		description = driver.find_element_by_id('transcript').get_attribute('innerHTML').strip().replace('<br>', '<br/>')
		#related videos
		related_video_tags = driver.find_element_by_xpath("//div[@id='owl-demo1']").find_elements_by_class_name('item')
		rel_original_video_ids = []
		for item in related_video_tags:
			a_tag = item.find_element_by_tag_name('a')
			#split to get original video id
			a_terms = [x.strip() for x in a_tag.get_attribute('href').split('/')]
			rel_original_video_ids.append(a_terms[len(a_terms)-1])
		related_vid_ids = ','.join(rel_original_video_ids)
		#author info
		author_link = driver.find_element_by_xpath("//span[@class='credits']/a[1]")
		author_name = html2text.html2text(author_link.get_attribute('innerHTML')).strip()
		#related_blog_ids
		related_blog_tags = driver.find_element_by_xpath("//div[@id='owl-demo-blog']").find_elements_by_class_name('item')
		rel_original_blog_href = []
		for item in related_blog_tags:
			a_tag = item.find_element_by_tag_name('a')
			rel_original_blog_href.append(a_tag.get_attribute('href').replace('https://watchmojo.com/blog/',''))
		related_blog_urls = ','.join(rel_original_blog_href)
		if (video_link is ''):
			is_non_video = 1
		else:
			is_non_video = 0
		#update to db
		cursor = cnx.cursor(buffered=True)
		update_sql = ('UPDATE tbl_video SET is_active=%s,video_link=%s,description=%s,related_vid_ids=%s,author_info=%s,type=%s,is_non_video=%s,is_parsed_detail=%s,related_blog_urls=%s '+
			'WHERE original_id='+str(video[0]))
		cursor.execute(update_sql, (1, video_link, description, related_vid_ids, author_name, vid_type, is_non_video, 1, related_blog_urls))
		cnx.commit()
print(datetime.datetime.now())
cnx.close()
