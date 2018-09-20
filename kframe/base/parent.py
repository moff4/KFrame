#!/usr/bin/env python3

import time 
import sys
from traceback import format_exc as Trace

#
# cfg - module conf
# plugins - dict : key as str => dict { target -> module/class, dependes -> list of key, module -> True if that's module, args -> tuple of args for plugins (optional) ]
#
class Parent:
	def __init__(self,cfg,plugins=None,name="KFrame"):
		try:
			self.cfg = cfg
			self.name = name

			# variables
			self.debug = '--debug' in sys.argv[1:]
			self.plugins = {}
			self.modules = {}
			self.RUN_FLAG = True # U can use this falg as a signal to stop program

			self._argv_p = {}    # keep params and flags
			self._argv_rules = {}# collected rules from all plugins
			self._my_argvs = {
				'-h' 		:{'critical':False,'description':"See this message again"},
				'-?' 		:{'critical':False,'description':"See this message again"},
				'--help'	:{'critical':False,'description':"See this message again"},
				'--stdout' 	:{'critical':False,'description':"Extra print logs to stdout"},
				'--debug' 	:{'critical':False,'description':"Verbose log"},
				'--no-log' 	:{'critical':False,'description':"Do not save logs to log.file"},

			}

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

	def collect_argv(self):
		rules = {}
		for i in self.plugins:
			r = self.plugins[i].get_argv_rules()
			for j in r:
				if not j in rules:
					rules[j] = r[j]
				else:
					rules[j]['critical'] = rules[j]['critical'] or r[j]['critical']
		self._argv_rules = rules
		self._argv_rules.update(self._my_argvs)

	#
	# parse argv according to plugin's rules
	#
	def parse_argv(self):
		self.collect_argv()
		l = list(filter(lambda x:self._argv_rules[x]['critical'],self._argv_rules.keys()))
		for arg in sys.argv[1:]:
			if '=' in arg:
				key = arg.split('=')
				value = arg[len(key)+1:]
			else:
				key = arg
				value = True
			self._argv_p[key] = value
			if key in l:
				l.pop(l.index(l))
		if len(l) > 0:
			self.FATAL = True
			self.errmsg = ["Parent: parse-argv: not all critical params were passed : %s"%l]

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
					a ,b = self.init_plugin(key=i,plugin_name=i,args=self.plugin_t[i]['args'],kwargs=self.plugin_t[i]['kwargs'])
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
	def init_plugin(self,key,plugin_name,args,kwargs):
		try:
			if self.plugin_t[key]['module']:
				self.modules[key] = self.plugin_t[plugin_name]['target']
				return True , "\t%s loaded successfully"%(plugin_name)
			else:
				self.plugins[key] = self.plugin_t[plugin_name]['target'](self,plugin_name,args,kwargs)
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
			self.log("\t"+i,_type=_type)

	#
	# print all expected 
	#
	def print_help(self):
		def topic(name):

			st = name
			while len(st) < 20:
				st = " %s "%st
			st = '|%s|'%st
			x = '-' if len(st)%2 else ''
			return "".join([" " for i in range(16)]) + "+-------------------%s-+\n"%x \
			+ "".join([" " for i in range(16)]) + st + "\n" \
			+ "".join([" " for i in range(16)]) + "+-------------------%s-+\n"%x 
		def insert_tabs(txt,tabs):
			return "".join(list(map(lambda x: "".join(["\t" for i in range(tabs)]) + x,txt.split("\n"))))
		st = topic(self.name) + "Flags:\n"
		self.collect_argv()
		for i in self._argv_rules:
			st += "\t{key}\n{desc}{critical}\n\n".format(key=i,desc=insert_tabs(self._argv_rules[i]['description'],tabs=2),critical="\n\t\tCritical!" if self._argv_rules[i]['critical'] else "")
		print(st)
	#
	# start each plugins
	#
	def run(self):
		self("PARENT: start plugins",_type="debug")
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
				"kwargs"	: kwargs['kwargs'] if 'kwargs' in kwargs else {},
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
	# return param's value if param was passed
	# return True as bool if that's was flag
	# else return None if nothing was passed
	#
	def get_param(self,key):
		return self._argv_p[key] if key in self._argv_p else None

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
		if '-h' in sys.argv[1:] or '-?' in sys.argv[1:] or '--help' in sys.argv[1:]:
			self.print_help()
			return
		self.print_errmsg()
		if self.FATAL:
			return
		else:
			try:
				self.parse_argv()
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