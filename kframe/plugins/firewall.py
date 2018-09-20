#!/usr/bin/env python3

import time
from traceback import format_exc as Trace

from ..base.plugin import Plugin

DEFAULT_RULES = [
	{
		"type":"count",
		"num-of-req":3,
		"delta-time":5,
	},
	{
		"type":"count",
		"num-of-req":5,
		"delta-time":15,
	}
]

#
# Firewall - class for filtering ip activity
# Saves all requests statuses and timestamps
# if too much bad requests => ban ip
#
# **kwargs:
#	rules - list of dict; each dict - rule how to filter IP
#
# Rules can be:
# -- Simple filter {
# 	"type":"count",
# 	"num-of-req":3, # number of bad requests
# 	"delta-time":5, # delta time for such number of bad requests
# },
# -- Lambda filter {
# 	"type":"filter",
# 	# fst - ip
# 	# snd - list of tuples ( time.time() , bool as status of request )
# 	# return True if ip must be banned
# 	"filter":lambda x,y:False
# }
#
class Firewall(Plugin):
	def init(self,**kwargs):
		defaults = {
			"rules": DEFAULT_RULES
		}
		self.cfg = {}
		for i in defaults:
			self.cfg[i] = kwargs[i] if i in kwargs else defaults[i]

		self._d = {} # ip -> list of tuples ( time.time() , bool as status of request )
		self._black = set() # list of tuples ( ip , time.time() )
		self._black_ips = set() # same as self._black but only ips

	#
	# decide to ban or not to ban ip
	# return True if ip was banned
	#     or False if not
	#
	def _ban(self,ip):
		az = list(map(lambda x: x[0],self._d[ip]))
		bz = list(map(lambda x: not x[1],self._d[ip]))
		if len(az) <= 0:
			return False
		for rule in self.cfg['rules']:
			if rule['type'] == 'count' and len(az) >= rule['num-of-req'] and (max(az) - min(az)) < rule['delta-time'] and len(bz) == len(az):
				self._black.add((ip,time.time()))
				self._black_ips.add(ip)
				self._d.pop(ip)
				return True
			elif rule['type'] == 'filter':
				try:
					return rule['filter'](ip,self._d[ip])
				except Exception as e:
					e = Trace()
					self("Filter(%s) %s"%(ip,e))
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
		
		if ip in self._black_ips:
			boo = True		
		elif ip in self._d:
			boo = self._ban(ip)

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

DEFAULT_LOAD_SCHEME = {
	"target":Firewall,
	"module":False,
	"arg":(),
	"kwargs":{},
	"dependes":[]
}

