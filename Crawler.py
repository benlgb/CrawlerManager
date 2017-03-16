# -*- coding: utf-8 -*-

import os
import gevent
import logging, logging.config
from gevent.event import Event
from gevent.queue import JoinableQueue

from conf import settings
from src.RequestController import RequestController
from bin.DataController import DataController

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

# 启用日志
if not os.path.isdir('log'):
	os.makedirs('log')
logging.config.fileConfig('conf/logger.conf')

class Crawler(object):
	def __init__(self, middlewares, request_process_count):
		self.middlewares = middlewares
		self.request_process_count = request_process_count
		self.exit = Event()
		self.input_queue = JoinableQueue()
		self.output_queue = JoinableQueue()

	def run(self):
		try:
			self.request_controller = RequestController(self.exit, 
				self.input_queue, self.output_queue, self.middlewares)
			self.data_controller = DataController(self.exit, 
				self.input_queue, self.output_queue)
			self.request_process = []
			for pid in range(self.request_process_count):
				request_process = gevent.spawn(self.request_controller, pid)
				self.request_process.append(request_process)
			self.data_process = gevent.spawn(self.data_controller)
			gevent.joinall(self.request_process + [self.data_process])
		except Exception, e:
			self.exit.set()
			logging.error('%s: %s' % (e.__class__.__name__, e), exc_info=True)

if __name__ == '__main__':
	Crawler(**{
		'middlewares': settings.MIDDLEWARES,
		'request_process_count': settings.REQUEST_COUNT
	}).run()