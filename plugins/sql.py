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
#         DDL  		-  list of tuple ( str - tablename , str - script for creating )
#         }
#
class SQL(Plugin):
	def init(self,cfg):
		try:
			self.cfg = cfg
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
			self('connect-error: ({user}@{host}:{port}/{scheme}): {}'.format(self.cfg['user'],self.cfg['host'],self.cfg['port'],self.cfg['scheme'] if 'scheme' in cfg else "",e),_type="error")
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

	#
	# TESTED
	# exec query
	# return tuple( flag of success , data as list of tuples )
	#
	def execute(self,query,commit=False):
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
				cu.execute(query)
				res = []
				try:
					res = cu.fetchall()
				except:
					pass
				if commit:
					try:
						self.conn.commit()
					except:
						pass
			else:
				boo = False
		except Exception as e:
			self('exec-query: {}'.format(e),_type="error")
			boo = False
		self.close()
		self.lock = False
		return boo , res

	#==========================================================================
	#                                USER API
	#==========================================================================

	#
	# TESTED
	# create all tables according to there DDL
	# return tuple ( True in case of success or False , None or Exception)
	#
	def create_table(self):
		try:
			for i in self.ddl:	
				self("%s execute create table script: %s"%(i[0],self.execute(i[1],commit=True)[0]),_type="debug")
			return True, None
		except Exception as e:
			self("create-table: %s"%(e),_type="error")
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