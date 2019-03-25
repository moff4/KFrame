#!/use/bin/env python3

import os

from ..basic_response import Response
from ...utils import *
from .scripts import ScriptRunner
BIN = 'binary'
HTML = 'html'
TEXT = 'text'


class StaticResponse(Response):

    name = 'static_response'

    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)
        self.content_mod = None
        self.req = kwargs['req'] if 'req' in kwargs else None
        self.vars = {}
        self.P.add_plugin(key='ScR', target=ScriptRunner, autostart=False, module=False)

    def Content_type(self, st):
        """
            get filename and decide content-type header
            return (Http-Header, content_mod)
        """
        extra = ''
        content_mod = None
        st = st.split('.')[-1]
        if st in {'html', 'css', 'txt', 'csv', 'xml', 'js', 'json', 'php', 'md'}:
            type_1 = 'text'
            content_mod = TEXT
            if st == 'js':
                type_2 = 'javascript'
            elif st == 'md':
                type_2 = 'markdown'
            elif st == 'html':
                type_2 = st
                content_mod = HTML
                extra = '; charset=utf-8'
            else:
                type_2 = st
        elif st in {'jpg', 'jpeg', 'png', 'gif', 'tiff'}:
            type_1 = 'image'
            type_2 = st
            content_mod = BIN
        elif st in {'mkv', 'avi', 'mp4'}:
            content_mod = BIN
            type_1 = 'video'
            type_2 = st if st in {'mp4', 'avi'} else 'webm'
        else:
            content_mod = TEXT
            type_1 = 'text'
            type_2 = 'plain'
        return {'Content-type': '{}/{}{}'.format(type_1, type_2, extra)}, content_mod

    def usefull_inserts(self, az):
        """
            az - list of tuples:
              [.., (template, data), ..]
            find template => change into data
        """
        if self.content_mod in {TEXT, HTML}:
            for i in az:
                while i[0] in self._data:
                    j = self._data.index(i[0])
                    self._data = self._data[:j] + i[1] + self._data[j + len(i[0]):]
        return self

    def run_scripts(self):
        if self.content_mod in {TEXT, HTML} and self._data:
            sr = self.P.init_plugin(key='ScR', text=self._data)
            if sr.run(args=self.vars):
                self._data = sr.export()
            else:
                self._data = SMTH_HAPPENED
                self.code = 500
        return self

    def load_static_file(self, filename):
        """
            load static file
            return True in case of success
        """
        if os.path.isfile(filename):
            self.Debug('gonna send file: {}'.format(filename))
            size = os.path.getsize(filename)
            if size <= self.P.neon.cfg['response_settings']['max_response_size']:
                with open(filename, 'rb') as f:
                    self._data = f.read()
                _code = 200
            else:
                _from = 0
                _to = self.P.neon.cfg['response_settings']['max_response_size']
                if self.req is not None and 'range' in self.req.headers:
                    tmp = self.req.headers['range'].split('=')
                    if tmp[0] == 'bytes':
                        a, b = tmp[1].split('-')
                        _from = int(a)
                        _to = int(b)
                with open(filename, 'rb') as f:
                    if _from > 0:
                        f.read(_from)
                    self._data = f.read(_to - _from)
                    self.add_header(
                        'Content-Range',
                        'bytes={_from}-{_to}/{size}'.format(
                            _from=_from,
                            _to=_to,
                            size=size,
                        )
                    )
                _code = 206
            content_type, self.content_mod = self.Content_type(filename)
            self.add_headers(content_type)
            self.add_headers(
                {
                    'Cache-Control': 'max-age={cache_min}'.format(
                        cache_min=self.P.neon.cfg['response_settings']['cache_min']
                    ),
                },
            ).code = _code
            return True
        else:
            self.Debug('File not found: {}'.format(filename))
            self._data = NOT_FOUND
            self.add_headers(CONTENT_HTML)
            self.add_header('Connection', 'close')
            self.code = 404
            return False

    def _extra_prepare_data(self):
        self.run_scripts()
        return self._data
