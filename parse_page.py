from lxml import html
import requests

page = requests.get('http://www.ign.com/videos')
tree = html.fromstring(page.content)

items = tree.xpath('//a[@class="grid_4 alpha"]/text()')

print 'Items: ', items