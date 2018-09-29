#!/usr/bin/env python3

from os import urandom

INT_POS 	= 1
INT_NEG 	= 2
FLOAT_POS 	= 3
FLOAT_NEG 	= 4
BYTES 		= 5
STRING 		= 6
LIST  		= 7
MAP 		= 8
TRUE 		= 9
FALSE 		= 10
NULL 		= 11

class Coder:
	def __init__(self,data,random=True):
		self.result = b""
		self.data = data
		self.rand = random

	#
	# generate type with noice
	#
	def _gen_type(self,t):
		return bytes([ t | (urandom(1)[0] & 0xF0) ]) if self.rand else bytes([t])

	#
	# Positive Integer
	#
	def _int(self,data,just=False):
		if data != 0:
			st = []
			sign = data < 0
			data = -data if sign else data
			while data > 0:
				st.insert(0,data % 128)
				data //= 128
			st[-1] |= 0x80
			st = bytes(st)
		else:
			st = b"\x80"
		return st if just else self._gen_type(INT_NEG if sign else INT_POS) + st

	#
	# Float
	#
	def _float(self,data,just=False):
		a = data
		sign = a < 0
		c = 0
		while a != round(a):
			a *= 10
			c += 1
		st = self._int(int(a),just=True) + self._int(int(c),just=True)
		return st if just else self._gen_type(FLOAT_NEG if sign else FLOAT_POS) + st

	#
	# String
	#
	def _bytes(self,data,string=False,just=False):
		st = []
		c = 0
		for i in range(len(data)):
			if data[i] == 0:
				c += 1
			elif c != 0:
				st.append(0)
				st += list(self._int(c,just=True))
				c = 0
				st.append(data[i])
			else:
				st.append(data[i])
		if c != 0:
			st.append(0)
			st += list(self._int(c,just=True))
		st.append(0)
		st.append(0)
		if not just:
			st.insert(0,self._gen_type(STRING if string else BYTES)[0])
		return bytes(st)


	#
	# list
	#
	def _list(self,data,just=False):
		_st = [self._none()] if len(data) <= 0 else ([ i for i in map(self._type,data)] + [self._none()])
		st = b""
		for i in _st:
			st += i
		return st if just else self._gen_type(LIST) + st

	#
	# dict
	#
	def _map(self,data,just=False):
		st = b""

		for key in data:
			st += self._type(data=key,unallowed_types=(dict,list,tuple))
			st += self._type(data=data[key])
		st += self._none()
		return st if just else self._gen_type(MAP) + st

	#
	# Bool
	#
	def _bool(self,data):
		return self._gen_type(TRUE if data else FALSE)

	#
	# None
	#
	def _none(self):
		return self._gen_type(NULL)

	def _type(self,data,unallowed_types=()):
		if type(data) in unallowed_types:
			raise ValueError("This type (%s) is not allowed here"%(type(data)))
		elif type(data) == int:
			return self._int(data)
		elif type(data) == float:
			return self._float(data)
		elif type(data) in [str,bytes]:
			string = False
			if type(data) == str: 
				data = data.encode() 
				string = True
			return self._bytes(data,string=string)
		elif type(data) in [list,tuple]:
			return self._list(list(data))
		elif type(data) == dict:
			return self._map(data)
		elif type(data) == bool:
			return self._bool(data)
		elif data is None:
			return self._none()
		else:
			raise ValueError("Unexpected type: %s for %s"%(type(data),str(data)))

	def magic(self):
		self.result = self._type(self.data)
		self.result = self._int(len(self.result),just=True) + self.result
	
	def export(self):
		return self.result