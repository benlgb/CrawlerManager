# -*- coding: utf-8 -*-

# # 最高同时访问数
REQUEST_COUNT = 10

from bin.MiddleWares import *

# 中间件
MIDDLEWARES = (
	# Proxies,
	# Authentication,
	# RequestLimit,
	StatusCodeCheck,
	TimeoutCheck,
	ConnectionError,
	TimeoutError,
	StatusCodeError,
	Error,
	SessionHeaders,
)