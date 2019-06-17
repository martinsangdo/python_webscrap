#get all updated videos by category/channels, not parse each video detail yet
import const_mojo
import mysql.connector
from selenium import webdriver
import sys
import html2text

def getCategoryInfo(conn, group_type, group_id):
	cur = conn.cursor()
	if (group_type == const_mojo.CAT_TYPE):
		sql = 'SELECT slug FROM tbl_category WHERE is_active=1 AND id='+group_id
	else:
		sql = 'SELECT slug FROM tbl_channel WHERE is_active=1 AND id='+group_id
	cur.execute(sql)
	row = cur.fetchone()
	return row

# Option 1 - with ChromeOptions
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox') # required when running as root user. otherwise you would get no sandbox errors.
driver = webdriver.Chrome(executable_path=const_mojo.CHROME_DRIVER, options=chrome_options)
#get category id
if (len(sys.argv) < 3):	#empty parameter
	sys.exit()
group_id = sys.argv[1]		#category or channel id
group_type = sys.argv[2]	#category or channel
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
group_info = getCategoryInfo(cnx, group_type, group_id)
if (group_info is None):	#not found
    sys.exit()

# begin parse page
if (group_type == const_mojo.CAT_TYPE):
	driver.get(const_mojo.DOMAIN+'categories/'+group_info[0])
else:
	driver.get(const_mojo.DOMAIN+group_info[0])
tags = []
vid_items = driver.find_elements_by_class_name('item')
#begin parse each video item
for item in vid_items:
	a_tag = item.find_elements_by_tag_name('a')[0]
	#split to get original video id
	a_terms = [x.strip() for x in a_tag.get_attribute('href').split('/')]
	original_video_id = a_terms[len(a_terms)-1]
	#thumbnail url
	img_tag = item.find_elements_by_tag_name('img')[0]
    #title
	title = html2text.html2text(item.find_element_by_class_name('hptitle').get_attribute('innerHTML'))
	published_date = item.find_element_by_class_name('hpdate').text
	#check if the video existed in db
	cursor = cnx.cursor(buffered=True)
	existed_sql = 'SELECT id FROM tbl_video WHERE original_id='+original_video_id
	cursor.execute(existed_sql)
	if (cursor.rowcount > 0):
		#existed, update title & thumbnail if changed to DB
		update_sql = ('UPDATE tbl_video SET title=%s,thumbnail_url=%s,published_date=%s WHERE original_id='+original_video_id)
		cursor.execute(update_sql, (title, img_tag.get_attribute('src'), published_date))
		cnx.commit()
	else:
		#insert new one
		if (group_type == const_mojo.CAT_TYPE):
			insert_sql = ('INSERT INTO tbl_video (title, thumbnail_url, original_id, category_id, published_date) '+
				'VALUES (%(title)s,%(thumbnail_url)s,%(original_id)s,%(category_id)s, %(published_date)s)')
			vid_detail = {
				'title': title,
				'thumbnail_url': img_tag.get_attribute('src'),
				'original_id': original_video_id,
				'category_id': group_id,
				'published_date': published_date
			}
		else:
			insert_sql = ('INSERT INTO tbl_video (title, thumbnail_url, original_id, channel_id, published_date) '+
				'VALUES (%(title)s,%(thumbnail_url)s,%(original_id)s,%(channel_id)s, %(published_date)s)')
			vid_detail = {
				'title': title,
				'thumbnail_url': img_tag.get_attribute('src'),
				'original_id': original_video_id,
				'channel_id': group_id,
				'published_date': published_date
			}
		cursor.execute(insert_sql, vid_detail)
		cnx.commit()

cnx.close()
