from selenium import webdriver
# Option 1 - with ChromeOptions
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox') # required when running as root user. otherwise you would get no sandbox errors.
driver = webdriver.Chrome(executable_path='/Users/sangdt/Downloads/SetupApps/python/chromedriver', options=chrome_options)
driver.get('https://watchmojo.com/categories/music/1')
tags = []
tags = driver.find_elements_by_class_name('owl-item')
print (len(tags))
# for tag in tags:
#     print(tag.text)
