#!/usr/bin/env python3

import time 
import sys
from traceback import format_exc as Trace

#
# cfg - module conf
# plugins - dict : key as str => dict { target -> module/class, dependes -> list of key, module -> True if that's module, args -> tuple of args for plugins (optional) ]
#
class Parent:
	def __init__(self,cfg,plugins=None):
		try:
			self.cfg = cfg
			
			# variables
			self.debug = '--debug' in sys.argv[1:]
			self.plugins = {}
			self.modules = {}
			self.RUN_FLAG = True # U can use this falg as a signal to stop program

			self.log('---------------------------------------------')

			self.plugin_t = {} if plugins is None else plugins
			for pl in self.plugin_t:
				for i in ['target','module']:
					if i not in self.plugin_t[pl]:
						raise RuntimeError("%s plugin does not has propery %s"%(pl,i))
				


			self.FATAL = False
			self.errmsg = []

		except Exception as e:
			e = Trace()
			self.FATAL = True
			self.errmsg = ["Parent init : %s"%(e)]

	#
	# initialize plugins and modules
	#
	def _init_plugins(self):
		try:
			d = dict(self.plugin_t)
			az = []
			bz = list(self.plugin_t.keys())
			i = 0
			l = len(bz)
			while i < l and len(bz) > 0:
				for j in list(d.keys()):
					if d[j]['module']:
						d.pop(j)
						az.append(j)
						if j in bz:
							bz.pop(bz.index(j))
					else:
						if len(list(filter(lambda x:x in d,d[j]['dependes']))) <= 0:
							d.pop(j)
							az.append(j)
							if j in bz:
								bz.pop(bz.index(j))
				i+=1
			self.log("Load priority queue: %s"%(az),_type="debug")
			for i in az:
				try:
					a ,b = self.init_plugin(key=i,plugin_name=i,args=self.plugin_t[i]['args'])
					self.FATAL = self.FATAL or not a
					self.errmsg.append(b)
				except Exception as e:
					self.FATAL = True
					self.errmsg.append("-- plugin (%s) init: %s"%(i,e))
		except Exception as e:
			e = Trace()
			self.errmsg.append("Parent: init-plugins: %s"%e)
			self.FATAL = True

	#
	# initialize plugin with plugin_name
	# and save it with key
	# return True on success , extra msg (errmsg) 
	#
	def init_plugin(self,key,plugin_name,args):
		try:
			if self.plugin_t[key]['module']:
				self.modules[key] = self.plugin_t[plugin_name]['target']
				return True , "\t%s loaded successfully"%(plugin_name)
			else:
				self.plugins[key] = self.plugin_t[plugin_name]['target'](self,plugin_name,args)
				return not self.plugins[key].FATAL , self.plugins[key].errmsg
		except Exception as e:
			e = Trace()
			self.log("Parent: init plugin(%s): %s"%(plugin_name,e),_type="error")
			return False , "%s: Exception: %s"%(plugin_name,e)

	#
	# print plugins' initializations status
	#
	def print_errmsg(self):
		_type = "error" if self.FATAL else "notify"
		for i in self.errmsg:
			self.log(i,_type="\t"+_type)

	#
	# start each plugins
	#
	def run(self):
		for i in self.plugins:
			self.plugins[i].start()
		while self.RUN_FLAG:
			try:
				time.sleep(1.0)
			except KeyboardInterrupt:
				self.stop(lite=False)

	#========================================================================
	#                                USER API
	#========================================================================

	#
	# Add new plugin/module
	# kwargs:
	# -- must be --
	#	key as str - how u wanna call it
	#	target as class/module - smth that'll be kept here and maybe called
	# 	module as bool -
	# -- optional --
	#	dependes as list of str - list of other plugins/modules that must be initialized before this one
	#		ignored if kwagrs[module] == True
	#		Default: empty list
	#	args as tuple - tuple of arg that will be passed to init() (plugins only)
	# return True if plugin/module added to list of all plugins/modules
	# or False if not
	#
	def add_plugin(self,**kwargs):
		try:
			for i in ['key','target','module']:
				if i not in kwargs:
					return False , "Expected '%s'"%i
			self.plugin_t[kwargs['key']] = {
				"target"	: kwargs['target'],
				"module"    : kwargs['module'],
				"args"		: kwargs['args'] if 'args' in kwargs else (),
				"dependes"	: kwargs['dependes'] if 'dependes' in kwargs else [],
			}

			return True , "Success"
		except Exception as e:
			return False, "Exception: %s"%e

	#
	# initialize plugins and modules
	# return True in case of success
	# or False if not
	#
	def init_plugins(self):
		if self.FATAL:
			self.print_errmsg()
			return False
		self._init_plugins()
		return not self.FATAL
		

	#
	# return already initialized plugin or module
	# or return None
	#
	def get_plugin(self,key):
		if key in self.plugins:
			return self.plugins[key]
		elif key in self.modules:
			return self.modules[key]
		raise AttributeError('no plugin/module "%s"'%(key))

	#
	# operator overload
	# return already initialized plugin or module
	# or return None
	#
	def __getitem__(self,key):
		return self.get_plugin(key)

	#
	# operator overload
	# return True if plugin or module exists
	# or False if not
	#
	def __contains__(self,key):
		return key in self.plugins or key in self.modules

	#
	# return Class/Module for the key
	# NOT the initialized object!
	# or None in case of nothing was found
	#
	def get_class(self,key):
		return self.plugin_t[key]['target'] if key in self.plugin_t else None

	#
	# log function
	# st - message to save
	# _type | sence
	#	0 "notify"	|	Notify
	#	1 "warring"	|	Warring
	#	2 "error"	|	Error - default
	#	3 "debug"	|	Debug
	#
	def log(self,st,_type=0):
		_type = str(_type)
		yn = " Error "
		if _type in ["0","notify"]:
			yn = "Notify "
		elif _type in ["1","warring"]:
			yn = "Warring"
		elif _type in ["3","debug"]:
			if not self.debug:
				return
			yn = " Debug "
		st = "%s -:- %s : %s"%(time.strftime(self.cfg.SHOW_TIME_FORMAT,time.localtime()),yn,st)
		if '--stdout' in sys.argv[1:]:
			print(st)
		if '--no-log' not in sys.argv[1:]:
			f = open(self.cfg.LOG_FILE,'ab')
			f.write(st.encode('utf-8') + b'\n')
			f.close()

	#
	# same as log()
	#
	def __call__(self,st,_type=0):
		self.log(st,_type)

	#
	# start program
	#
	def start(self):
		if self.FATAL:
			self.print_errmsg()
		else:
			try:
				self.run() 
			except Exception as e:
				e = Trace()
				self.log("Twin: start: %s"%(e),_type="error")

	#
	# stop all plugins
	#
	def stop(self,lite=True):
		self.RUN_FLAG = False
		for i in self.plugins:
			self.plugins[i].stop(wait=False)
		if not lite:
			for i in self.plugins:
				self.plugins[i].stop(wait=True)