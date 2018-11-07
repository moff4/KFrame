#!/usr/bin/env python3

from ...base.plugin import Plugin
from .utils import *

class Response(Plugin):
	def init(self,data=None,headers=None,code=404,http_version="HTTP/1.1"):
		self.data 			= b"" if data is None else data
		self.headers 		= [] if headers is None else headers
		self.code 			= code
		self.http_version 	= http_version

	def set_code(self,code):
		self.code = code
		return self
	def add_header(self,header):
		self.headers.append(header)
		return self
	def add_headers(self,headers):
		self.headers += headers
		return self
	def set_data(self,data):
		self.data = data
		return self
	def set_http_verion(self,http_verion):
		self.http_version = http_version
		return self

	def export(self):
		st = []
		st.append("{http_version} {code} {code_msg}\r\n".format(http_version=self.http_version,code=self.code,code_msg=http_code_msg[self.code]))
		st.append("".join(["".join([i,"\r\n"]) for i in filter(lambda x:x != None and len(x) > 0,apply_standart_headers(self.headers + ["Content-Length: {length}".format(length=len(self.data))]))]))
		st.append("\r\n")
		st = "".join(st).encode() 
		return st + (self.data if type(self.data) == bytes else self.data.encode())