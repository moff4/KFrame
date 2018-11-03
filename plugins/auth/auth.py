#!/usr/bin/env python3

from ...base.plugin import Plugin
from ...plugins import crypto
from ..stats import DEFAULT_LOAD_SCHEME as stat_scheme
from ..sql import DEFAULT_LOAD_SCHEME as sql_scheme

class Auth(Plugin):
	#
	# kwargs same as for SQL
	# maybe + smth else 
	#
	def init(self,**kwargs):

		if 'stats' not in self:
			self.P.add_plugin(key="stats",**stat_scheme).init_plugin(key="stats",export=False)
		if 'crypto' not in self:
			self.P.add_module(key="crypto",target=crypto).init_plugin(key="crypto",export=False)
		if 'sql' not in self:
			self.P.add_plugin(key="sql",**sql_scheme).init_plugin(key="sql",export=False,**kwargs)
