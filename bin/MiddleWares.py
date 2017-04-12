# -*- coding: utf-8 -*-

import time
import gevent
import logging
import requests
from src import MiddleWare
from src.Request import Request
from requests_oauthlib import OAuth1

# 默认请求头
HEADERS = {
	'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.75 Safari/537.36'
}

# 超时时间
TIMEOUT = 10

# 最高重复请求数
MAX_REPEAT_TIMES = 5

# 翻墙代理
PROXIES = {
	'http': 'http://127.0.0.1',
	'https': 'https://127.0.0.1'
}

# 最短访问间隔
LIMIT = 0.25

# 身份认证
APPS = [{
	'consumer_key': '7cjhj2oyEv1CAkcQ414Qx4WmC',
	'consumer_secret': 'UkVBF1OKaMRomJyGnQDHti9B6MC9gNhPNuAD4zSNiPS8ip7f9b',
	'access_token_key': '831032425241206784-61gKvbULqvYCawcPDTWFfuZnWz5NNM3',
	'access_token_secret': 'C1seiGpSzGayEicUuJDGQZJdcHKns59KHne4SHcyalKjk'
}, {
	'consumer_key': 'FW7HvhgVzbiSPBuacI6XtJrrq',
	'consumer_secret': 'aXLe0FXInwkDbhEkVdgl25mdGxAebPFQnDnbMRu9DUftdxd91U',
	'access_token_key': '831032425241206784-RbWP7oFIk53YKcTgoO5VXRNNTxuNIwh',
	'access_token_secret': '2XBtyFH7Vfauof1Nd4jf17BiiyzKrTfM88lC4bHTUDjcV'
}, {
	'consumer_key': 'lDX4rkXwjvg2b0gxL6vpPlyFh',
	'consumer_secret': 'BXVAXPoo6GCo89HNGBM7ypaREYLkiL6bTtdK4awEB6iVJpVncg',
	'access_token_key': '831032425241206784-348RiEI9wVvFVOUbaoGnQ7nujmoxG0M',
	'access_token_secret': 'WS0W8bkWgBnJ3JelIgS2umJUkGRYCCc6v9LLRkwH5SPEl'
}, {
	'consumer_key': 'yJttCZvzvLRWHbAIWaxplvPAg',
	'consumer_secret': 'btdH5AEtUHwPd52A3S5IierQ1yDcbvwwGMPpZpsxRUwELDBS07',
	'access_token_key': '831032425241206784-TOtvqkYdC8zMfWXiCUwh95lz5NN3UeA',
	'access_token_secret': 'L7PntxGBDRbl5ZisVQsZLPoJfDyCPW81GTRH8Cnps4mOg'
}]

# 翻墙代理
# class Proxies(MiddleWare.PreProcess):
# 	def process(self, request, pid):
# 		request.args.proxies = TIMEOUT
# 		return request

# 限制频繁访问机制
class RequestLimit(MiddleWare.PreProcess):
	limit = LIMIT

	def process(self, request, pid):
		limit = self.__class__.limit
		self.request_time = getattr(self, 'request_time', 0)
		while time.time() - self.request_time < limit:
			gevent.sleep(limit)
		self.request_time = time.time()
		return request

# Auth认证
class Authentication(MiddleWare.PreProcess):
	def __init__(self, *args, **kwargs):
		super(self.__class__, self).__init__(*args, **kwargs)
		self.auths = [{
			'auth': OAuth1(app['consumer_key'], app['consumer_secret'], 
				app['access_token_key'], app['access_token_secret']),
			'remaining': -1
		} for app in APPS]

	def process(self, request, pid):
		if not request.api:
			return request
		while True:
			for index, auth in enumerate(self.auths):
				if auth['remaining'] > 0:
					auth['remaining'] -= 1
					request.args.auth = auth['auth']
					return request
				elif auth['remaining'] == -1:
					auth['remaining'] = 0
					self.get_limit(request, index, auth['auth'])
					return
			gevent.sleep(1)

	def get_limit(self, request, index, auth):
		self.input_queue.put_nowait(Request(
			url = 'https://api.twitter.com/1.1/application/rate_limit_status.json',
			success = self.repeat_request,
			request = request,
			error = request.error,
			auth_index = index,
			args = {
				'auth': auth
			}
		))

	def repeat_request(self, response, input_queue):
		limit = response.json()['resources']['search']
		limit = limit['/search/tweets']['remaining']
		self.auths[response.auth_index]['remaining'] = limit
		input_queue.put_nowait(Request(**response.request))

# 添加默认请求头
class SessionHeaders(MiddleWare.MiddleWare):
	def __init__(self, *args, **kwargs):
		super(self.__class__, self).__init__(*args, **kwargs)
		self.session.headers.update(HEADERS)

# 异常处理
class Error(MiddleWare.MiddleWare):
	exception = Exception

	def middleware(self, request, pid):
		try:
			return self.callback(request, pid)
		except self.__class__.exception, e:
			self.error(e, request, pid)

	def run_error(self, e, request, pid):
		try:
			if request.error:
				request.error(e, request, pid)
		except Exception, e:
			logging.error('%s: %s' % (e.__class__.__name__, e), exc_info=True)

	def error(self, e, request, pid):
		logging.error('%s: %s' % (e.__class__.__name__, request.url), exc_info=True)
		self.run_error(e, request, pid)

# 超时检测
class TimeoutCheck(MiddleWare.PreProcess):
	def process(self, request, pid):
		request.args.timeout = TIMEOUT
		return request

# 超时处理
class TimeoutError(Error):
	exception = requests.exceptions.ReadTimeout

	def error(self, e, request, pid):
		request.repeat_times = (request.repeat_times or 0) + 1
		if request.repeat_times > MAX_REPEAT_TIMES:
			logging.error('TimeoutError: %s' % request.url)
			self.run_error(e, request, pid)
		else:
			self.input_queue.put_nowait(request)
			logging.warning('TimeoutError(%(repeat_times)d): %(url)s' % request)

# 链接失败处理
class ConnectionError(Error):
	exception = requests.exceptions.ConnectionError

	def error(self, e, request, pid):
		request.repeat_times = (request.repeat_times or 0) + 1
		if request.repeat_times > MAX_REPEAT_TIMES:
			logging.error('ConnectionError: %s' % request.url)
			self.run_error(e, request, pid)
		else:
			self.input_queue.put_nowait(request)
			logging.warning('ConnectionError(%(repeat_times)d): %(url)s' % request)

# 请求状态异常检查
class StatusCodeCheck(MiddleWare.PostProcess):
	def process(self, response, pid):
		status_code = response.response.status_code
		if status_code == 200:
			return response
		raise StatusCodeCheck.StatusCodeException(status_code)

	class StatusCodeException(Exception):
		def __init__(self, status_code):
			msg = 'Status Code Error(%d)' % status_code
			Exception.__init__(self, msg)

# 请求状态异常处理
class StatusCodeError(Error):
	exception = StatusCodeCheck.StatusCodeException

	def error(self, e, request, pid):
		request.repeat_times = (request.repeat_times or 0) + 1
		if request.repeat_times > MAX_REPEAT_TIMES:
			logging.error('%s: %s' % (e, request.url))
			self.run_error(e, request, pid)
		else:
			self.input_queue.put_nowait(request)
			logging.warning('%s(%d): %s' % (e, request.repeat_times, request.url))

