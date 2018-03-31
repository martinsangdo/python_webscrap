#http://lxml.de/lxmlhtml.html
from lxml import html
import requests

page = requests.get('http://www.ign.com/videos', headers={'User-Agent': 'Mozilla/5.0'})
# print page.content
tree = html.fromstring(page.content)

# items = tree.xpath('//a[@class="grid_4 alpha"]/text()')
hrefs = [a.attrib['href'] for a in tree.xpath('//a[@class="grid_4 alpha"]')]

print 'Items: ', hrefs


# This is probably because of mod_security or some similar server security feature which blocks known spider/bot user agents (urllib uses something like python urllib/3.3.0, it's easily detected). Try setting a known browser user agent with:

# from urllib.request import Request, urlopen
# 
# req = Request('http://www.ign.com/videos', headers={'User-Agent': 'Mozilla/5.0'})
# webpage = urlopen(req).read()
# print webpage.content
# tree = html.fromstring(page.content)
