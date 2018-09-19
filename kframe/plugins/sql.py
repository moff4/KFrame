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
			self.host 				= cfg['host']		# str
			self.port 				= cfg['port']		# int
			self.user 				= cfg['username']	# str
			self.passwd 			= cfg['password']	# str
			self.db 				= cfg['scheme']		# str
			self.ddl  				= cfg['DDL']  		# list of tuple ( str - tablename , str - script for creating )
			
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
			self.conn = sql.connect(host=self.host,port=self.port,user=self.user,passwd=self.passwd,db=self.db)
			return True
		except Exception as e:
			self('connect-error: ({}@{}:{}/{}): {}'.format(self.user,self.host,self.port,self.db,e),_type="error")
			return False

	#
	# TESTED
	# close connection
	#
	def close(self):
		try:
			self.conn.close()
		except:
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