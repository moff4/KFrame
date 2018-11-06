#!/usr/bin/env python3


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

class Parser:
	def __init__(self,mask=None):
		self.result = None
		self.input_fd = None
		self.input_data = None
		self.input_status = None

		self.mask = mask

		self._read_total = 0
		self._len = None

	def _get(self):
		if self._len != None and self._read_total >= self._len:
			raise RuntimeError("Reaced end of input")
		if self.input_status == "fd":
			if 'read' in dir(self.input_fd):
				res = self.input_fd.read(1)	
			else:
				res = self.input_fd.recv(1)
		elif self._read_total < len(self.input_data):
			x = self.input_data[self._read_total]
			res = x
		else:
			raise ValueError("Unexpetedly reached end of input")
		if type(res) == bytes:
			if len(res) <= 0:
				raise RuntimeError("reached EOF")
			res = res[0]
		if self.mask != None:
			res = res ^ self.mask[self._read_total%len(self.mask)]
		self._read_total += 1
		return res

	def _load(self,x):
		if self.input_status == "fd":
			if 'read' in dir(self.input_fd):
				self.input_data = self.input_fd.read(x)
			else:
				self.input_data = self.input_fd.recv(x)
			self.input_status = "dt"

	#
	# 1 Integer
	#
	def _get_int(self,z=None):
		x = 0
		while True:
			if not z is None:
				y = z
				z = None
			else:
				y = self._get()
			if y < 128:
				x = x * 128 + y
			else:
				return x * 128 + y % 128
		return x

	#
	# 2 Float
	#
	def _get_float(self):
		a = self._get_int()
		c = self._get_int()
		return float(a) /10.0**c

	#
	# 3 Bytes
	#
	def _get_bytes(self):
		c = 0
		st = []
		while c < 2:
			x = self._get()
			if x == 0:
				c += 1
			elif c != 0:
				x = self._get_int(x)
				st += [ 0 for i in range(x)]
				c = 0
			else:
				st.append(x)
		return bytes(st)

	
	#
	# 4 List
	#
	def _get_list(self):
		az = []
		while True:
			x = self._type()
			if x is None:
				return az
			else:
				az.append(x)
		return az
	
	#
	# 5 Map
	#
	def _get_map(self):
		az = {}
		while True:
			key = self._type(unallowed_types=(LIST,MAP))
			if key is None:
				return az
			value = self._type()
			az[key] = value
		return az

	def _type(self,unallowed_types=()):
		t = self._get() & 0x0F
		if t in unallowed_types:
			raise ValueError("Unexpected element type of %s"%t)
		if t == INT_POS: # 1
			res = self._get_int()
		elif t == INT_NEG: # 2
			res =  self._get_int() * (-1)
		elif t == FLOAT_POS: # 3
			res =  self._get_float()
		elif t == FLOAT_NEG: # 4
			res =  self._get_float() * (-1)
		elif t == BYTES: # 5 
			res =  self._get_bytes()
		elif t == STRING: # 6
			res =  self._get_bytes().decode()
		elif t == LIST: # 7
			res =  self._get_list()
		elif t == MAP: # 8
			res =  self._get_map()
		elif t == TRUE: # 9
			res =  True
		elif t == FALSE: # 10
			res =  False
		elif t == NULL: # 11
			res =  None
		else:
			raise ValueError("Unexpected type number: %s"%t)
		return res

	#==========================================================================
	#                                 USER API
	#==========================================================================

	def set_fd(self,fd):
		if 'read' not in dir(fd) and 'recv' not in dir(fd):
			raise ValueError("Filed descriptor does not has needed interface")
		self.input_fd = fd
		self.input_status = "fd"

	def set_data(self,data):
		self.input_data = data
		self.input_status = "dt"


	def magic(self):
		l = self._get_int()
		self._len = l + self._read_total
		self.result = self._type()

	def export(self):
		return self.result