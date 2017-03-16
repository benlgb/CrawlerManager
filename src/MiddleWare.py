# -*- coding: utf-8 -*-

import logging
import traceback

class MiddleWare(object):
	def __init__(self, session, callback, input_queue, output_queue):
		self.session = session
		self.callback = callback
		self.input_queue = input_queue
		self.output_queue = output_queue

	def __call__(self, request, pid):
		if request:
			return self.middleware(request, pid)

	def middleware(self, request, pid):
		return self.callback(request, pid)

class PreProcess(MiddleWare):
	def middleware(self, request, pid):
		request = self.process(request, pid)
		if request:
			return self.callback(request, pid)

	def process(self, request, pid):
		return request

class PostProcess(MiddleWare):
	def middleware(self, request, pid):
		response = self.callback(request, pid)
		if response:
			return self.process(response, pid)

	def process(self, response, pid):
		return response

