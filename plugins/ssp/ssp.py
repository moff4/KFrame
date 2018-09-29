#!/usr/bin/env python3

from kframe.base import Plugin

from traceback import format_exc as Trace

#
# Simple Secure Protocol
# Wrapper over socket
# FIXME: Add authetication methods
#
class SSP(Plugin):
	#
	# conn - raw socket
	# kwargs:
	#	keys - tuple ( private , public ) - keys for DH
	#		if not passed - generate new pair of keys
	# 	ukm - User Key Material - parametr for DH 
	#		if not passed - generate new ukm
	#	auth - bool - should ask peer to authenticate
	#		if not passed - auth == False
	# 	known_users - list of unmarshaled public - keys of known peers
	#		if not passed - empty list
	#
	def init(self,conn,**kwargs):
		self.conn = conn
		self.private , self.public = kwargs['keys'] if 'keys' in kwargs else self['crypto'].generate_key_pair()
		self.ukm = kwargs['ukm'] if 'ukm' in kwargs else self['crypto'].gen_ukm()
		self.auth = kwargs['auth'] if 'auth' in kwargs else False
		self.known_users = kwargs['known_users']  if 'known_users' in kwargs else []
		self.cipher = None
		return self

	#
	# Marshal , encrypt, send!
	#
	def _send(self,data,iv,system=False):
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
	#
	def connect(self):
		def int_to_bytes(x):
			st = []
			while x > 0:
				st.append(x%256)
				x //= 256
			return bytes(st)
		try:
			self.conn.send(self['art'].marshal({
					"ukm":self.ukm,
					"pub":self['crypto'].export_public_key(self.public),
					"auth":self.auth
				}))
			res = self['art'].unmarshal(fd=self.conn)
			
			if 'ukm' not in res or 'pub' not in res:
				return False , "Bad peer's answer"
			self.peers_ukm = int_to_bytes(res['ukm'])
			self.mine_ukm = int_to_bytes(self.ukm)
			secret = self['crypto'].diffie_hellman(self.private,self['crypto'].import_public_key(res['pub']),res['ukm'] ^ self.ukm)
			
			self.cipher = self['crypto'].Cipher(secret)

			# FIXME
			if res["auth"]:
				# send proof
				# wait for answer
				pass
			if self.auth: # deadlock ?????? 
				# wait for proof
				# answer
				pass


			return True , "Success!"
		except Exception as e:
			return False , str(e)
	#
	# recive data from peer
	# return tuple ( Flag of success , recived data )
	# Flag is True in case of success
	# or False in case of error
	#
	def recv(self):
		try:
			res = self['art'].unmarshal(fd=self.conn,mask=self.peers_ukm)
			if 3 not in res:
				raise ValueError("IV was nto passed")
			if 1 in res:
				res = self.cipher.decrypt(data=res[1],iv=res[3])
				return True , self['art'].unmarshal(res,mask=self.peers_ukm)
			elif 2 in res:
				code = self.cipher.decrypt(data=res[2],iv=res[3])
				if code == b"1":
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
		try:
			data = self['art'].marshal(data,mask=self.mine_ukm)
			return self._send(data,self['crypto'].gen_iv())
		except Exception as e:
			self("Connetion (S) closed: %s"%(e))
			self.conn.close()
			return False

	#
	# close connection
	#
	def close(self):
		try:
			self._send(data=b"1",iv=self['crypto'].gen_iv(),system=True)
			self.conn.close()
		except:
			pass