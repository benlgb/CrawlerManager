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
		classifications = ['news', 'business', 'tech', 'culture', 'opinion']
		for classification in classifications:
			input_queue.put_nowait(Request(
				url = 'http://www.ibtimes.com.cn/archives/articles/categories/%s/' % classification,
				success = self.news_list,
				data = {
					'classification': classification,
					'source_id': 10,
					'language': 'chi'
				}
			))
	
	def news_list(self, response, input_queue):
		logging.info('[+] get news list: %s' % response.url)
		soup = BeautifulSoup(response.text)
		for news in soup('li', 'list-style'):
			data = response.data.copy()
			img = news.find('img')
			data.update({
				'request_url': urljoin(response.url, news.find('a').get('href')),
				'title': news.find('div', 'title').text,
				'pub_time': news.find('div', 'timedate').text,
				'abstract': news.find('div', 'summary').text,
				'images': [img.get('src')] if img else []
			})
			input_queue.put_nowait(Request(
				url = data['request_url'],
				success = self.news,
				data = data
			))
		next_page = soup.find('li', 'pager-next')
		if next_page:
			next_page = next_page.find('a').get('href')
			response.url = urljoin(response.url, next_page)
			input_queue.put_nowait(response)
		
	def news(self, response, input_queue):
		logging.info('[+] get news: %s' % response.url)
		soup = BeautifulSoup(response.text)
		response.data.update({
			'response_url': response.response.url,
			'title': soup.find('div', 'title-header').find('div', 'title').text,
			'pub_time': soup.find('p', 'timestamp').text,
			'body': soup('div', 'enlarge-font'),
			'cole_time': time.time(),
			'out_links': soup('a')
		})
		self.save(response.data)

	def save(self, data):
		self.count = getattr(self, 'count', 0) + 1
		data = Statictis(data).filter()
		data.news_id = self.count
		path = 'data/%d.json' % self.count
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
		self.title()
		return self.data

	def out_links(self):
		out_links = []
		for link in self.data['out_links']:
			link = link.get('href')
			if link is not None:
				out_links.append(link)
		self.data['out_links'] = out_links

	def body(self):
		body = '\n'.join([str(body) for body in self.data['body']])
		self.data['body'] = self.text_handle(body)

	def abstract(self):
		self.data['abstract'] = self.text_handle(self.data['abstract'])

	def title(self):
		self.data['title'] = self.text_handle(self.data['title'])

	def pub_time(self):
		matches = re.search(r'(\d{2,4}).(\d{1,2}).(\d{1,2}).*?(\d{1,2}):(\d{1,2})', self.data['pub_time'])
		self.data['pub_time'] = '%s-%s-%s %s:%s:00' % matches.groups()

	def text_handle(self, string):
		string = re.sub(r'<script( .*?|)>[\w\W]*?</script>', '', string)
		string = re.sub(r'<\/?(p|div|li|ul)( .*?|)>', '\n', string)
		string = re.sub(r'<!--[\w\W]*?-->|<.*?>', '', string)
		string = re.sub(r'\s*\n\s*', '\n', string).strip()
		return HTMLParser().unescape(string)


		





