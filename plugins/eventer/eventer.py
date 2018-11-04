#!/usr/bin/env python3

import time
from collections import deque


class Eventer:
	def init(self,timeout):
		self.timeout = timeout
		self.queue 	= deque() 	# item = ( key , timestamp )
		self.i_c 	= {} 		# key => count
		self.c_i 	= {} 		# count => set of key
		self.pop_b 	= {} 		# key => num

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

	def __dec(self,key):
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

	#
	# return list of poped keys
	#
	def __check(self,timestamp):
		az = []
		while len(self.queue) > 0:
			key , _t = self.queue[0]
			if timestamp - _t <= self.timeout:
				return az
			else:
				key , _ = self.queue.popleft()
				if key in self.pop_b and self.pop_b[key] > 0:
					self.pop_b[key] -= 1
					if self.pop_b[key] == 0:
						self.pop_b.pop(key)
				else:
					self.__dec(key)
				az.append(key)

	#==========================================================================
	#                             USER API
	#==========================================================================

	#
	# True if key in queue else False
	#
	def __contains__(self,key):
		return key in self.i_c

	#
	# registrate new event for key
	#
	def registrate(self,key,timestamp=None,check_queue=True):
		timestamp = int(time.time()) if timestamp is None else timestamp
		self.__inc(key,timestamp)
		if check_queue:
			self.__check(timestamp)

	#
	# return count of events for key
	#
	def get_count(self,key,timestamp=None,check_queue=True):
		timestamp = int(time.time()) if timestamp is None else timestamp
		if check_queue:
			self.__check(timestamp)
		return self.i_c[key] if key in self.i_c else 0

	#
	# return set of keys WHERE count(events) == k
	#
	def get_keys(self,k,timestamp=None,check_queue=True):
		timestamp = int(time.time()) if timestamp is None else timestamp
		if check_queue:
			self.__check(timestamp)
		return self.c_i[k] if k in self.c_i else set()

	#
	# pop key from queue before timeout
	#
	def pop(self,key):
		self.pop_b[key] = ( self.pop_b[key] if key in self.pop_b else 0 ) + 1
		self.__dec(key)

	#
	# delete old keys from queue
	# return list of poped keys
	#
	def check_queue(self,timestamp=None):
		return self.__check(int(time.time()) if timestamp is None else timestamp)

	#
	# improt data from dict
	#
	def _import(self,data):
		self.queue 	= deque()
		self.i_c = data["ic"]
		self.c_i = data["ci"]
		self.pop_b=data["p"]
		i = 0
		while i in data["q"]:
			self.queue.append((data["q"][str(i)]["tag"],data["q"][str(i)]["ts"]))
			i += 1

	#
	# export data as dict
	#
	def _export(self,data):
		def export_q(queue,f=lambda x:x):
			d = {}
			i = 0
			while len(queue) > 0:
				x = queue.popleft()
				d[str(i)]=f(x)
				i += 1
		return {
					"ic":self.i_c,
					"ci":self.c_i,
					"q" :export_q(self.queue,f=lambda x:{"tag":x[1],"ts":x[1]}),
					"p" :self.pop_b
				}
