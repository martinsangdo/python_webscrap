#get all updated videos by category, not parse each video detail yet
import const_mojo
import mysql.connector
from selenium import webdriver
import sys
import html2text

def getCategoryInfo(conn, cat_id):
	cur = conn.cursor()
	sql = 'SELECT slug FROM tbl_category WHERE is_active=1 AND id='+cat_id
	cur.execute(sql)
	row = cur.fetchone()
	return row

# Option 1 - with ChromeOptions
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox') # required when running as root user. otherwise you would get no sandbox errors.
driver = webdriver.Chrome(executable_path=const_mojo.CHROME_DRIVER, options=chrome_options)
#get category id
if (len(sys.argv) == 1):	#empty parameter
	sys.exit()
category_id = sys.argv[1]
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
cat_info = getCategoryInfo(cnx, category_id)
if (cat_info is None):
    sys.exit()

# begin parse page
driver.get(const_mojo.DOMAIN+'categories/'+cat_info[0]+'/1')
tags = []
vid_items = driver.find_elements_by_class_name('item')
#
# print(len(vid_items))
# print('-----')
# print (html2text.html2text(vid_items[1].find_element_by_class_name('hptitle').get_attribute('innerHTML')))
# print('-----')
# print (html2text.html2text(vid_items[3].find_element_by_class_name('hptitle').get_attribute('innerHTML')))
# print (vid_items[3].text)
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
		insert_sql = ('INSERT INTO tbl_video (title, thumbnail_url, original_id, category_id, published_date) '+
			'VALUES (%(title)s,%(thumbnail_url)s,%(original_id)s,%(category_id)s, %(published_date)s)')
		vid_detail = {
			'title': title,
			'thumbnail_url': img_tag.get_attribute('src'),
			'original_id': original_video_id,
			'category_id': category_id,
			'published_date': published_date
		}
		cursor.execute(insert_sql, vid_detail)
		cnx.commit()

cnx.close()
