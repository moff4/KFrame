
from ...base.plugin import Plugin


def delete_spaces(st):
	while len(st) > 0:
		if st[0].isspace():
			st = st[1:]
		else:
			break
	while len(st) > 0:
		if st[-1].isspace():
			st = st[:-1]
		else:
			break
	return st

#
# get smth like b'A%66C'
# return smth like b'ABC'
#
def urldecode(az):
	def pp(z):
		if z in b'ABCDEF':
			return ord(z) - ord(b'A') + 10
		elif z in b'abcdef':
			return ord(z) - ord(b'a') + 10
		else:
			return ord(z) - ord(b'0')
	bz = b''
	while len(az) > 0:
		if az[:1] != b'%':
			bz += az[:1]
			az = az[1:]
		else:
			az = az[1:]
			x = az[:1]
			az = az[1:]
			y = az[:1]
			az = az[1:]
			x = pp(x)
			y = pp(y)
			bz += bytes([x*16+y])
	return bz

#
# class to handle single cookie
#
class Cookie(Plugin):
	def init(self,cookie_string=None,key=None,value=None):
		self.attr = {}
		self._key = None
		self._value = None

		if not cookie_string is None:
			self._parse(cookie_string)
		elif not (key is None or value is None):
			self._key = key
			self._value = value

	def _parse(self,string):
		key , value = list(map(delete_spaces,string.split("=")))
		self._key = urldecode(key.encode()).decode()
		self._value = urldecode(value.encode()).decode()
		
	def _ecran(self,st):
		return st

	def _export_attr(self,key):
		if type(self.attr[key]) == bool:
			return "%s; "%key
		else:
			return "%s=%s; "%(key,self._ecran(self.attr[key]))

	def _export(self):
		return "".join(["Set-Cookie: ","%s=%s; "%(self._key,self._ecran(self._value))] + list(map(self._export_attr,self.attr.keys())))

	#==========================================================================
	#                                  USER API
	#==========================================================================

	#
	# force initialization
	#
	def init(self,key,value):
		self._key = key
		self._value = value

	#
	# return key of cookie
	# or None if the Cookie.object is not initialized
	#
	def key(self):
		return self._key
	#
	# return value of cookie
	# or None if the Cookie.object is not initialized
	#
	def value(self):
		return self._value

	#
	# set attributes value
	#
	def set_attr(self,attr,value):
		self.attr[attr] = value

	#
	# return Attributes value
	# or None if there are no such attriblute
	#
	def get_attr(self,attr):
		if attr in self.attr:
			return self.attr[attr]
		else:
			return None

	#
	# export as HTTP-header
	#
	def __str__(self):
		return self._export()
