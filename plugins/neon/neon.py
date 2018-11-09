#!/usr/bin/env python3
import os
import ssl
import sys
import time
import random
import socket
import signal
import binascii
import threading as th
from traceback import format_exc as Trace


from ...base.plugin import Plugin
from ...modules import crypto
from ..stats import stats_scheme
from .request import Request
from .response import Response
from .utils import *

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
				'use_neon_server' 	: False,
			}
			self.cfg = {}
			for i in defaults:
				self.cfg[i] = kwargs[i] if i in kwargs else defaults[i]

			self._run = True
			self._th = None
			self._rng = random.random() * 10**2
		
			self.Hosts = ['any']
			self.Path = '/'

			if self.cfg['site_directory'].endswith("/"):
				self.cfg['site_directory'] = self.cfg['site_directory'][:-1]

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
				self.P.add_plugin(key="stats",**stats_scheme).init_plugin(key="stats",export=False)
			if 'crypto' not in self:
				self.P.add_module(key="crypto",target=crypto).init_plugin(key="crypto",export=False)

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

	def gen_id(self):
		self._rng += 1
		st = binascii.hexlify(self.P.crypto._hash(str(self._rng).encode('utf-8'))[:2]).decode()
		az = []
		while len(st) > 0:
			az.append(st[:4])
			az.append("-")
			st = st[4:]
		return "".join(az[:-1])

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
	def get(self,req):
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
				req.static_file(path)
		except Exception as e:
			self.Error(e)
			data = NOT_FOUND 
			headers = [CONTENT_HTML,"Connection: close"] 
			code = 404

		req.resp.set_data(data)
		req.resp.set_headers(headers)
		req.resp.set_code(code)
		return req.resp

	def choose_module(self,request):
		res = None
		if request.method not in HTTP_METHODS:
			request.Debug('{ip}: Unallowed method "{method}" ({url})'.format(**request.dict()))
		elif request.http_version not in HTTP_VERSIONS:
			request.Debug('{ip}: Unallowed version "{method}" ({url})'.format(**request.dict()))
		elif "Host" not in request.headers:
			request.Debug("{ip}: No Host passed ({url})".format(**request.dict()))
		else:
			modules = sorted(list(filter(lambda x:(request.headers['Host'] in x.Host or "any" in x.Host) and request.url.startswith(x.Path),self.cfg['cgi_modules'])),reverse=True,key=lambda x:len(x.Path))
			if len(modules) > 0:
				module = modules[0]
			elif self.cfg['use_neon_server']:
				module = self
			else:
				module = None
			if module is None:
				request.Debug("{ip}: Handler not found ({url})".format(**request.dict()))
			else:
				request.Debug("Found handler: {name}".format(name=module.name))
				try:
					res = getattr(module,request.method.lower())(request)
					#res = module.handler(request)
				except Exception as e:
					request.Error("cgi handler: {ex}".format(ex=e))
					request.Debug("cgi handler: {ex}".format(ex=Trace()))
					res = self.P.init_plugin(key="response",code=500,headers=[CONTENT_HTML],data=SMTH_HAPPENED)
		request.send(res)
		request.Notify("{code} - {url} ? {args}".format(**request.dict(),code=res.code))
		try:
			request.after_handler()
		except Exception as e:
			request.Error("cgi after-handler: {ex}".format(ex=e))
			request.Debug("cgi handler: {ex}".format(ex=Trace()))
	
	
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
			try:
				self.P.stats.add(key="ip",value=addr[0])
				self.P.stats.add(key="connections")
				conn = self.wrap_ssl(conn) if _ssl else conn # only if self.cfg['use_ssl'] == True
				request = self.P.init_plugin(key="request",conn=conn,addr=addr,id=self.gen_id(),**self.cfg)
				if request.FATAL:
					self.Error("request-init: {}".format(request.errmsg))
				else:
					request.set_ssl(_ssl)
					request.set_secure((self.cfg['use_ssl'] and _ssl) or (not self.cfg['use_ssl']))
					self.choose_module(request)
				conn.close()

			except Exception as e:
				self.Warring('Another-Deal: (%s) %s'%(addr[0],e))
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
	# Module - Module/Object that has special interface:
	# 	Path - str - begginig of all urls that this module handle
	#	Host - list/set of all possible values of Host HTTP-header that associates with this module (or ["any"] for all Hosts)
	#	get(request) 		- handler for GET requests 		; if not presented -> send 404 by default
	# 	post(requests) 		- handler for POST requests 	; if not presented -> send 404 by default
	# 	head(requests) 		- handler for HEAD requests 	; if not presented -> send 404 by default
	# 	put(requests) 		- handler for PUT requests 		; if not presented -> send 404 by default
	# 	delete(requests) 	- handler for DELETE requests 	; if not presented -> send 404 by default
	# 	trace(requests) 	- handler for TRACE requests 	; if not presented -> send 404 by default
	# 	connect(requests) 	- handler for CONNECT requests 	; if not presented -> send 404 by default
	# 	options(requests) 	- handler for OPTIONS requests 	; if not presented -> send 404 by default
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