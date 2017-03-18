# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import time
import gevent
import logging
from urlparse import urljoin
from src.Request import Request
from HTMLParser import HTMLParser
from BeautifulSoup import BeautifulSoup
from src.DataController import DataController

class DataController(DataController):
	def start(self, input_queue):
		classifications = [
			('新闻', '2013-09-08-02-08-40'),
			('副刊', '2013-09-09-13-07-36'),
			('大声公', '2013-09-09-13-16-53'),
			('评论', '2013-09-09-13-17-28'),
			('生活的事', '2013-09-09-13-17-55')
		]

		for classification, model in classifications:
			input_queue.put_nowait(Request(
				url = 'http://intimes.com.my/index.php/%s' % model,
				classification = classification,
				success = self.news_list,
				model = model,
				page = 0,
				data = {
					'classification': classification,
					'source_id': 28,
					'language': 'chi'
				}
			))

	def news_list(self, response, input_queue):
		logging.info('[+] get %d news list: %s' % (response.page + 1, response.url))
		soup = BeautifulSoup(response.text)
		count = 0
		for news in soup('div', 'itemContainer'):
			data = response.data.copy()
			img = news.find('img')
			data.update({
				'request_url': urljoin(response.url, news.find('a').get('href')),
				'title': news.find('a').text,
				'pub_time': news.find('time').get('datetime'),
				'abstract': str(news.find('div', 'itemIntroText')),
				'images': [img.get('src')] if img else []
			})
			input_queue.put_nowait(Request(
				url = data['request_url'],
				success = self.news,
				data = data
			))
			count += 1
		if count > 0:
			model = response.model
			page = response.page = response.page + 1
			response.url = 'http://intimes.com.my/index.php/%s?start=%d' % (model, 10 * page)
			input_queue.put_nowait(response)
		
	def news(self, response, input_queue):
		logging.info('[+] get news: %s' % response.url)
		soup = BeautifulSoup(response.text)
		body = soup.find('div', 'itemBody')
		joom = body.find('div', id="joomsharebar")
		if joom:
			joom.decompose()
		response.data.update({
			'response_url': response.response.url,
			'body': str(body),
			'cole_time': time.time(),
			'out_links': soup('a')
		})
		self.save(response.data)

	def save(self, data):
		self.count = getattr(self, 'count', 0) + 1
		data = Statictis(data).filter()
		data.news_id = self.count
		path = 'data/28_chi/%d.json' % self.count
		with open(path, 'w+') as f:
			json.dump(data, f, indent=4)
		logging.info('[+] save news: %d' % self.count)

class Statictis(object):
	def __init__(self, data):
		self.data = data

	def filter(self):
		self.pub_time()
		self.out_links()
		self.body()
		self.abstract()
		return self.data

	def out_links(self):
		out_links = []
		for link in self.data['out_links']:
			link = link.get('href')
			if link is not None:
				out_links.append(link)
		self.data['out_links'] = out_links

	def body(self):
		self.data['body'] = self.text_handle(self.data['body'])

	def abstract(self):
		self.data['abstract'] = self.text_handle(self.data['abstract'])

	def title(self):
		self.data['title'] = self.text_handle(self.data['title'])

	def pub_time(self):
		matches = re.search(r'(\d{2,4})-(\d{1,2})-(\d{1,2})T(\d{1,2}):(\d{1,2}):(\d{1,2})', self.data['pub_time'])
		self.data['pub_time'] = '%s-%s-%s %s:%s:%s' % matches.groups()

	def text_handle(self, string):
		string = re.sub(r'<script( .*?|)>[\w\W]*?</script>', '', string)
		string = re.sub(r'<\/?(p|div|li|ul)( .*?|)>', '\n', string)
		string = re.sub(r'<!--[\w\W]*?-->|<.*?>', '', string)
		string = re.sub(r'\s*\n\s*', '\n', string).strip()
		return HTMLParser().unescape(string)


		





