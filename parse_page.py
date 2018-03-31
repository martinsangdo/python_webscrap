#http://lxml.de/lxmlhtml.html
from lxml import html

import json
import requests

# page = requests.get('http://www.ign.com/videos', headers={'User-Agent': 'Mozilla/5.0'})
page = requests.get('http://www.ign.com/videos/2018/04/01/are-x-men-console-games-dead', headers={'User-Agent': 'Mozilla/5.0'})

# print page.content
tree = html.fromstring(page.content)

# items = tree.xpath('//a[@class="grid_4 alpha"]/text()')
# src = [tag.attrib['data-settings'] for tag in tree.xpath('//div[@class="video-embed-content-v6"]')]

tag = tree.find_class('video-embed-content-v6')
j = json.loads(tag[0].attrib['data-settings'])

print j['video']['assetsByHeight']


# This is probably because of mod_security or some similar server security feature which blocks known spider/bot user agents (urllib uses something like python urllib/3.3.0, it's easily detected). Try setting a known browser user agent with:

# from urllib.request import Request, urlopen
# 
# req = Request('http://www.ign.com/videos', headers={'User-Agent': 'Mozilla/5.0'})
# webpage = urlopen(req).read()
# print webpage.content
# tree = html.fromstring(page.content)
