#!/usr/bin/env python3

import time

from ...base.plugin import Plugin

try:
	from .cookie import Cookie
except:
	from cookie import Cookie

COOKIE_TIMELIFE = 7*86400

#
#
class Cookies(Plugin):
	def init(self,req = None):
		
		self.cookies = {}
		self.scheme = {}

		req = {'headers':{}} if req is None else req

		if 'Cookie' in req['headers']:
			self._parse(req['headers']['Cookie'])

	#
	# Parse HTTP-header
	#
	def _parse(self,headers):
		for ck in headers:
			for c in ck.split(";"):
				new_cookie = Cookie(self.parent,c)
				self.cookies[new_cookie.key()] = new_cookie

	#==========================================================================
	#                                USER API
	#==========================================================================

	#
	# return cookie by key
	# return None in case of cookie not exists
	#
	def get(self,key):
		if key in self.cookies:
			return self.cookies[key]
		else:
			return None

	#
	# delete cookie
	#
	def pop(self,key):
		if key in self.cookies:
			self.cookies.pop(key)

	def __getitem__(self,key):
		return self.get(key)
	
	def __contains__(self,key):
		return key in self.cookies

	def __str__(self):
		st = ""
		for i in self.export():
			st += i + "\n"
		return st[:-1]

	def __len__(self):
		return len(self.cookies)

	#
	# return list of HTTP-header
	#
	def export(self):
		st = []
		for key in self.cookies:
			st.append(str(self.cookies[key]))
		return st

	#
	# scheme = dict: cookie-key => attributes
	# attributes = dict: attribute-key => attribute-value
	# unique attribute-key == "default":
	#	if there are no cookie => create with default value
	# attribute-value = anything including callable types
	#	if attribute-value is callable -> it'll be called with Cookie-object passed as arg
	#
	def apply_scheme(self,scheme = None,create_only=False):
		def get_value(ck,att,cookie):
			value = scheme[ck][att]
			if "__call__" in dir(value):
				value = value(cookie)
			return value
		scheme = self.scheme if scheme is None else scheme
		for ck in scheme:
			if ck not in self.cookies and 'default' in scheme[ck]:
				new_cookie = Cookie(self.parent)
				new_cookie.init(key=ck,value=get_value(ck,'default',new_cookie))
				self.cookies[ck] = new_cookie
			if not create_only:
				if ck in self.cookies:
					for attr in scheme[ck]:
						if attr != 'default':
							value = get_value(ck,attr,self.cookies[ck])
							self.cookies[ck].set_attr(attr=attr,value=value)


	def test(self):
		scheme = {
			"_ym_uid":{
				"secure":True,
				"expire":lambda x:time.time()
			},
			"PHPSESSID":{
				"http":"123"
			},
			"ABC":{
				"qwe":"123",
				"default":lambda x:time.time()
			}
		}
		self.apply_scheme(scheme=scheme)
