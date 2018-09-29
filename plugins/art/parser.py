#!/usr/bin/env python3


INT_POS 	= 1
INT_NEG 	= 2
FLOAT_POS 	= 3
FLOAT_NEG 	= 4
BYTES 		= 5
STRIGN 		= 6
LIST  		= 7
MAP 		= 8
NULL 		= 9


class Parser:
	def __init__(self,mask=None):
		self.result = None
		self.input_fd = None
		self.input_data = None
		self.input_index = 0
		self.input_status = None

		self.mask = mask
		self.mask_index = 0

		self._read_once = 0

	def _get(self):
		self._read_once += 1
		if self.input_status == "fd":
			res = self.input_fd.read(1)
		elif self.input_index < len(self.input_data):
			x = self.input_data[self.input_index]
			self.input_index += 1
			res = x
		else:
			raise ValueError("Unexpetedly reached end of input")
		if self.mask != None:
			res = res ^ self.mask[self.mask_index%len(self.mask)]
			self.mask_index += 1
		return res

	def _load(self,x):
		if self.input_status == "fd":
			self.input_data = self.input_fd.read(x)
			self.input_status = "dt"

	#
	# 1 Integer
	#
	def _get_int(self,z=None):
		self._read_once = 0
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
		self._read_once = 0
		a = self._get_int()
		c = self._get_int()
		return float(a) /10.0**c

	#
	# 3 Bytes
	#
	def _get_bytes(self):
		self._read_once = 0
		c = 0
		st = []
		while c < 2:
			x = self._get()
			if x == 0:
				c += 1
			elif c != 0:
				x = self._get_int(x)
				print("Zeros passed: %s"%x)
				st += [ 0 for i in range(x)]
				c = 0
			else:
				st.append(x)
		return bytes(st)

	
	#
	# 4 List
	#
	def _get_list(self):
		self._read_once = 0
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
		self._read_once = 0
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
		if t == INT_POS:
			return self._get_int()
		elif t == INT_NEG:
			return self._get_int() * (-1)
		elif t == FLOAT_POS:
			return self._get_float()
		elif t == FLOAT_NEG:
			return self._get_float() * (-1)
		elif t == BYTES:
			return self._get_bytes()
		elif t == STRIGN:
			return self._get_bytes().decode()
		elif t == LIST:
			return self._get_list()
		elif t == MAP:
			return self._get_map()
		elif t == NULL:
			return None
		else:
			raise ValueError("Unexpected type number: %s"%t)

	#==========================================================================
	#                                 USER API
	#==========================================================================

	def set_fd(self,fd):
		self.input_fd = fd
		self.input_status = "fd"

	def set_data(self,data):
		self.input_data = data
		self.input_status = "dt"


	def magic(self):
		y = self._get_int()
		if y != 0:
			if self._read_once > y:
				raise ValueError("Strange Length")
			if self._read_once == y:
				return None
			self._load(y-self._read_once)
		self.result = self._type()

	def export(self):
		return self.result