#!/usr/bin/env python3

from ...base.plugin import Plugin
from .parser import parse_data
from .utils import *

class Request(Plugin):
	def init(self,**kwargs):
		self._id = kwargs['id'] if 'id' in kwargs else "0"
		if any(map(lambda x:x not in kwargs,['cfg','addr','conn'])):
			self.FATAL = True
			self.errmsg = "missed kwargs argument"
			self.Error(self.errmsg)
			return
		self.conn 	= kwargs['conn']
		self.addr 	= kwargs['addr']
		self.ip 	= self.addr[0]
		self.port 	= self.addr[1]
		self.ssl 	= False
		self.secure = False
		self._dict 	= {}
		try:
			self._dict = parse_data(self.conn,kwargs['cfg'])
			self._dict_keys = list(self._dict.keys())
		except Exception as e:
			self.FATAL = True
			self.errmsg = "parse data: %s"%e
			self.Debug(self.errmsg)
			return
		for i in self._dict:
			setattr(self,i,self._dict[i])

		self.resp = self.P.init_plugin(key="response")
		self._send = False
	
	#
	# local log function
	#
	def __call__(self,st="",_type="notify"):
		self.log(st="[{id}] {st}".format(id=self._id,st=st),_type=_type)

	def set_ssl(self,ssl):
		self.ssl = ssl
		return self

	def set_secure(self,secure):
		self.secure = secure
		return self

	def dict(self):
		d = {}
		for i in ["conn","addr","ip","port","ssl"] + self._dict_keys:
			d[i] = getattr(self,i)
		return d

	def after_handler(self):
		pass # this will be called after main handler done

	def send(self,resp=None):
		if not self._send:
			self.conn.send(self.resp.export() if resp is None else resp.export())
			self._send = True