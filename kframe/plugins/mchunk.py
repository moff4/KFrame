#!/usr/bin/env python3

from os import urandom # random

from ..base.plugin import Plugin

class Mchunk(Plugin):
	def init(self):
		self._masked = False
		self._mask = b''
		self._data   = b''

	#
	# set internal data in state 0
	# data must be bytes
	#
	def set(self,data):
		if len(data) <= 0:
			return
		self._masked = False
		self._mask = urandom(len(data))
		self._data = data

	#
	# unmask data
	#
	def mask(self):
		if not self._masked:
			data 		= self._data
			self._data 	= b''
			self._masked = True
			for i in range(len(data)):
				self._data += bytes([data[i] ^ self._mask[i]])
	#
	# unmask data
	#
	def unmask(self):
		if self._masked:
			data 		= self._data
			self._data 	= b''
			self._masked = False
			for i in range(len(data)):
				self._data += bytes([data[i] ^ self._mask[i]])

	#
	# return data as is
	# return bytes
	#
	def get(self):
		return self._data

LOAD_SCHEME = {
	"target":Mchunk,
	"module":False,
	"arg":(),
	"kwargs":{},
	"dependes":[]
}