#!/usr/bin/env python3

import time
import mysql.connector as sql 

from ..base.plugin import Plugin

#
# Parent - any class/module that has:
#   - method log(st,_type)
#   - object/module that has field SQL - dict {
#         host		-  str
#         port		-  int
#         username	-  str
#         password	-  str
#         scheme	-  str
#         DDL  		-  dict : str - tablename => str - DDL script for creating
#     }
#
class SQL(Plugin):
	def init(self,cfg=None,**kwargs):
		try:
			if cfg != None:
				self.cfg = cfg
			else:
				self.cfg = {}
				defaults = {
					'host'		: '127.0.0.1',
					'port'		: 3306,
					'username'	: 'root',
					'password'	: 'password',
					'scheme'	: 'scheme',
					'ddl'		: {},
				}
				for i in defaults:
					self.cfg = kwargs[i] if i in kwargs else defaults[i]
			self.conn = None
			self.lock = False

			self.FATAL = not self.connect()
			if self.FATAL:
				self.errmsg = "%s: could not connect to SQL-server"%(self.name);
			self.close()
		except Exception as e:
			self.FATAL = True
			self.errmsg = "%s: %s"%(self.name,str(e))

	def __del__(self):
		self.close()

	#==========================================================================
	#                                INTERNAL METHODS
	#==========================================================================

	#
	# TESTED
	# open connection
	#
	def connect(self):
		try:
			params = {}
			for i in ['user','passwd','host','port']:
				params[i] = self.cfg[i]
			if 'scheme' in self.cfg:
				params['db'] = self.cfg['scheme']
			self.conn = sql.connect(**params)
			return True
		except Exception as e:
			self('connect-error: ({user}@{host}:{port}/{scheme}): {ex}'.format(user=self.cfg['user'],host=self.cfg['host'],port=self.cfg['port'],scheme=self.cfg['scheme'] if 'scheme' in self.cfg else "",ex=e),_type="error")
			return False

	#
	# TESTED
	# close connection
	#
	def close(self):
		try:
			self.conn.close()
		except Exception:
			pass

	#
	# TESTED
	# reopen connection to database
	#
	def reconnect(self):
		try:
			self.close()
			self.connect()
			# if not self.conn.is_connected():
			# 	self.conn.reconnect(2,1)
		except Exception as e:
			self('reconnect-error',_type="error")

	#==========================================================================
	#                                USER API
	#==========================================================================

	#
	# TESTED
	# exec query
	# return tuple( flag of success , data as list of tuples )
	#
	def execute(self,query,commit=False,multi=False):
		i = 0.1
		while self.lock:
			time.sleep(min(i,1.5))
			i *= 2
		self.lock = True

		res = []
		boo = True
		try:
			self.reconnect()
			if self.conn != None and self.conn.is_connected():
				cu = self.conn.cursor()
				cu.execute(query,multi=multi)
				res = []
				try:
					res = cu.fetchall()
				except Exception as e:
					pass
				if commit:
					try:
						self.conn.commit()
					except Exception:
						pass
			else:
				boo = False
		except Exception as e:
			self('exec-query: {}'.format(e),_type="error")
			boo = False
		self.close()
		self.lock = False
		return boo , res

	#
	# TESTED
	# create all tables according to there DDL
	# return tuple ( True in case of success or False , None or Exception)
	#
	def create_table(self):
		try:
			if 'ddl' in self.cfg:
				for i in self.cfg['ddl']:	
					self.Debug("{name} execute create table script: {result}".format(name=i,result=self.execute(self.cfg['ddl'][i],commit=True)[0]))
			return True, None
		except Exception as e:
			self.Error("create-table: %s"%(e))
			return False , e

	#
	# need for integration
	#
	def start(self):
		self.create_table()

	#
	# need for integration
	#
	def stop(self,wait=True):
		pass

DEFAULT_LOAD_SCHEME = {
	"target":SQL,
	"module":False,
	"arg":(),
	"kwargs":{},
	"dependes":[]
}