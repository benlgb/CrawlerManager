# -*- coding: utf-8 -*-

class SuperObject(dict):
	def __init__(self, dictionary):
		for key, value in dictionary.items():
			setattr(self, key, value)

	def __getattr__(self, key):
		return self.get(key)

	def __setattr__(self, key, value):
		if isinstance(value, dict):
			self[key] = SuperObject(value)
		else:
			self[key] = value

class Request(SuperObject):
	def __init__(self, url, method='get', args={}, **kwargs):
		self.url = url
		self.method = method.lower()
		self.args = args
		SuperObject.__init__(self, kwargs)

	def set_response(self, response):
		self.response = response
		self.text = response.text
		self.json = response.json