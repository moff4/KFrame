#!/usr/bin/env python3

from ....base.plugin import Plugin
from ..utils import *

PROPS = {'data', 'code', 'headers', 'header', 'http_version'}


class Response(Plugin):
    def init(self, data=None, headers=None, code=404, http_version="HTTP/1.1"):
        self._data = b"" if data is None else data
        self.headers = [] if headers is None else headers
        self._code = code
        self._http_version = http_version

    # kwargs can be:
    #   data - (bytes) Response data
    #   code - (int) HTTP CODE
    #   headers - (list of str) Http headers
    #   header - (str) Http header (example: "Content-Type: text/html")
    #   http_version - (str) Version of protocol (example: "HTTP/1.1")
    def set(self, **kwargs):
        for key in kwargs:
            if key not in PROPS:
                raise AttributeError('no response property "{}"'.format(key))
            elif key == 'headers':
                self.add_headers(kwargs[key])
            elif key == 'header':
                self.add_header(kwargs[key])
            else:
                setattr(self, key, kwargs[key])
        return self

    @property
    def code(self):
        return self._code

    @code.setter
    def code(self, code):
        self._code = code

    @property
    def http_version(self):
        return self._http_version

    @http_version.setter
    def http_version(self, http_version):
        self.set_http_verion(http_verion)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self.set_data(data)

    def set_code(self, code):
        self._code = code
        return self

    def add_header(self, header):
        self.headers.append(header)
        return self

    def add_headers(self, headers):
        self.headers += headers
        return self

    def set_data(self, data=None):
        if data is None:
            self._data = b''
        else:
            self._data = data.encode() if type(data) == str else data
        return self

    def set_http_verion(self, http_verion):
        self._http_version = http_version
        return self

    def export(self):
        st = []
        st.append("{http_version} {code} {code_msg}\r\n".format(
            http_version=self._http_version,
            code=self._code,
            code_msg=http_code_msg[self._code])
        )
        st.append(
            "".join(
                [
                    "".join([i, "\r\n"])
                    for i in filter(
                        lambda x: x is not None and len(x) > 0,
                        apply_standart_headers(self.headers + [
                            "Content-Length: {length}".format(
                                length=len(self._data)
                            )]
                        )
                    )
                ]
            )
        )
        st.append("\r\n")
        st = "".join(st).encode()
        return st + (self._data.encode() if type(self._data) == str else self._data)
