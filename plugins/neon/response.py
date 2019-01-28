#!/usr/bin/env python3

from ...base.plugin import Plugin
from .utils import *

PROPS = {'data', 'code', 'headers', 'header', 'http_version'}


class Response(Plugin):
    def init(self, data=None, headers=None, code=404, http_version="HTTP/1.1"):
        self.data = b"" if data is None else data
        self.headers = [] if headers is None else headers
        self.code = code
        self.http_version = http_version

    # kwargs can be:
    #   data - (bytes) Response data
    #   code - (int) HTTP CODE
    #   headers - (list of str) Http headers
    #   header - (str) Http header (example: "Content-Type: text/html")
    #   http_version - (str) Version of protocol (example: "HTTP/1.1")
    def set(sekf, **kwargs):
        for key in kwargs:
            if key not in PROPS:
                raise AttributeError('no response property "{}"'.format(key))
            elif key == 'headers':
                self.add_headers(kwargs[key])
            elif key == 'header':
                self.add_header(kwargs[key])
            else:
                setattr(self, key, kwargs[key])

    def set_code(self, code):
        self.code = code
        return self

    def add_header(self, header):
        self.headers.append(header)
        return self

    def add_headers(self, headers):
        self.headers += headers
        return self

    def set_data(self, data=None):
        if data is None:
            self.data = b''
        else:
            self.data = data.encode() if type(data) == str else data
        return self

    def set_http_verion(self, http_verion):
        self.http_version = http_version
        return self

    def export(self):
        st = []
        st.append("{http_version} {code} {code_msg}\r\n".format(
            http_version=self.http_version,
            code=self.code,
            code_msg=http_code_msg[self.code])
        )
        st.append(
            "".join(
                [
                    "".join([i, "\r\n"])
                    for i in filter(
                        lambda x: x is not None and len(x) > 0,
                        apply_standart_headers(self.headers + [
                            "Content-Length: {length}".format(
                                length=len(self.data)
                            )]
                        )
                    )
                ]
            )
        )
        st.append("\r\n")
        st = "".join(st).encode()
        return st + (self.data.encode() if type(self.data) == str else self.data)
