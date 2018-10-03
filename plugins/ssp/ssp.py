#!/usr/bin/env python3

from kframe.base import Plugin

from traceback import format_exc as Trace
from os import urandom
from socket import timeout as Timeout

CODE_CLOSE 			= b"1"
CODE_AUTH_SUCCESS 	= b"2"
CODE_AUTH_FAILED 	= b"3"

#
# Simple Secure Protocol
# Wrapper over socket
#
class SSP(Plugin):
	#
	# kwargs:
	# 	conn - raw socket
	#	keys - tuple ( private , public ) - keys for DH
	#		if not passed - generate new pair of keys
	# 	ukm - User Key Material - parametr for DH 
	#		if not passed - generate new ukm
	#	auth - bool - should ask peer to authenticate
	#		if not passed - auth == False
	# 	known_users - list of ART-marshaled public keys with random=False - public keys of known peers
	#		if not passed - empty list
	#
	def init(self,**kwargs):
		self.conn = kwargs['conn'] if 'conn' in kwargs else None
		self.private , self.public = kwargs['keys'] if 'keys' in kwargs else self['crypto'].generate_key_pair()
		self.ukm = kwargs['ukm'] if 'ukm' in kwargs else self['crypto'].gen_ukm()
		self.auth = kwargs['auth'] if 'auth' in kwargs else False
		self.known_users = kwargs['known_users']  if 'known_users' in kwargs else []
		self.cipher = None
		self._chan = False

		self.peers_pub_key 	= b''
		self.peers_ukm 		= b''
		self.mine_ukm 		= b''

		return self

	#
	# Marshal , encrypt, send!
	# if system - send system code as bytes()
	# code = 1 - close connection
	# code = 2 - auth successeded
	# code = 3 - auth failed ; close connection
	#
	def _send(self,data,system=False):
		iv = self['crypto'].gen_iv()
		data = self['art'].marshal( 
			{
				(1 + int(system)):self.cipher.encrypt(data=data,iv=iv),
				3:iv,
			},mask=self.mine_ukm)

		self.conn.send(data)

	#==========================================================================
	#                                 USER API
	#==========================================================================

	#
	# generate shared secret and start encrypted connection
	# kwargs can be passed same as for SSP.init()
	# return tuple ( Flag , msg )
	# Flag is True if conenction established
	# or False when error happened
	#
	def connect(self,**kwargs):
		def int_to_bytes(x):
			st = []
			while x > 0:
				st.append(x%256)
				x //= 256
			return bytes(st)

		self.conn = kwargs['conn'] if 'conn' in kwargs else self.conn
		self.private , self.public = kwargs['keys'] if 'keys' in kwargs else (self.private , self.public)
		self.ukm = kwargs['ukm'] if 'ukm' in kwargs else self.ukm
		self.auth = kwargs['auth'] if 'auth' in kwargs else self.auth
		self.known_users = kwargs['known_users']  if 'known_users' in kwargs else self.known_users

		try:
			pkg = {
				"ukm":self.ukm,
				"pub":self['crypto'].export_public_key(self.public),
			}
			
			self.conn.send(self['art'].marshal(pkg))
			res = self['art'].unmarshal(fd=self.conn)
			
			if 'ukm' not in res or 'pub' not in res:
				return False , "Bad peer's answer"
			self.peers_ukm = int_to_bytes(res['ukm'])
			self.mine_ukm = int_to_bytes(self.ukm)
			peers_key = self['crypto'].import_public_key(res['pub'])
			self.peers_pub_key = self['art'].marshal(peers_key,random=False)
			secret = self['crypto'].diffie_hellman(self.private,peers_key,res['ukm'] ^ self.ukm)
			peers_key = self['art'].marshal(peers_key,random=False)

			self.cipher = self['crypto'].Cipher(secret)

			if self.auth and peers_key not in self.known_users:
				self._send(data=CODE_AUTH_FAILED,system=True)
				self.conn.close()
			else:
				self._send(data=CODE_AUTH_SUCCESS,system=True)
				self._chan = True

			if self.recv(system=True) == CODE_AUTH_SUCCESS:
				self._chan = True
				return True , "Success!"
			else:
				self._chan = False
				self.conn.close()
				return False , "Authentication failed"
		except Exception as e:
			return False , str(e)
	#
	# recive data from peer
	# return tuple ( Flag of success , recived data )
	# Flag is True in case of success
	# or False in case of error
	#
	def recv(self,system=False):
		if not self._chan:
			return False , None
		try:
			res = self['art'].unmarshal(fd=self.conn,mask=self.peers_ukm)
			if 3 not in res:
				raise ValueError("IV was not passed")
			if 1 in res:
				res = self.cipher.decrypt(data=res[1],iv=res[3])
				return True , self['art'].unmarshal(res,mask=self.peers_ukm)
			elif 2 in res:
				code = self.cipher.decrypt(data=res[2],iv=res[3])
				if system:
					return code
				if code == CODE_CLOSE:
					self.conn.close()
					return False , None
				else:
					self("Unknow service code: %s"%(code),_type="error")
			else:
				self("Unknow message: %s"%(res),_type="error")
			return self.recv()
		except Exception as e:
			self("Connetion (R) closed: %s"%(e),_type="debug")
			self.conn.close()
			return False , None

	#
	# send data to peer
	# return True in case of success
	# or False in case of error
	#
	def send(self,data):
		if not self._chan:
			return False
		try:
			data = self['art'].marshal(data,mask=self.mine_ukm)
			self._send(data)
			return True
		except Exception as e:
			self("Connetion (S) closed: %s"%(e))
			self.conn.close()
			return False

	#
	# equal to socket.settimeout()
	#
	def settimeout(self,value):
		if self.conn:
			self.conn.settimeout(value)

	#
	# close connection
	#
	def close(self):
		try:
			self._send(data=CODE_CLOSE,system=True)
			self.conn.close()
		except:
			pass