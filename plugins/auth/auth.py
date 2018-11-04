#!/usr/bin/env python3

from ...base.plugin import Plugin
from ...plugins import crypto
from ...plugins import art
from ..mchunk import DEFAULT_LOAD_SCHEME as mchunk_scheme
from ..stats import DEFAULT_LOAD_SCHEME as stat_scheme
from ..sql import DEFAULT_LOAD_SCHEME as sql_scheme

#
# This module is to work with sessions, cookies and SQL-storing
#
class Auth(Plugin):
	#
	# sercret - secret key for crypto
	# kwargs:
	# 	host 		- for sql if not inited
	# 	port 		- for sql if not inited
	# 	username 	- for sql if not inited
	# 	password 	- for sql if not inited
	#
	def init(self,secret,**kwargs):

		if 'mchunk' not in self:
			self.P.add_plugin(key="mchunk",**mchunk_scheme)
		self.secret = self.P.init_plugin(key="mchunk",export=True).set(secret).mask()
		if 'stats' not in self:
			self.P.add_plugin(key="stats",**stat_scheme).init_plugin(key="stats",export=False)
		if 'sql' not in self:
			self.P.add_plugin(key="sql",**sql_scheme).init_plugin(key="sql",export=False,**kwargs)
		self.mask = kwargs['mask'] if mask in kwargs else None

	#
	# return True if cookie is valid
	# or False if not valid
	#
	def valid_cookie(self,cookie):
		return False

	#
	# user_id - int
	# expires - int - num of seconds this cookie lives
	#
	def generate_cookie(self,user_id=None,expires=None):
		
		data = {
			'create':int(time.time()),
		}
		if user_id not is None:
			data['uid'] = user_id
		if expires not is None:
			data['exp'] = expires
		data = art.marshal(data,mask=self.mask,random=True)

		self.secret.unmask()
		c = crypto.Cipher(key=self.secret.get())
		self.secret.mask()
		
		iv = crypto.gen_iv()
		data = c.encrypt(data=data,iv=iv)

		return art.marshal({
			"d":data,
			"i":iv
		},mask=self.mask,random=True)

	def test(self):
		pass