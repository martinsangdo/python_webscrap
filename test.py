import re

str = 'hello bitcoin litecoin bing ...'
m = re.search('bitd|bin|lite', str)
print m is not None     #found
