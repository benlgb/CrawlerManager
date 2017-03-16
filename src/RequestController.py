# -*- coding: utf-8 -*-

import gevent
import requests

from gevent import monkey
monkey.patch_socket()
monkey.patch_ssl()

class RequestController(object):
	def __init__(self, exit, input_queue, output_queue, middlewares=[]):
		# 存储初始信息
		self.exit = exit
		self.input_queue = input_queue
		self.output_queue = output_queue
		self.middlewares = middlewares

		# 初始化session和中间件
		self.session = requests.Session()
		self.request = self._request
		for middleware in middlewares:
			self.request = middleware(self.session, self.request, 
				input_queue, output_queue)

	def __call__(self, pid):
		while not self.exit.ready():
			if self.input_queue.empty():
				gevent.sleep(0)
				continue
			request = self.input_queue.get_nowait()
			response = self.request(request, pid)
			if response:
				self.output_queue.put_nowait(response)
			self.input_queue.task_done()

	def _request(self, request, pid):
		method = request.method.lower()
		if method == 'get':
			response = self.session.get(request.url, **request.args)
		elif method == 'post':
			response = self.session.post(request.url, **request.args)
		request.set_response(response)
		return request

	def close(self):
		self.exit.set()