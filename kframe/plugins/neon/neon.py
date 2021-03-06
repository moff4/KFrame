#!/usr/bin/env python3
import os
import ssl
import time
import random
import socket
import binascii
import threading as th

from kframe.base.plugin import Plugin
from kframe.modules import crypto
from kframe.plugins.stats import Stats
from kframe.plugins.neon.requests import Request
from kframe.plugins.neon.responses import (
    Response,
    StaticResponse,
    RestResponse,
)
from kframe.plugins.neon.decorators import recursion
from kframe.plugins.neon.utils import *
from kframe.plugins.neon.exceptions import ResponseError
from kframe.plugins.neon.parser import pop_zeros


class Neon(Plugin):
    name = 'neon'
    defaults = {
        'allowed_hosts': {'any'},
        'only_local_hosts': False,
        'believe_x_from_y': False,
        'http_port': 8080,
        'https_port': 8081,
        'use_ssl': False,
        'ca_cert': None,
        'ssl_certs': {},  # host -> {certfile -> str, keyfile -> str, keypassword -> str}
        'site_directory': './var',
        'max_data_length': MAX_DATA_LEN,
        'max_header_count': MAX_HEADER_COUNT,
        'max_header_length': MAX_HEADER_LEN,
        'threading': False,
        'use_neon_server': False,
        'response_settings': {
            'cache_min': 120,
            'max_response_size': 2**20,
        },
        'single_request_per_socket': True,
        'enable_stats': True,
        'answer_ping': False,  # "/ping" -> pong!
    }

    def init(self, **kwargs):
        try:
            self.cgi_modules = []
            self.ws_handlers = {}  # key = path; value - WSHandler
            self.middleware = []

            self._run = True
            self._th = None
            self._rng = random.random() * 10**2

            self.thread_list = []
            self._ws = []

            self.response_types = {
                'base': 'response',
                'rest': 'rest_response',
                'static': 'static_response',
            }
            if self.cfg['site_directory'].endswith('/'):
                self.cfg['site_directory'] = self.cfg['site_directory'][:-1]

            self.contexts = {}
            if self.cfg['use_ssl']:
                if self.cfg['ssl_certs']:
                    for hostname in self.cfg['ssl_certs']:
                        context = ssl.create_default_context(
                            purpose=ssl.Purpose.CLIENT_AUTH,
                            cafile=self.cfg['ca_cert']
                        )
                        context.load_cert_chain(
                            certfile=self.cfg['ssl_certs'][hostname]['certfile'],
                            keyfile=self.cfg['ssl_certs'][hostname]['keyfile'],
                            password=self.cfg['ssl_certs'][hostname].get('keypassword', None),
                        )
                        self.contexts[hostname] = context

                # gonna be deprecated
                if self.cfg.get('ssl_cert'):
                    context = ssl.create_default_context(cafile=self.cfg['ca_cert'])
                    context.load_cert_chain(
                        certfile=self.cfg['ssl_cert']['certfile'],
                        keyfile=self.cfg['ssl_cert']['keyfile'],
                        password=self.cfg['ssl_cert'].get('keypassword')
                    )
                    self.contexts[None] = context

                self.context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
                self.context.set_servername_callback(self.servername_callback)
            else:
                self.context = None

            self.P.add_plugin(target=Request, autostart=False, module=False)
            self.P.add_plugin(target=Response, autostart=False, module=False)
            self.P.add_plugin(target=RestResponse, autostart=False, module=False)
            self.P.add_plugin(target=StaticResponse, autostart=False, module=False)

            if self.cfg['enable_stats']:
                if 'stats' not in self:
                    self.P.fast_init(key='stats', target=Stats, export=False)
                if 'crypto' not in self:
                    self.P.add_module(key='crypto', target=crypto)

                self.P.stats.init_stat(
                    key='start-time',
                    type='single',
                    default=time.strftime('%H:%M:%S %d %b %Y'),
                    desc='Время запуска сервера'
                )
                self.P.stats.init_stat(
                    key='start-timestamp',
                    type='single',
                    default=int(time.time()),
                    desc='Время запуска сервера'
                )
                for i in range(1, 6):
                    self.P.stats.init_stat(
                        key='requests-{}xx'.format(i),
                        type='event_counter',
                        desc='Кол-во запросов с кодом ответа {}xx'.format(i),
                    )
                self.P.stats.init_stat(key='aver-response-time', type='aver', desc='Среднее время ответа')

        except Exception as e:
            self.FATAL = True
            self.errmsg = '{}: {}'.format(self.name, str(e))

    # ========================================================================
    #                                  UTILS
    # ========================================================================

    def gen_id(self):
        self._rng += 1
        st = binascii.hexlify(self.P.crypto._hash(str(self._rng).encode('utf-8'))[:2]).decode()
        az = []
        while len(st) > 0:
            az.append(st[:4])
            az.append('-')
            st = st[4:]
        return ''.join(az[:-1])

    def open_port(self, use_ssl=False, port=80):
        j = 1
        while j <= 3:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('', port))
                sock.listen(5)
                sock.settimeout(60 * 3600)
                return sock
            except Exception as e:
                time.sleep(j * 5)
                self.Debug('open-port {} : {}', port, e)
            j += 1
        raise RuntimeError('Could not open port (%s)' % (port))

    def get(self, req):
        """
            handler of original connection
            return Response Object
        """
        def dirs(path):
            if not req.url.endswith('/'):
                req.url += '/'
            return DIR_TEMPLATE.format(
                cells=''.join(
                    [
                        DIR_CELL_TEMPLATE.format(
                            filename=file,
                            **req.dict()
                        )
                        for file in os.listdir(path)
                    ]
                ),
                **req.dict()
            )
        path = self.cfg['site_directory'].rstrip('/') + req.url
        try:
            if os.path.isdir(path):
                req.resp.data = dirs(path)
                req.resp.add_headers(CONTENT_HTML)
            else:
                req.resp.load_static_file(path)
        except Exception as e:
            self.Error(e)
            self.Trace(e, _type='debug')
            req.resp.data = SMTH_HAPPENED
            req.resp.add_headers(CONTENT_HTML)
            req.resp.add_headers('Connection', 'close')
            req.resp.code = 500
        return req.resp

    def choose_module(self, request):
        """
            return True if need to keep-alive socket
        """
        _t = time.time()
        res = None
        module = None
        if request.method not in HTTP_METHODS:
            request.Debug('{ip}: Unallowed method "{method}" ({url})', **request.dict())
            return False
        elif request.http_version not in HTTP_VERSIONS:
            request.Debug('{ip}: Unallowed version "{method}" ({url})', **request.dict())
            return False
        elif 'host' not in request.headers:
            request.Debug('{ip}: No Host passed ({url})', **request.dict())
            return False
        elif request.headers['host'] not in self.cfg['allowed_hosts'] and 'any' not in self.cfg['allowed_hosts']:
            request.Debug('{ip}: Invalid Header-Host "{}"', request.headers['host'], **request.dict())
            return False
        elif self.cfg['answer_ping'] and request.url == '/ping':
            request.init_response('response')
            request.resp.data = 'pong'
            request.resp.code = 200
            request.resp.add_headers(CONTENT_HTML)
        elif request.url in self.ws_handlers and request.headers.get('upgrade') == 'websocket':
            try:
                self.P.fast_init(
                    self.ws_handlers[request.url],
                    req=request
                ).loop()
                return True
            except Exception as e:
                self.Error('Handle ws [{}], {}', request.id, e)
                self.Trace('Handle ws [{}],', request.id)
                return False
        else:
            modules = sorted(
                list(
                    filter(
                        lambda x: request.url.startswith(x['path']),
                        self.cgi_modules
                    )
                ),
                reverse=True,
                key=lambda x: len(x['path'])
            )
            if len(modules) > 0:
                module = modules[0]
            elif self.cfg['use_neon_server']:
                module = {
                    'module': self,
                    'path': '/',
                    'type': 'static',
                }
            else:
                module = None
            if module is None:
                request.init_response('response')
                request.Debug('{ip}: Handler not found ({url})'.format(**request.dict()))
                request.resp.code = 404
                res = request.resp
            else:
                request.Debug('Found handler: {name}'.format(name=module['module'].name))
                if self.cfg['enable_stats']:
                    self.P.stats.init_and_add(
                        'choose_module_{name}'.format(
                            name=module['module'].name
                        ),
                        type='event_counter',
                    )
                try:
                    request.init_response(self.response_types[module['type']])
                    handler = getattr(
                        module['module'],
                        request.method.lower(),
                        None,
                    )
                    if handler is None:
                        request.resp.code = 405
                        request.resp.data = NOT_FOUND
                        res = request.resp
                    else:
                        for middleware, postware in self.middleware:
                            middleware(request, handler)
                            if postware:
                                request.postware.append(postware)
                        res = handler(request)
                        if res is None:
                            res = request.resp
                        for postware in reversed(request.postware):
                            postware(request, res, handler)
                except ResponseError as e:
                    res = self.P.init_plugin(
                        key='response',
                        code=e.status,
                        headers=e.headers,
                        data=e.message,
                    )
                    try:
                        for ck in e.cookies:
                            res.add_cookie(
                                *ck.get('s', []),
                                cookie_name=ck['cookie_name'],
                                **ck.get('kw', {})
                            )
                    except Exception as e:
                        request.Error('cookie marshal: {ex}'.format(ex=e))
                        request.Trace('cookie marshal:')
                        res = self.P.init_plugin(
                            key='response',
                            code=500,
                            headers=CONTENT_HTML,
                            data=SMTH_HAPPENED,
                        )
                except Exception as e:
                    request.Error('cgi handler: {ex}'.format(ex=e))
                    request.Trace('cgi handler:')
                    res = self.P.init_plugin(
                        key='response',
                        code=500,
                        headers=CONTENT_HTML,
                        data=SMTH_HAPPENED,
                    )
        request.send(res)
        request.Notify('[{ip}] {code} : {method} {url} {args}', code=res.code, **request.dict())
        if self.cfg['enable_stats']:
            self.P.stats.init_and_add(
                'module_{name}_answer_{code}xx'.format(
                    name='None' if module is None else module['module'].name,
                    code=(res.code // 100),
                ),
                type='event_counter',
            )
            _t = time.time() - _t
            self.P.stats.add(key="aver-response-time", value=_t)
            if 200 <= res.code < 300:
                self.P.stats.init_and_add(
                    key="{name}-aver-response-time".format(
                        name='None' if module is None else module['module'].name
                    ),
                    type="aver",
                    value=_t,
                )
        try:
            request.after_handler()
        except Exception as e:
            request.Error('cgi after-handler: {ex}'.format(ex=e))
            request.Trace('cgi after-handler:')
        return request.headers.get('connection') == 'keep-alive'

    # ========================================================================
    #                              DEMON TOOLS
    # ========================================================================

    def check_thread(self):
        try:
            self._ws = [i for i in self._ws if i.alive]
            for i in self.thread_list:
                if not i.is_alive():
                    i.join()
                    self.thread_list.pop(self.thread_list.index(i))
        except Exception as e:
            self.Error('check_thread: {}', e)

    def servername_callback(self, sock, req_hostname, cb_context, as_callback=True):
        """
            ssl context callback
        """
        context = self.contexts.get(req_hostname)
        if context is None:
            context = self.contexts.get(None)
        if context is not None:
            sock.context = context

    def wrap_ssl(self, conn):
        if self.context is not None:
            self.Debug('Gonna wrap')
            conn = self.context.wrap_socket(conn, server_side=True)
            self.Debug('Done wrap')
        return conn

    def __alt_run(self, sock, port, _ssl=False):
        @recursion
        def another_deal(conn, addr):
            try:
                if self.cfg['enable_stats']:
                    self.P.stats.add(key='connections')
                conn = self.wrap_ssl(conn) if _ssl else conn
                request = self.P.init_plugin(key='request', conn=conn, addr=addr, id=self.gen_id(), **self.cfg)
                if request.FATAL:
                    self.Error('request-init: {}'.format(request.errmsg))
                    conn.close()
                else:
                    request.set_ssl(_ssl)
                    request.set_secure((self.cfg['use_ssl'] and _ssl) or (not self.cfg['use_ssl']))
                    if self.choose_module(request) and not self.cfg['single_request_per_socket']:
                        try:
                            pop_zeros(conn)
                        except Exception as e:
                            self.Warning('pop-zeros: {}', e)
                        another_deal.call(conn, addr)
                    else:
                        conn.close()

            except Exception as e:
                conn.close()
                self.Warning('Another-Deal: ({}) {}', addr[0], e)
                self.Trace('Another-Deal: ({}) ', addr[0])
        self.Debug('Starting my work on port {}!', port)
        try:
            while self._run:
                try:
                    conn, addr = sock.accept()
                    self.Debug('New: {ip}:{port}', ip=addr[0], port=addr[1])
                except socket.timeout as e:  # time to reopen port
                    try:
                        sock.close()
                    except Exception as e:
                        self('Err while opennig port')
                        time.sleep(5)
                    finally:
                        if self.cfg['use_ssl']:
                            port = https_port
                        else:
                            port = http_port
                        sock = self.open_port(use_ssl=_ssl, port=port)

                if (
                    not self.cfg['only_local_hosts']
                ) or (
                    self.cfg['only_local_hosts'] and is_local_ip(addr[0])
                ):
                    if self.cfg['threading']:
                        t = th.Thread(target=another_deal, args=(conn, addr))
                        t.start()
                        self.thread_list.append(t)
                    else:
                        another_deal(conn, addr)
                else:
                    self.Debug('Not private_ip')
                    conn.close()
                time.sleep(0.1)
                self.check_thread()

        except Exception as e:
            self.Error('Listen port error: {}', e)
            time.sleep(5)
        except KeyboardInterrupt:
            self.Notify('got SIGINT: stopping')
        finally:
            sock.close()

    def _open(self):
        def open(port):
            try:
                # in Windows u cannot stop program while it's listening the port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('0.0.0.0', port))
                sock.close()
            except Exception:
                pass
        if self.cfg['use_ssl']:
            open(self.cfg['https_port'])
        open(self.cfg['http_port'])

    def _loop(self):
        try:
            self._threads = []
            if self.cfg['use_ssl']:
                self._threads.append(
                    [
                        th.Thread(
                            target=self.__alt_run,
                            args=[
                                self.open_port(use_ssl=True, port=self.cfg['https_port']),
                                self.cfg['https_port'],
                                True
                            ]
                        ),
                        self.cfg['https_port']
                    ]
                )
                self._threads[-1][0].start()
                self._threads.append(
                    [
                        th.Thread(
                            target=self.__alt_run, args=[
                                self.open_port(use_ssl=False, port=self.cfg['http_port']),
                                self.cfg['http_port'],
                                False
                            ]
                        ),
                        self.cfg['http_port']
                    ]
                )
                self._threads[-1][0].start()
                while self._run:
                    time.sleep(1)
            else:
                self.__alt_run(
                    sock=self.open_port(
                        use_ssl=False,
                        port=self.cfg['http_port']
                    ),
                    _ssl=False,
                    port=self.cfg['http_port']
                )
        except Exception as e:
            self.Error('run: Exception: {}', e)
        except KeyboardInterrupt:
            self.Notify('run: KeyboardInterrupt')
        finally:
            self._run = False
            self.Notify('socket closed')
            self._open()
            for i in self._ws:
                i.close()
            for i in self._threads:
                i[0].join()
            for i in self.thread_list:
                i.join()
        self.Notify('Finishing my work!')

    # ========================================================================
    #                                USER API
    # ========================================================================

    def add_ws_handler(self, handler, path: str=None):
        """
            Add ws handler to Neon
            if path not passed then user handler.Path
            WS handler must be isinstance of kframe.plugins.xeon.WSHandler
        """
        from kframe.plugins.xeon import WSHandler
        if not isinstance(module, WSHandler):
            raise TypeError('WS handler must be isinstance of kframe.plugins.xeon.WSHandler')
        if path is None:
            path = handler.Path
        self.ws_handlers[path] = handler

    def add_site_module(self, module, path: str=None, response_type: str=None):
        """
            add new site_module
            response_type - type of response object; default 'base'
                possible values for response_type: 'base' / 'rest' / 'static'
            path - str - default '/'; path that assosiates with this module
            Module - Module/Object that has special interface:
              Path - str ; Going to be deprecated
              get(request)        - handler for GET requests      ; if not presented -> send 404 by default
              post(requests)      - handler for POST requests     ; if not presented -> send 404 by default
              head(requests)      - handler for HEAD requests     ; if not presented -> send 404 by default
              put(requests)       - handler for PUT requests      ; if not presented -> send 404 by default
              delete(requests)    - handler for DELETE requests   ; if not presented -> send 404 by default
              options(requests)   - handler for OPTIONS requests  ; if not presented -> send 404 by default
        """
        if isinstance(module, Plugin) and module.FATAL:
            module.Error(module.errmsg)
            raise ValueError('module is not initialized properly')

        if getattr(module, 'Path', None) is not None and path is not None:
            raise ValueError('"path" for passed as param and module has field "Path"; cannot choose')

        if response_type is not None and response_type not in self.response_types:
            raise ValueError('Invaled param "response_type"')

        path = getattr(module, 'Path', None) if path is None else path
        self.cgi_modules.append({
            'module': module,
            'path': '/' if path is None else path,
            'type': 'base' if response_type is None else response_type,
        })

    def add_middleware(self, target=None, post=None):
        """
            Middleware will be called before calling site_module
            There will be passed 2 arguments:
                req - request object
                module - site_module, that will be called after middleware
            If site_module was not found or does not support method? the middlewaver will not be called
            all return values will be ignored
            If you registrate severals middlewares, they will be called order

            post is same as middleware but will be called
        """
        if not target and not post:
            raise ValueError('Expected "target" or "post"')
        if target and not callable(target):
            raise ValueError('middleware "{}" must be callable'.format(str(target)))
        elif post and not callable(post):
            raise ValueError('middleware "{}" must be callable'.format(str(post)))
        else:
            self.middleware.append((target, post))

    def start(self):
        """
            start web-server
        """
        self._th = th.Thread(target=self._loop)
        self._th.start()

    def stop(self, wait=True):
        """
            stop web-server
        """
        self._run = False
        self._open()
        if wait and self._th is not None:
            self._th.join()
