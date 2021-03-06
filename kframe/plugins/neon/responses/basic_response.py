#!/usr/bin/env python3

from kframe.base.plugin import Plugin
from kframe.plugins.neon.utils import *

from urllib.parse import quote

PROPS = {'data', 'code', 'http_version'}


class Response(Plugin):
    name = 'response'

    def init(self, data=None, headers=None, code=404, http_version='HTTP/1.1', *args, **kwargs):
        self._data = b"" if data is None else data
        self._headers = dict() if headers is None else headers
        self._code = code
        self._http_version = http_version
        self._cookies = []

    def _extra_prepare_data(self) -> str:
        return self.data

    def set(self, **kwargs):
        """
            kwargs can be:
              data - (bytes) Response data
              code - (int) HTTP CODE
              http_version - (str) Version of protocol (example: "HTTP/1.1")
        """
        for key in kwargs:
            if key not in PROPS:
                raise AttributeError('no response property "{}"'.format(key))
            else:
                setattr(self, key, kwargs[key])
        return self

    @property
    def code(self) -> int:
        return self._code

    @code.setter
    def code(self, code):
        self._code = code

    @property
    def http_version(self) -> str:
        return self._http_version

    @http_version.setter
    def http_version(self, http_version):
        self.set_http_verion(http_verion)

    @property
    def data(self) -> bytes:
        return self._data

    @data.setter
    def data(self, data):
        self.set_data(data)

    def add_header(self, header: str, value: str):
        self._headers[header] = value
        return self

    def add_headers(self, headers: dict):
        """
            headers - dict: header -> value
        """
        self._headers.update(headers)
        return self

    def set_data(self, data=None):
        if data is None:
            self._data = b''
        else:
            self._data = data.encode() if isinstance(data, str) else data
        return self

    def set_http_verion(self, http_verion):
        self._http_version = http_version
        return self

    def add_cookie(self, *cookie_properties_s, **cookie_properties_kw):
        """
            cookie_properties_s - boolean pproperties like HttpOnly and Secure
            cookie_properties_kw - kev-value properties like Max-Age and Domain
                also may contain smth like 'session_id': 1234567
        """
        self._cookies.append(
            '; '.join(
                (
                    [
                        '{}={}'.format(
                            cookie_properties_kw['cookie_name'],
                            quote(
                                str(
                                    cookie_properties_kw[cookie_properties_kw['cookie_name']]
                                )
                            )
                        )
                    ]
                    if 'cookie_name' in cookie_properties_kw else
                    ['']
                ) + [
                    '{}={}'.format(
                        key,
                        quote(
                            str(
                                cookie_properties_kw[key]
                            )
                        )
                    )
                    for key in {
                        k for k in cookie_properties_kw.keys()
                        if k != 'cookie_name'
                    }
                ] + list(
                    cookie_properties_s
                )
            )
        )

    def export(self) -> str:
        def union(d1, d2):
            d1.update(d2)
            return d1

        data = self._extra_prepare_data()
        data = data.encode() if isinstance(data, str) else data
        headers = apply_standart_headers(
            union(
                self._headers,
                {
                    'Content-Length': len(data),
                },
            ),
        )
        return ''.join(
            [
                '{http_version} {code} {code_msg}\r\n'.format(
                    http_version=self.http_version,
                    code=204 if len(data) <= 0 and self.code in {200, 201} else self.code,
                    code_msg=http_code_msg[self.code]
                ),
                '\r\n'.join(
                    [
                        ''.join([i, ': ', str(headers[i])])
                        for i in filter(
                            lambda x: x,
                            headers,
                        )
                    ] + [
                        'Set-Cookie: {}'.format(k)
                        for k in self._cookies
                    ]
                ),
                '\r\n',
                '\r\n',
            ]
        ).encode() + data
