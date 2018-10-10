#!/usr/bin/enc python3.5
import ssl
import sys
import time
import socket
import signal
import threading as th
from traceback import format_exc as Trace
from ...base.plugin import Plugin

from .utils import *

private_ip =  set(['10.',  '192.168.',  '0.0.0.0',  '127.0.0.' ] +  [("100.%s."%i) for i in range(64,128)]  +  [("172.%s."%i) for i in range(16,32)])

http_code_msg = {
	200:'OK',
	206:'Partial Content',
	304:'Not Modified',
	307:'Temporary Redirect',
	308:'Permanent Rederict',
	404:'Not found'
}

ALLOWED_HTTP_METHODS = ['GET','POST','HEAD']

NOT_FOUND = '''
<html><head>
<title>404 Not Found</title>
</head><body>
<h1>Not Found</h1>
<p>The requested URL was not found on this kek-server.</p>
</body></html>
'''

CONTENT_HTML 		= 'Content-type: text/html; charset=utf-8'
CONTENT_JS 			= 'Content-type: application/javascript'
CONTENT_JSON 		= 'Content-type: text/json'

FUCK_U 				= NOT_FOUND , [CONTENT_HTML] , 404

MAX_DATA_LEN 		= 4*2**10
MAX_HEADER_COUNT	= 32
MAX_HEADER_LEN 		= 2*2**10

