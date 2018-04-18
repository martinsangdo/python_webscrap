#http://lxml.de/lxmlhtml.html
from lxml import html
# https://github.com/Anorov/cloudflare-scrape
import json
import requests
import time
import cfscrape

scraper = cfscrape.create_scraper()  # returns a CloudflareScraper instance
# Or: scraper = cfscrape.CloudflareScraper()  # CloudflareScraper inherits from requests.Session
print scraper.get("https://www.coindesk.com/wp-json/wp/v2/posts").content
