#!/usr/bin/env python3

class Plugin:
	def __init__(self,parent,plugin_name,args):
		try:
			self.parent = parent
			self.name = plugin_name
			
			self.FATAL = True
			self.errmsg = "initialized successfully - %s"%(self.name)

			if 'init' in dir(self):
				self.init(*args)

		except Exception as e:
			self.FATAL = True
			self.errmsg = "%s: %s"%(self.name,e)


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