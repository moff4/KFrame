#!/usr/bin/env python3
import os
import ssl
import sys
import time
import socket
import signal
import threading as th
from traceback import format_exc as Trace


from ...base.plugin import Plugin
from ..stats import DEFAULT_LOAD_SCHEME as stat_scheme
from .request import Request
from .response import Response
from .utils import *

MAX_DATA_LEN 		= 4*2**10
MAX_HEADER_COUNT	= 32
MAX_HEADER_LEN 		= 2*2**10

class Neon(Plugin):
	def init(self,**kwargs):
		try:
			defaults = {
				'only_local_hosts'	: False,
				'http_port'			: 8080,
				'https_port'		: 8081,
				'use_ssl'			: False,
				'ca_cert'			: "./ca.cert",
				'keyfile'			: "./key.pem",
				'certfile'			: "./cert.pem",
				'site_directory'	: './var',
				'cgi_modules'		: [],
				'max_data_length'	: MAX_DATA_LEN,
				'max_header_count' 	: MAX_HEADER_COUNT,
				'max_header_length'	: MAX_HEADER_LEN,
				'threading' 		: False,
				'user_neon_server' 	: True,
			}
			self.cfg = {}
			for i in defaults:
				self.cfg[i] = kwargs[i] if i in kwargs else defaults[i]

			self._run = True
			self._th = None
		
			self.Hosts = ['any']
			self.Path = '/'

			if self.cfg['use_ssl']:
				self.raw_socket = self.open_port(use_ssl=False,port=self.cfg['http_port'])
				self.socket = self.open_port(use_ssl=True,port=self.cfg['https_port'])
				self.context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH,cafile=self.cfg['ca_cert'])
				self.context.load_cert_chain(certfile=self.cfg['certfile'], keyfile=self.cfg['keyfile'])
			else:
				self.socket = self.open_port(use_ssl=False,port=self.cfg['http_port'])
				self.context = None
			
			
			self.P.add_plugin(key="request",target=Request,autostart=False,module=False)
			self.P.add_plugin(key="response",target=Response,autostart=False,module=False)

			if 'stats' not in self:
				self.P.add_plugin(key="stats",**stat_scheme).init_plugin(key="stats",export=False)

			self.P.stats.init_stat(key="start-time"      ,type="single",default=time.time())
			self.P.stats.init_stat(key="requests-success",type="inc")
			self.P.stats.init_stat(key="requests-failed" ,type="inc")
			self.P.stats.init_stat(key="connections"     ,type="inc")
			self.P.stats.init_stat(key="ip"              ,type="set")

			self.FATAL = False
			self.errmsg = '%s initialized successfully'%(self.name)
		except Exception as e:
			self.FATAL = True
			self.errmsg = "%s: %s"%(self.name,str(e))

	#========================================================================
	#                                  UTILS
	#========================================================================

	def open_port(self,use_ssl=False,port=80):
		host = '' # here we can make some restrictions on connections
		j = 1
		while j <= 3:
			try:
				sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				sock.bind((host, port))
				sock.listen(5)
				sock.settimeout(60*3600)
				return sock
			except Exception as e:
				time.sleep(j*5);
				self("open-port %s : %s"%(port,e),_type="debug")
			j += 1
		raise RuntimeError("Could not open port (%s)"%(port))

	#
	# handler of original connection
	# return Response Object
	#
	def handler(self,req):
		def dirs(path):
			if not req.url.endswith("/"):
				req.url += "/"
			return DIR_TEMPLATE.format(cells="".join([ DIR_CELL_TEMPLATE.format(filename=file,**req.dict()) for file in os.listdir(path)]),**req.dict())
		path = self.cfg['site_directory'] + req.url
		code = 200
		try:
			if os.path.isdir(path):
				data = dirs(path)
				headers = [CONTENT_HTML]
			else:
				data = open(path,'rb').read()
				headers = [Content_type(req['url'])]
		except Exception as e:
			self.Error(e)
			data = NOT_FOUND 
			headers = [CONTENT_HTML,"Connection: close"] 
			code = 404
		return self.P.init_plugin(key="response",data=data,headers=headers,code=code)

	def choose_module(self,request):
		modules = sorted(map(lambda x:len(x.Path),filter(lambda x:request.headers['Host'] in x.Host and x.url.startswith(x.Path),self.cfg['cgi_modules'])),reverse=True)
		if len(modules) > 0:
			module = modules[0]
		elif self.cfg['user_neon_server']:
			module = self
		else:
			module = None
		if module is None:
			self.Debug("{ip}: Handler not found ({url})".format(**request.dict()))
			res = self.P.init_plugin(key="response",code=404,headers=[CONTENT_HTML],data=NOT_FOUND)
		else:
			self.Debug("Found handler: {name}".format(name=module.name))
			res = module.handler(request)
		request.send(res)
		request.after_handler()
	
	#========================================================================
	#                              DEMON TOOLS
	#========================================================================

	def check_thread(self):
		try:
			for i in self.thread_list:
				if not i.is_alive():
					i.join()
					self.thread_list.pop(self.thread_list.index(i))
		except Exception as e:
			self('check_thread: %s'%e)

	def wrap_ssl(self,conn):
		if self.context != None:
			conn = self.context.wrap_socket(conn, server_side=True)
		return conn

	def __alt_run(self,sock,port,_ssl=False):
		def another_deal(conn,addr):
			print('-')
			try:
				self.P.stats.add(key="ip",value=addr[0])
				conn = self.wrap_ssl(conn) if _ssl else conn # only if self.cfg['use_ssl'] == True
				self.Debug("Gonna create Reqeust-Object")
				request = self.P.init_plugin(key="request",conn=conn,addr=addr,cfg=self.cfg)\
					.set_ssl(_ssl)\
					.set_secure((self.cfg['use_ssl'] and _ssl) or (not self.cfg['use_ssl']))
				self.Debug("Gonna choose module-handler")
				self.choose_module(request)
				if 'stats' in self:
					self.P.stats.add('connections')
				
				#conn.close() ???

			except Exception as e:
				self.Debug('Another-Deal: (%s) %s'%(addr[0],Trace()))
				conn.close()
		self('Starting my work on port %s!'%port)
		try:
			self.thread_list = []
			while self._run:
				try:
					conn , addr = sock.accept()
					self.Debug("New: {ip}:{port}".format(ip=addr[0],port=addr[1]))
				except socket.timeout as e: # time to reopen port
					try:
						sock.close()
					except Exception as e:
						self('Err while opennig port')
						time.sleep(5)
					finally:
						if self.cfg['use_ssl']:
							port = https_port
						else:
							port = http_port
						sock = self.open_port(use_ssl=_ssl,port=port)
				
				if (not self.cfg['only_local_hosts']) or (self.cfg['only_local_hosts'] and any(lambda x:addr[0].startswith(x),private_ip)):
					if self.cfg['threading']:
						t = th.Thread(target=another_deal,args=(conn,addr))
						t.start()
						self.thread_list.append(t)
					else:
						another_deal(conn,addr)
				else:
					self.Debug("Not private_ip")
					conn.close()
				time.sleep(0.1)
				self.check_thread()
			
		except Exception as e:
			self('Listen port error: %s'%e)
			time.sleep(5)
		except KeyboardInterrupt:
			self('got SIGINT: stopping')			
		finally:
			sock.close();

	def beep(self,obj,thread=True):
		try:
			if not thread and obj != None:
				os.kill(obj.pid,signal.SIGINT)
		except:
			pass
	def _open(self):
		def open(port):
			try:
				# in Windows u cannot stop program while it's listening the port
				sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				sock.connect(("0.0.0.0",port))
				sock.close()
			except:
				pass
		if self.cfg['use_ssl']:
			open(self.cfg['https_port'])
		open(self.cfg['http_port'])

	def _loop(self):
		try:
			self._threads = []
			if self.cfg['use_ssl']:
				self._threads.append([th.Thread(target=self.__alt_run,args=[self.socket,self.cfg['https_port'],True]),self.cfg['https_port']])
				self._threads[-1][0].start()
				self._threads.append([th.Thread(target=self.__alt_run,args=[self.raw_socket,self.cfg['http_port'],False]),self.cfg['http_port']])
				self._threads[-1][0].start()
				while self._run:
					time.sleep(1)
			else:
				self.__alt_run(self.socket,_ssl=False,port=self.cfg['http_port'])
		except Exception as e:
			self('web: run: Exception: %s'%e)
		except KeyboardInterrupt:
			self('web: run: KeyboardInterrupt')
		finally:
			self._run = False
			self('web: socket closed')
			self._open()
			for i in self._threads:
				self.beep(i[0])
				i[0].join()
		self('Finishing my work!')		

	#========================================================================
	#                                USER API
	#========================================================================

	#
	# add new cgi_modules
	#
	def add_site_module(self,module):
		self.cfg['cgi_modules'].append(module)

	#
	# start web-server
	#
	def start(self):
		self._th = th.Thread(target=self._loop)
		self._th.start()

	#
	# stop web-server
	#
	def stop(self,wait=True):
		self._run = False
		self.beep(self._th)
		self._open()
		if wait and not self._th is None:
				self._th.join()