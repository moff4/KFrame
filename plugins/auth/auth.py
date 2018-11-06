#!/usr/bin/env python3

import time
from traceback import format_exc as Trace

from ...base.plugin import Plugin
from ...modules import jscheme
from ...modules import crypto
from ...modules import art
from ..mchunk import mchunk_scheme
from ..stats import stats_scheme

#
# This module is to work with sessions, cookies and SQL-storing
#
class Auth(Plugin):
	#
	# sercret - secret key for crypto
	#
	def init(self,secret,**kwargs):

		if 'mchunk' not in self:
			self.P.add_plugin(key="mchunk",**mchunk_scheme)
		self.secret = self.P.init_plugin(key="mchunk",export=True).set(secret).mask()
		if 'stats' not in self:
			self.P.add_plugin(key="stats",**stat_scheme).init_plugin(key="stats",export=False)
		
		self.mask = kwargs['mask'] if 'mask' in kwargs else None

		self.P.stats.init_stat(key="cookie-created"  ,type="inc")
		
		self.cookie_scheme = {
			"type":dict,
			"value":{
				"create":{
					"type":int
				},
				"uid":{
					"type":int,
					"default":None
				},
				"exp":{
					"type":int,
					"default":None
				},
				"ip":{
					"type":str,
					"default":None
				},
			}
		}

	#
	# return decoded cookie as dict
	# or None in case of error
	#
	def decode_cookie(self,cookie):
		try:
			data = art.unmarshal(data=cookie,mask=self.mask)
			
			self.secret.unmask()
			c = crypto.Cipher(key=self.secret.get())
			self.secret.mask()

			data = art.unmarshal(data=c.decrypt(data=data['d'],iv=data['i']),mask=self.mask)

			return jscheme.apply_json_scheme(obj=data,scheme=self.cookie_scheme,key="cookie")
		except Exception as e:
			self.Warring("decode cookie: {ex}".format(ex=e))
			self.Warring("decode cookie: {ex}".format(ex=Trace()))
			return None

	#==========================================================================
	#                               USER API
	#==========================================================================

	#
	# generate cookie
	# must:
	# 	user_id 	- int - user identificator
	# optional:
	# 	expires 	- int - num of seconds this cookie is valid
	# 	ip 			- str - ip addr of client
	# return bytes() as value of cookie
	#
	def generate_cookie(self, user_id, **kwargs):
		
		data = {
			'create':int(time.time()),
		}
		kwargs = dict(kwargs)
		kwargs['user_id'] = user_id
		params = {
			'user_id':'uid',
			'expires':'exp',
			'ip':'ip'
		}
		for i in filter(lambda x:x in kwargs,params.keys()):
			data[params[i]] = kwargs[i]
		data = art.marshal(data, mask=self.mask, random=True)

		self.secret.unmask()
		c = crypto.Cipher(key=self.secret.get())
		self.secret.mask()
		
		iv = crypto.gen_iv()
		data = c.encrypt(data=data, iv=iv)

		res = art.marshal({
			"d":data,
			"i":iv
		}, mask=self.mask, random=True)

		self.P.stats.add("cookie-created")
		return res
	
	#
	# return user_id if cookie is valid
	# or None if cookie is not valid
	#
	def valid_cookie(self,cookie,ip=None):
		cookie = self.decode_cookie(cookie)
		if cookie is None or (cookie['exp'] is not None and (cookie['create'] + cookie['exp']) < time.time()) or (cookie['ip'] != ip):
			return None
		else:
			return cookie['uid']