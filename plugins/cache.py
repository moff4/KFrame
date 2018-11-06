#!/usr/bin/env python3

import time
import json
from threading import Thread

from ..base.plugin import Plugin

#
# kwargs:
#	timeout - interval of checking nodes for old rows ; default: 1.0
#	save_file - filename for temporary buffer ; default: cache.json
#
class Cache(Plugin):
	def init(self,**kwargs):
		defaults = {
			'timeout'		: 1.0,
			'save_file'		: 'cache.json',
		}
		self.cfg = {}
		for i in defaults:
			self.cfg[i] = cfg[i] if i in kwargs else defaults[i]
		self._d = {} # nodename -> [  cache as dict , timeout as float , filter as function : time.time() of add -> bool , autoclean ]
		self._th = None
		self._run = True
		self.load()
	#==========================================================================
	#                                 UTILS
	#==========================================================================

	def save(self):
		try:
			data = {}
			for i in self._d:
				data[i] = {"d":self._d[i][0],"t":self._d[i][1],"a":self._d[i][3]}
			open(self.cfg['save_file'],"w").write(json.dumps(data))
		except Exception as e:
			self("save temporary file: %s"%e,_type="warring")


	def load(self):
		try:
			data = json.load(open(self.cfg['save_file']))
			for i in data:
				self._d[i] = [ data[i]["d"] , data[i]["t"] , None , data[i]["a"]]
		except Exception as e:
			self("read temporary file: %s"%e,_type="warring")

	def _clean(self):
		k = 0
		for nodename in self._d:
			if self._d[nodename][3]:
				k += self.clean_node(nodename)
		if k > 0:
			self("clean: delete %s rows"%(k),_type="debug")

	def _loop(self):
		self("start loop",_type="debug")
		while self._run:
			time.sleep(self.cfg['timeout'])
			self._clean()
		self("stop loop",_type="debug")

	#==========================================================================
	#                                USER API
	#==========================================================================

	#
	# overwrite
	#
	def start(self):
		self._run = True
		self._th = Thread(target=self._loop)
		self._th.start()

	#
	# overwrite
	#
	def stop(self,wait=True):
		self._run = False
		if wait:
			self._th.join()
			self.save()

	#
	# Add new node or change timeout if node exists
	# Timeout will be ignored if _filter passed
	# filter is fuction : value , timestamp => bool
	#	value - smth saved
	# 	timestamp - timestamp when this was added
	# 	return True if row must be deleted
	#
	def add_node(self,nodename,timeout=3600,_filter=None,autoclean=True):
		if nodename not in self._d:
			self._d[nodename] = [{},timeout,_filter,autoclean]
		else:
			self._d[nodename] = [self._d[nodename][0],timeout,_filter,autoclean]

	#
	# Delete whole node
	#
	def delete_node(self,nodename):
		if nodename in self._d:
			self._d.pop(nodename)

	#
	# delete old rows from node
	# return number of deleted rows
	#
	def clean_node(self,nodename):
		if nodename not in self._d:
			return 0
		k = 0
		_time = time.time()
		for key in list(self._d[nodename][0].keys()):
			if self._d[nodename][2] is None:
				if ( self._d[nodename][1] + self._d[nodename][0][key][1] ) < _time:
					self._d[nodename][0].pop(key)
					k += 1
			elif self._d[nodename][2](*self._d[nodename][0][key][1]):
				self._d[nodename][0].pop(key)
				k += 1
		return k


	#
	# Push new data to cache
	#
	def push(self,nodename,key,val):
		self._d[nodename][0][key] = (val,time.time())

	#
	# Return value for key in cache or None
	#
	def get(self,nodename,key):
		if key in self._d[nodename][0]:
			return self._d[nodename][0][key][0]
		else:
			return None

	#
	# return number of keys in one node
	#  OR return 0
	#
	def count(self,nodename):
		if nodename in self._d:
			return len(self._d[nodename][0])
		else:
			return 0

cache_scheme = {
	"target":Cache,
	"module":False,
	"arg":(),
	"kwargs":{},
	"dependes":[],
	"autostart":True,
}