#
# class for web-server
# **kwargs - configuration parametrs {
#       only_local_hosts 	: bool
#       use_ssl 			: bool
#       http_port 			: int
#       https_port 			: int
#       ca_cert 			: path as str
#       keyfile 			: path as str
#       certfile 			: path as str
#       cgi_bin_dir 		: str ( self.Path + cgi_bin_dir == prefix of url for dinamic requests)
#	    site_directory 		: str
#	    cgi_modules 		: list of Objects/Modules with CGI-plugin interfce
#		max_data_length		: max size of data in bytes in one request
#		max_header_count	: max number of headers in one request
#		max_header_length	: max size of one header in bytes
#	 }
# }
#
# CGI-plugin interface :
#  - method handler(req as dict, secure - True if SSL or False if not secure)
#    must return tuple ( data (bytes or str) , Headers (list of str) , HTTP-CODE (int) )
#  - method cgi(req as dict, secure - True if SSL or False if not secure)
#    must return tuple ( data (bytes or str) , Headers (list of str) , HTTP-CODE (int) )
#  - Hosts - list of str (list of domain names) or ['any']
#  - Path - path identifier for handler-module (str)
#
class Web(Plugin):
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
				'cgi_bin_dir'		: "cgi/",
				'site_directory'	: './var',
				'cgi_modules'		: [self],
				'max_data_length'	: MAX_DATA_LEN,
				'max_header_count' 	: MAX_HEADER_COUNT,
				'max_header_length'	: MAX_HEADER_LEN,
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
			else:
				self.socket = self.open_port(use_ssl=False,port=self.cfg['http_port'])
			
			self.main_requested = 0;

			if 'stats' in self:
				self['stats'].init_stat(key="start-time"      ,type="single",default=time.time())
				self['stats'].init_stat(key="requests-success",type="inc")
				self['stats'].init_stat(key="requests-failed" ,type="inc")
				self['stats'].init_stat(key="connections"     ,type="inc")
				self['stats'].init_stat(key="ip"              ,type="set")

			self.FATAL = False
			self.errmsg = '%s initialized successfully'%(self.name)
		except Exception as e:
			self.FATAL = True
			self.errmsg = "%s: %s"%(self.name,str(e))

	def open_port(self,use_ssl=False,port=80):
		host = '' # here we can make some restrictions on connections

		if use_ssl:
			self.context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH,cafile=self.cfg['ca_cert'])
			self.context.load_cert_chain(certfile=self.cfg['certfile'], keyfile=self.cfg['keyfile'])
		else:
			self.context = None

		j = 1
		while j <= 10:
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
	# should return tuple ( data , list of HTTP headers , HTTP code)
	#
	def cgi(self,req,secure):
		# FUCK EVERY BODY
		return '<h1>Error: cgi not implemented<h1>', [CONTENT_HTML] , 404

	#
	# handler of original connection
	#
	def handler(self,req,secure):
		if 'firewall' in self:
			self['firewall'].banned(req['addr'][0],code=False,react=True)
		if req['url'].endswith('/'):
			req['url'] += 'index.html'
		try:
			return open(self.cfg['site_directory'] + req['url'],'rb').read(), [Content_type(req['url'])] , 200
		except Exception as e:
			self(e,_type="error")
			return NOT_FOUND , [CONTENT_HTML,"Connection: close"] , 404

	#
	# read and parse data from socket
	#
	def read_request(self,conn,addr):
		request = {
			'url':b'',
			'args':{},
			'method': b'',
			'http_version': b'',
			'headers': {},
			'data':b'',
			'addr':addr,
			'postfix':b''
		}
		if 'stats' in self:
			self['stats'].add('ip',addr[0]) # add ip to set of connections
		st = readln(conn,max_len=self.cfg['max_header_length'])
		while 0 < len(st) and st[:1] != b' ':
			request['method'] += st[:1]
			st = st[1:]
		st = st[1:]
		while 0 < len(st) and st[:1] not in [b' ',b'?',b'#']:
			request['url'] += st[:1]
			st = st[1:]
		request['url'] = urldecode(request['url'])
		if st[:1] == b'?':
			while (st[:1] != b' ') and len(st) > 0:
				st = st[1:]
				key = b''
				val = b''
				while 0 < len(st) and st[:1] != b'=':
					key += st[:1]
					st = st[1:]
				st = st[1:]
				while 0 < len(st) and st[:1] != b' ' and st[:1] != b'&':
					val += st[:1]
					st = st[1:]
				request['args'][key.decode('utf-8')] = urldecode(val)
		if st[:1] == b'#':
			st = st[1:]
			val = b''
			while st[:1] != b' ':
				val += st[:1]
				st = st[1:]
			request['postfix'] = val
		st = st[1:]
		while 0 < len(st) and st[:1] != b' ':
			request['http_version'] += st[:1]
			st = st[1:]

		header_count = 0
		while True:
			value = ''
			st = readln(conn,max_len=self.cfg['max_header_length']).decode('utf-8')
			if st == '':
				break
			else:
				st = st.split(':')
			key = st[0]
			for i in st[1:]:
				if len(value)>0:
					value+=':'
				value += i
			if len(value) > 0:
				while (ord(value[0]) <= 32):
					value = value[1:]
					if len(value) <= 0:
						break
			if len(value) > 0:
				while (ord(value[-1]) <= 32):
					value = value[:-1]
					if len(value) <= 0:
						break

			if key in request['headers']:
				request['headers'][key].append(value)
			else:
				request['headers'][key] = [value]
			header_count += 1
			if header_count >= self.cfg['max_header_count']:
				raise RuntimeError("Too many headers")

		for i in ['http_version','url','method']:
			request[i] = request[i].decode('utf-8')

		for i in request['args']:
			request['args'][i] = request['args'][i].decode('utf-8')

		if 'Content-Length' in request['headers']:
			_len = int(request['headers']['Content-Length'][0])
			if _len >= self.cfg['max_data_length']:
				raise RuntimeError("Too much data")
			request['data'] = conn.recv(_len)
		return request

	def parse_request(self,conn,req,secure=False):
		try:
			if 'firewall' in self:
				if self['firewall'].banned(req['addr'][0]):
					self("BLACK-LISTED IP: %s"%req['addr'][0],_type="notify")
					return True

			if req['method'] not in ALLOWED_HTTP_METHODS:
				raise RuntimeError('unknown method %s'%(req['method']))

			# cookies import :D
			if 'cookies' in self:
				req['cookies'] = self['cookies'](self.parent,'cookies',args={req})

			site_extensions = []
			if 'Host' in req['headers']:
				host = req['headers']['Host'][0]
				self('host - %s'%host)
				try:
					for i in self.cfg['cgi_modules']:
						if host in i.Hosts or 'any' in i.Hosts:
							site_extensions.append(i)
							break;
				except Exception as e:
					self("Searching for cgi module %s"%e)
			else:
				raise RuntimeError("No host header")

			az = []
			for i in site_extensions:
				if req['url'].startswith(i.Path):
					az.append([i,len(i.Path)])
			if len(az) <= 0:
				site_extension = self
			else:
				site_extension = list(sorted(az,key=lambda x:x[1],reverse=True))[0][0]

			self('%s (%s) : %s %s %s %s'%(req['addr'][0],host,req['method'],req['url'],req['args'],req['http_version']),_type="notify")
			if req['url'] in ['/','/index.html']:
				self.main_requested = 4;
			elif '..' in req['url']:
				raise RuntimeError('got ".." in request')
			if req['url'].startswith('%s%s'%(site_extension.Path,self.cfg['cgi_bin_dir'])):
				try:
					txt , extra_headers , CODE = site_extension.cgi(req,secure)
				except Exception as e:
					self('in runnning cgi module (%s) exception %s'%(site_extension.cgi,e))
					txt = NOT_FOUND
					extra_headers = []
					CODE = 404
			else:
				try:
					txt , extra_headers , CODE = site_extension.handler(req,secure)
				except Exception as e:
					self('in runnning handler module (%s) exception %s'%(site_extension.handler,e))
					txt = NOT_FOUND
					extra_headers = []
					CODE = 404

			# cookies export :D
			if 'cookies' in req and req['cookies'] != None:
					extra_headers += req['cookies'].export()

			headers = apply_standart_headers(extra_headers)
			if 'Content-Length' not in headers:
				headers += "Content-Length: %s\r\n"%(len(txt))

		except Exception as e:
			e = Trace()
			self('Parse answer: %s'%e)
			CODE = 404
			txt = NOT_FOUND
			headers = "Content-type: text/html; charset=utf-8\r\nConnection: close" 

		if type(txt) == str:
			txt = txt.encode('utf-8')
		conn.send(("%s %s %s\r\n%s\r\n"%(req['http_version'],CODE,http_code_msg[CODE],headers)).encode('utf-8'))
		conn.send(txt)
		if 'stats' in self:
			self['stats'].add('requests-'% "success" if CODE <= 400 else "failed" )
		self("%s %s %s"%(req['http_version'],CODE,http_code_msg[CODE]))
		return True


	def check_thread(self):
		try:
			for i in self.thread_list:
				if not i.is_alive():
					i.join()
					self.thread_list.pop(self.thread_list.index(i))
		except Exception as e:
			self('check_thread: %s'%e)

	#
	# return True if connection should be accepted
	# or False if not
	#
	def should_accept(self,addr):
		if 'firewall' in self:
			if self['firewall'].banned(addr[0]):
				self("BLACK-LISTED IP: %s"%addr[0],_type="notify")
				return False
		return len(self.thread_list) <= 10

	def wrap_ssl(self,conn):
		if self.context != None:
			conn = self.context.wrap_socket(conn, server_side=True)
		return conn

	def __alt_run(self,sock,port,_ssl=False):
		def deal_with_it(conn,addr):
			try:
				if _ssl:
					conn = self.wrap_ssl(conn) # only if self.cfg['use_ssl'] == True
				request = self.read_request(conn,addr)
				request['ssl'] = _ssl
				secure = (self.cfg['use_ssl'] and _ssl) or (not self.cfg['use_ssl'])
				self.parse_request(conn,request,secure=secure)
				if 'stats' in self:
					self['stats'].add('connections')
				conn.close()
			except Exception as e:
				self('Deal with it: (%s) %s'%(addr[0],e))
				conn.close()
		try:
			self.thread_list = []
			while self._run:
				try:
					conn , addr = sock.accept()
					# self('NEW: %s'%str(addr))
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
				
				boo = False
				if self.cfg['only_local_hosts']:
					for i in private_ip:
						if addr[0].startswith(i):
							boo = True
							break
				else:
					boo = True
				if boo:
					if self.should_accept(addr):
						t = th.Thread(target=deal_with_it,args=[conn,addr])
						t.start()
						self.thread_list.append(t)
					else:
						conn.close()
				if self.main_requested > 0:
					self.main_requested -=1
				else:
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
		self('Starting my work!')
		try:
			self._threads = []
			if self.cfg['use_ssl']:
				self._threads.append([Thread(target=self.__alt_run,args=[self.socket,self.cfg['https_port'],True]),self.cfg['https_port']])
				self._threads[-1][0].start()
				self._threads.append([Thread(target=self.__alt_run,args=[self.raw_socket,self.cfg['http_port'],False]),self.cfg['http_port']])
				self._threads[-1][0].start()
				while self._run:
					time.sleep(1)
			else:
				self.__alt_run(self.socket,_ssl=False,port=self.cfg['https_port'])
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
		if wait:
			if not self._th is None:
				self._th.join()


DEFAULT_LOAD_SCHEME = {
	"target":Web,
	"module":False,
	"arg":(),
	"kwargs":{},
	"dependes":['firewall','cookies','stats']
}