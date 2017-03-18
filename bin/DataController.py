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
from bs4 import BeautifulSoup
from src.DataController import DataController

class DataController(DataController):
	def start(self, input_queue):
		classifications = [
			('砂拉越', 3),
			('沙巴', 8),
			('西马', 11),
			('汶莱', 10),
			('国际', 12),
			('体育', 13),
			('娱乐', 15),
			('科技', 14),
			('健康', 23),
			('新奇', 16),
			('财经', 18),
			('评论', 27),
			('综合', 21)
		]

		for classification, model in classifications:
			input_queue.put_nowait(Request(
				url = 'http://news.seehua.com/?cat=%d' % model,
				classification = classification,
				success = self.news_list,
				model = model,
				page = 1,
				data = {
					'classification': classification,
					'source_id': 31,
					'language': 'chi'
				}
			))

	def news_list(self, response, input_queue):
		logging.info('[+] get %d news list: %s' % (response.page, response.url))
		soup = BeautifulSoup(response.text, 'lxml')
		for news in soup('article', 'item-list'):
			data = response.data.copy()
			data.update({
				'request_url': urljoin(response.url, news.find('a').get('href')),
				'title': news.find('a').text,
				'pub_time': news.find('span', 'tie-date').text,
				'abstract': news.find('div', 'entry').find('p').text,
			})
			input_queue.put_nowait(Request(
				url = data['request_url'],
				success = self.news,
				data = data
			))
		response.page += 1
		response.url = 'http://news.seehua.com/?cat=%s&paged=%d' % (response.model, response.page)
		input_queue.put_nowait(response)
		
	def news(self, response, input_queue):
		logging.info('[+] get news: %s' % response.url)
		soup = BeautifulSoup(response.text, 'lxml')
		body = soup.find('div', 'entry')
		share = body.find('div', 'share-post')
		comment = body.find('div', id="wpdevar_comment_1")
		if share:
			share.decompose()
		if comment:
			comment.decompose()
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
		path = 'data/31_chi/%d.json' % self.count
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
		matches = re.search(u'(\d{2,4})年(\d{1,2})月(\d{1,2})日', self.data['pub_time'])
		self.data['pub_time'] = '%s-%s-%s 00:00:00' % matches.groups()

	def text_handle(self, string):
		string = re.sub(r'<script( .*?|)>[\w\W]*?</script>', '', string)
		string = re.sub(r'<\/?(p|div|li|ul)( .*?|)>', '\n', string)
		string = re.sub(r'<!--[\w\W]*?-->|<.*?>', '', string)
		string = re.sub(r'\s*\n\s*', '\n', string).strip()
		return HTMLParser().unescape(string)


		





