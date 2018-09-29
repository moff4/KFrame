#!/usr/bin/env python3

from .parser import Parser
from .coder import Coder

#
# convert data to bytes
# mask - some mask to be applied on marshaled data
#
def marshal(data,mask=None):
	c = Coder(data)
	c.magic()
	if mask is None:
		return c.export()
	else:
		data = c.export()
		return bytes([ data[i] ^ mask[i%len(mask)] for i in range(len(data)) ])

#
# convert data as bytes() or from fd {interface : read() }
#
def unmarshal(data=None,fd=None,mask=None):
	if data is None and fd is None:
		raise ValueError("Expected argement")
	p = Parser(mask=mask)
	if data is None:
		p.set_fd(fd)
	else:
		p.set_data(data)
	p.magic()
	return p.export()