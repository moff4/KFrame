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
#         user		-  str
#         passwd	-  str
#         scheme	-  str
#         DDL  		-  dict : str - tablename => str - DDL script for creating
#     }
#
class SQL(Plugin):
	def init(self,host,port,user,passwd,**kwargs):
		try:	
			self.cfg = {
				'host'		: host,
				'port'		: port,
				'user'		: user,
				'passwd'	: passwd,
			}
			defaults = {
				'ddl'		: {},
			}
			for i in defaults:
				self.cfg[i] = kwargs[i] if i in kwargs else defaults[i]
			self.conn = None
			self._lock = 0

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
			self._lock += 1
			return True
		except Exception as e:
			self('connect-error: ({user}@{host}:{port}/{scheme}): {ex}'.format(user=self.cfg['user'],host=self.cfg['host'],port=self.cfg['port'],scheme=self.cfg['scheme'] if 'scheme' in self.cfg else "",ex=e),_type="error")
			return False

	#
	# TESTED
	# close connection
	#
	def close(self):
		self._lock -=1 
		if self._lock <= 0:
			self._lock = 0
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
		except Exception as e:
			self('reconnect-error',_type="error")
	
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

	#==========================================================================
	#                                USER API
	#==========================================================================

	#
	# universal method: select/create/insert/update/...
	# exec query
	# return tuple( flag of success , data as list of tuples )
	#
	def execute(self,query,commit=False,multi=False):
		i = 0.1
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
			self.Error('exec-query: {ex}'.format(ex=e))
			boo = False
		return boo , res

	#
	# method specialy for select
	# return list of tuples (rows) in case of success
	# or None in case of error
	#
	def select_all(self,query):
		try:
			if self.conn is None or not self.conn.is_connected():
				self.reconnect()
			cu = self.conn.cursor()
			cu.execute(query)
			return cu.fetchall()
		except Exception as e:
			self.Error('select-all: {ex}'.format(ex=e))
			return None

	#
	# method specialy for select
	# return generator that returns tuples (row) in case of success
	# or raise Exception in case of error
	#
	def select(self,query):
		try:
			if self.conn is None or not self.conn.is_connected():
				self.reconnect()
			cu = self.conn.cursor()
			cu.execute(query)
			while True:
				res = cu.fetchone()
				if res is None:
					return None
				yield res
		except Exception as e:
			self.Error('select-one: {ex}'.format(ex=e))
			raise

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

sql_scheme = {
	"target":SQL,
	"module":False,
	"arg":(),
	"kwargs":{},
	"dependes":[]
}