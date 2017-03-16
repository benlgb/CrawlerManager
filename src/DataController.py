# -*- coding: utf-8 -*-

import gevent
import logging

class DataController(object):
	def __init__(self, exit, input_queue, output_queue):
		self.exit = exit
		self.input_queue = input_queue
		self.output_queue = output_queue

	def __call__(self):
		self.start(self.input_queue)
		while not self.exit.ready():
			if self.output_queue.empty():
				if self.input_queue._cond.ready():
					self.exit.set()
				gevent.sleep(0)
				continue
			response = self.output_queue.get_nowait()
			try:
				if response.success:
					response.success(response, self.input_queue)
			except Exception, e:
				logging.error('%s: %s' % (e.__class__.__name__, response.url), exc_info=True)
			self.output_queue.task_done()

	def start(self):
		pass