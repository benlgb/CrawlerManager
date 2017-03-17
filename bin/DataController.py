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
	def start (self, input_queue):
		with open('1.json') as f:
			keywords = json.load(f)
		for keyword in keywords:
			input_queue.put_nowait(Request(
				url = 'https://twitter.com/i/search/timeline',
				success = self.twitters,
				keyword = keyword,
				args = {
					'params': {
						'vertical': 'default',
						'q': keyword,
						'src': 'typd',
						'max_position': '',
						'reset_error_state': False
					}
				}
			))

	def twitters(self, response, input_queue):
		index = 0
		data = response.json()
		soup = BeautifulSoup(data['items_html'], 'lxml')
		ids = response.ids = response.get('ids', [])
		twitters = response.twitters = response.get('twitters', [])
		for item in soup('li', 'stream-item'):
			index += 1
			tweet = item.find('div', 'tweet')
			content = tweet.find('div', 'js-tweet-text-container')
			footer = tweet.find('div', 'ProfileTweet-actionCountList')
			media = tweet.find('div', 'AdaptiveMediaOuterContainer')
			if tweet.get('data-tweet-id') in ids:
				print '[-] find repeat id'
				continue
			twitters.append({
				'id': tweet.get('data-tweet-id'),
				'content': self.content_fixed(content),
				'publish_time': tweet.find('span', '_timestamp').get('data-time'),
				'reply_count': int(footer.find('span', 'ProfileTweet-action--reply').find(
					'span', 'ProfileTweet-actionCount').get('data-tweet-stat-count')),
				'retweet_count': int(footer.find('span', 'ProfileTweet-action--retweet').find(
					'span', 'ProfileTweet-actionCount').get('data-tweet-stat-count')),
				'favorite_count': int(footer.find('span', 'ProfileTweet-action--favorite').find(
					'span', 'ProfileTweet-actionCount').get('data-tweet-stat-count')),
				'ilustris': [img.get('src') for img in media('img')] if media else [],
				'author': {
					'id': tweet.get('data-user-id'),
					'nickname': tweet.get('data-name'),
					'username': tweet.get('data-screen-name'),
					'avatar': tweet.find('img').get('src')
				},
			})
			ids.append(tweet.get('data-tweet-id'))
		print ('[+] get %s twitters: %d' % (response.keyword, len(twitters))).encode('gbk')
		if index == 0:
			response.zero_times = response.get('zero_times', 0) + 1
		else:
			response.zero_times = 0
		if len(twitters) >= 1000 or response.zero_times > 5:
			self.save_twitter(twitters, response.keyword)
		else:
			response.args['params']['max_position'] = data['min_position']
			gevent.sleep(1)
			input_queue.put_nowait(response)

	def save_twitter(self, twitters, keyword):
		print '[+] save twitters'
		with open(u'data/%s.json' % keyword, 'w+') as f:
			json.dump({
				'count': len(twitters),
				'keyword': keyword,
				'twitters': twitters
			}, f, indent=4)

	def content_fixed(self, content):
		a = content.find('a')
		for a in content('a'):
			a.string = ' %s' % a.text
		return content.getText()