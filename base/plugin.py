#!/usr/bin/env python3

from traceback import format_exc as Trace

class Plugin:
	def __init__(self,parent,plugin_name,args,kwargs):
		try:
			self.parent = parent
			self.P = self.parent
			self.name = plugin_name
			
			self._params = {}

			self.FATAL = False
			self.errmsg = "initialized successfully - %s"%(self.name)

			try:
				self.init(*args,**kwargs)
			except Exception as e:
				self("__init__ - init : %s"%Trace(),_type="error")

		except Exception as e:
			self.FATAL = True
			self.errmsg = "%s: %s"%(self.name,e)

	#
	# export argv rules for Parent
	#
	def get_argv_rules(self):
		return self._params


	#==========================================================================
	#                            USER API
	#==========================================================================

	#
	# debug log function
	#
	def Debug(self,st):
		self.log(st=st,_type="debug")

	#
	# debug log function
	#
	def Error(self,st):
		self.log(st=st,_type="error")

	#
	# debug log function
	#
	def Warring(self,st):
		self.log(st=st,_type="warring")

	#
	# debug log function
	#
	def Notify(self,st):
		self.log(st=st,_type="notify")

	#
	# local log function
	#
	def log(self,st="",_type="notify"):
		self.parent("%s: %s"%(self.name,st),_type=_type)

	#
	# local log function
	#
	def __call__(self,st="",_type="notify"):
		self.log(st=st,_type=_type)


	#
	# operator overload
	# return already initialized plugin or module
	# or return None
	#
	def __getitem__(self,key):
		return self.parent.get_plugin(key)

	#
	# operator overload
	# return True if plugin or module exists
	# or False if not
	#
	def __contains__(self,key):
		return key in self.parent

	#
	# return param's value if param was passed
	# return True as bool if that's was flag
	# else return None if nothing was passed
	#
	def get_param(self,key,default=None):
		return self.parent.get_param(key=key,default=default)

	#
	# CAN BE OVERLOADED
	# method to start you main job
	#
	def start(self):
		pass
	
	#
	# CAN BE OVERLOADED
	# method to stop you main job
	#
	def stop(self,wait=True):
		pass

	#
	# add expected key to storage
	# flag as bool - True if we expect flag or False if param
	# critical as bool - True if this param/flag is critical (default: False)
	# description as str - some descrition for human (default: "")
	#
	def expect_argv(self,key,critical=False,description=""):
		self._params[key] = {
			'critical':critical,
			'description':description,
		}
