#!/usr/bin/env python3

import time
from collections import deque


class Eventer:
	def __init__(self,timeout):
		self.timeout = timeout
		self.queue 	= deque() 	# item = ( id , timestamp )
		self.i_c 	= {} 		# id => count
		self.c_i 	= {} 		# count => set of id

	#==========================================================================
	#                                 UTILS
	#==========================================================================

	def __inc(self,key,timestamp):
		if key in self.i_c:
			if self.i_c[key] in self.c_i:
				self.c_i[self.i_c[key]].remove(key)
			self.i_c[key] += 1
			if self.i_c[key] in self.c_i:
				self.c_i[self.i_c[key]].add(key)
			else:
				self.c_i[self.i_c[key]] = set([key])
		else:
			self.i_c[key] = 1
			if 1 not in self.c_i:
				self.c_i[1] = set()
			self.c_i[1].add(key)
		self.queue.append((key,timestamp))

	def __dec(self,key,timestamp):
		if key in self.i_c:
			if self.i_c[key] in self.c_i:
				self.c_i[self.i_c[key]].remove(key)
			self.i_c[key] -= 1
			if self.i_c[key] > 0:
				if self.i_c[key] in self.c_i:
					self.c_i[self.i_c[key]].add(key)
				else:
					self.c_i[self.i_c[key]] = set([key])
			else:
				self.i_c.pop(key)

	def __check(self,timestamp):
		self.out()
		while len(self.queue) > 0:
			key , _t = self.queue[0]
			if timestamp - _t <= self.timeout:
				return
			else:
				print("pop: %s"%key)
				self.__dec(*self.queue.popleft())

	#==========================================================================
	#                             USER API
	#==========================================================================

	def registrate(self,id,timestamp=None):
		timestamp = int(time.time()) if timestamp is None else timestamp
		self.__inc(id,timestamp)
		self.__check(timestamp)

	def get_count(self,id,timestamp=None):
		timestamp = int(time.time()) if timestamp is None else timestamp
		self.__check(timestamp)
		return self.i_c[id] if id in self.i_c else 0

	def get_ids(self,k,timestamp=None):
		timestamp = int(time.time()) if timestamp is None else timestamp
		self.__check(timestamp)
		return self.c_i[k] if k in self.c_i else set()
