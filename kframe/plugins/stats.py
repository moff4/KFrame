#!/usr/bin/env python3

from ..base.plugin import Plugin

POSSIBLE_TYPES 	= set(['inc','single','aver','collect','set'])
SIMPLE_TYPES 	= set(['inc','single','collect'])

class Stats(Plugin):
	def init(self):
		self._stats = {}

	def _export(self,key):
		if key not in self._stats:
			return None
		if self._stats[key]['type'] in SIMPLE_TYPES:
			return self._stats[key]['data']
		if self._stats[key]['type'] == 'aver':
			if len(self._stats[key]['data']) > 0:
				return "%.4f"%(sum(self._stats[key]['data']) / len(self._stats[key]['data']))
			return 0.0
		if self._stats[key]['type'] == 'set':
			return list(self._stats[key]['data'])

	#==========================================================================
	#                                 USER API
	#==========================================================================

	#
	# initialize new stat
	# params:
	#   <must be>
	#     key - internal name of stat
	#     type - type of stats possible: aver / collect / set / single / inc
	#   <optional>
	#     default - default value for any type
	#     count - number of elements saved for type "aver" and "collect"
	#       default: 500
	#     increment - increment for signle call for type "inc"
	#       default: 1
	# return tuple ( flag of success , errmsg in case of error )
	#
	def init_stat(self,key,type,**kwargs):
		if 'key' not in kwargs:
			return False, "Expected key 'key'"
		if 'type' not in kwargs:
			return False , "No type of stat"
		if kwargs['type'] not in POSSIBLE_TYPES:
			return False , "Unknown type of stat"
		d = dict(kwargs)
		if 'default' in d:
			default = d['default']
		else:
			if d['type'] == 'inc':
				default = 0
			elif d['type'] in ['aver','collect']:
				default = []
			elif d['type'] == 'single':
				default = None
			else:
				default = set()
		d['data'] = default
		self._stats[d['key']] = d
		return True , "Success"

	#
	# add stat data
	# return True in case of success
	# or False in case of error
	#
	def add(self,key,value=None):
		if key not in self._stats:
			return False
		if self._stats[key]['type'] == 'aver':
			count = self._stats[key]['count'] if 'count' in self._stats[key] else 500
			while len(self._stats[key]['data']) > count:
				self._stats[key]['data'].pop(0)
			self._stats[key]['data'].append(value)
		elif self._stats[key]['type'] == 'collect':
			self._stats[key]['data'].append(value)
		elif self._stats[key]['type'] == 'inc':
			self._stats[key]['data'] += self._stats[key]['increment'] if 'increment' in self._stats[key] else 1
		elif self._stats[key]['type'] == 'single':
			self._stats[key]['data'] = value
		elif self._stats[key]['type'] == 'set':
			self._stats[key]['data'].add(value)
		else:
			return False
		return True

	#
	# return saved data or None in case of error
	#
	def get(self,key):
		return self._stats[key]['data'] if key in self._stats else None

	#
	# return dict containing all stats
	#
	def export(self):
		d = {}
		for key in self._stats:
			d[key] = self._export(key)
		return d

DEFAULT_LOAD_SCHEME = {
	"target":Stats,
	"module":False,
	"arg":(),
	"kwargs":{},
	"dependes":[]
}