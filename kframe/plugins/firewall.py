#!/usr/bin/env python3

import time

from ..base.plugin import Plugin

DEFAULT_RULES = [
	#
	# fst - number of requests
	# snd - delta time between fst and last
	#
	(3, 5),
	(5,15)
]

class Firewall(Plugin):
	# FIXME think about rules
	def init(self,rules = None):
		self.rules = DEFAULT_RULES if rules is None else rules
		self._d = {} # ip -> list of tuples ( time.time() , http-code )
		self._black = set() # list of tuples ( ip , time.time() )
		self._black_ips = set() # same as self._black but only ips

	#
	# decide to ban or not to ban ip
	# return True if ip was banned
	#     or False if not
	#
	def _ban(self,ip):
		az = list(map(lambda x:x[0],self._d[ip]))
		bz = list(map(lambda x:x[1] == 404,self._d[ip]))
		if len(az) <= 0:
			return False
		for rule in self.rules:
			if len(az) >= rule[0]:
				if (max(az) - min(az)) < rule[1] and len(bz) == len(az):
					self._black.add((ip,time.time()))
					self._black_ips.add(ip)
					self._d.pop(ip)
					return True
		return False

	#==========================================================================
	#                                 USER API
	#==========================================================================

	#
	# add data to history
	#
	def add(self,ip,code):
		t = ( time.time() , code )
		if ip in self._d:
			self._d[ip].append(t)
			self._d[ip] = self._d[ip][-5:]
		else:
			self._d[ip] = [t]

	#
	# if code not None => call Firewall.add
	# return True if connection should be dropped
	# return False if connection allowed to listen
	# if react is True => call Firewall.react if ip was banned
	#
	def banned(self,ip,code=None,react=False):
		boo = False
		done = False
		
		if ip in self._black_ips:
			boo = True
			done = True
		
		if ip in self._d and not done:
			boo = self._ban(ip)
			done = True

		if code != None:
			self.add(ip,code)
		if react and boo:
			self.react(ip)
		return boo

	#
	# CAN BE OVERLOADED
	# reaction on blocked IP
	#
	def react(self,ip):
		time.sleep(60)

	#
	# return list of blocked ips and timestamps of blockings
	#
	def get_blacklist(self):
		return self._black

LOAD_SCHEME = {
	"target":Firewall,
	"module":False,
	"arg":(),
	"kwargs":{},
	"dependes":[]
}

