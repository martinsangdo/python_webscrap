#http://lxml.de/lxmlhtml.html
from lxml import html

import json
import requests
import time

# page = requests.get('http://www.ign.com/videos', headers={'User-Agent': 'Mozilla/5.0'})
# page = requests.get('https://www.eurogamer.net/archive/news', headers={'User-Agent': 'Mozilla/5.0'})
page = ''
while page == '':
    try:
        page = requests.get('https://www.eurogamer.net/archive/news', headers={'User-Agent': 'Mozilla/5.0'})
        break
    except:
        time.sleep(5)
        print 'wake up'
        continue
# print page.content
tree = html.fromstring(page.content)

tags = tree.xpath('//h2[@class="title"]')
#     app = tree.xpath("//div[@class='column first']/ul/li/a/@href")

# src = [tag.attrib['data-settings'] for tag in tree.xpath('//li[@class="video-embed-content-v6"]')]

# tag = tree.find_class('video-embed-# content-v6')
# j = json.loads(tag[0].attrib['data-settings'])

for tag in tags:
	print tag.text_content()

# print items


# This is probably because of mod_security or some similar server security feature which blocks known spider/bot user agents (urllib uses something like python urllib/3.3.0, it's easily detected). Try setting a known browser user agent with:

# from urllib.request import Request, urlopen
# 
# req = Request('http://www.ign.com/videos', headers={'User-Agent': 'Mozilla/5.0'})
# webpage = urlopen(req).read()
# print webpage.content
# tree = html.fromstring(page.content)
