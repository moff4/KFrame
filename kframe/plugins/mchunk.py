#!/usr/bin/env python3

from os import urandom

from ..base.plugin import Plugin


class Mchunk(Plugin):
    def init(self):
        self._masked = False
        self._mask = b''
        self._data = b''

    def set(self, data):
        """
            set internal data in state 0
            data must be bytes
        """
        if len(data) <= 0:
            return
        self._masked = False
        self._mask = urandom(len(data))
        self._data = data
        return self

    def mask(self):
        """
            mask data
        """
        if not self._masked:
            data = self._data
            self._data = b''
            self._masked = True
            for i in range(len(data)):
                self._data += bytes([data[i] ^ self._mask[i]])
        return self

    def unmask(self):
        """
            unmask data
        """
        if self._masked:
            data = self._data
            self._data = b''
            self._masked = False
            for i in range(len(data)):
                self._data += bytes([data[i] ^ self._mask[i]])
        return self

    def get(self):
        """
            return data as is
            return bytes
        """
        return self._data
