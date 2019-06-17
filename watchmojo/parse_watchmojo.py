from selenium import webdriver
# Option 1 - with ChromeOptions
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox') # required when running as root user. otherwise you would get no sandbox errors.
driver = webdriver.Chrome(executable_path='/Users/sangdt/Downloads/SetupApps/python/chromedriver', options=chrome_options)
driver.get('https://watchmojo.com/video/id/28413')
# tags = []
# tags = driver.find_elements_by_class_name('owl-item')
# for tag in tags:
#     print(tag.text)
video = driver.find_element_by_id('videoplay')
print(video)
