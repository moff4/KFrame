#!/usr/bin/env python3

import os
from traceback import format_exc as Trace
from ...base.plugin import Plugin
from .parser import parse_data
from .utils import *


#
# class for each request
# must be args:
#   addr - tuple (ip,port)
#   conn - socket
# kwargs:
#   max_header_length   - int - max length of each header
#   max_header_count    - int - max number of passed headers
#   max_data_length     - int - max length of data
#   cache_min           - int - seconds for HTTP header 'Cache-Control: max-age'
#
class Request(Plugin):
    def init(self, addr, conn, **kwargs):
        defaults = {
            'id': 0,
            'cache_min': 120,
            'max_header_length': MAX_HEADER_LEN,
            'max_header_count': MAX_HEADER_COUNT,
            'max_data_length': MAX_DATA_LEN,
        }
        self.cfg = {}
        for i in defaults:
            self.cfg[i] = kwargs[i] if i in kwargs else defaults[i]
        self._dict = {}
        try:
            self.Debug('Gonna read')
            self._dict = parse_data(conn, cfg=self.cfg)
            self.Debug('Done read')
        except Exception as e:
            self.FATAL = True
            self.errmsg = 'parse data: %s' % e
            self.Error(self.errmsg)
            self.Debug(Trace())
            return
        self._dict.update(kwargs)
        self._dict_keys = list(self._dict.keys())
        for i in self._dict:
            setattr(self, i, self._dict[i])
        self.addr = addr
        self.conn = conn
        self.ip = self.addr[0]
        self.port = self.addr[1]
        self.ssl = False
        self.secure = False
        self.resp = self.P.init_plugin(key='response')
        self._send = False

    #
    # local log function
    #
    def __call__(self, st='', _type='notify'):
        self.log(st='[{id}] {st}'.format(id=self.cfg['id'], st=st), _type=_type)

    # ==========================================================================
    #                             USER API
    # ==========================================================================

    def set_ssl(self, ssl):
        self.ssl = ssl
        return self

    def set_secure(self, secure):
        self.secure = secure
        return self

    def dict(self):
        return {i: getattr(self, i) for i in ['conn', 'addr', 'ip', 'port', 'ssl'] + self._dict_keys}

    # this will be called after main handler done
    # u can override it
    def after_handler(self):
        pass

    def send(self, resp=None):
        if not self._send:
            resp = self.resp if resp is None else resp
            self.conn.send(resp.export())
            self.P.stats.add(key='requests-success' if 200 <= resp.code < 300 else 'requests-failed')
            self._send = True

    #
    # init response with static file
    # afterward method will be ready to send()
    # extra_modifier(Request,data,*args,**kwargs) - some handler that will be called with data from file if passed
    #
    def static_file(self, filename, extra_modifier=None, *args, **kwargs):
        if os.path.isfile(filename):
            self.Debug('gonna send file: {}'.format(filename))
            with open(filename, 'rb') as f:
                data = f.read()
            if extra_modifier is not None:
                data = extra_modifier(self, data, *args, **kwargs)
            self.resp.code = 200
            self.resp.data = data
            self.resp.add_header(Content_type(self.url))
            self.resp.add_header('Cache-Control: max-age={cache_min}'.format(
                cache_min=self.P.neon.cfg['response_settings']['cache_min']
            ))
        else:
            self.Debug('File not found: {}'.format(filename))
            self.resp.code = 404
            self.resp.data = NOT_FOUND
            self.resp.add_header(CONTENT_HTML)
            self.resp.add_header('Connection: close')

    #
    # return True if IP is private
    #
    def is_local(self):
        return is_local_ip(
            self.addr
        ) or (
            (
                'X-From-Y' in self.headers
            ) and (
                self.P.neon.cfg['believe_x_from_y']
            ) and (
                is_local_ip(
                    self.headers['X-From-Y']
                )
            )
        )
