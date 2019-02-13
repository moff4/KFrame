#!/use/bin/env python3

import os

from ..basic_response import Response
from ...utils import *
from .scripts import ScriptRunner
BIN = 'binary'
HTML = 'html'
TEXT = 'text'


class StaticResponse(Response):

    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)
        self.content_mod = None
        self.req = kwargs['req'] if 'req' in kwargs else None
        self.vars = {}
        self.P.add_plugin(key='ScR', target=ScriptRunner, autostart=False, module=False)

    #
    # get filename and decide content-type header
    # return (Http-Header, content_mod)
    #
    def Content_type(self, st):
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
            if st in {'mp4', 'avi'}:
                type_2 = st
            else:
                type_2 = 'webm'
        else:
            content_mod = TEXT
            type_1 = 'text'
            type_2 = 'plain'
        return 'Content-type: {}/{}{}'.format(type_1, type_2, extra), content_mod

    # az - list of tuples:
    #   [.., (template, data), ..]
    # find template => change into data
    def usefull_inserts(self, az):
        if self.content_mod in {TEXT, HTML}:
            for i in az:
                while i[0] in self.data:
                    j = self.data.index(i[0])
                    self.data = self.data[:j] + i[1] + self.data[j + len(i[0]):]
        return self

    def run_scripts(self):
        if self.content_mod in {TEXT, HTML} and self.data:
            sr = self.P.init_plugin(key='ScR', text=self.data)
            vars = dict(self.vars)
            if self.req is not None:
                vars.update(self.req.args)
            sr.run(args=vars)
            self.data = sr.export()
        return self

    # load static file
    # return True in case of success
    def load_static_file(self, filename):
        if os.path.isfile(filename):
            self.Debug('gonna send file: {}'.format(filename))
            with open(filename, 'rb') as f:
                self.data = f.read()
            content_type, self.content_mod = self.Content_type(filename)
            self.add_headers(
                [
                    content_type,
                    'Cache-Control: max-age={cache_min}'.format(
                        cache_min=self.P.neon.cfg['response_settings']['cache_min']
                    ),
                ],
            ).code = 200
            return True
        else:
            self.Debug('File not found: {}'.format(filename))
            self.data = NOT_FOUND
            self.add_headers(
                [
                    CONTENT_HTML,
                    'Connection: close',
                ],
            ).code = 404
            return False

    def _extra_prepare_data(self):
        self.run_scripts()
        return self.data
